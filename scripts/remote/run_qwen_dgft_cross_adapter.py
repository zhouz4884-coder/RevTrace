#!/usr/bin/env python3
"""Qwen cross-adapter gate for DGFT and RevOCC composition.

GPU 0 executes three fine 2-second FP16 batched revisions from the last
committed macro-state.  Concurrently, GPU 1 executes one FP16 singleton
authority over the same 6-second audio frontier.  The coarse authority may be
installed directly (DGFT) or replaced by a native 2-second singleton replay
when the frozen directional/numerical evidence policy requests it (hybrid).

The experiment does not claim that a 6-second authority equals Qwen's official
2-second singleton trajectory.  A fresh 2-second singleton audit is reported
as an independent reference so that semantic drift cannot be hidden by merely
renaming the authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
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
    parser.add_argument("--mode", choices=("dgft", "hybrid"), required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--fine-window-seconds", type=int, default=2)
    parser.add_argument("--windows-per-segment", type=int, default=3)
    parser.add_argument("--forward-threshold", type=float, default=0.20)
    parser.add_argument("--reverse-ceiling", type=float, default=0.20)
    parser.add_argument("--risk-margin", type=float, default=0.05)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--authority-gpu", default="1")
    parser.add_argument(
        "--authority-dtype", choices=("float16", "float32"), default="float16"
    )
    parser.add_argument(
        "--authority-execution", choices=("singleton", "batch"),
        default="singleton",
    )
    parser.add_argument(
        "--audit-first-authority-segment", action="store_true",
        help="repeat the first authority batch and compare every row with singleton",
    )
    parser.add_argument(
        "--hybrid-terminal-fine-replay", action="store_true",
        help="require the native fine singleton path at terminal boundaries",
    )
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--authority-memory-utilization", type=float, default=0.82)
    parser.add_argument("--authority-max-model-len", type=int, default=4096)
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--contract-epoch", type=int, default=10)
    parser.add_argument("--policy-version", default="r10-qwen-cross-v1")
    parser.add_argument("--seed", type=int, default=20260803)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def authority_worker(
    command_queue: Any,
    result_queue: Any,
    *,
    model: str,
    gpu: str,
    memory_utilization: float,
    data_manifest: str,
    dtype: str,
    execution: str,
    audit_first_segment: bool,
    max_model_len: int,
) -> None:
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu
        script_dir = str(Path(__file__).resolve().parent)
        source_dir = str(Path(__file__).resolve().parents[2] / "src")
        for entry in (script_dir, source_dir):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        from run_revbatch_gate import load_sources, official_smoke
        from run_revguard_same_input import candidate_record
        from run_revtrace_dual_gpu import build_asr, singleton_records

        asr = build_asr(
            model, dtype, memory_utilization,
            max_model_len=max_model_len, logprobs=20,
            max_num_seqs=128,
        )
        sources = load_sources(Path(data_manifest))
        smoke = official_smoke(asr, sources["English"][0])
        if not smoke["exact"]:
            raise AssertionError("authority official-semantics smoke failed")
        result_queue.put({"kind": "ready", "pid": os.getpid(), "smoke": smoke})
        while True:
            message = command_queue.get()
            if message["kind"] == "stop":
                result_queue.put({"kind": "stopped"})
                return
            if message["kind"] != "segment":
                raise ValueError(f"unknown authority command: {message['kind']}")
            jobs = message["jobs"]
            if execution == "singleton":
                outputs, elapsed, request_seconds = singleton_records(asr, jobs)
            else:
                started = time.perf_counter()
                outputs = asr.model.generate(
                    jobs, sampling_params=asr.sampling_params, use_tqdm=False
                )
                elapsed = time.perf_counter() - started
                request_seconds = [elapsed / len(jobs) for _ in jobs]
            records = [candidate_record(output) for output in outputs]
            invariance = {
                "audited": False,
                "batch_repeat_mismatches": 0,
                "batch_vs_singleton_mismatches": 0,
            }
            if (
                audit_first_segment
                and execution == "batch"
                and int(message["segment_index"]) == 0
            ):
                repeat_outputs = asr.model.generate(
                    jobs, sampling_params=asr.sampling_params, use_tqdm=False
                )
                repeat_records = [
                    candidate_record(output) for output in repeat_outputs
                ]
                singleton_outputs, _, _ = singleton_records(asr, jobs)
                singleton_rows = [
                    candidate_record(output) for output in singleton_outputs
                ]
                invariance = {
                    "audited": True,
                    "batch_repeat_mismatches": sum(
                        left["token_ids"] != right["token_ids"]
                        for left, right in zip(records, repeat_records)
                    ),
                    "batch_vs_singleton_mismatches": sum(
                        left["token_ids"] != right["token_ids"]
                        for left, right in zip(records, singleton_rows)
                    ),
                }
            result_queue.put({
                "kind": "segment-result",
                "segment_index": message["segment_index"],
                "elapsed_seconds": elapsed,
                "request_seconds": request_seconds,
                "records": records,
                "invariance": invariance,
            })
    except BaseException as exc:
        result_queue.put({
            "kind": "error",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        })


def receive(result_queue: Any, timeout: float) -> dict[str, Any]:
    try:
        message = result_queue.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError("authority result timeout") from exc
    if message.get("kind") == "error":
        raise RuntimeError(f"authority failed: {message['error']}\n{message['traceback']}")
    return message


def main() -> int:
    args = parse_args()
    segment_seconds = args.fine_window_seconds * args.windows_per_segment
    if args.duration_seconds % segment_seconds:
        raise ValueError("duration must be divisible by the macro-segment size")
    if args.fine_window_seconds != 2:
        raise ValueError("the frozen Qwen native revision is 2 seconds")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parents[2]
    script_dir = str(Path(__file__).resolve().parent)
    for entry in (script_dir, str(root / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)

    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    worker = context.Process(
        target=authority_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "model": str(args.model),
            "gpu": args.authority_gpu,
            "memory_utilization": args.authority_memory_utilization,
            "data_manifest": str(args.data_manifest),
            "dtype": args.authority_dtype,
            "execution": args.authority_execution,
            "audit_first_segment": args.audit_first_authority_segment,
            "max_model_len": args.authority_max_model_len,
        },
        name="qwen-dgft-authority",
    )
    worker.start()
    ready = receive(result_queue, args.result_timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected authority initialization: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    import numpy as np
    from qwen_asr import parse_asr_output
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
    from run_revtrace_dual_gpu import build_asr, singleton_records
    from revtrace.core import RevisionCommitLedger
    from revtrace.cross_adapter import (
        decide_qwen_cross_adapter,
        normalized_boundary_chunk_id,
        unit_edit_rate,
    )
    from revtrace.dgft import (
        CanonicalSegmentJob,
        FeedbackTransactionState,
        build_dual_axis_certificate,
        commit_canonical_segment,
        digest_bytes,
        digest_tokens,
    )
    from revtrace.phase5 import NvidiaPowerSampler, summarize_energy

    sources = load_sources(args.data_manifest)
    streams = make_streams(
        sources, duration=args.duration_seconds, concurrency=args.concurrency
    )
    proposer = build_asr(
        str(args.model), "float16", args.gpu_memory_utilization, logprobs=20
    )
    smoke = official_smoke(proposer, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    states = [
        proposer.init_streaming_state(
            language=stream["language"], unfixed_chunk_num=2,
            unfixed_token_num=5, chunk_size_sec=2.0,
        )
        for stream in streams
    ]
    ledger = RevisionCommitLedger()
    tx_states: list[FeedbackTransactionState] = []
    contract = {
        "mode": args.mode,
        "model": args.model_name,
        "fine_window_seconds": args.fine_window_seconds,
        "windows_per_segment": args.windows_per_segment,
        "forward_threshold": args.forward_threshold,
        "reverse_ceiling": args.reverse_ceiling,
        "risk_margin": args.risk_margin,
        "policy_version": args.policy_version,
        "contract_epoch": args.contract_epoch,
        "authority_dtype": args.authority_dtype,
        "authority_execution": args.authority_execution,
        "authority_first_segment_invariance_audit": (
            args.audit_first_authority_segment
        ),
        "authority_max_model_len": args.authority_max_model_len,
        "hybrid_terminal_fine_replay": args.hybrid_terminal_fine_replay,
    }
    contract_digest = canonical_digest(contract)
    runtime_digest = (
        f"qwen-{args.authority_dtype}-{args.authority_execution}-segment-v1"
    )
    for index, stream in enumerate(streams):
        ledger.register(stream["session_id"])
        tx_states.append(FeedbackTransactionState(
            session_id=index,
            contract_epoch=args.contract_epoch,
            policy_version=args.policy_version,
            contract_digest=contract_digest,
            canonical_runtime_digest=runtime_digest,
            prompt_tokens=(),
            speculative_version=0,
        ))

    segment_samples = segment_seconds * SAMPLE_RATE
    fine_samples = args.fine_window_seconds * SAMPLE_RATE
    segments = args.duration_seconds // segment_seconds
    events: list[dict[str, Any]] = []
    display_latencies: list[float] = []
    commit_latencies: list[float] = []
    proposer_seconds = 0.0
    authority_seconds = 0.0
    authority_request_seconds: list[float] = []
    replay_seconds = 0.0
    replay_segments = 0
    transaction_violations = 0
    authority_batch_repeat_mismatches = 0
    authority_batch_vs_singleton_mismatches = 0

    service_power = NvidiaPowerSampler(
        [int(args.proposer_gpu), int(args.authority_gpu)],
        interval_seconds=0.1,
    )
    service_power.start()
    service_started = time.perf_counter()

    for segment_index in range(segments):
        segment_started = time.perf_counter()
        boundary_states = [copy.deepcopy(state) for state in states]
        coarse_states = [copy.deepcopy(state) for state in states]
        coarse_prefixes: list[str] = []
        coarse_jobs: list[dict[str, Any]] = []
        segment_audio: list[np.ndarray] = []
        begin = segment_index * segment_samples
        end = begin + segment_samples
        for stream, state in zip(streams, coarse_states):
            audio = np.asarray(stream["audio"][begin:end], dtype=np.float32)
            segment_audio.append(audio)
            state.audio_accum = (
                np.concatenate([state.audio_accum, audio])
                if state.audio_accum.size else audio.copy()
            )
            prefix = rollback_prefix(proposer, state, tail=False)
            coarse_prefixes.append(prefix)
            coarse_jobs.append({
                "prompt": state.prompt_raw + prefix,
                "multi_modal_data": {"audio": [state.audio_accum]},
            })

        command_queue.put({
            "kind": "segment",
            "segment_index": segment_index,
            "jobs": coarse_jobs,
        })

        fine_states = [copy.deepcopy(state) for state in boundary_states]
        fine_records: list[list[dict[str, Any]]] = [
            [] for _ in streams
        ]
        fine_group_started = time.perf_counter()
        for local_window in range(args.windows_per_segment):
            jobs: list[dict[str, Any]] = []
            prefixes: list[str] = []
            window_started = time.perf_counter()
            for stream, state in zip(streams, fine_states):
                window_begin = begin + local_window * fine_samples
                window_end = window_begin + fine_samples
                job, prefix = prepare_job(
                    proposer, state, stream["audio"][window_begin:window_end],
                    tail=False,
                )
                jobs.append(job)
                prefixes.append(prefix)
            generation_started = time.perf_counter()
            outputs = proposer.model.generate(
                jobs, sampling_params=proposer.sampling_params, use_tqdm=False
            )
            generation_elapsed = time.perf_counter() - generation_started
            proposer_seconds += generation_elapsed
            display_latencies.extend(
                [time.perf_counter() - window_started] * len(streams)
            )
            for index, (state, output, prefix) in enumerate(zip(
                fine_states, outputs, prefixes
            )):
                record = candidate_record(output)
                fine_records[index].append(record)
                apply_output(state, output, prefix)
        fine_group_seconds = time.perf_counter() - fine_group_started

        authority = receive(result_queue, args.result_timeout_seconds)
        if authority.get("kind") != "segment-result":
            raise RuntimeError(f"unexpected authority result: {authority}")
        if int(authority["segment_index"]) != segment_index:
            raise RuntimeError("out-of-order authority segment")
        authority_seconds += float(authority["elapsed_seconds"])
        authority_request_seconds.extend(
            float(value) for value in authority["request_seconds"]
        )
        invariance = authority.get("invariance", {})
        authority_batch_repeat_mismatches += int(
            invariance.get("batch_repeat_mismatches", 0)
        )
        authority_batch_vs_singleton_mismatches += int(
            invariance.get("batch_vs_singleton_mismatches", 0)
        )

        for index, (stream, boundary, fine_state, coarse_state, prefix,
                    coarse_record, audio) in enumerate(zip(
            streams, boundary_states, fine_states, coarse_states,
            coarse_prefixes, authority["records"], segment_audio,
        )):
            coarse_state._raw_decoded = prefix + str(coarse_record["text"])
            language, text = parse_asr_output(
                coarse_state._raw_decoded,
                user_language=coarse_state.force_language,
            )
            coarse_state.language = language
            coarse_state.text = text
            coarse_state.chunk_id = normalized_boundary_chunk_id(
                boundary.chunk_id, args.windows_per_segment
            )
            fine_margin = min(
                float(row["minimum_margin"]) for row in fine_records[index]
            )
            terminal = segment_index == segments - 1
            decision = decide_qwen_cross_adapter(
                fine_text=fine_state.text,
                coarse_text=coarse_state.text,
                fine_minimum_margin=fine_margin,
                mode=args.mode,
                forward_threshold=args.forward_threshold,
                reverse_ceiling=args.reverse_ceiling,
                risk_margin=args.risk_margin,
                terminal=(terminal and args.hybrid_terminal_fine_replay),
            )

            selected_state = coarse_state
            selected_record = coarse_record
            replay_elapsed = 0.0
            if decision.replay_required:
                replay_segments += 1
                replay_state = copy.deepcopy(boundary)
                replay_started = time.perf_counter()
                last_record: dict[str, Any] | None = None
                for local_window in range(args.windows_per_segment):
                    window_begin = local_window * fine_samples
                    window_end = window_begin + fine_samples
                    job, replay_prefix = prepare_job(
                        proposer, replay_state,
                        audio[window_begin:window_end], tail=False,
                    )
                    outputs, _, _ = singleton_records(proposer, [job])
                    last_record = candidate_record(outputs[0])
                    apply_output(replay_state, outputs[0], replay_prefix)
                replay_elapsed = time.perf_counter() - replay_started
                replay_seconds += replay_elapsed
                if last_record is None:
                    raise AssertionError("empty fine replay")
                selected_state = replay_state
                selected_record = last_record

            revision_id = f"{stream['session_id']}:segment:{segment_index}"
            ticket = ledger.issue(stream["session_id"], revision_id)
            tx_state = tx_states[index]
            prompt_tokens = tuple(
                int(token) for token in proposer.processor.tokenizer.encode(
                    selected_state._raw_decoded
                )
            )
            job = CanonicalSegmentJob(
                session_id=index,
                contract_epoch=args.contract_epoch,
                policy_version=args.policy_version,
                parent_checkpoint_id=tx_state.checkpoint_id,
                audio_start_window=segment_index * args.windows_per_segment,
                audio_end_window=(segment_index + 1) * args.windows_per_segment,
                segment_id=revision_id,
                prompt_digest=digest_tokens(tx_state.prompt_tokens),
                contract_digest=contract_digest,
                canonical_runtime_digest=runtime_digest,
                audio_sha256=digest_bytes(audio.tobytes()),
            )
            selected_tokens = tuple(
                int(token) for token in selected_record["token_ids"]
            )
            certificate = build_dual_axis_certificate(
                job=job,
                audio=audio.tobytes(),
                display_tokens=selected_tokens,
                feedback_state_tokens=prompt_tokens,
                canonical_runtime_digest=runtime_digest,
            )
            committed = commit_canonical_segment(
                tx_state,
                job,
                certificate=certificate,
                display_tokens=selected_tokens,
                segment_tokens=selected_tokens,
                next_prompt_tokens=prompt_tokens,
                descendant_versions=(ticket.next_version,),
            )
            if not committed.accepted or not ledger.can_commit(ticket):
                transaction_violations += 1
                raise AssertionError(
                    f"transaction commit rejected: {committed.reason}"
                )
            ledger.commit(ticket)
            tx_states[index] = committed.state
            states[index] = selected_state
            if ledger.version(stream["session_id"]) != segment_index + 1:
                transaction_violations += 1
                raise AssertionError("ledger segment version drift")
            events.append({
                "session_id": stream["session_id"],
                "segment_index": segment_index,
                "audio_start_seconds": segment_index * segment_seconds,
                "audio_end_seconds": (segment_index + 1) * segment_seconds,
                "selected_authority": decision.selected_authority,
                "reasons": list(decision.reasons),
                "fine_minimum_margin": fine_margin,
                "forward_deficit": decision.forward_deficit,
                "reverse_deficit": decision.reverse_deficit,
                "fine_text": fine_state.text,
                "coarse_text": coarse_state.text,
                "selected_text": selected_state.text,
                "replay_seconds": replay_elapsed,
                "transaction_certificate_digest": canonical_digest(
                    certificate.__dict__
                ),
                "committed_checkpoint_id": committed.state.checkpoint_id,
            })
        commit_latencies.extend(
            [time.perf_counter() - segment_started] * len(streams)
        )
        print(json.dumps({
            "model": args.model_name,
            "mode": args.mode,
            "segment": segment_index + 1,
            "segments": segments,
            "fine_group_seconds": fine_group_seconds,
            "authority_seconds": authority["elapsed_seconds"],
            "replays": replay_segments,
        }, sort_keys=True), flush=True)

    service_wall_seconds = time.perf_counter() - service_started
    service_power_samples = service_power.stop()
    command_queue.put({"kind": "stop"})
    stopped = receive(result_queue, args.result_timeout_seconds)
    if stopped.get("kind") != "stopped":
        raise RuntimeError(f"unexpected authority stop result: {stopped}")
    worker.join(timeout=30)
    if worker.exitcode not in (0, None):
        raise RuntimeError(f"authority exited with code {worker.exitcode}")

    reference_power = NvidiaPowerSampler(
        [int(args.proposer_gpu)], interval_seconds=0.1
    )
    reference_power.start()
    reference_started = time.perf_counter()
    reference_states = [
        proposer.init_streaming_state(
            language=stream["language"], unfixed_chunk_num=2,
            unfixed_token_num=5, chunk_size_sec=2.0,
        )
        for stream in streams
    ]
    reference_request_seconds: list[float] = []
    total_windows = args.duration_seconds // args.fine_window_seconds
    for window in range(total_windows):
        for stream, state in zip(streams, reference_states):
            begin = window * fine_samples
            end = begin + fine_samples
            job, prefix = prepare_job(
                proposer, state, stream["audio"][begin:end], tail=False
            )
            outputs, _, requests = singleton_records(proposer, [job])
            reference_request_seconds.extend(requests)
            apply_output(state, outputs[0], prefix)
    reference_seconds = time.perf_counter() - reference_started
    reference_power_samples = reference_power.stop()

    final_rows: list[dict[str, Any]] = []
    for stream, selected, reference in zip(streams, states, reference_states):
        error = unit_edit_rate(reference.text, selected.text)
        final_rows.append({
            "session_id": stream["session_id"],
            "language": stream["language"],
            "selected_text": selected.text,
            "reference_text": reference.text,
            "exact": selected.text == reference.text,
            "unit_edit_rate": error,
        })

    audio_seconds = args.duration_seconds * args.concurrency
    service_energy = summarize_energy(
        service_power_samples, completed_audio_seconds=audio_seconds
    )
    reference_energy = summarize_energy(
        reference_power_samples, completed_audio_seconds=audio_seconds
    )
    errors = [float(row["unit_edit_rate"]) for row in final_rows]
    wall_speedup = reference_seconds / service_wall_seconds
    gpu_normalized = reference_seconds / (2.0 * service_wall_seconds)
    decision = (
        "PASS_QWEN_CROSS_ADAPTER_GATE"
        if transaction_violations == 0
        and authority_batch_repeat_mismatches == 0
        and authority_batch_vs_singleton_mismatches == 0
        and wall_speedup >= 2.0
        and gpu_normalized >= 1.0
        and statistics.median(errors) <= 0.05
        and percentile(errors, 0.95) <= 0.20
        and not any(error > 0.25 for error in errors)
        else "FAIL_QWEN_CROSS_ADAPTER_GATE"
    )
    payload = {
        "schema_version": 1,
        "study": "R10 Qwen DGFT/RevOCC cross-adapter gate",
        "decision": decision,
        "model": args.model_name,
        "mode": args.mode,
        "contract": contract,
        "contract_digest": contract_digest,
        "summary": {
            "segments": segments,
            "events": len(events),
            "transaction_install_violations": transaction_violations,
            "authority_batch_repeat_mismatches": (
                authority_batch_repeat_mismatches
            ),
            "authority_batch_vs_singleton_mismatches": (
                authority_batch_vs_singleton_mismatches
            ),
            "coarse_authority_fraction": sum(
                row["selected_authority"] == "coarse-segment" for row in events
            ) / len(events),
            "fine_replay_fraction": replay_segments / len(events),
            "directional_omission_events": sum(
                "directional-omission" in row["reasons"] for row in events
            ),
            "numerical_risk_events": sum(
                "fine-numerical-risk" in row["reasons"] for row in events
            ),
            "terminal_finalization_events": sum(
                "terminal-finalization" in row["reasons"] for row in events
            ),
            "service_wall_seconds": service_wall_seconds,
            "reference_singleton_seconds": reference_seconds,
            "deployed_wall_speedup": wall_speedup,
            "gpu_normalized_speedup": gpu_normalized,
            "proposer_service_seconds": proposer_seconds,
            "coarse_authority_service_seconds": authority_seconds,
            "fine_replay_service_seconds": replay_seconds,
            "authority_to_proposer_ratio": (
                authority_seconds / proposer_seconds if proposer_seconds else None
            ),
            "display_latency_seconds_p99": percentile(display_latencies, 0.99),
            "segment_commit_latency_seconds_p99": percentile(commit_latencies, 0.99),
            "reference_request_seconds_p99": percentile(
                reference_request_seconds, 0.99
            ),
            "final_exact_sessions": sum(row["exact"] for row in final_rows),
            "final_sessions": len(final_rows),
            "final_unit_edit_rate_median": statistics.median(errors),
            "final_unit_edit_rate_p95": percentile(errors, 0.95),
            "final_unit_edit_rate_max": max(errors),
            "catastrophic_sessions_over_0_25": sum(error > 0.25 for error in errors),
            "service_energy": service_energy,
            "reference_energy": reference_energy,
            "energy_reduction_fraction": 1.0 - (
                service_energy["joules_per_audio_second"]
                / reference_energy["joules_per_audio_second"]
            ),
        },
        "events": events,
        "final_comparison": final_rows,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get("REVTRACE_CODE_COMMIT", "UNRECORDED"),
            "proposer_gpu": args.proposer_gpu,
            "authority_gpu": args.authority_gpu,
            "authority_pid": ready["pid"],
            "authority_dtype": args.authority_dtype,
            "authority_execution": args.authority_execution,
            "authority_max_model_len": args.authority_max_model_len,
            "source_sha256": {
                "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "cross_adapter": hashlib.sha256(
                    (root / "src/revtrace/cross_adapter.py").read_bytes()
                ).hexdigest(),
                "dgft": hashlib.sha256(
                    (root / "src/revtrace/dgft.py").read_bytes()
                ).hexdigest(),
            },
        },
        "claim_boundary": {
            "authority": (
                f"coarse {args.authority_dtype} {args.authority_execution} "
                "segment or native fine singleton replay"
            ),
            "reference": "fresh official 2-second FP16 singleton trajectory",
            "coverage_signal": "reference-free scheduler, not a correctness certificate",
            "scope": "bounded cross-adapter compatibility gate, not production prevalence",
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": decision,
        "model": args.model_name,
        "mode": args.mode,
        **payload["summary"],
    }, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if decision.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
