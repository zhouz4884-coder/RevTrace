#!/usr/bin/env python3
"""Frozen-job age-concurrency matrix for natural growing-audio ASR.

One c12 proposer-only trace creates immutable jobs at 30/60/90/120 seconds.
Every concurrency cell then executes a nested subset of those exact jobs, so
age and execution shape are varied without changing request contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--experiment-id",
        default="revtrace-frozen-age-concurrency",
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-concurrency", type=int, default=12)
    parser.add_argument("--concurrency", default="1,4,8,12")
    parser.add_argument("--ages", default="30,60,90,120")
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def job_digest(job: dict[str, Any]) -> str:
    prompt = str(job["prompt"]).encode("utf-8")
    audio = np.asarray(
        job["multi_modal_data"]["audio"][0], dtype=np.float32
    ).reshape(-1)
    hasher = hashlib.sha256()
    hasher.update(prompt)
    hasher.update(audio.shape[0].to_bytes(8, "little"))
    hasher.update(audio.tobytes())
    return hasher.hexdigest()


def main() -> int:
    args = parse_args()
    concurrencies = [int(item) for item in args.concurrency.split(",")]
    ages = [int(item) for item in args.ages.split(",")]
    if (
        max(concurrencies) > args.trace_concurrency
        or max(ages) > args.duration_seconds
        or any(age % 2 for age in ages)
    ):
        raise ValueError("matrix exceeds trace contract")
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
        max_num_seqs=args.trace_concurrency,
    )
    sources = load_sources(args.data_manifest)
    silence_samples = args.silence_ms * SAMPLE_RATE // 1000
    streams = []
    for position in range(args.trace_concurrency):
        language = "English" if position % 2 == 0 else "Chinese"
        audio, provenance = concatenate_distinct_audio(
            sources[language],
            target_samples=args.duration_seconds * SAMPLE_RATE,
            start_index=(position * 17) % len(sources[language]),
            silence_samples=silence_samples,
        )
        streams.append(
            {
                "session_id": f"s{position:03d}",
                "language": language,
                "audio": audio,
                "audio_provenance": provenance,
            }
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
    frozen: dict[int, list[dict[str, Any]]] = {}
    trace_rows = []
    for chunk_index in range(args.duration_seconds // 2):
        age = (chunk_index + 1) * 2
        terminal = age == args.duration_seconds
        prepare_started = time.perf_counter()
        jobs = []
        prefixes = []
        for stream, state in zip(streams, states):
            begin = chunk_index * 2 * SAMPLE_RATE
            end = begin + 2 * SAMPLE_RATE
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=terminal,
            )
            jobs.append(job)
            prefixes.append(prefix)
        prepare_seconds = time.perf_counter() - prepare_started
        if age in ages:
            frozen[age] = [
                {
                    "prompt": str(job["prompt"]),
                    "multi_modal_data": {
                        "audio": [
                            np.asarray(
                                job["multi_modal_data"]["audio"][0],
                                dtype=np.float32,
                            ).copy()
                        ]
                    },
                }
                for job in jobs
            ]
        started = time.perf_counter()
        outputs = asr.model.generate(
            jobs,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        execution_seconds = time.perf_counter() - started
        for state, output, prefix in zip(states, outputs, prefixes):
            apply_output(state, output, prefix)
        trace_rows.append(
            {
                "age_seconds": age,
                "prepare_seconds": prepare_seconds,
                "proposer_seconds": execution_seconds,
                "maximum_audio_samples": max(
                    int(job["multi_modal_data"]["audio"][0].shape[0])
                    for job in jobs
                ),
                "maximum_model_input_tokens": max(
                    (
                        len(output.prompt_token_ids)
                        for output in outputs
                        if getattr(output, "prompt_token_ids", None)
                        is not None
                    ),
                    default=None,
                ),
            }
        )
    if set(frozen) != set(ages):
        raise AssertionError("not every requested age was frozen")

    # Initialize each measured execution shape with the shortest frozen jobs.
    for concurrency in concurrencies:
        asr.model.generate(
            frozen[min(ages)][:concurrency],
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )

    cells = []
    for age in ages:
        for concurrency in concurrencies:
            jobs = frozen[age][:concurrency]
            digests_before = [job_digest(job) for job in jobs]
            elapsed = []
            token_rows = []
            input_tokens = []
            for _ in range(args.repetitions):
                started = time.perf_counter()
                outputs = asr.model.generate(
                    jobs,
                    sampling_params=asr.sampling_params,
                    use_tqdm=False,
                )
                elapsed.append(time.perf_counter() - started)
                records = [candidate_record(output) for output in outputs]
                token_rows.append(
                    [record["token_ids"] for record in records]
                )
                input_tokens.extend(
                    int(record["model_input_token_count"])
                    for record in records
                    if record["model_input_token_count"] is not None
                )
            digests_after = [job_digest(job) for job in jobs]
            cells.append(
                {
                    "age_seconds": age,
                    "concurrency": concurrency,
                    "job_digests": digests_before,
                    "job_immutability_preserved": (
                        digests_before == digests_after
                    ),
                    "elapsed_seconds": elapsed,
                    "mean_seconds": statistics.mean(elapsed),
                    "median_seconds": statistics.median(elapsed),
                    "maximum_seconds": max(elapsed),
                    "minimum_seconds": min(elapsed),
                    "repeat_token_exact": all(
                        row == token_rows[0] for row in token_rows[1:]
                    ),
                    "maximum_audio_samples": max(
                        int(
                            job["multi_modal_data"]["audio"][0].shape[0]
                        )
                        for job in jobs
                    ),
                    "maximum_model_input_tokens": (
                        max(input_tokens) if input_tokens else None
                    ),
                }
            )
    c1_late = next(
        cell
        for cell in cells
        if cell["age_seconds"] == max(ages)
        and cell["concurrency"] == 1
    )
    physical_limit = (
        float(c1_late["median_seconds"]) >= 1.9
        or float(c1_late["maximum_seconds"]) >= 2.0
    )
    payload = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "study": "Frozen-job natural age-concurrency matrix",
        "decision": (
            "SINGLE_STREAM_FULL_HISTORY_LIMIT_CONFIRMED"
            if physical_limit
            else "CONCURRENCY_RESHAPING_CAN_RESTORE_SINGLE_STREAM_SLO"
        ),
        "model": args.model_name,
        "dtype": "float16",
        "trace_concurrency": args.trace_concurrency,
        "concurrencies": concurrencies,
        "ages_seconds": ages,
        "repetitions": args.repetitions,
        "trace_rows": trace_rows,
        "cells": cells,
        "claim_boundaries": [
            (
                "all matrix cells use immutable jobs frozen from one natural "
                "c12 proposer-only trace"
            ),
            (
                "concurrency cells use nested job subsets; job digests are "
                "checked before and after every cell"
            ),
            (
                "the matrix measures execution cost and repeatability, not "
                "state-entry risk or transcript quality"
            ),
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
