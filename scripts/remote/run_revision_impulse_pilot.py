#!/usr/bin/env python3
"""Follow one legal execution-shape flip under identical future audio."""

from __future__ import annotations

import argparse
import copy
import json
import platform
from pathlib import Path
from typing import Any

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
    load_sources,
    make_streams,
    official_smoke,
    prepare_job,
    rollback_prefix,
)
from run_revguard_same_input import candidate_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-session", required=True)
    parser.add_argument("--target-chunk", type=int, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--natural-flip-rate", type=float, required=True)
    return parser.parse_args()


def state_tokens(asr: Any, state: Any, *, terminal: bool) -> list[int]:
    text = (
        state._raw_decoded
        if terminal
        else rollback_prefix(asr, state, tail=False)
    )
    return [int(token) for token in asr.processor.tokenizer.encode(text)]


def main() -> int:
    args = parse_args()
    sources = load_sources(args.data_manifest)
    streams = make_streams(
        sources,
        duration=args.duration_seconds,
        concurrency=args.concurrency,
    )
    target_index = next(
        (
            index
            for index, stream in enumerate(streams)
            if stream["session_id"] == args.target_session
        ),
        None,
    )
    if target_index is None:
        raise ValueError("target session is absent from frozen workload")

    asr = Qwen3ASRModel.LLM(
        model=str(args.model),
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_inference_batch_size=128,
        max_new_tokens=32,
        enforce_eager=True,
        max_num_seqs=128,
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
        stream["audio"].shape[0] // chunk_samples for stream in streams
    )
    target_job = None
    target_prefix = None
    for chunk_index in range(args.target_chunk + 1):
        jobs = []
        prefixes = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=chunk_index == rounds - 1,
            )
            jobs.append(job)
            prefixes.append(prefix)
        if chunk_index == args.target_chunk:
            target_job = jobs[target_index]
            target_prefix = prefixes[target_index]
            break
        for state, prefix, job in zip(states, prefixes, jobs):
            output = asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
            apply_output(state, output, prefix)
    if target_job is None or target_prefix is None:
        raise AssertionError("failed to reconstruct target revision")

    canonical_output = asr.model.generate(
        [target_job],
        sampling_params=asr.sampling_params,
        use_tqdm=False,
    )[0]
    canonical = candidate_record(canonical_output)
    divergent_output = None
    divergent = None
    attempts = 0
    for _ in range(args.repeats):
        outputs = asr.model.generate(
            [target_job] * args.batch_size,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        attempts += len(outputs)
        for output in outputs:
            record = candidate_record(output)
            if record["token_ids"] != canonical["token_ids"]:
                divergent_output = output
                divergent = record
                break
        if divergent_output is not None:
            break
    if divergent_output is None or divergent is None:
        raise RuntimeError("no legal execution-shape flip was reproduced")

    canonical_state = copy.deepcopy(states[target_index])
    divergent_state = copy.deepcopy(states[target_index])
    apply_output(canonical_state, canonical_output, target_prefix)
    apply_output(divergent_state, divergent_output, target_prefix)
    target_stream = streams[target_index]
    terminal = args.target_chunk == rounds - 1
    canonical_tokens = state_tokens(
        asr, canonical_state, terminal=terminal
    )
    divergent_tokens = state_tokens(
        asr, divergent_state, terminal=terminal
    )
    distances = [
        float(token_edit_distance(canonical_tokens, divergent_tokens))
    ]
    trajectory = [
        {
            "offset": 0,
            "chunk_index": args.target_chunk,
            "distance": distances[-1],
            "canonical_state_token_ids": canonical_tokens,
            "divergent_state_token_ids": divergent_tokens,
        }
    ]
    if distances[0] == 0:
        payload = {
            "schema_version": 1,
            "study": (
                "RevTrace fixed-future canonical Revision Impulse pilot"
            ),
            "decision": "RIR_PILOT_NO_STATE_IMPULSE",
            "model": args.model_name,
            "dtype": args.dtype,
            "target": {
                "session_id": args.target_session,
                "chunk_index": args.target_chunk,
                "canonical": canonical,
                "divergent": divergent,
                "execution_shape_attempts": attempts,
            },
            "trajectory": trajectory,
            "summary": {
                "pairs": 1,
                "initial_distance": 0.0,
                "interpretation": (
                    "the legal output flip was absorbed by the official "
                    "state projection, so no revision-state impulse exists"
                ),
            },
            "official_semantics_smoke": smoke,
            "environment": {"python": platform.python_version()},
            "claim_boundaries": {
                "sample_size": (
                    "one pilot pair; not the Phase 3C population gate"
                ),
                "state_projection": (
                    "an output mismatch is not an impulse when D(0)=0"
                ),
                "frequency": (
                    "the execution-shape search is a stress test and is "
                    "not a production mismatch-rate estimate"
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
        print(json.dumps(payload["summary"], sort_keys=True))
        return 2
    for chunk_index in range(args.target_chunk + 1, rounds):
        terminal = chunk_index == rounds - 1
        begin = chunk_index * chunk_samples
        end = begin + chunk_samples
        future_audio = target_stream["audio"][begin:end]
        for state in (canonical_state, divergent_state):
            job, prefix = prepare_job(
                asr, state, future_audio, tail=terminal
            )
            output = asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
            apply_output(state, output, prefix)
        left = state_tokens(asr, canonical_state, terminal=terminal)
        right = state_tokens(asr, divergent_state, terminal=terminal)
        distances.append(float(token_edit_distance(left, right)))
        trajectory.append(
            {
                "offset": chunk_index - args.target_chunk,
                "chunk_index": chunk_index,
                "distance": distances[-1],
                "canonical_state_token_ids": left,
                "divergent_state_token_ids": right,
            }
        )
    pair = RevisionImpulsePair(
        pair_id=(
            f"{args.model_name}:{args.target_session}:"
            f"{args.target_chunk}"
        ),
        distances=tuple(distances),
        terminal_different=distances[-1] > 0,
    )
    summary = summarize_impulses(
        [pair], flip_rate=args.natural_flip_rate
    )
    decision = (
        "RIR_PILOT_PASS"
        if distances[0] > 0
        else "RIR_PILOT_FAIL"
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace fixed-future canonical Revision Impulse pilot",
        "decision": decision,
        "model": args.model_name,
        "dtype": args.dtype,
        "target": {
            "session_id": args.target_session,
            "chunk_index": args.target_chunk,
            "canonical": canonical,
            "divergent": divergent,
            "execution_shape_attempts": attempts,
        },
        "trajectory": trajectory,
        "summary": summary.to_dict(),
        "official_semantics_smoke": smoke,
        "environment": {"python": platform.python_version()},
        "claim_boundaries": {
            "sample_size": "one pilot pair; not the Phase 3C population gate",
            "future_control": (
                "future audio and canonical singleton executor are identical"
            ),
            "half_life": (
                "no recovery within the finite horizon is right-censored, "
                "never reported as infinite"
            ),
            "frequency": (
                "natural flip-rate input is external frozen evidence; the "
                "execution-shape search is a stress test"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **payload["summary"]}))
    return 0 if decision.endswith("_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
