#!/usr/bin/env python3
"""Flip-rich execution-shape stress gate for the FP16 RevTrace proposer.

The script reconstructs one naturally observed low-margin revision from the
canonical streaming state, then changes only legal serving context: batch size,
row slot, co-runner permutation, and repeat.  It never injects logit noise or
changes the model input.  A singleton execution is the canonical oracle.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
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
    parser.add_argument("--target-session", required=True)
    parser.add_argument("--target-chunk", type=int, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, default=0.05)
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def generate_singleton(asr: Any, job: dict[str, Any]) -> dict[str, Any]:
    output = asr.model.generate(
        [job], sampling_params=asr.sampling_params, use_tqdm=False
    )[0]
    return candidate_record(output)


def run_batch(
    asr: Any,
    jobs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    outputs = asr.model.generate(
        jobs, sampling_params=asr.sampling_params, use_tqdm=False
    )
    return (
        [candidate_record(output) for output in outputs],
        time.perf_counter() - started,
    )


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
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
        raise ValueError(f"target session not found: {args.target_session}")

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
        raise AssertionError("official semantics smoke failed")

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
    target_jobs: list[dict[str, Any]] | None = None
    target_prefixes: list[str] | None = None
    for chunk_index in range(args.target_chunk + 1):
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
        if chunk_index == args.target_chunk:
            target_jobs = jobs
            target_prefixes = prefixes
            break
        for state, prefix, job in zip(states, prefixes, jobs):
            output = asr.model.generate(
                [job], sampling_params=asr.sampling_params, use_tqdm=False
            )[0]
            apply_output(state, output, prefix)
    if target_jobs is None or target_prefixes is None:
        raise AssertionError("target jobs were not reconstructed")

    target_job = target_jobs[target_index]
    canonical = generate_singleton(asr, target_job)
    rng = random.Random(17)
    trials: list[dict[str, Any]] = []
    total_rows = 0
    mismatch_rows = 0
    false_safe_rows = 0

    def record_trial(
        family: str,
        repeat: int,
        jobs: list[dict[str, Any]],
        target_slots: list[int],
    ) -> None:
        nonlocal total_rows, mismatch_rows, false_safe_rows
        records, elapsed = run_batch(asr, jobs)
        rows = []
        for slot in target_slots:
            record = records[slot]
            mismatch = record["token_ids"] != canonical["token_ids"]
            false_safe = (
                mismatch
                and record["minimum_margin"] is not None
                and record["minimum_margin"] > args.margin_threshold
            )
            total_rows += 1
            mismatch_rows += int(mismatch)
            false_safe_rows += int(false_safe)
            rows.append(
                {
                    "slot": slot,
                    "token_ids": record["token_ids"],
                    "minimum_margin": record["minimum_margin"],
                    "mismatch": mismatch,
                    "false_safe": false_safe,
                }
            )
        trials.append(
            {
                "family": family,
                "repeat": repeat,
                "batch_size": len(jobs),
                "target_slots": target_slots,
                "elapsed_seconds": elapsed,
                "rows": rows,
            }
        )

    for batch_size in (4, 8, 16, 32):
        for repeat in range(args.repeats):
            record_trial(
                f"replicated_b{batch_size}",
                repeat,
                [target_job] * batch_size,
                list(range(batch_size)),
            )

    for repeat in range(args.repeats):
        permutation = list(range(len(target_jobs)))
        rng.shuffle(permutation)
        jobs = [target_jobs[index] for index in permutation]
        slot = permutation.index(target_index)
        record_trial("permuted_round", repeat, jobs, [slot])

    filler_indices = [
        index for index in range(len(target_jobs)) if index != target_index
    ]
    for slot in range(len(target_jobs)):
        for repeat in range(args.repeats):
            rng.shuffle(filler_indices)
            jobs = [
                target_jobs[
                    filler_indices[index % len(filler_indices)]
                ]
                for index in range(len(target_jobs))
            ]
            jobs[slot] = target_job
            record_trial("slot_composition", repeat, jobs, [slot])

    decision = (
        "FLIP_RICH_STRESS_GATE_PASS"
        if mismatch_rows >= 50 and false_safe_rows == 0
        else "FLIP_RICH_STRESS_GATE_FAIL"
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace FP16 flip-rich execution-shape stress",
        "decision": decision,
        "model_name": args.model_name,
        "dtype": args.dtype,
        "target": {
            "session_id": args.target_session,
            "chunk_id": args.target_chunk,
            "canonical_token_ids": canonical["token_ids"],
            "canonical_minimum_margin": canonical["minimum_margin"],
        },
        "stress_boundary": {
            "legal_changes": [
                "batch size",
                "batch slot",
                "co-runner composition",
                "repeat",
            ],
            "prohibited_changes": [
                "logit noise injection",
                "model input mutation",
                "state mutation between paired runs",
            ],
            "frequency_claim": (
                "stress safety only; not an estimate of natural prevalence"
            ),
            "margin_claim": (
                "empirical scheduling signal; not a deterministic certificate"
            ),
        },
        "summary": {
            "target_row_evaluations": total_rows,
            "mismatch_rows": mismatch_rows,
            "false_safe_rows": false_safe_rows,
            "mismatch_rate": mismatch_rows / total_rows,
            "false_safe_rate_among_mismatches": (
                false_safe_rows / mismatch_rows if mismatch_rows else 0.0
            ),
        },
        "trials": trials,
        "official_semantics_smoke": smoke,
        "environment": {"python": platform.python_version()},
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **payload["summary"]}, sort_keys=True))
    return 0 if decision.endswith("_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
