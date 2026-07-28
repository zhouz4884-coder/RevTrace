#!/usr/bin/env python3
"""Diversity-aware active mining of consequential revision state pairs.

Every candidate comes from a distinct LibriSpeech file.  A canonical FP16
singleton establishes the parent state and candidate output.  Candidates are
ranked once, then receive at most one legal replicated-batch probe.  No logits,
tokens, or model state are modified to manufacture a flip.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from qwen_asr import Qwen3ASRModel
from vllm import SamplingParams

from revtrace.amplification import (
    RevisionImpulsePair,
    summarize_contamination_tail,
    summarize_impulses,
    token_edit_distance,
)
from revtrace.mining import (
    MiningFeatures,
    acoustic_uncertainty,
    active_mining_score,
)
from run_revbatch_gate import (
    SAMPLE_RATE,
    apply_output,
    cycle_audio,
    official_smoke,
    prepare_job,
    read_audio,
)
from run_revguard_same_input import candidate_record
from run_revision_impulse_population import (
    follow_pair,
    state_digest,
    state_tokens,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-budget", type=int, default=500)
    parser.add_argument("--target-pairs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--future-rounds", type=int, default=4)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def pair_signature(
    parent_tokens: list[int],
    canonical_output: list[int],
    divergent_output: list[int],
    canonical_state: list[int],
    divergent_state: list[int],
) -> str:
    payload = [
        parent_tokens,
        canonical_output,
        divergent_output,
        canonical_state,
        divergent_state,
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = manifest["records"][: args.candidate_budget]
    if len(records) < args.candidate_budget:
        raise RuntimeError(
            f"manifest has {len(records)} records, expected "
            f"{args.candidate_budget}"
        )
    duration_seconds = 4 + 2 * args.future_rounds
    streams = [
        {
            "session_id": f"active-{index:04d}",
            "language": record.get("language", "English"),
            "source": record["path"],
            "audio": cycle_audio(
                read_audio(Path(record["path"])),
                duration_seconds,
                offset=0,
            ),
        }
        for index, record in enumerate(records)
    ]
    sources = {
        "English": [streams[0]["audio"]],
        "Chinese": [],
    }
    asr = Qwen3ASRModel.LLM(
        model=str(args.model),
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_inference_batch_size=max(128, args.batch_size),
        max_new_tokens=32,
        enforce_eager=True,
        max_num_seqs=max(128, args.batch_size),
        mm_processor_cache_gb=0,
        async_scheduling=False,
        enable_prefix_caching=False,
        dtype=args.dtype,
    )
    asr.sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=20,
    )
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("official-semantics smoke failed")

    chunk_samples = 2 * SAMPLE_RATE
    canonical_counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, stream in enumerate(streams):
        state = asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=2.0,
        )
        first_job, first_prefix = prepare_job(
            asr, state, stream["audio"][:chunk_samples], tail=False
        )
        first_output = asr.model.generate(
            [first_job],
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )[0]
        apply_output(state, first_output, first_prefix)
        parent_tokens = state_tokens(asr, state, terminal=False)
        parent_snapshot = copy.deepcopy(state)
        second_job, second_prefix = prepare_job(
            asr,
            state,
            stream["audio"][chunk_samples : 2 * chunk_samples],
            tail=False,
        )
        canonical_output = asr.model.generate(
            [second_job],
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )[0]
        record = candidate_record(canonical_output)
        canonical_state = copy.deepcopy(parent_snapshot)
        apply_output(canonical_state, canonical_output, second_prefix)
        canonical_tokens = state_tokens(
            asr, canonical_state, terminal=False
        )
        canonical_key = state_digest(canonical_tokens)
        finite = [
            (position, value)
            for position, value in enumerate(record["margins"])
            if value is not None
        ]
        if finite:
            margin_position, minimum_margin = min(
                finite, key=lambda item: item[1]
            )
        else:
            margin_position, minimum_margin = 0, float("inf")
        probe_audio = stream["audio"][
            chunk_samples : 2 * chunk_samples
        ]
        flatness, crossings = acoustic_uncertainty(probe_audio)
        features = MiningFeatures(
            minimum_margin=float(minimum_margin),
            minimum_margin_position=min(
                margin_position, max(0, len(record["token_ids"]) - 1)
            ),
            output_length=max(1, len(record["token_ids"])),
            spectral_flatness=flatness,
            zero_crossing_rate=crossings,
            canonical_signature_count=canonical_counts[canonical_key],
        )
        canonical_counts[canonical_key] += 1
        score = (
            active_mining_score(features)
            if np.isfinite(minimum_margin)
            else float("-inf")
        )
        candidates.append(
            {
                "candidate_index": index,
                "stream": stream,
                "parent_snapshot": parent_snapshot,
                "parent_tokens": parent_tokens,
                "job": second_job,
                "prefix": second_prefix,
                "canonical_output": canonical_output,
                "canonical_record": record,
                "canonical_state": canonical_state,
                "canonical_tokens": canonical_tokens,
                "features": features,
                "score": score,
            }
        )
        if (index + 1) % 25 == 0:
            print(
                json.dumps(
                    {
                        "stage": "screen",
                        "model": args.model_name,
                        "candidates": index + 1,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    candidates.sort(
        key=lambda item: (-item["score"], item["candidate_index"])
    )
    signatures: set[str] = set()
    pairs: list[RevisionImpulsePair] = []
    pair_records: list[dict[str, Any]] = []
    search = {
        "independent_candidates_screened": len(candidates),
        "candidates_probed": 0,
        "replicated_rows": 0,
        "output_flips": 0,
        "absorbed_output_flips": 0,
        "duplicate_pair_early_stops": 0,
        "distinct_state_pairs": 0,
    }
    for rank, candidate in enumerate(candidates, start=1):
        if len(pairs) >= args.target_pairs:
            break
        outputs = asr.model.generate(
            [candidate["job"]] * args.batch_size,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        search["candidates_probed"] += 1
        search["replicated_rows"] += len(outputs)
        for slot, output in enumerate(outputs):
            divergent_record = candidate_record(output)
            if (
                divergent_record["token_ids"]
                == candidate["canonical_record"]["token_ids"]
            ):
                continue
            search["output_flips"] += 1
            divergent_state = copy.deepcopy(
                candidate["parent_snapshot"]
            )
            apply_output(
                divergent_state, output, candidate["prefix"]
            )
            divergent_tokens = state_tokens(
                asr, divergent_state, terminal=False
            )
            initial_distance = token_edit_distance(
                candidate["canonical_tokens"], divergent_tokens
            )
            if initial_distance == 0:
                search["absorbed_output_flips"] += 1
                continue
            signature = pair_signature(
                candidate["parent_tokens"],
                candidate["canonical_record"]["token_ids"],
                divergent_record["token_ids"],
                candidate["canonical_tokens"],
                divergent_tokens,
            )
            if signature in signatures:
                search["duplicate_pair_early_stops"] += 1
                break
            signatures.add(signature)
            rounds = 2 + args.future_rounds
            distances, trajectory = follow_pair(
                asr=asr,
                stream=candidate["stream"],
                canonical_state=copy.deepcopy(
                    candidate["canonical_state"]
                ),
                divergent_state=divergent_state,
                start_chunk=1,
                rounds=rounds,
                chunk_samples=chunk_samples,
            )
            pair_id = (
                f"{args.model_name}:active:"
                f"{candidate['candidate_index']}:b{args.batch_size}:"
                f"s{slot}:{signature[:12]}"
            )
            pair = RevisionImpulsePair(
                pair_id=pair_id,
                distances=tuple(distances),
                terminal_different=distances[-1] > 0,
            )
            pairs.append(pair)
            pair_records.append(
                {
                    "pair_id": pair_id,
                    "signature": signature,
                    "candidate_index": candidate["candidate_index"],
                    "rank": rank,
                    "source": candidate["stream"]["source"],
                    "batch_size": args.batch_size,
                    "slot": slot,
                    "score": candidate["score"],
                    "features": {
                        key: value
                        for key, value in vars(candidate["features"]).items()
                    },
                    "canonical_output_token_ids": (
                        candidate["canonical_record"]["token_ids"]
                    ),
                    "divergent_output_token_ids": (
                        divergent_record["token_ids"]
                    ),
                    "trajectory": trajectory,
                }
            )
            search["distinct_state_pairs"] += 1
            break
        if rank % 25 == 0 or len(pairs) >= args.target_pairs:
            print(
                json.dumps(
                    {
                        "stage": "probe",
                        "model": args.model_name,
                        "probed": search["candidates_probed"],
                        "pairs": len(pairs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    exhausted = (
        search["candidates_probed"] == args.candidate_budget
        and len(pairs) < args.target_pairs
    )
    payload = {
        "schema_version": 1,
        "study": (
            "RevTrace Phase 4D diversity-aware active state-pair mining"
        ),
        "decision": (
            "PHASE4D_ACTIVE_MINING_TARGET_PASS"
            if len(pairs) >= args.target_pairs
            else "PHASE4D_ACTIVE_MINING_BUDGET_EXHAUSTED"
            if exhausted
            else "PHASE4D_ACTIVE_MINING_INCOMPLETE"
        ),
        "model": args.model_name,
        "dtype": args.dtype,
        "config": {
            "candidate_budget": args.candidate_budget,
            "target_pairs": args.target_pairs,
            "batch_size": args.batch_size,
            "future_rounds": args.future_rounds,
        },
        "search": search,
        "impulse_summary": (
            summarize_impulses(
                pairs,
                flip_rate=(
                    len(pairs) / search["candidates_probed"]
                    if search["candidates_probed"]
                    else 0.0
                ),
            ).to_dict()
            if pairs
            else None
        ),
        "contamination_tail": (
            summarize_contamination_tail(
                pairs, horizon=args.future_rounds
            ).to_dict()
            if pairs
            else None
        ),
        "pairs": pair_records,
        "official_semantics_smoke": smoke,
        "elapsed_seconds": time.perf_counter() - started,
        "environment": {"python": platform.python_version()},
        "claim_boundaries": {
            "population": (
                "targeted mechanism population; pair yield is not a "
                "production prevalence estimate"
            ),
            "causality": (
                "both pair branches receive identical future audio and "
                "canonical singleton execution"
            ),
            "intervention": (
                "only legal execution shape changes; no logit, token, or "
                "state noise is injected"
            ),
            "budget": (
                "each independent candidate receives at most one replicated "
                "batch probe"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "search": search,
                "tail": payload["contamination_tail"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
