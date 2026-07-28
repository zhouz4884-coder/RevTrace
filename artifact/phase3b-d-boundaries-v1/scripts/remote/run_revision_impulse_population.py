#!/usr/bin/env python3
"""Search legal execution-shape flips and measure their future state response.

The search uses replicated FP16 batches only; it never injects logit noise or
edits a decoded token.  A pair is counted once per distinct
(revision, canonical state, divergent state) tuple, so repeated slots cannot
inflate the population gate.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
from qwen_asr import Qwen3ASRModel
from vllm import SamplingParams

from revtrace.amplification import (
    RevisionImpulsePair,
    summarize_impulses,
    token_edit_distance,
)
from run_revbatch_gate import (
    SAMPLE_RATE,
    apply_output,
    cycle_audio,
    load_sources,
    make_streams,
    official_smoke,
    prepare_job,
    read_audio,
    rollback_prefix,
)
from run_revguard_same_input import candidate_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--target-pairs", type=int, default=50)
    parser.add_argument("--search-margin", type=float, default=0.5)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--natural-flip-rate", type=float, required=True)
    parser.add_argument("--audio-stress", action="store_true")
    parser.add_argument("--stress-seed", type=int, default=20260730)
    parser.add_argument(
        "--language-mode",
        choices=("bilingual", "English", "Chinese"),
        default="bilingual",
    )
    return parser.parse_args()


def state_tokens(asr: Any, state: Any, *, terminal: bool) -> list[int]:
    text = (
        state._raw_decoded
        if terminal
        else rollback_prefix(asr, state, tail=False)
    )
    return [
        int(token) for token in asr.processor.tokenizer.encode(text)
    ]


def state_digest(tokens: list[int]) -> str:
    payload = ",".join(str(token) for token in tokens).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def follow_pair(
    *,
    asr: Any,
    stream: dict[str, Any],
    canonical_state: Any,
    divergent_state: Any,
    start_chunk: int,
    rounds: int,
    chunk_samples: int,
) -> tuple[list[float], list[dict[str, Any]]]:
    canonical_tokens = state_tokens(
        asr, canonical_state, terminal=start_chunk == rounds - 1
    )
    divergent_tokens = state_tokens(
        asr, divergent_state, terminal=start_chunk == rounds - 1
    )
    distances = [
        float(token_edit_distance(canonical_tokens, divergent_tokens))
    ]
    trajectory = [
        {
            "offset": 0,
            "chunk_index": start_chunk,
            "distance": distances[0],
            "canonical_state_sha256": state_digest(canonical_tokens),
            "divergent_state_sha256": state_digest(divergent_tokens),
            "canonical_state_token_ids": canonical_tokens,
            "divergent_state_token_ids": divergent_tokens,
        }
    ]
    for chunk_index in range(start_chunk + 1, rounds):
        terminal = chunk_index == rounds - 1
        begin = chunk_index * chunk_samples
        end = begin + chunk_samples
        audio = stream["audio"][begin:end]
        for state in (canonical_state, divergent_state):
            job, prefix = prepare_job(asr, state, audio, tail=terminal)
            output = asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
            apply_output(state, output, prefix)
        canonical_tokens = state_tokens(
            asr, canonical_state, terminal=terminal
        )
        divergent_tokens = state_tokens(
            asr, divergent_state, terminal=terminal
        )
        distances.append(
            float(
                token_edit_distance(
                    canonical_tokens, divergent_tokens
                )
            )
        )
        trajectory.append(
            {
                "offset": chunk_index - start_chunk,
                "chunk_index": chunk_index,
                "distance": distances[-1],
                "canonical_state_sha256": state_digest(
                    canonical_tokens
                ),
                "divergent_state_sha256": state_digest(
                    divergent_tokens
                ),
                "canonical_state_token_ids": canonical_tokens,
                "divergent_state_token_ids": divergent_tokens,
            }
        )
    return distances, trajectory


def main() -> int:
    args = parse_args()
    if args.target_pairs < 1 or args.repeats < 1:
        raise ValueError("target pairs and repeats must be positive")
    if args.language_mode == "bilingual":
        sources = load_sources(args.data_manifest)
    else:
        manifest = json.loads(
            args.data_manifest.read_text(encoding="utf-8")
        )
        selected = [
            read_audio(Path(record["path"]))
            for record in manifest["records"]
            if record["language"] == args.language_mode
        ]
        if not selected:
            raise RuntimeError(
                f"no sources for language mode {args.language_mode}"
            )
        sources = {"English": [], "Chinese": []}
        sources[args.language_mode] = selected
    if args.language_mode == "bilingual":
        streams = make_streams(
            sources,
            duration=args.duration_seconds,
            concurrency=args.concurrency,
        )
    else:
        candidates = sources[args.language_mode]
        streams = [
            {
                "session_id": f"s{index:03d}",
                "language": args.language_mode,
                "audio": cycle_audio(
                    candidates[index % len(candidates)],
                    args.duration_seconds,
                    offset=0,
                ),
            }
            for index in range(args.concurrency)
        ]
    stress_records = []
    if args.audio_stress:
        rng = np.random.default_rng(args.stress_seed)
        snr_values = (6.0, 10.0, 14.0, 18.0, 22.0, 26.0)
        for index, stream in enumerate(streams):
            clean = np.asarray(stream["audio"], dtype=np.float32)
            rms = float(np.sqrt(np.mean(clean.astype(np.float64) ** 2)))
            snr_db = snr_values[index % len(snr_values)]
            noise_rms = max(rms, 1e-6) / (10.0 ** (snr_db / 20.0))
            noise = rng.normal(
                0.0, noise_rms, size=clean.shape
            ).astype(np.float32)
            stressed = np.clip(clean + noise, -1.0, 1.0)
            stream["audio"] = stressed
            stream["session_id"] = (
                f"{stream['session_id']}-snr{int(snr_db):02d}"
            )
            stress_records.append(
                {
                    "session_id": stream["session_id"],
                    "snr_db": snr_db,
                    "noise_rms": noise_rms,
                }
            )
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
    states = [
        asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=2.0,
        )
        for stream in streams
    ]
    chunk_samples = 2 * SAMPLE_RATE
    rounds = min(
        stream["audio"].shape[0] // chunk_samples
        for stream in streams
    )
    pairs: list[RevisionImpulsePair] = []
    pair_records: list[dict[str, Any]] = []
    signatures: set[tuple[Any, ...]] = set()
    search = {
        "candidate_revisions": 0,
        "replicated_rows": 0,
        "output_flips": 0,
        "absorbed_output_flips": 0,
        "duplicate_state_pairs": 0,
        "distinct_state_pairs": 0,
    }
    started = time.perf_counter()
    for chunk_index in range(rounds):
        terminal = chunk_index == rounds - 1
        jobs: list[dict[str, Any]] = []
        prefixes: list[str] = []
        snapshots: list[Any] = []
        canonical_outputs: list[Any] = []
        canonical_records: list[dict[str, Any]] = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=terminal,
            )
            jobs.append(job)
            prefixes.append(prefix)
            snapshots.append(copy.deepcopy(state))
            output = asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
            canonical_outputs.append(output)
            canonical_records.append(candidate_record(output))

        if not terminal:
            ranked = sorted(
                range(len(streams)),
                key=lambda index: (
                    canonical_records[index]["minimum_margin"]
                    if canonical_records[index]["minimum_margin"]
                    is not None
                    else float("-inf"),
                    streams[index]["session_id"],
                ),
            )
            for index in ranked:
                margin = canonical_records[index]["minimum_margin"]
                if margin is not None and margin > args.search_margin:
                    continue
                search["candidate_revisions"] += 1
                canonical_state = copy.deepcopy(snapshots[index])
                apply_output(
                    canonical_state,
                    canonical_outputs[index],
                    prefixes[index],
                )
                canonical_tokens = state_tokens(
                    asr, canonical_state, terminal=False
                )
                for repeat in range(args.repeats):
                    outputs = asr.model.generate(
                        [jobs[index]] * args.batch_size,
                        sampling_params=asr.sampling_params,
                        use_tqdm=False,
                    )
                    search["replicated_rows"] += len(outputs)
                    for slot, output in enumerate(outputs):
                        divergent_record = candidate_record(output)
                        if (
                            divergent_record["token_ids"]
                            == canonical_records[index]["token_ids"]
                        ):
                            continue
                        search["output_flips"] += 1
                        divergent_state = copy.deepcopy(
                            snapshots[index]
                        )
                        apply_output(
                            divergent_state,
                            output,
                            prefixes[index],
                        )
                        divergent_tokens = state_tokens(
                            asr, divergent_state, terminal=False
                        )
                        initial_distance = token_edit_distance(
                            canonical_tokens, divergent_tokens
                        )
                        if initial_distance == 0:
                            search["absorbed_output_flips"] += 1
                            continue
                        signature = (
                            streams[index]["session_id"],
                            chunk_index,
                            tuple(canonical_tokens),
                            tuple(divergent_tokens),
                        )
                        if signature in signatures:
                            search["duplicate_state_pairs"] += 1
                            continue
                        signatures.add(signature)
                        distances, trajectory = follow_pair(
                            asr=asr,
                            stream=streams[index],
                            canonical_state=copy.deepcopy(
                                canonical_state
                            ),
                            divergent_state=divergent_state,
                            start_chunk=chunk_index,
                            rounds=rounds,
                            chunk_samples=chunk_samples,
                        )
                        pair_id = (
                            f"{args.model_name}:"
                            f"{streams[index]['session_id']}:"
                            f"{chunk_index}:b{args.batch_size}:"
                            f"r{repeat}:s{slot}:"
                            f"{state_digest(divergent_tokens)[:12]}"
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
                                "session_id": streams[index][
                                    "session_id"
                                ],
                                "language": streams[index]["language"],
                                "chunk_index": chunk_index,
                                "batch_size": args.batch_size,
                                "repeat": repeat,
                                "slot": slot,
                                "canonical_minimum_margin": margin,
                                "canonical_token_ids": (
                                    canonical_records[index]["token_ids"]
                                ),
                                "divergent_token_ids": (
                                    divergent_record["token_ids"]
                                ),
                                "trajectory": trajectory,
                            }
                        )
                        search["distinct_state_pairs"] += 1
                        if len(pairs) >= args.target_pairs:
                            break
                    if len(pairs) >= args.target_pairs:
                        break
                if len(pairs) >= args.target_pairs:
                    break

        for state, output, prefix in zip(
            states, canonical_outputs, prefixes
        ):
            apply_output(state, output, prefix)
        if len(pairs) >= args.target_pairs:
            break

    summary = (
        summarize_impulses(
            pairs, flip_rate=args.natural_flip_rate
        ).to_dict()
        if pairs
        else None
    )
    passed = len(pairs) >= args.target_pairs
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 3C Revision Impulse population gate",
        "decision": (
            "PHASE3C_RIR_POPULATION_PASS"
            if passed
            else "PHASE3C_RIR_POPULATION_INSUFFICIENT_DISTINCT_PAIRS"
        ),
        "model": args.model_name,
        "dtype": args.dtype,
        "config": {
            "duration_seconds": args.duration_seconds,
            "concurrency": args.concurrency,
            "batch_size": args.batch_size,
            "repeats": args.repeats,
            "target_pairs": args.target_pairs,
            "search_margin": args.search_margin,
            "natural_flip_rate": args.natural_flip_rate,
            "audio_stress": args.audio_stress,
            "stress_seed": args.stress_seed,
            "language_mode": args.language_mode,
        },
        "audio_stress_records": stress_records,
        "search": search,
        "summary": summary,
        "pairs": pair_records,
        "official_semantics_smoke": smoke,
        "elapsed_seconds": time.perf_counter() - started,
        "environment": {"python": platform.python_version()},
        "claim_boundaries": {
            "population": (
                "pairs are deduplicated by revision and state-token pair"
            ),
            "stress": (
                "replicated execution-shape search is a legal numerical "
                "stress test; optional waveform noise is applied before "
                "both pair branches and is not a production flip-rate estimate"
            ),
            "future": (
                "both branches use identical future audio and canonical "
                "singleton execution"
            ),
            "half_life": (
                "no observed recovery is reported as right-censored"
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
                "summary": summary,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
