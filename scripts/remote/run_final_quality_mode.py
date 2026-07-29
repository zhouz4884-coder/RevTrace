#!/usr/bin/env python3
"""Run one frozen RevTrace ASR-quality mode on a held-out manifest.

Every invocation creates fresh streaming states.  Modes are intentionally
separate processes so that changing the authoritative dtype cannot inherit
vLLM engine state from another condition.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "singleton_authoritative",
            "unprotected_batch",
            "revtrace_risk_limited",
            "fp32_reproducible",
        ),
        required=True,
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, required=True)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    return parser.parse_args()


def fixed_shape_generate(
    asr: Any,
    jobs: list[dict[str, Any]],
    fixed_shape: int,
) -> tuple[list[Any], float]:
    if not jobs:
        return [], 0.0
    if len(jobs) > fixed_shape:
        raise ValueError("jobs exceed fixed batch shape")
    padded = list(jobs)
    padded.extend([jobs[0]] * (fixed_shape - len(jobs)))
    started = time.perf_counter()
    outputs = asr.model.generate(
        padded,
        sampling_params=asr.sampling_params,
        use_tqdm=False,
    )
    return outputs[: len(jobs)], time.perf_counter() - started


def singleton_generate(asr: Any, jobs: list[dict[str, Any]]) -> tuple[list[Any], float]:
    outputs = []
    started = time.perf_counter()
    for job in jobs:
        outputs.append(
            asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
        )
    return outputs, time.perf_counter() - started


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be positive")
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        prepare_job,
        read_audio,
    )
    from run_revguard_same_input import candidate_record
    from run_revtrace_dual_gpu import apply_candidate_record, build_asr

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = manifest["records"]
    dtype = "float32" if args.mode == "fp32_reproducible" else "float16"
    asr = build_asr(
        str(args.model),
        dtype,
        args.gpu_memory_utilization,
        max_model_len=4096,
        logprobs=20 if args.mode == "revtrace_risk_limited" else None,
        max_num_seqs=args.batch_size,
    )
    streams = []
    for row in records:
        audio = read_audio(Path(row["path"]))
        streams.append(
            {
                **row,
                "audio": audio,
                "cursor": 0,
                "partials": [],
                "events": [],
                "state": asr.init_streaming_state(
                    language=row["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=args.chunk_seconds,
                ),
            }
        )

    chunk_samples = int(round(args.chunk_seconds * SAMPLE_RATE))
    model_seconds = 0.0
    verified_events = 0
    candidate_events = 0
    started = time.perf_counter()
    while any(stream["cursor"] < stream["audio"].shape[0] for stream in streams):
        active = [
            stream
            for stream in streams
            if stream["cursor"] < stream["audio"].shape[0]
        ]
        for begin in range(0, len(active), args.batch_size):
            group = active[begin : begin + args.batch_size]
            items = []
            for stream in group:
                cursor = int(stream["cursor"])
                end = min(cursor + chunk_samples, stream["audio"].shape[0])
                terminal = end >= stream["audio"].shape[0]
                chunk = stream["audio"][cursor:end]
                job, prefix = prepare_job(
                    asr,
                    stream["state"],
                    chunk,
                    tail=terminal,
                )
                items.append(
                    {
                        "stream": stream,
                        "job": job,
                        "prefix": prefix,
                        "terminal": terminal,
                        "end": end,
                    }
                )

            if args.mode == "singleton_authoritative":
                candidates, elapsed = singleton_generate(
                    asr, [item["job"] for item in items]
                )
            else:
                candidates, elapsed = fixed_shape_generate(
                    asr,
                    [item["job"] for item in items],
                    args.batch_size,
                )
            model_seconds += elapsed
            candidate_events += len(items)

            candidate_rows = [candidate_record(output) for output in candidates]
            selected_rows = list(candidate_rows)
            selected_outputs: list[Any | None] = list(candidates)
            verified_flags = [False] * len(items)

            if args.mode == "revtrace_risk_limited":
                verify_positions = [
                    index
                    for index, (item, row) in enumerate(
                        zip(items, candidate_rows)
                    )
                    if item["terminal"]
                    or row["minimum_margin"] is None
                    or float(row["minimum_margin"]) <= args.margin_threshold
                ]
                if verify_positions:
                    verified, verify_elapsed = singleton_generate(
                        asr, [items[index]["job"] for index in verify_positions]
                    )
                    model_seconds += verify_elapsed
                    for position, output in zip(verify_positions, verified):
                        selected_rows[position] = candidate_record(output)
                        selected_outputs[position] = output
                        verified_flags[position] = True
                    verified_events += len(verify_positions)

            for item, candidate, selected, selected_output, verified in zip(
                items,
                candidate_rows,
                selected_rows,
                selected_outputs,
                verified_flags,
            ):
                stream = item["stream"]
                if args.mode == "revtrace_risk_limited":
                    applied = apply_candidate_record(
                        stream["state"], selected, item["prefix"]
                    )
                else:
                    if selected_output is None:
                        raise AssertionError("selected output is missing")
                    applied = apply_output(
                        stream["state"], selected_output, item["prefix"]
                    )
                stream["cursor"] = item["end"]
                stream["partials"].append(applied["text"])
                stream["events"].append(
                    {
                        "terminal": item["terminal"],
                        "candidate_minimum_margin": candidate["minimum_margin"],
                        "verified": verified,
                        "candidate_token_ids": candidate["token_ids"],
                        "selected_token_ids": selected["token_ids"],
                        "selected_text": applied["text"],
                    }
                )

    wall_seconds = time.perf_counter() - started
    outputs = []
    for stream in streams:
        outputs.append(
            {
                "sample_id": stream["sample_id"],
                "language": stream["language"],
                "reference": stream["reference"],
                "audio_seconds": stream["audio"].shape[0] / SAMPLE_RATE,
                "final_text": stream["state"].text,
                "final_raw_decoded": stream["state"]._raw_decoded,
                "partials": stream["partials"],
                "events": stream["events"],
            }
        )

    payload = {
        "schema_version": 1,
        "study": "RevTrace Final Evaluation Closure F1",
        "model": args.model_name,
        "mode": args.mode,
        "configured_dtype": dtype,
        "fixed_batch_shape": (
            1 if args.mode == "singleton_authoritative" else args.batch_size
        ),
        "margin_threshold": args.margin_threshold,
        "candidate_events": candidate_events,
        "verified_events": verified_events,
        "verification_fraction": (
            verified_events / candidate_events if candidate_events else 0.0
        ),
        "wall_seconds": wall_seconds,
        "model_seconds": model_seconds,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "UNRECORDED"
            ),
        },
        "outputs": outputs,
        "claim_boundaries": [
            "each mode starts from fresh streaming states in a fresh process",
            "risk-limited terminal revisions are always authoritative singleton draws",
            "margin is an empirical scheduling signal, not a deterministic certificate",
            "FP32 defines a separate versioned reproducible contract",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "model": args.model_name,
                "mode": args.mode,
                "streams": len(outputs),
                "events": candidate_events,
                "verification_fraction": payload["verification_fraction"],
            }
        )
    )
    del asr
    gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
