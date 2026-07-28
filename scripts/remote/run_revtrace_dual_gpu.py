#!/usr/bin/env python3
"""Deployed two-GPU revision transaction gate for Qwen3-ASR.

GPU 0 runs an FP16 batched proposer.  GPU 1 runs an FP16, batch-size-one
canonical verifier.  Every proposed transition is bound to its parent revision
version.  Safe proposals commit immediately; low-margin and terminal proposals
commit only after canonical verification.  Independent sessions may continue
while another session waits for verification, which creates real proposer /
verifier overlap without allowing an uncertified result to become parent state.

After the timed service run, GPU 1 replays every stream through the canonical
singleton path from a fresh state.  This audit is excluded from service timing
and is used to compare the complete output and exact next-state projection for
every committed transition.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import queue
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, default=0.05)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--verifier-lanes", type=int, default=1)
    parser.add_argument(
        "--verifier-gpu-memory-utilization",
        type=float,
        default=None,
    )
    parser.add_argument("--verifier-max-model-len", type=int, default=4096)
    parser.add_argument("--terminal-canonical-dtype")
    parser.add_argument("--terminal-canonical-batch-size", type=int, default=16)
    parser.add_argument(
        "--terminal-canonical-batch-invariant",
        action="store_true",
    )
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--power-sampling-interval-seconds",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--arrival-mode",
        choices=("sync", "poisson", "burst"),
        default="sync",
    )
    parser.add_argument("--arrival-seed", type=int, default=20260728)
    parser.add_argument("--arrival-scale-seconds", type=float, default=0.02)
    parser.add_argument(
        "--language-mode",
        choices=("mixed", "English", "Chinese"),
        default="mixed",
    )
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


def build_asr(
    model: str,
    dtype: str,
    gpu_memory_utilization: float,
    max_model_len: int | None = None,
    logprobs: int | None = 20,
    max_num_seqs: int | None = None,
) -> Any:
    from qwen_asr import Qwen3ASRModel
    from vllm import SamplingParams

    engine_kwargs = {
        "model": model,
        "gpu_memory_utilization": gpu_memory_utilization,
        "max_inference_batch_size": 128,
        "max_new_tokens": 32,
        "enforce_eager": True,
        "max_num_seqs": 128,
        "mm_processor_cache_gb": 0,
        "async_scheduling": False,
        "enable_prefix_caching": False,
        "dtype": dtype,
    }
    if max_model_len is not None:
        engine_kwargs["max_model_len"] = max_model_len
        verifier_capacity = max_num_seqs or 1
        engine_kwargs["max_inference_batch_size"] = verifier_capacity
        engine_kwargs["max_num_seqs"] = verifier_capacity
    asr = Qwen3ASRModel.LLM(
        **engine_kwargs,
    )
    asr.sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=logprobs,
    )
    return asr


def singleton_records(asr: Any, jobs: list[dict[str, Any]]) -> tuple[list[Any], float, list[float]]:
    outputs: list[Any] = []
    request_seconds: list[float] = []
    started = time.perf_counter()
    for job in jobs:
        item_started = time.perf_counter()
        output = asr.model.generate(
            [job], sampling_params=asr.sampling_params, use_tqdm=False
        )[0]
        request_seconds.append(time.perf_counter() - item_started)
        outputs.append(output)
    return outputs, time.perf_counter() - started, request_seconds


def apply_candidate_record(
    state: Any,
    record: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    from qwen_asr import parse_asr_output

    state._raw_decoded = prefix + str(record["text"])
    language, text = parse_asr_output(
        state._raw_decoded, user_language=state.force_language
    )
    state.language = language
    state.text = text
    state.chunk_id += 1
    return {
        "token_ids": [int(token) for token in record["token_ids"]],
        "raw_decoded": state._raw_decoded,
        "language": language,
        "text": text,
    }


def verifier_worker(
    command_queue: Any,
    result_queue: Any,
    *,
    gpu: str,
    model: str,
    dtype: str,
    gpu_memory_utilization: float,
    data_manifest: str,
    duration_seconds: int,
    concurrency: int,
    worker_id: int,
    max_model_len: int,
    terminal_canonical_batch_size: int,
    terminal_canonical_batch_invariant: bool,
) -> None:
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu
        if terminal_canonical_batch_invariant:
            os.environ["VLLM_BATCH_INVARIANT"] = "1"
            os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
        script_dir = str(Path(__file__).resolve().parent)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from run_revbatch_gate import (
            SAMPLE_RATE,
            apply_output,
            load_sources,
            make_streams,
            official_smoke,
            prepare_job,
        )
        from run_revguard_same_input import (
            candidate_record,
            state_projection_record,
        )

        asr = build_asr(
            model,
            dtype,
            gpu_memory_utilization,
            max_model_len=max_model_len,
            logprobs=None,
            max_num_seqs=terminal_canonical_batch_size,
        )
        sources = load_sources(Path(data_manifest))
        smoke = official_smoke(asr, sources["English"][0])
        if not smoke["exact"]:
            raise AssertionError("verifier official-semantics smoke failed")
        result_queue.put(
            {
                "kind": "ready",
                "role": "verifier",
                "worker_id": worker_id,
                "max_model_len": max_model_len,
                "smoke": smoke,
                "pid": os.getpid(),
            }
        )

        while True:
            message = command_queue.get()
            kind = message["kind"]
            if kind == "stop":
                result_queue.put(
                    {
                        "kind": "stopped",
                        "role": "verifier",
                        "worker_id": worker_id,
                    }
                )
                return
            if kind == "verify":
                items = message["items"]
                for position, item in enumerate(items):
                    outputs, elapsed, request_seconds = singleton_records(
                        asr, [item["job"]]
                    )
                    result_queue.put(
                        {
                            "kind": "verified_item",
                            "worker_id": worker_id,
                            "batch_id": message["batch_id"],
                            "position": position,
                            "batch_size": len(items),
                            "elapsed_seconds": elapsed,
                            "request_seconds": request_seconds[0],
                            "ticket": item["ticket"],
                            "record": candidate_record(outputs[0]),
                        }
                    )
                continue
            if kind == "canonical_batch":
                items = message["items"]
                fixed_shape = int(
                    message.get(
                        "fixed_shape",
                        terminal_canonical_batch_size,
                    )
                )
                if not items:
                    raise ValueError("canonical batch cannot be empty")
                if not 1 <= fixed_shape <= terminal_canonical_batch_size:
                    raise ValueError("invalid canonical fixed shape")
                if len(items) > fixed_shape:
                    raise ValueError("canonical batch exceeds fixed shape")
                padded_jobs = [item["job"] for item in items]
                padded_jobs.extend(
                    [items[0]["job"]]
                    * (fixed_shape - len(items))
                )
                started = time.perf_counter()
                outputs = asr.model.generate(
                    padded_jobs,
                    sampling_params=asr.sampling_params,
                    use_tqdm=False,
                )
                elapsed = time.perf_counter() - started
                for position, (item, output) in enumerate(
                    zip(items, outputs)
                ):
                    result_queue.put(
                        {
                            "kind": "verified_item",
                            "worker_id": worker_id,
                            "batch_id": message["batch_id"],
                            "position": position,
                            "batch_size": len(items),
                            "fixed_shape": fixed_shape,
                            "elapsed_seconds": (
                                elapsed if position == 0 else 0.0
                            ),
                            "request_seconds": elapsed,
                            "ticket": item["ticket"],
                            "record": candidate_record(output),
                            "canonical_batch": True,
                        }
                    )
                continue
            if kind == "audit":
                streams = make_streams(
                    sources,
                    duration=duration_seconds,
                    concurrency=concurrency,
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
                    stream["audio"].shape[0] // chunk_samples
                    for stream in streams
                )
                audit_events: list[dict[str, Any]] = []
                audit_started = time.perf_counter()
                request_seconds: list[float] = []
                for chunk_index in range(rounds):
                    terminal = chunk_index == rounds - 1
                    for stream, state in zip(streams, states):
                        begin = chunk_index * chunk_samples
                        end = begin + chunk_samples
                        job, prefix = prepare_job(
                            asr,
                            state,
                            stream["audio"][begin:end],
                            tail=False,
                        )
                        outputs, _, per_request = singleton_records(asr, [job])
                        request_seconds.extend(per_request)
                        record = candidate_record(outputs[0])
                        record["state_projection"] = state_projection_record(
                            asr,
                            state,
                            prefix,
                            record,
                            terminal=terminal,
                        )
                        audit_events.append(
                            {
                                "session_id": stream["session_id"],
                                "chunk_id": chunk_index,
                                "record": record,
                            }
                        )
                        apply_output(state, outputs[0], prefix)
                result_queue.put(
                    {
                        "kind": "audit_complete",
                        "worker_id": worker_id,
                        "elapsed_seconds": time.perf_counter() - audit_started,
                        "request_seconds": request_seconds,
                        "events": audit_events,
                    }
                )
                continue
            raise ValueError(f"unsupported verifier command: {kind}")
    except BaseException as exc:
        result_queue.put(
            {
                "kind": "error",
                "role": "verifier",
                "worker_id": worker_id,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
        )


def receive_or_raise(result_queue: Any, timeout: float) -> dict[str, Any]:
    message = result_queue.get(timeout=timeout)
    if message.get("kind") == "error":
        raise RuntimeError(
            f"{message.get('role')} failed: {message.get('error')}\n"
            f"{message.get('traceback')}"
        )
    return message


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    context = mp.get_context("spawn")
    if args.verifier_lanes < 1:
        raise ValueError("--verifier-lanes must be positive")
    verifier_memory_utilization = (
        args.verifier_gpu_memory_utilization
        if args.verifier_gpu_memory_utilization is not None
        else args.gpu_memory_utilization / args.verifier_lanes
    )
    command_queues = [context.Queue() for _ in range(args.verifier_lanes)]
    result_queue = context.Queue()
    verifiers = []
    ready_by_worker: dict[int, dict[str, Any]] = {}
    for worker_id, command_queue in enumerate(command_queues):
        verifier = context.Process(
            target=verifier_worker,
            kwargs={
                "command_queue": command_queue,
                "result_queue": result_queue,
                "gpu": args.verifier_gpu,
                "model": str(args.model),
                "dtype": (
                    args.terminal_canonical_dtype or args.dtype
                ),
                "gpu_memory_utilization": verifier_memory_utilization,
                "data_manifest": str(args.data_manifest),
                "duration_seconds": args.duration_seconds,
                "concurrency": args.concurrency,
                "worker_id": worker_id,
                "max_model_len": args.verifier_max_model_len,
                "terminal_canonical_batch_size": (
                    args.terminal_canonical_batch_size
                ),
                "terminal_canonical_batch_invariant": (
                    args.terminal_canonical_batch_invariant
                ),
            },
            name=f"revtrace-verifier-{worker_id}",
        )
        verifier.start()
        verifiers.append(verifier)
        ready = receive_or_raise(result_queue, args.result_timeout_seconds)
        if ready.get("kind") != "ready":
            raise RuntimeError(
                f"unexpected verifier initialization result: {ready}"
            )
        ready_by_worker[int(ready["worker_id"])] = ready

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    import numpy as np
    from run_revbatch_gate import (
        SAMPLE_RATE,
        cycle_audio,
        load_sources,
        make_streams,
        official_smoke,
        prepare_job,
    )
    from run_revguard_same_input import (
        candidate_record,
        compare_records,
        state_projection_record,
    )
    from revtrace.core import RevisionCommitLedger, RevisionTicket
    from revtrace.phase5 import NvidiaPowerSampler, summarize_energy

    sources = load_sources(args.data_manifest)
    streams = make_streams(
        sources,
        duration=args.duration_seconds,
        concurrency=args.concurrency,
    )
    if args.language_mode != "mixed":
        for index, stream in enumerate(streams):
            language = args.language_mode
            source = sources[language][index % len(sources[language])]
            stream["language"] = language
            stream["audio"] = cycle_audio(
                source,
                args.duration_seconds,
                offset=(index * 7919) % max(1, source.size),
            )
    asr = build_asr(
        str(args.model),
        args.dtype,
        args.gpu_memory_utilization,
    )
    proposer_smoke = official_smoke(asr, sources["English"][0])
    if not proposer_smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

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
    next_chunks = [0 for _ in streams]
    pending_by_revision: dict[str, dict[str, Any]] = {}
    ledger = RevisionCommitLedger()
    for stream in streams:
        ledger.register(stream["session_id"])

    events: list[dict[str, Any]] = []
    proposer_seconds = 0.0
    verifier_seconds = 0.0
    proposer_gpu_terminal_verifier_seconds = 0.0
    proposer_gpu_terminal_verified_events = 0
    verifier_request_seconds: list[float] = []
    verifier_wait_seconds: list[float] = []
    verifier_wait_terminal_seconds: list[float] = []
    verifier_wait_intermediate_seconds: list[float] = []
    proposal_batch_sizes: list[int] = []
    max_pending = 0
    stale_results = 0
    verification_batches = 0
    verifier_dispatch_cursor = 0
    verifier_worker_events = [0 for _ in range(args.verifier_lanes)]
    terminal_burst_sizes: list[int] = []

    def commit_record(
        pending: dict[str, Any],
        selected_record: dict[str, Any],
        *,
        verified: bool,
        verifier_elapsed: float = 0.0,
    ) -> None:
        nonlocal stale_results
        ticket = RevisionTicket(**pending["ticket"])
        state_index = int(pending["state_index"])
        state = states[state_index]
        if not ledger.can_commit(ticket) or int(state.chunk_id) != ticket.parent_version:
            stale_results += 1
            return
        projection = state_projection_record(
            asr,
            state,
            pending["prefix"],
            selected_record,
            terminal=pending["terminal"],
        )
        selected_record["state_projection"] = projection
        ledger.commit(ticket)
        apply_candidate_record(state, selected_record, pending["prefix"])
        if int(state.chunk_id) != ledger.version(ticket.session_id):
            raise AssertionError("model state and transaction ledger diverged")
        next_chunks[state_index] += 1
        proposal = pending["proposal"]
        events.append(
            {
                "session_id": ticket.session_id,
                "language": streams[state_index]["language"],
                "chunk_id": pending["chunk_index"],
                "terminal": pending["terminal"],
                "revision_id": ticket.revision_id,
                "parent_version": ticket.parent_version,
                "committed_version": ticket.next_version,
                "verified": verified,
                "proposal_minimum_margin": proposal["minimum_margin"],
                "proposal_token_ids": proposal["token_ids"],
                "selected_token_ids": selected_record["token_ids"],
                "selected_text": selected_record["text"],
                "selected_state_projection": projection,
                "verifier_elapsed_seconds": verifier_elapsed,
                "state_entry_latency_seconds": (
                    time.perf_counter() - pending["issued_at"]
                ),
            }
        )

    def process_verified_message(message: dict[str, Any]) -> None:
        nonlocal verifier_seconds, stale_results
        if message.get("kind") != "verified_item":
            raise RuntimeError(f"unexpected verifier result: {message}")
        elapsed = float(message["elapsed_seconds"])
        verifier_seconds += elapsed
        verifier_worker_events[int(message["worker_id"])] += 1
        verifier_request_seconds.append(float(message["request_seconds"]))
        revision_id = message["ticket"]["revision_id"]
        pending = pending_by_revision.pop(revision_id, None)
        if pending is None:
            stale_results += 1
            return
        wait_seconds = time.perf_counter() - pending["submitted_at"]
        verifier_wait_seconds.append(wait_seconds)
        if pending["terminal"]:
            verifier_wait_terminal_seconds.append(wait_seconds)
        else:
            verifier_wait_intermediate_seconds.append(wait_seconds)
        commit_record(
            pending,
            message["record"],
            verified=True,
            verifier_elapsed=elapsed,
        )

    service_power = NvidiaPowerSampler(
        [int(args.proposer_gpu), int(args.verifier_gpu)],
        interval_seconds=args.power_sampling_interval_seconds,
    )
    service_power.start()
    service_started = time.perf_counter()
    arrival_rng = np.random.default_rng(args.arrival_seed)
    if args.arrival_mode == "sync":
        session_release_seconds = [0.0 for _ in streams]
    elif args.arrival_mode == "poisson":
        intervals = arrival_rng.exponential(
            args.arrival_scale_seconds,
            size=max(0, len(streams) - 1),
        )
        session_release_seconds = [0.0]
        for interval in intervals:
            session_release_seconds.append(
                session_release_seconds[-1] + float(interval)
            )
    else:
        burst_size = max(1, len(streams) // 4)
        session_release_seconds = [
            (index // burst_size) * args.arrival_scale_seconds
            for index in range(len(streams))
        ]
    batch_id = 0
    while len(events) < len(streams) * rounds:
        progressed = False

        while True:
            try:
                message = result_queue.get_nowait()
            except queue.Empty:
                break
            if message.get("kind") == "error":
                raise RuntimeError(
                    f"verifier failed: {message.get('error')}\n"
                    f"{message.get('traceback')}"
                )
            process_verified_message(message)
            progressed = True

        ready_indices = [
            index
            for index, chunk_index in enumerate(next_chunks)
            if chunk_index < rounds
            and (
                time.perf_counter() - service_started
                >= session_release_seconds[index]
            )
            and not any(
                pending["state_index"] == index
                for pending in pending_by_revision.values()
            )
        ]
        if ready_indices:
            jobs: list[dict[str, Any]] = []
            prepared: list[dict[str, Any]] = []
            for index in ready_indices:
                chunk_index = next_chunks[index]
                terminal = chunk_index == rounds - 1
                stream = streams[index]
                state = states[index]
                if int(state.chunk_id) != ledger.version(stream["session_id"]):
                    raise AssertionError("state version mismatch before proposal")
                revision_id = f"{stream['session_id']}:{chunk_index}"
                ticket = ledger.issue(stream["session_id"], revision_id)
                begin = chunk_index * chunk_samples
                end = begin + chunk_samples
                job, prefix = prepare_job(
                    asr,
                    state,
                    stream["audio"][begin:end],
                    tail=False,
                )
                jobs.append(job)
                prepared.append(
                    {
                        "state_index": index,
                        "chunk_index": chunk_index,
                        "terminal": terminal,
                        "prefix": prefix,
                        "job": job,
                        "issued_at": time.perf_counter(),
                        "ticket": {
                            "session_id": ticket.session_id,
                            "revision_id": ticket.revision_id,
                            "parent_version": ticket.parent_version,
                            "next_version": ticket.next_version,
                        },
                    }
                )
            terminal_direct_ids: set[str] = set()
            if args.terminal_canonical_dtype:
                terminal_items: list[dict[str, Any]] = []
                for item in prepared:
                    if not item["terminal"]:
                        continue
                    pending = {
                        **item,
                        "proposal": {
                            "minimum_margin": None,
                            "token_ids": [],
                        },
                        "submitted_at": time.perf_counter(),
                    }
                    revision_id = item["ticket"]["revision_id"]
                    pending_by_revision[revision_id] = pending
                    terminal_direct_ids.add(revision_id)
                    terminal_items.append(
                        {
                            "ticket": item["ticket"],
                            "job": item["job"],
                        }
                    )
                if terminal_items:
                    terminal_burst_sizes.append(len(terminal_items))
                    for begin in range(
                        0,
                        len(terminal_items),
                        args.terminal_canonical_batch_size,
                    ):
                        command_queues[0].put(
                            {
                                "kind": "canonical_batch",
                                "batch_id": batch_id,
                                "items": terminal_items[
                                    begin : begin
                                    + args.terminal_canonical_batch_size
                                ],
                            }
                        )
                        batch_id += 1
                        verification_batches += 1
                    max_pending = max(
                        max_pending, len(pending_by_revision)
                    )
            proposal_batch_sizes.append(len(jobs))
            proposal_started = time.perf_counter()
            outputs = asr.model.generate(
                jobs,
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            proposer_seconds += time.perf_counter() - proposal_started
            verify_items: list[dict[str, Any]] = []
            verify_pending: list[dict[str, Any]] = []
            for item, output in zip(prepared, outputs):
                state = states[item["state_index"]]
                proposal = candidate_record(output)
                proposal["state_projection"] = state_projection_record(
                    asr,
                    state,
                    item["prefix"],
                    proposal,
                    terminal=item["terminal"],
                )
                revision_id = item["ticket"]["revision_id"]
                if revision_id in terminal_direct_ids:
                    pending_by_revision[revision_id]["proposal"] = proposal
                    continue
                pending = {
                    **item,
                    "proposal": proposal,
                }
                risky = (
                    item["terminal"]
                    or proposal["minimum_margin"] is None
                    or proposal["minimum_margin"] <= args.margin_threshold
                )
                if risky:
                    pending["submitted_at"] = time.perf_counter()
                    pending_by_revision[item["ticket"]["revision_id"]] = pending
                    verify_items.append(
                        {
                            "ticket": item["ticket"],
                            "job": item["job"],
                        }
                    )
                    verify_pending.append(pending)
                else:
                    commit_record(pending, proposal, verified=False)
            if verify_items and args.terminal_canonical_dtype:
                for verify_item, pending in zip(
                    verify_items, verify_pending
                ):
                    local_outputs, elapsed, local_request_seconds = (
                        singleton_records(asr, [verify_item["job"]])
                    )
                    request_elapsed = local_request_seconds[0]
                    proposer_gpu_terminal_verifier_seconds += elapsed
                    proposer_gpu_terminal_verified_events += 1
                    verifier_request_seconds.append(request_elapsed)
                    revision_id = pending["ticket"]["revision_id"]
                    current = pending_by_revision.pop(revision_id, None)
                    if current is None:
                        stale_results += 1
                        continue
                    wait_seconds = (
                        time.perf_counter() - current["submitted_at"]
                    )
                    verifier_wait_seconds.append(wait_seconds)
                    verifier_wait_intermediate_seconds.append(wait_seconds)
                    commit_record(
                        current,
                        candidate_record(local_outputs[0]),
                        verified=True,
                        verifier_elapsed=request_elapsed,
                    )
                    while True:
                        try:
                            message = result_queue.get_nowait()
                        except queue.Empty:
                            break
                        if message.get("kind") == "error":
                            raise RuntimeError(
                                "verifier failed: "
                                f"{message.get('error')}\n"
                                f"{message.get('traceback')}"
                            )
                        process_verified_message(message)
                verify_items = []
                verify_pending = []
            if verify_items:
                terminal_burst = all(
                    pending["terminal"] for pending in verify_pending
                )
                lane_count = (
                    args.verifier_lanes + 1
                    if terminal_burst and len(verify_items) >= 4
                    else args.verifier_lanes
                )
                if terminal_burst:
                    terminal_burst_sizes.append(len(verify_items))
                lane_items: list[list[dict[str, Any]]] = [
                    [] for _ in range(lane_count)
                ]
                lane_pending: list[list[dict[str, Any]]] = [
                    [] for _ in range(lane_count)
                ]
                for position, (verify_item, pending) in enumerate(
                    zip(verify_items, verify_pending)
                ):
                    lane = position % lane_count
                    lane_items[lane].append(verify_item)
                    lane_pending[lane].append(pending)
                for lane in range(args.verifier_lanes):
                    if not lane_items[lane]:
                        continue
                    worker_id = (
                        verifier_dispatch_cursor + lane
                    ) % args.verifier_lanes
                    command_queues[worker_id].put(
                        {
                            "kind": "verify",
                            "batch_id": batch_id,
                            "items": lane_items[lane],
                        }
                    )
                    batch_id += 1
                    verification_batches += 1
                verifier_dispatch_cursor = (
                    verifier_dispatch_cursor + args.verifier_lanes
                ) % args.verifier_lanes
                max_pending = max(max_pending, len(pending_by_revision))
                if lane_count > args.verifier_lanes:
                    local_lane = args.verifier_lanes
                    for verify_item, pending in zip(
                        lane_items[local_lane],
                        lane_pending[local_lane],
                    ):
                        local_outputs, elapsed, local_request_seconds = (
                            singleton_records(asr, [verify_item["job"]])
                        )
                        request_elapsed = local_request_seconds[0]
                        proposer_gpu_terminal_verifier_seconds += elapsed
                        proposer_gpu_terminal_verified_events += 1
                        verifier_request_seconds.append(request_elapsed)
                        revision_id = pending["ticket"]["revision_id"]
                        current = pending_by_revision.pop(revision_id, None)
                        if current is None:
                            stale_results += 1
                            continue
                        wait_seconds = (
                            time.perf_counter() - current["submitted_at"]
                        )
                        verifier_wait_seconds.append(wait_seconds)
                        verifier_wait_terminal_seconds.append(wait_seconds)
                        commit_record(
                            current,
                            candidate_record(local_outputs[0]),
                            verified=True,
                            verifier_elapsed=request_elapsed,
                        )
                        while True:
                            try:
                                message = result_queue.get_nowait()
                            except queue.Empty:
                                break
                            if message.get("kind") == "error":
                                raise RuntimeError(
                                    "verifier failed: "
                                    f"{message.get('error')}\n"
                                    f"{message.get('traceback')}"
                                )
                            process_verified_message(message)
            progressed = True

        if not progressed:
            if pending_by_revision:
                message = receive_or_raise(
                    result_queue,
                    args.result_timeout_seconds,
                )
                process_verified_message(message)
            else:
                elapsed = time.perf_counter() - service_started
                future = [
                    release
                    for release, chunk_index in zip(
                        session_release_seconds, next_chunks
                    )
                    if chunk_index < rounds and release > elapsed
                ]
                if not future:
                    raise RuntimeError(
                        "scheduler made no progress without pending work"
                    )
                time.sleep(
                    min(0.01, max(0.0, min(future) - elapsed))
                )

        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "committed": len(events),
                    "pending": len(pending_by_revision),
                    "max_pending": max_pending,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    service_wall_seconds = time.perf_counter() - service_started
    service_power_samples = service_power.stop()
    if pending_by_revision:
        raise AssertionError("service ended with unresolved revisions")

    audit_power = NvidiaPowerSampler(
        [int(args.proposer_gpu), int(args.verifier_gpu)],
        interval_seconds=args.power_sampling_interval_seconds,
    )
    audit_power.start()
    if args.terminal_canonical_dtype:
        audit_streams = make_streams(
            sources,
            duration=args.duration_seconds,
            concurrency=args.concurrency,
        )
        if args.language_mode != "mixed":
            for index, stream in enumerate(audit_streams):
                language = args.language_mode
                source = sources[language][index % len(sources[language])]
                stream["language"] = language
                stream["audio"] = cycle_audio(
                    source,
                    args.duration_seconds,
                    offset=(index * 7919) % max(1, source.size),
                )
        audit_states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in audit_streams
        ]
        audit_events: list[dict[str, Any]] = []
        audit_request_seconds: list[float] = []
        for chunk_index in range(rounds):
            terminal = chunk_index == rounds - 1
            audit_jobs: list[dict[str, Any]] = []
            audit_prefixes: list[str] = []
            singleton_audit_records: list[dict[str, Any]] = []
            for stream, state in zip(audit_streams, audit_states):
                begin = chunk_index * chunk_samples
                end = begin + chunk_samples
                job, prefix = prepare_job(
                    asr,
                    state,
                    stream["audio"][begin:end],
                    tail=False,
                )
                audit_jobs.append(job)
                audit_prefixes.append(prefix)
                outputs, _, request_seconds = singleton_records(asr, [job])
                audit_request_seconds.extend(request_seconds)
                singleton_audit_records.append(
                    candidate_record(outputs[0])
                )
            selected_audit_records = singleton_audit_records
            if terminal:
                audit_items = [
                    {
                        "ticket": {
                            "session_id": stream["session_id"],
                            "revision_id": (
                                f"audit:{stream['session_id']}:{chunk_index}"
                            ),
                            "parent_version": chunk_index,
                            "next_version": chunk_index + 1,
                        },
                        "job": job,
                    }
                    for stream, job in zip(audit_streams, audit_jobs)
                ]
                terminal_records: list[dict[str, Any] | None] = [
                    None for _ in audit_items
                ]
                for begin in range(
                    0,
                    len(audit_items),
                    args.terminal_canonical_batch_size,
                ):
                    chunk = audit_items[
                        begin : begin + args.terminal_canonical_batch_size
                    ]
                    command_queues[0].put(
                        {
                            "kind": "canonical_batch",
                            "batch_id": -1 - begin,
                            "items": chunk,
                        }
                    )
                    for _ in chunk:
                        message = receive_or_raise(
                            result_queue, args.result_timeout_seconds
                        )
                        if message.get("kind") != "verified_item":
                            raise RuntimeError(
                                "unexpected terminal audit result: "
                                f"{message}"
                            )
                        terminal_records[
                            begin + int(message["position"])
                        ] = message["record"]
                if any(item is None for item in terminal_records):
                    raise AssertionError(
                        "terminal audit returned an incomplete batch"
                    )
                selected_audit_records = [
                    item
                    for item in terminal_records
                    if item is not None
                ]
            for stream, state, prefix, selected_record in zip(
                audit_streams,
                audit_states,
                audit_prefixes,
                selected_audit_records,
            ):
                selected_record["state_projection"] = (
                    state_projection_record(
                        asr,
                        state,
                        prefix,
                        selected_record,
                        terminal=terminal,
                    )
                )
                audit_events.append(
                    {
                        "session_id": stream["session_id"],
                        "chunk_id": chunk_index,
                        "record": selected_record,
                    }
                )
                apply_candidate_record(state, selected_record, prefix)
        audit = {
            "kind": "audit_complete",
            "elapsed_seconds": sum(audit_request_seconds),
            "request_seconds": audit_request_seconds,
            "events": audit_events,
            "hybrid_terminal_canonical": True,
        }
    else:
        command_queues[0].put({"kind": "audit"})
        audit = receive_or_raise(result_queue, args.result_timeout_seconds)
        if audit.get("kind") != "audit_complete":
            raise RuntimeError(f"unexpected audit result: {audit}")
    audit_power_samples = audit_power.stop()
    canonical_by_key = {
        (event["session_id"], int(event["chunk_id"])): event["record"]
        for event in audit["events"]
    }
    output_violations = 0
    state_violations = 0
    for event in events:
        canonical = canonical_by_key[
            (event["session_id"], int(event["chunk_id"]))
        ]
        selected = {
            "token_ids": event["selected_token_ids"],
            "text": event["selected_text"],
            "state_projection": event["selected_state_projection"],
        }
        comparison = compare_records(canonical, selected)
        event["selected_vs_canonical"] = comparison
        output_violations += int(not comparison["token_exact"])
        state_violations += int(
            not comparison["state_projection_token_exact"]
        )

    verified_events = sum(bool(event["verified"]) for event in events)
    reference_seconds = float(audit["elapsed_seconds"])
    online_speedup = reference_seconds / service_wall_seconds
    gpu_normalized_speedup = reference_seconds / (
        service_wall_seconds * 2.0
    )
    state_entry_latencies = [
        float(event["state_entry_latency_seconds"]) for event in events
    ]
    slo_seconds = 2.0
    deployed_slo_events = sum(
        latency <= slo_seconds for latency in state_entry_latencies
    )
    canonical_slo_events = sum(
        float(value) <= slo_seconds for value in audit["request_seconds"]
    )
    deployed_slo_goodput = deployed_slo_events / service_wall_seconds
    canonical_slo_goodput = canonical_slo_events / reference_seconds
    verifier_ratio = (
        verifier_seconds / proposer_seconds
        if proposer_seconds
        else float("inf")
    )
    decision = (
        "TERMINAL_RESERVED_REVISION_TRANSACTION_GATE_PASS"
        if output_violations == 0
        and state_violations == 0
        and stale_results == 0
        and verifier_ratio < 0.8
        and online_speedup >= 4.0
        and gpu_normalized_speedup >= 2.0
        and (len(events) - deployed_slo_events) / len(events) < 0.01
        else "TERMINAL_RESERVED_REVISION_TRANSACTION_GATE_FAIL"
    )
    summary = {
        "event_count": len(events),
        "verified_events": verified_events,
        "verification_fraction": verified_events / len(events),
        "output_violation_events": output_violations,
        "state_projection_violation_events": state_violations,
        "stale_or_replayed_result_events": stale_results,
        "proposal_batches": len(proposal_batch_sizes),
        "proposal_batch_size_p50": statistics.median(proposal_batch_sizes),
        "proposal_batch_size_p95": percentile(proposal_batch_sizes, 0.95),
        "verification_batches": verification_batches,
        "verifier_lanes": args.verifier_lanes,
        "verifier_worker_events": verifier_worker_events,
        "terminal_burst_count": len(terminal_burst_sizes),
        "terminal_burst_size_max": (
            max(terminal_burst_sizes) if terminal_burst_sizes else 0
        ),
        "max_pending_verifications": max_pending,
        "proposer_service_seconds": proposer_seconds,
        "verifier_service_seconds": verifier_seconds,
        "proposer_gpu_terminal_verifier_seconds": (
            proposer_gpu_terminal_verifier_seconds
        ),
        "proposer_gpu_terminal_verified_events": (
            proposer_gpu_terminal_verified_events
        ),
        "verifier_to_proposer_service_ratio": verifier_ratio,
        "service_wall_seconds": service_wall_seconds,
        "canonical_audit_seconds_excluded_from_service": reference_seconds,
        "deployed_two_gpu_wall_speedup": online_speedup,
        "gpu_normalized_throughput_speedup": gpu_normalized_speedup,
        "state_entry_latency_seconds_p50": statistics.median(
            state_entry_latencies
        ),
        "state_entry_latency_seconds_p95": percentile(
            state_entry_latencies, 0.95
        ),
        "state_entry_latency_seconds_p99": percentile(
            state_entry_latencies, 0.99
        ),
        "state_entry_deadline_seconds": slo_seconds,
        "state_entry_deadline_miss_events": (
            len(events) - deployed_slo_events
        ),
        "state_entry_deadline_miss_rate": (
            (len(events) - deployed_slo_events) / len(events)
        ),
        "deployed_slo_goodput_events_per_second": deployed_slo_goodput,
        "canonical_slo_goodput_events_per_second": canonical_slo_goodput,
        "slo_goodput_speedup": (
            deployed_slo_goodput / canonical_slo_goodput
            if canonical_slo_goodput
            else float("inf")
        ),
        "verifier_wait_seconds_p50": (
            statistics.median(verifier_wait_seconds)
            if verifier_wait_seconds
            else 0.0
        ),
        "verifier_wait_seconds_p95": percentile(
            verifier_wait_seconds, 0.95
        ),
        "intermediate_verifier_wait_seconds_p95": percentile(
            verifier_wait_intermediate_seconds, 0.95
        ),
        "terminal_verifier_wait_seconds_p50": (
            statistics.median(verifier_wait_terminal_seconds)
            if verifier_wait_terminal_seconds
            else 0.0
        ),
        "terminal_verifier_wait_seconds_p95": percentile(
            verifier_wait_terminal_seconds, 0.95
        ),
        "verifier_request_seconds_p50": (
            statistics.median(verifier_request_seconds)
            if verifier_request_seconds
            else 0.0
        ),
        "service_energy": summarize_energy(
            service_power_samples,
            completed_audio_seconds=len(events) * 2.0,
        ),
        "canonical_audit_energy": summarize_energy(
            audit_power_samples,
            completed_audio_seconds=len(events) * 2.0,
        ),
    }
    payload = {
        "schema_version": 1,
        "study": "RevTrace terminal-canonical revision transaction gate",
        "decision": decision,
        "model_name": args.model_name,
        "dtype": args.dtype,
        "duration_seconds": args.duration_seconds,
        "concurrency": args.concurrency,
        "margin_threshold": args.margin_threshold,
        "arrival_mode": args.arrival_mode,
        "arrival_seed": args.arrival_seed,
        "arrival_scale_seconds": args.arrival_scale_seconds,
        "language_mode": args.language_mode,
        "contract": {
            "canonical": (
                "FP16 singleton for intermediate revisions; "
                f"{args.terminal_canonical_dtype} fixed-shape batch for "
                "terminal revisions"
                if args.terminal_canonical_dtype
                else "FP16 singleton execution"
            ),
            "state_entry": (
                "only a version-matched selected transition may update state"
            ),
            "terminal": (
                "terminal revisions execute on the fixed-shape canonical "
                "path concurrently with the non-authoritative proposer"
                if args.terminal_canonical_dtype
                else "all terminal revisions require canonical verification"
            ),
            "margin_boundary": (
                "empirical scheduling signal; not a deterministic certificate"
            ),
            "audit": (
                "fresh singleton replay after service; excluded from timing"
            ),
        },
        "summary": summary,
        "events": sorted(
            events,
            key=lambda item: (item["session_id"], item["chunk_id"]),
        ),
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "UNRECORDED"
            ),
            "proposer_gpu": args.proposer_gpu,
            "verifier_gpu": args.verifier_gpu,
            "proposer_pid": os.getpid(),
            "verifier_pids": [
                ready_by_worker[index]["pid"]
                for index in sorted(ready_by_worker)
            ],
            "verifier_lanes": args.verifier_lanes,
            "verifier_gpu_memory_utilization_per_lane": (
                verifier_memory_utilization
            ),
            "terminal_canonical_dtype": args.terminal_canonical_dtype,
            "terminal_canonical_batch_size": (
                args.terminal_canonical_batch_size
            ),
            "terminal_canonical_batch_invariant": (
                args.terminal_canonical_batch_invariant
            ),
        },
        "smoke": {
            "proposer": proposer_smoke,
            "verifiers": [
                ready_by_worker[index]["smoke"]
                for index in sorted(ready_by_worker)
            ],
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for command_queue in command_queues:
        command_queue.put({"kind": "stop"})
    stopped_workers: set[int] = set()
    while len(stopped_workers) < args.verifier_lanes:
        stopped = receive_or_raise(
            result_queue, args.result_timeout_seconds
        )
        if stopped.get("kind") != "stopped":
            raise RuntimeError(
                f"unexpected verifier shutdown result: {stopped}"
            )
        stopped_workers.add(int(stopped["worker_id"]))
    for verifier in verifiers:
        verifier.join(timeout=30.0)
        if verifier.is_alive():
            verifier.terminate()
            verifier.join(timeout=10.0)
            raise RuntimeError("verifier failed to stop cleanly")

    print(json.dumps({"decision": decision, **summary}, sort_keys=True))
    return 0 if decision.endswith("_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
