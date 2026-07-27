#!/usr/bin/env python3
"""Probe fixed-shape invariance for multimodal revision generation.

The probe keeps batch size fixed while varying repeat execution, request slot,
batch permutation, and co-runner composition.  It deliberately does not claim
singleton equivalence: it tests whether a fixed-shape execution can serve as a
versioned canonical path.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any

from qwen_asr import Qwen3ASRModel
from vllm import SamplingParams

from run_revbatch_gate import (
    SAMPLE_RATE,
    apply_output,
    load_sources,
    make_streams,
    official_smoke,
    prepare_job,
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
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def record(output: Any) -> dict[str, Any]:
    item = candidate_record(output)
    return {
        "token_ids": item["token_ids"],
        "text": item["text"],
    }


def exact(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["token_ids"] == right["token_ids"]


def main() -> int:
    args = parse_args()
    if args.concurrency < 2:
        raise ValueError("fixed-shape probe requires concurrency >= 2")

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
        max_model_len=args.max_model_len,
    )
    asr.sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=None,
    )
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("official-semantics smoke failed")
    streams = make_streams(
        sources,
        duration=args.duration_seconds,
        concurrency=args.concurrency,
    )
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
    step = args.concurrency - 1
    while math.gcd(step, args.concurrency) != 1:
        step -= 1
    permutation = [
        (index * step + 3) % args.concurrency
        for index in range(args.concurrency)
    ]

    repeat_mismatches = 0
    permutation_mismatches = 0
    replicated_internal_mismatches = 0
    composition_mismatches = 0
    batch_seconds = {
        "base_a": 0.0,
        "base_b": 0.0,
        "permuted": 0.0,
        "replicated": 0.0,
    }
    chunk_records: list[dict[str, Any]] = []
    for chunk_index in range(rounds):
        jobs: list[dict[str, Any]] = []
        prefixes: list[str] = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=False,
            )
            jobs.append(job)
            prefixes.append(prefix)

        outputs_by_name: dict[str, list[Any]] = {}
        for name, selected_jobs in (
            ("base_a", jobs),
            ("base_b", jobs),
            ("permuted", [jobs[index] for index in permutation]),
        ):
            started = time.perf_counter()
            outputs_by_name[name] = asr.model.generate(
                selected_jobs,
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            batch_seconds[name] += time.perf_counter() - started

        target = chunk_index % args.concurrency
        started = time.perf_counter()
        replicated_outputs = asr.model.generate(
            [jobs[target] for _ in range(args.concurrency)],
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        batch_seconds["replicated"] += time.perf_counter() - started

        base_records = [record(output) for output in outputs_by_name["base_a"]]
        repeat_records = [record(output) for output in outputs_by_name["base_b"]]
        permuted_records = [
            record(output) for output in outputs_by_name["permuted"]
        ]
        restored_permuted: list[dict[str, Any] | None] = [
            None for _ in range(args.concurrency)
        ]
        for output_position, source_position in enumerate(permutation):
            restored_permuted[source_position] = permuted_records[output_position]
        replicated_records = [record(output) for output in replicated_outputs]

        chunk_repeat = sum(
            not exact(left, right)
            for left, right in zip(base_records, repeat_records)
        )
        chunk_permutation = sum(
            not exact(base_records[index], restored_permuted[index])
            for index in range(args.concurrency)
        )
        reference_replica = replicated_records[0]
        chunk_replication = sum(
            not exact(reference_replica, item)
            for item in replicated_records[1:]
        )
        chunk_composition = int(
            not exact(base_records[target], reference_replica)
        )
        repeat_mismatches += chunk_repeat
        permutation_mismatches += chunk_permutation
        replicated_internal_mismatches += chunk_replication
        composition_mismatches += chunk_composition
        chunk_records.append(
            {
                "chunk_id": chunk_index,
                "target_session": streams[target]["session_id"],
                "repeat_mismatches": chunk_repeat,
                "permutation_mismatches": chunk_permutation,
                "replicated_internal_mismatches": chunk_replication,
                "composition_mismatch": chunk_composition,
            }
        )

        for state, output, prefix in zip(states, outputs_by_name["base_a"], prefixes):
            apply_output(state, output, prefix)
        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "chunk": chunk_index,
                    "events": (chunk_index + 1) * args.concurrency,
                    "mismatches": {
                        "repeat": repeat_mismatches,
                        "permutation": permutation_mismatches,
                        "replication": replicated_internal_mismatches,
                        "composition": composition_mismatches,
                    },
                },
                sort_keys=True,
            ),
            flush=True,
        )

    invariant = (
        repeat_mismatches == 0
        and permutation_mismatches == 0
        and replicated_internal_mismatches == 0
        and composition_mismatches == 0
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace fixed-shape multimodal invariance",
        "decision": (
            "FIXED_SHAPE_CANONICAL_GATE_PASS"
            if invariant
            else "FIXED_SHAPE_CANONICAL_GATE_FAIL"
        ),
        "model_name": args.model_name,
        "dtype": args.dtype,
        "batch_size": args.concurrency,
        "event_count": rounds * args.concurrency,
        "summary": {
            "repeat_mismatches": repeat_mismatches,
            "permutation_mismatches": permutation_mismatches,
            "replicated_internal_mismatches": (
                replicated_internal_mismatches
            ),
            "composition_mismatches": composition_mismatches,
            "batch_seconds": batch_seconds,
        },
        "contract": {
            "scope": "fixed batch size and frozen runtime version",
            "singleton_equivalence": "not claimed",
            "logprobs": "disabled to isolate greedy execution",
        },
        "environment": {
            "python": platform.python_version(),
            "vllm_batch_invariant": os.getenv("VLLM_BATCH_INVARIANT"),
            "vllm_attention_backend": os.getenv("VLLM_ATTENTION_BACKEND"),
        },
        "smoke": smoke,
        "chunks": chunk_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], **payload["summary"]}))
    return 0 if invariant else 2


if __name__ == "__main__":
    raise SystemExit(main())
