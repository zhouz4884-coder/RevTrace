#!/usr/bin/env python3
"""Same-input GPU0/GPU1 singleton compatibility gate for checkpoint service."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import queue
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--checkpoint-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--gpu0", default="0")
    parser.add_argument("--gpu1", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--max-model-length", type=int, default=4096)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--seed", type=int, default=20260803)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def receive(queue_: Any, timeout: float) -> dict[str, Any]:
    message = queue_.get(timeout=timeout)
    if message.get("kind") == "error":
        raise RuntimeError(message["traceback"])
    return message


def main() -> int:
    args = parse_args()
    if (
        args.duration_seconds <= 0
        or args.duration_seconds % 2
        or args.checkpoint_seconds <= 0
        or args.duration_seconds % args.checkpoint_seconds
        or args.checkpoint_seconds % 2
        or args.concurrency <= 0
    ):
        raise ValueError("invalid duration, checkpoint, or concurrency")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)

    from run_revbatch_gate import SAMPLE_RATE, load_sources, prepare_job
    from run_revguard_same_input import (
        candidate_record,
        compare_records,
        state_projection_record,
    )
    from run_revtrace_dual_gpu import (
        apply_candidate_record,
        build_asr,
        verifier_worker,
    )
    from revtrace.long_horizon import (
        append_checkpoint_history,
        checkpoint_due,
        checkpoint_payload,
        concatenate_distinct_audio,
    )
    from revtrace.runtime_contract import batch_invariant_runtime_sha256

    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    verifier = context.Process(
        target=verifier_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "gpu": args.gpu1,
            "model": str(args.model),
            "dtype": "float16",
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.duration_seconds,
            "concurrency": 1,
            "worker_id": 1,
            "max_model_len": args.max_model_length,
            "terminal_canonical_batch_size": 1,
            # Match the deployed GPU1 singleton-authority runtime exactly.
            # Cross-lane compatibility is contract-relative, so a pilot with
            # this switch disabled cannot authorize the live dual-lane pool.
            "terminal_canonical_batch_invariant": True,
        },
        name="cross-lane-gpu1-singleton",
    )
    verifier.start()
    ready = receive(result_queue, args.timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier startup: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu0
    os.environ["VLLM_BATCH_INVARIANT"] = "1"
    os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
    gpu0 = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=args.max_model_length,
        # Match the proposer engine used for local singleton authority.
        logprobs=20,
        max_num_seqs=args.concurrency,
    )
    from vllm import SamplingParams

    gpu0_singleton_sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=None,
    )
    sources = load_sources(args.data_manifest)
    languages = ("English", "Chinese")
    streams: list[dict[str, Any]] = []
    target_samples = args.duration_seconds * SAMPLE_RATE
    silence_samples = args.silence_ms * SAMPLE_RATE // 1000
    for position in range(args.concurrency):
        language = languages[position % len(languages)]
        pool = sources[language]
        audio, provenance = concatenate_distinct_audio(
            pool,
            target_samples=target_samples,
            start_index=(args.seed + position * 101) % len(pool),
            silence_samples=silence_samples,
        )
        streams.append(
            {
                "session_id": f"cross-lane-{language.lower()}-{position:02d}",
                "language": language,
                "audio": audio,
                "audio_provenance": provenance,
            }
        )

    states = [
        gpu0.init_streaming_state(
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
    comparisons: list[dict[str, Any]] = []
    started = time.perf_counter()
    pair_id = 0
    try:
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
                    gpu0,
                    state,
                    stream["audio"][begin:end],
                    tail=terminal,
                )
                jobs.append(job)
                prefixes.append(prefix)

            for position, (job, prefix, state) in enumerate(
                zip(jobs, prefixes, states)
            ):
                ticket = f"pair-{pair_id:05d}"
                dispatch_started = time.perf_counter()
                command_queue.put(
                    {
                        "kind": "verify",
                        "batch_id": pair_id,
                        "items": [
                            {
                                "ticket": ticket,
                                "job": job,
                            }
                        ],
                    }
                )
                gpu0_started = time.perf_counter()
                gpu0_output = gpu0.model.generate(
                    [job],
                    sampling_params=gpu0_singleton_sampling_params,
                    use_tqdm=False,
                )[0]
                gpu0_seconds = time.perf_counter() - gpu0_started
                remote = receive(result_queue, args.timeout_seconds)
                if (
                    remote.get("kind") != "verified_item"
                    or remote.get("ticket") != ticket
                ):
                    raise RuntimeError(f"unexpected paired result: {remote}")
                pair_wall_seconds = time.perf_counter() - dispatch_started
                left = candidate_record(gpu0_output)
                right = dict(remote["record"])
                left_projection = state_projection_record(
                    gpu0,
                    state,
                    prefix,
                    left,
                    terminal=terminal,
                )
                right_projection = state_projection_record(
                    gpu0,
                    state,
                    prefix,
                    right,
                    terminal=terminal,
                )
                left["state_projection"] = left_projection
                right["state_projection"] = right_projection
                comparison = compare_records(left, right)
                comparisons.append(
                    {
                        "pair_id": pair_id,
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
                        "gpu0_seconds": gpu0_seconds,
                        "gpu1_seconds": remote["request_seconds"],
                        "paired_wall_seconds": pair_wall_seconds,
                        "model_input_token_count": left[
                            "model_input_token_count"
                        ],
                        "token_exact": comparison["token_exact"],
                        "text_exact": comparison["text_exact"],
                        "state_projection_token_exact": comparison[
                            "state_projection_token_exact"
                        ],
                        "state_projection_text_exact": comparison[
                            "state_projection_text_exact"
                        ],
                        "gpu0_token_ids": left["token_ids"],
                        "gpu1_token_ids": right["token_ids"],
                    }
                )
                apply_candidate_record(state, right, prefix)
                if checkpoint:
                    payload = checkpoint_payload(
                        prefix=prefix,
                        selected=right,
                        selected_projection=right_projection,
                    )
                    histories[position] = append_checkpoint_history(
                        histories[position],
                        payload,
                    )
                    if not session_terminal:
                        checkpoint_epochs[position] += 1
                        states[position] = gpu0.init_streaming_state(
                            context=histories[position],
                            language=streams[position]["language"],
                            unfixed_chunk_num=2,
                            unfixed_token_num=5,
                            chunk_size_sec=2.0,
                        )
                pair_id += 1
            if pair_id % 120 == 0:
                print(
                    json.dumps(
                        {
                            "pairs": pair_id,
                            "age_end_seconds": age_end,
                            "elapsed_seconds": time.perf_counter() - started,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
    finally:
        command_queue.put({"kind": "stop"})
        try:
            while True:
                stopped = receive(result_queue, 30.0)
                if stopped.get("kind") == "stopped":
                    break
        except queue.Empty:
            pass
        verifier.join(timeout=30.0)
        if verifier.is_alive():
            verifier.terminate()
            verifier.join()

    mismatch_keys = (
        "token_exact",
        "text_exact",
        "state_projection_token_exact",
        "state_projection_text_exact",
    )
    mismatch_counts = {
        key: sum(not bool(row[key]) for row in comparisons)
        for key in mismatch_keys
    }
    by_context = {}
    for context_class in ("initial_segment", "post_checkpoint"):
        subset = [
            row
            for row in comparisons
            if row["context_class"] == context_class
        ]
        by_context[context_class] = {
            "pairs": len(subset),
            **{
                f"{key}_mismatches": sum(
                    not bool(row[key]) for row in subset
                )
                for key in mismatch_keys
            },
        }
    passed = bool(
        len(comparisons) >= 720
        and all(value == 0 for value in mismatch_counts.values())
    )
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
        "study": "Checkpoint/Rebase same-input cross-lane singleton gate",
        "decision": (
            "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS"
            if passed
            else "CROSS_LANE_SINGLETON_COMPATIBILITY_FAIL"
        ),
        "model": args.model_name,
        "config": {
            "duration_seconds": args.duration_seconds,
            "checkpoint_seconds": args.checkpoint_seconds,
            "concurrency": args.concurrency,
        "dtype": "float16",
        "gpu0_engine_logprobs": 20,
        "gpu0_singleton_logprobs": None,
        "gpu1_singleton_logprobs": None,
        "gpu0_batch_invariant_runtime": True,
        "gpu1_batch_invariant_runtime": True,
        "gpu0": args.gpu0,
            "gpu1": args.gpu1,
            "max_model_length": args.max_model_length,
            "seed": args.seed,
            "lane_policy": "same_input_concurrent_singleton_gpu0_gpu1_v1",
        },
        "counts": {
            "pairs": len(comparisons),
            **{f"{key}_mismatches": value for key, value in mismatch_counts.items()},
        },
        "by_context": by_context,
        "comparisons": comparisons,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "nvidia_smi": nvidia_smi,
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT",
                "UNRECORDED",
            ),
            "runner_sha256": sha256(Path(__file__).resolve()),
            "batch_invariant_runtime_sha256": (
                batch_invariant_runtime_sha256()
            ),
        },
        "claim_boundaries": [
            "This gate establishes observed cross-lane compatibility for the "
            "frozen hardware/runtime/input contract; it is not a universal "
            "cross-device arithmetic determinism theorem.",
            "Every pair uses byte-identical input and singleton execution on "
            "both lanes before one authoritative state update.",
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
