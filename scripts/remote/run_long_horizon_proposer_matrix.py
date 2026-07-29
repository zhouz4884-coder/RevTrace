#!/usr/bin/env python3
"""Natural-audio proposer-only lower bound and age-concurrency matrix.

Every measured transition follows the official growing-audio and rollback
state update. Repeated frozen-job executions are excluded from the logical
service latency and are used only to expose execution variance.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--experiment-id",
        default="revtrace-proposer-lower-bound",
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", default="1,4,8,12")
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--chunk-seconds", type=int, default=2)
    parser.add_argument("--frozen-job-repetitions", type=int, default=3)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_bucket(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(row["logical_service_seconds"]) for row in rows]
    proposer = [float(row["proposer_seconds"]) for row in rows]
    frozen = [
        value
        for row in rows
        for value in row["frozen_job_execution_seconds"]
    ]
    return {
        "rounds": len(rows),
        "prepare_seconds_mean": statistics.mean(
            float(row["prepare_seconds"]) for row in rows
        ),
        "proposer_seconds_mean": statistics.mean(proposer),
        "proposer_seconds_p99": percentile(proposer, 0.99),
        "projection_apply_seconds_mean": statistics.mean(
            float(row["projection_apply_seconds"]) for row in rows
        ),
        "logical_service_seconds_p50": percentile(latencies, 0.50),
        "logical_service_seconds_p95": percentile(latencies, 0.95),
        "logical_service_seconds_p99": percentile(latencies, 0.99),
        "deadline_miss_rounds": sum(value > 2.0 for value in latencies),
        "frozen_job_execution_seconds_median": (
            statistics.median(frozen) if frozen else None
        ),
        "maximum_audio_samples": max(
            int(row["maximum_accumulated_audio_samples"]) for row in rows
        ),
        "maximum_prefix_tokens": max(
            int(row["maximum_prefix_token_count"]) for row in rows
        ),
        "maximum_model_input_tokens": max(
            (
                int(row["maximum_model_input_token_count"])
                for row in rows
                if row["maximum_model_input_token_count"] is not None
            ),
            default=None,
        ),
    }


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.chunk_seconds:
        raise ValueError("duration must be divisible by chunk size")
    concurrencies = [int(item) for item in args.concurrency.split(",")]
    if not concurrencies or min(concurrencies) < 1:
        raise ValueError("concurrency values must be positive")
    if args.frozen_job_repetitions < 1:
        raise ValueError("at least one frozen-job repetition is required")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    for path in (script_dir, source_dir):
        if path not in sys.path:
            sys.path.insert(0, path)

    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        load_sources,
        prepare_job,
    )
    from run_revguard_same_input import candidate_record
    from run_revtrace_dual_gpu import build_asr
    from revtrace.long_horizon import concatenate_distinct_audio

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    asr = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=4096,
        max_num_seqs=max(concurrencies),
    )
    sources = load_sources(args.data_manifest)
    silence_samples = args.silence_ms * SAMPLE_RATE // 1000

    def make_streams(concurrency: int) -> list[dict[str, Any]]:
        streams = []
        for position in range(concurrency):
            language = (
                "English"
                if concurrency == 1 or position % 2 == 0
                else "Chinese"
            )
            audio, provenance = concatenate_distinct_audio(
                sources[language],
                target_samples=args.duration_seconds * SAMPLE_RATE,
                start_index=(position * 17) % len(sources[language]),
                silence_samples=silence_samples,
            )
            streams.append(
                {
                    "session_id": f"c{concurrency:02d}-s{position:03d}",
                    "language": language,
                    "audio": audio,
                    "audio_provenance": provenance,
                }
            )
        return streams

    cells = []
    all_rounds: list[dict[str, Any]] = []
    for concurrency in concurrencies:
        streams = make_streams(concurrency)
        states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=float(args.chunk_seconds),
            )
            for stream in streams
        ]
        # Shape initialization is excluded from all measurements.
        warmup_states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=float(args.chunk_seconds),
            )
            for stream in streams
        ]
        warmup_jobs = [
            prepare_job(
                asr,
                state,
                stream["audio"][: args.chunk_seconds * SAMPLE_RATE],
                tail=False,
            )[0]
            for stream, state in zip(streams, warmup_states)
        ]
        asr.model.generate(
            warmup_jobs,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )

        cell_rounds: list[dict[str, Any]] = []
        for chunk_index in range(
            args.duration_seconds // args.chunk_seconds
        ):
            terminal = (
                chunk_index
                == args.duration_seconds // args.chunk_seconds - 1
            )
            round_started = time.perf_counter()
            prepare_started = time.perf_counter()
            jobs = []
            prefixes = []
            for stream, state in zip(streams, states):
                begin = chunk_index * args.chunk_seconds * SAMPLE_RATE
                end = begin + args.chunk_seconds * SAMPLE_RATE
                job, prefix = prepare_job(
                    asr,
                    state,
                    stream["audio"][begin:end],
                    tail=terminal,
                )
                jobs.append(job)
                prefixes.append(prefix)
            prepare_seconds = time.perf_counter() - prepare_started

            proposer_started = time.perf_counter()
            outputs = asr.model.generate(
                jobs,
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            proposer_seconds = time.perf_counter() - proposer_started
            records = [candidate_record(output) for output in outputs]

            apply_started = time.perf_counter()
            for state, output, prefix in zip(states, outputs, prefixes):
                apply_output(state, output, prefix)
            projection_apply_seconds = time.perf_counter() - apply_started
            logical_service_seconds = time.perf_counter() - round_started

            frozen_times = [proposer_seconds]
            repeat_exact = True
            for _ in range(args.frozen_job_repetitions - 1):
                repeated_started = time.perf_counter()
                repeated = asr.model.generate(
                    jobs,
                    sampling_params=asr.sampling_params,
                    use_tqdm=False,
                )
                frozen_times.append(time.perf_counter() - repeated_started)
                repeated_records = [
                    candidate_record(output) for output in repeated
                ]
                repeat_exact = repeat_exact and all(
                    left["token_ids"] == right["token_ids"]
                    for left, right in zip(records, repeated_records)
                )

            model_input_counts = [
                int(record["model_input_token_count"])
                for record in records
                if record["model_input_token_count"] is not None
            ]
            row = {
                "concurrency": concurrency,
                "chunk_index": chunk_index,
                "age_start_seconds": chunk_index * args.chunk_seconds,
                "age_end_seconds": (chunk_index + 1) * args.chunk_seconds,
                "terminal": terminal,
                "prepare_seconds": prepare_seconds,
                "proposer_seconds": proposer_seconds,
                "projection_apply_seconds": projection_apply_seconds,
                "logical_service_seconds": logical_service_seconds,
                "deadline_miss": logical_service_seconds > args.chunk_seconds,
                "frozen_job_execution_seconds": frozen_times,
                "frozen_job_repeat_token_exact": repeat_exact,
                "maximum_accumulated_audio_samples": max(
                    int(job["multi_modal_data"]["audio"][0].shape[0])
                    for job in jobs
                ),
                "maximum_prefix_token_count": max(
                    len(asr.processor.tokenizer.encode(prefix))
                    if prefix
                    else 0
                    for prefix in prefixes
                ),
                "maximum_model_input_token_count": (
                    max(model_input_counts) if model_input_counts else None
                ),
                "maximum_output_token_count": max(
                    len(record["token_ids"]) for record in records
                ),
            }
            cell_rounds.append(row)
            all_rounds.append(row)

        age_buckets = {}
        for lower, upper in ((0, 30), (30, 60), (60, 90), (90, 120)):
            bucket_rows = [
                row
                for row in cell_rounds
                if lower < int(row["age_end_seconds"]) <= upper
            ]
            age_buckets[f"{lower:03d}-{upper:03d}s"] = summarize_bucket(
                bucket_rows
            )
        cells.append(
            {
                "concurrency": concurrency,
                "streams": [
                    {
                        "session_id": stream["session_id"],
                        "language": stream["language"],
                        **stream["audio_provenance"],
                    }
                    for stream in streams
                ],
                "rounds": cell_rounds,
                "age_buckets": age_buckets,
                "all_frozen_repeats_exact": all(
                    row["frozen_job_repeat_token_exact"]
                    for row in cell_rounds
                ),
            }
        )

    c1_late = next(
        cell["age_buckets"]["090-120s"]
        for cell in cells
        if cell["concurrency"] == 1
    )
    c1_physical_limit = (
        float(c1_late["proposer_seconds_p99"]) >= 1.9
        or float(c1_late["proposer_seconds_mean"]) >= 1.9
    )
    payload = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "study": "Natural proposer-only age-concurrency lower bound",
        "decision": (
            "FULL_HISTORY_PHYSICAL_LIMIT_CONFIRMED"
            if c1_physical_limit
            else "CONCURRENCY_RESHAPING_REMAINS_PLAUSIBLE"
        ),
        "model": args.model_name,
        "dtype": "float16",
        "duration_seconds": args.duration_seconds,
        "chunk_seconds": args.chunk_seconds,
        "concurrencies": concurrencies,
        "frozen_job_repetitions": args.frozen_job_repetitions,
        "service_semantics": (
            "official growing-audio proposer-only state trace; terminal uses "
            "tail=True; repeated frozen-job probes are excluded from logical "
            "service latency"
        ),
        "cells": cells,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "UNRECORDED"
            ),
            "gpu": args.gpu,
            "vllm_execution_mode": "enforce_eager",
            "maximum_model_length": 4096,
        },
        "claim_boundaries": [
            "natural inputs concatenate distinct utterances with fixed silence",
            "no sample-level roll and no utterance repetition are used",
            "this is a physical proposer lower bound, not a risk certificate",
            (
                "actual vLLM model prompt token counts are reported when "
                "exported; audio encoder token counts are not inferred"
            ),
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
