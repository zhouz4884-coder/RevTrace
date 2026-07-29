#!/usr/bin/env python3
"""F5: quality evaluation on the deployed Phase-2 authority path.

The proposer is an FP16 batched engine on GPU 0.  Low-margin intermediate
revisions are re-executed by the FP16 singleton path on GPU 0, exactly as in
the frozen Phase-2 service.  Terminal revisions are issued to a separate
GPU-1 FP16 fixed-shape canonical engine; the non-authoritative terminal
proposal is retained only for diagnostics.  Only selected authoritative
records update the streaming state.
"""

from __future__ import annotations

import argparse
import gc
import json
import multiprocessing as mp
import os
import platform
import queue
import sys
import time
import traceback
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, required=True)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    return parser.parse_args()


def fixed_shape_records(
    asr: Any,
    jobs: list[dict[str, Any]],
    fixed_shape: int,
) -> tuple[list[dict[str, Any]], float]:
    from run_revguard_same_input import candidate_record

    if not jobs:
        return [], 0.0
    if len(jobs) > fixed_shape:
        raise ValueError("canonical jobs exceed fixed shape")
    padded = list(jobs)
    padded.extend([jobs[0]] * (fixed_shape - len(jobs)))
    started = time.perf_counter()
    outputs = asr.model.generate(
        padded,
        sampling_params=asr.sampling_params,
        use_tqdm=False,
    )
    elapsed = time.perf_counter() - started
    return [candidate_record(item) for item in outputs[: len(jobs)]], elapsed


def terminal_worker(
    command_queue: Any,
    result_queue: Any,
    *,
    gpu: str,
    model: str,
    fixed_shape: int,
    gpu_memory_utilization: float,
) -> None:
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
        os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
        script_dir = str(Path(__file__).resolve().parent)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from run_revtrace_dual_gpu import build_asr

        asr = build_asr(
            model,
            "float16",
            gpu_memory_utilization,
            max_model_len=4096,
            logprobs=None,
            max_num_seqs=fixed_shape,
        )
        result_queue.put(
            {
                "kind": "ready",
                "pid": os.getpid(),
                "fixed_shape": fixed_shape,
            }
        )
        while True:
            message = command_queue.get()
            if message["kind"] == "stop":
                result_queue.put({"kind": "stopped"})
                return
            if message["kind"] != "canonical":
                raise ValueError(f"unsupported command: {message['kind']}")
            records, elapsed = fixed_shape_records(
                asr,
                message["jobs"],
                fixed_shape,
            )
            result_queue.put(
                {
                    "kind": "canonical",
                    "request_id": message["request_id"],
                    "records": records,
                    "elapsed_seconds": elapsed,
                }
            )
    except BaseException as exc:
        result_queue.put(
            {
                "kind": "error",
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
        )


def receive(result_queue: Any, timeout: float) -> dict[str, Any]:
    message = result_queue.get(timeout=timeout)
    if message.get("kind") == "error":
        raise RuntimeError(
            f"terminal verifier failed: {message['error']}\n"
            f"{message['traceback']}"
        )
    return message


def singleton_records(
    asr: Any,
    jobs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    from run_revguard_same_input import candidate_record

    records = []
    started = time.perf_counter()
    for job in jobs:
        output = asr.model.generate(
            [job],
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )[0]
        records.append(candidate_record(output))
    return records, time.perf_counter() - started


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    verifier = context.Process(
        target=terminal_worker,
        args=(command_queue, result_queue),
        kwargs={
            "gpu": args.verifier_gpu,
            "model": str(args.model),
            "fixed_shape": args.batch_size,
            "gpu_memory_utilization": args.gpu_memory_utilization,
        },
        name="f5-fixed-shape-terminal-authority",
    )
    verifier.start()
    ready = receive(result_queue, args.result_timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier startup: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    from run_revbatch_gate import SAMPLE_RATE, prepare_job, read_audio
    from run_revguard_same_input import candidate_record
    from run_revtrace_dual_gpu import apply_candidate_record, build_asr

    proposer = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=4096,
        logprobs=20,
        max_num_seqs=args.batch_size,
    )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    streams = []
    for row in manifest["records"]:
        audio = read_audio(Path(row["path"]))
        streams.append(
            {
                **row,
                "audio": audio,
                "cursor": 0,
                "partials": [],
                "events": [],
                "state": proposer.init_streaming_state(
                    language=row["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=args.chunk_seconds,
                ),
            }
        )

    chunk_samples = int(round(args.chunk_seconds * SAMPLE_RATE))
    candidate_events = 0
    terminal_events = 0
    terminal_verified = 0
    nonterminal_events = 0
    nonterminal_verified = 0
    online_authority_violations = 0
    proposer_seconds = 0.0
    verifier_seconds = 0.0
    request_id = 0
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
                job, prefix = prepare_job(
                    proposer,
                    stream["state"],
                    stream["audio"][cursor:end],
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

            proposal_started = time.perf_counter()
            proposal_outputs = proposer.model.generate(
                [item["job"] for item in items],
                sampling_params=proposer.sampling_params,
                use_tqdm=False,
            )
            proposer_seconds += time.perf_counter() - proposal_started
            proposals = [candidate_record(output) for output in proposal_outputs]
            selected = list(proposals)
            verified = [False] * len(items)
            authority = ["fast_path"] * len(items)

            terminal_positions = [
                index for index, item in enumerate(items) if item["terminal"]
            ]
            if terminal_positions:
                command_queue.put(
                    {
                        "kind": "canonical",
                        "request_id": request_id,
                        "jobs": [items[index]["job"] for index in terminal_positions],
                    }
                )
                message = receive(result_queue, args.result_timeout_seconds)
                if (
                    message.get("kind") != "canonical"
                    or message.get("request_id") != request_id
                ):
                    raise RuntimeError(f"unexpected terminal result: {message}")
                request_id += 1
                verifier_seconds += float(message["elapsed_seconds"])
                for position, record in zip(
                    terminal_positions, message["records"]
                ):
                    selected[position] = record
                    verified[position] = True
                    authority[position] = "gpu1_fixed_shape_b16"

            intermediate_positions = [
                index
                for index, (item, proposal) in enumerate(zip(items, proposals))
                if not item["terminal"]
                and (
                    proposal["minimum_margin"] is None
                    or float(proposal["minimum_margin"])
                    <= args.margin_threshold
                )
            ]
            if intermediate_positions:
                records, elapsed = singleton_records(
                    proposer,
                    [items[index]["job"] for index in intermediate_positions],
                )
                proposer_seconds += elapsed
                for position, record in zip(intermediate_positions, records):
                    selected[position] = record
                    verified[position] = True
                    authority[position] = "gpu0_fp16_singleton"

            for item, proposal, chosen, was_verified, authority_path in zip(
                items, proposals, selected, verified, authority
            ):
                if was_verified and authority_path == "fast_path":
                    online_authority_violations += 1
                applied = apply_candidate_record(
                    item["stream"]["state"], chosen, item["prefix"]
                )
                item["stream"]["cursor"] = item["end"]
                item["stream"]["partials"].append(applied["text"])
                item["stream"]["events"].append(
                    {
                        "terminal": item["terminal"],
                        "candidate_minimum_margin": proposal["minimum_margin"],
                        "verified": was_verified,
                        "authority_path": authority_path,
                        "candidate_token_ids": proposal["token_ids"],
                        "selected_token_ids": chosen["token_ids"],
                        "selected_text": applied["text"],
                    }
                )
                candidate_events += 1
                if item["terminal"]:
                    terminal_events += 1
                    terminal_verified += int(was_verified)
                else:
                    nonterminal_events += 1
                    nonterminal_verified += int(was_verified)

    wall_seconds = time.perf_counter() - started
    outputs = [
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
        for stream in streams
    ]
    payload = {
        "schema_version": 2,
        "study": "RevTrace F5 deployed-path quality attachment",
        "model": args.model_name,
        "mode": "deployed_revtrace_fixed_shape_authority",
        "configured_dtype": "float16",
        "fixed_batch_shape": args.batch_size,
        "margin_threshold": args.margin_threshold,
        "candidate_events": candidate_events,
        "verified_events": terminal_verified + nonterminal_verified,
        "verification_fraction": (
            (terminal_verified + nonterminal_verified) / candidate_events
            if candidate_events
            else 0.0
        ),
        "terminal_events": terminal_events,
        "terminal_verified_events": terminal_verified,
        "terminal_verification_fraction": (
            terminal_verified / terminal_events if terminal_events else 0.0
        ),
        "nonterminal_events": nonterminal_events,
        "nonterminal_verified_events": nonterminal_verified,
        "nonterminal_verification_fraction": (
            nonterminal_verified / nonterminal_events
            if nonterminal_events
            else 0.0
        ),
        "online_selection_authority_violations": online_authority_violations,
        "wall_seconds": wall_seconds,
        "proposer_seconds": proposer_seconds,
        "gpu1_terminal_verifier_seconds": verifier_seconds,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get("REVTRACE_CODE_COMMIT", "UNRECORDED"),
            "proposer_gpu": args.proposer_gpu,
            "verifier_gpu": args.verifier_gpu,
            "terminal_batch_invariant_requested": True,
            "end_to_end_invariance_verified": False,
        },
        "outputs": outputs,
        "claim_boundaries": [
            "this runner reproduces the frozen Phase-2 authority split",
            "terminal authority is a real GPU-1 FP16 fixed-shape b16 draw",
            "low-margin intermediate authority is an FP16 singleton draw on GPU 0",
            "margin is an empirical scheduling signal, not a deterministic certificate",
            "requested batch invariance is not end-to-end bitwise verification",
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    command_queue.put({"kind": "stop"})
    stopped = receive(result_queue, args.result_timeout_seconds)
    if stopped.get("kind") != "stopped":
        raise RuntimeError(f"unexpected verifier shutdown: {stopped}")
    verifier.join(timeout=30.0)
    if verifier.is_alive():
        verifier.terminate()
        verifier.join(timeout=10.0)
        raise RuntimeError("terminal verifier did not stop")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "model": args.model_name,
                "streams": len(outputs),
                "events": candidate_events,
                "terminal_verification_fraction": payload[
                    "terminal_verification_fraction"
                ],
                "nonterminal_verification_fraction": payload[
                    "nonterminal_verification_fraction"
                ],
            }
        )
    )
    del proposer
    gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
