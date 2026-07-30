#!/usr/bin/env python3
"""Same-input B=1 versus fixed-B=2 checkpoint authority gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--checkpoint-seconds", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--max-model-length", type=int, default=4096)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20260825)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    if (
        args.duration_seconds <= 0
        or args.duration_seconds % args.checkpoint_seconds
        or args.checkpoint_seconds % 2
        or args.concurrency < 2
        or args.concurrency % 2
    ):
        raise ValueError("invalid B1/B2 checkpoint gate configuration")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    for directory in (script_dir, source_dir):
        if directory not in sys.path:
            sys.path.insert(0, directory)

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ["VLLM_BATCH_INVARIANT"] = "1"
    os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"

    from run_revbatch_gate import SAMPLE_RATE, load_sources, prepare_job
    from run_revguard_same_input import (
        candidate_record,
        compare_records,
        state_projection_record,
    )
    from run_revtrace_dual_gpu import apply_candidate_record, build_asr
    from revtrace.long_horizon import (
        append_checkpoint_history,
        checkpoint_due,
        checkpoint_payload,
        concatenate_distinct_audio,
    )
    from revtrace.runtime_contract import batch_invariant_runtime_sha256

    asr = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=args.max_model_length,
        logprobs=None,
        max_num_seqs=args.concurrency,
    )
    sources = load_sources(args.data_manifest)
    languages = ("English", "Chinese")
    target_samples = args.duration_seconds * SAMPLE_RATE
    silence_samples = args.silence_ms * SAMPLE_RATE // 1000
    streams: list[dict[str, Any]] = []
    for position in range(args.concurrency):
        language = languages[position % 2]
        pool = sources[language]
        audio, provenance = concatenate_distinct_audio(
            pool,
            target_samples=target_samples,
            start_index=(args.seed + position * 101) % len(pool),
            silence_samples=silence_samples,
        )
        streams.append(
            {
                "session_id": f"b1-b2-{language.lower()}-{position:02d}",
                "language": language,
                "audio": audio,
                "provenance": provenance,
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
    histories = ["" for _ in streams]
    checkpoint_epochs = [0 for _ in streams]
    chunk_samples = 2 * SAMPLE_RATE
    rows: list[dict[str, Any]] = []
    singleton_seconds = 0.0
    burst_seconds = 0.0
    started = time.perf_counter()

    for chunk_index in range(args.duration_seconds // 2):
        age_end = (chunk_index + 1) * 2
        session_terminal = age_end == args.duration_seconds
        checkpoint = checkpoint_due(age_end, args.checkpoint_seconds)
        terminal = session_terminal or checkpoint
        jobs = []
        prefixes = []
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

        singleton_records = []
        for job in jobs:
            call_started = time.perf_counter()
            output = asr.model.generate(
                [job],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )[0]
            singleton_seconds += time.perf_counter() - call_started
            singleton_records.append(candidate_record(output))

        burst_records: list[dict[str, Any]] = []
        for begin in range(0, len(jobs), 2):
            call_started = time.perf_counter()
            outputs = asr.model.generate(
                jobs[begin : begin + 2],
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            burst_seconds += time.perf_counter() - call_started
            burst_records.extend(candidate_record(output) for output in outputs)

        for position, (left, right, state, prefix) in enumerate(
            zip(
                singleton_records,
                burst_records,
                states,
                prefixes,
            )
        ):
            left_projection = state_projection_record(
                asr,
                state,
                prefix,
                left,
                terminal=terminal,
            )
            right_projection = state_projection_record(
                asr,
                state,
                prefix,
                right,
                terminal=terminal,
            )
            comparison = compare_records(
                {**left, "state_projection": left_projection},
                {**right, "state_projection": right_projection},
            )
            rows.append(
                {
                    "pair_id": len(rows),
                    "session_id": streams[position]["session_id"],
                    "position": position,
                    "chunk_index": chunk_index,
                    "age_end_seconds": age_end,
                    "checkpoint_epoch": checkpoint_epochs[position],
                    "checkpoint_boundary": checkpoint,
                    "terminal": terminal,
                    "context_class": (
                        "initial_segment"
                        if checkpoint_epochs[position] == 0
                        else "post_checkpoint"
                    ),
                    "token_exact": comparison["token_exact"],
                    "text_exact": comparison["text_exact"],
                    "state_projection_token_exact": comparison[
                        "state_projection_token_exact"
                    ],
                    "state_projection_text_exact": comparison[
                        "state_projection_text_exact"
                    ],
                    "singleton_token_ids": left["token_ids"],
                    "burst_b2_token_ids": right["token_ids"],
                }
            )
            apply_candidate_record(state, left, prefix)
            if checkpoint:
                payload = checkpoint_payload(
                    prefix=prefix,
                    selected=left,
                    selected_projection=left_projection,
                )
                histories[position] = append_checkpoint_history(
                    histories[position],
                    payload,
                )
                if not session_terminal:
                    checkpoint_epochs[position] += 1
                    states[position] = asr.init_streaming_state(
                        context=histories[position],
                        language=streams[position]["language"],
                        unfixed_chunk_num=2,
                        unfixed_token_num=5,
                        chunk_size_sec=2.0,
                    )
        if len(rows) % 120 == 0:
            print(
                json.dumps(
                    {
                        "pairs": len(rows),
                        "elapsed_seconds": time.perf_counter() - started,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    fields = (
        "token_exact",
        "text_exact",
        "state_projection_token_exact",
        "state_projection_text_exact",
    )
    mismatches = {
        f"{field}_mismatches": sum(not bool(row[field]) for row in rows)
        for field in fields
    }
    passed = len(rows) >= 720 and all(value == 0 for value in mismatches.values())
    nvidia_smi = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,driver_version",
            "--format=csv,noheader",
        ],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    payload = {
        "schema_version": 1,
        "study": "Checkpoint same-input B1/B2 authority compatibility",
        "decision": (
            "BURST_B2_AUTHORITY_COMPATIBILITY_PASS"
            if passed
            else "BURST_B2_AUTHORITY_COMPATIBILITY_FAIL"
        ),
        "model": args.model_name,
        "config": {
            "duration_seconds": args.duration_seconds,
            "checkpoint_seconds": args.checkpoint_seconds,
            "concurrency": args.concurrency,
            "dtype": "float16",
            "batch_invariant_runtime": True,
            "singleton_shape": 1,
            "burst_fixed_shape": 2,
            "gpu": args.gpu,
            "seed": args.seed,
            "batch_invariant_runtime_sha256": (
                batch_invariant_runtime_sha256()
            ),
        },
        "counts": {"pairs": len(rows), **mismatches},
        "performance": {
            "singleton_total_seconds": singleton_seconds,
            "burst_b2_total_seconds": burst_seconds,
            "authority_speedup": singleton_seconds / burst_seconds,
        },
        "comparisons": rows,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "nvidia_smi": nvidia_smi,
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT",
                "UNRECORDED",
            ),
            "runner_sha256": sha256(Path(__file__).resolve()),
        },
        "claim_boundaries": [
            "This is observed B1/B2 compatibility for the frozen runtime and "
            "hardware, not a universal floating-point determinism theorem.",
            "Every comparison uses the same model input before one B1 "
            "reference transition updates the checkpoint state.",
            "The checkpoint payload is the full terminal state projection.",
        ],
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
