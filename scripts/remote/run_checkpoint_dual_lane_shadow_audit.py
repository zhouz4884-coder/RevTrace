#!/usr/bin/env python3
"""Anytime-valid randomized audit for checkpoint/rebase authority services."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import queue
import random
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
    parser.add_argument("--cross-lane-compatibility-artifact", type=Path)
    parser.add_argument("--burst-b2-compatibility-artifact", type=Path)
    parser.add_argument(
        "--dual-lane-intermediate-authority",
        action="store_true",
        help=(
            "Split nonterminal singleton authority across GPU0/GPU1. "
            "Without this flag, GPU1 is the only canonical authority and "
            "GPU0 remains an ordinary batched proposer."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-risk-entries", type=int, default=30_000)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--checkpoint-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--margin-threshold", type=float, required=True)
    parser.add_argument(
        "--low-margin-policy",
        choices=("verify", "holdback"),
        default="verify",
    )
    parser.add_argument("--audit-probability", type=float, default=0.021)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--max-model-length", type=int, default=4096)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def receive_many(
    result_queue: Any,
    expected: int,
    *,
    timeout: float,
) -> dict[str, dict[str, Any]]:
    by_ticket: dict[str, dict[str, Any]] = {}
    deadline = time.monotonic() + timeout
    while len(by_ticket) < expected:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"received {len(by_ticket)}/{expected} canonical results"
            )
        message = result_queue.get(timeout=remaining)
        if message.get("kind") == "error":
            raise RuntimeError(message["traceback"])
        if message.get("kind") != "verified_item":
            continue
        by_ticket[str(message["ticket"])] = message
    return by_ticket


def validate_cross_lane(
    path: Path,
    *,
    current_runtime_sha256: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    if payload.get("decision") != "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS":
        raise ValueError("cross-lane gate did not pass")
    if int(counts.get("pairs", 0)) < 720:
        raise ValueError("cross-lane gate is undersized")
    config = payload.get("config", {})
    if (
        config.get("gpu0_batch_invariant_runtime") is not True
        or config.get("gpu1_batch_invariant_runtime") is not True
    ):
        raise ValueError(
            "cross-lane gate does not match the deployed two-lane "
            "batch-invariant runtime"
        )
    if (
        config.get("gpu0_engine_logprobs") != 20
        or config.get("gpu0_singleton_logprobs") is not None
        or config.get("gpu1_singleton_logprobs") is not None
    ):
        raise ValueError(
            "cross-lane gate does not match deployed lane logprob settings"
        )
    if any(
        int(counts.get(key, -1)) != 0
        for key in (
            "token_exact_mismatches",
            "text_exact_mismatches",
            "state_projection_token_exact_mismatches",
            "state_projection_text_exact_mismatches",
        )
    ):
        raise ValueError("cross-lane gate contains mismatches")
    if current_runtime_sha256 is not None:
        from revtrace.runtime_contract import require_runtime_sha256

        require_runtime_sha256(payload, current_runtime_sha256)
    return payload


def validate_burst_b2(
    path: Path,
    *,
    current_runtime_sha256: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    config = payload.get("config", {})
    if payload.get("decision") != "BURST_B2_AUTHORITY_COMPATIBILITY_PASS":
        raise ValueError("B1/B2 authority gate did not pass")
    if int(counts.get("pairs", 0)) < 720:
        raise ValueError("B1/B2 authority gate is undersized")
    if (
        config.get("batch_invariant_runtime") is not True
        or int(config.get("singleton_shape", 0)) != 1
        or int(config.get("burst_fixed_shape", 0)) != 2
    ):
        raise ValueError("B1/B2 gate has an incompatible runtime contract")
    if any(
        int(counts.get(key, -1)) != 0
        for key in (
            "token_exact_mismatches",
            "text_exact_mismatches",
            "state_projection_token_exact_mismatches",
            "state_projection_text_exact_mismatches",
        )
    ):
        raise ValueError("B1/B2 authority gate contains mismatches")
    if current_runtime_sha256 is not None:
        from revtrace.runtime_contract import require_runtime_sha256

        require_runtime_sha256(
            {
                "environment": {
                    "batch_invariant_runtime_sha256": config[
                        "batch_invariant_runtime_sha256"
                    ]
                }
            },
            current_runtime_sha256,
        )
    return payload


def main() -> int:
    args = parse_args()
    if not 0.0 < args.audit_probability < 1.0:
        raise ValueError("audit probability must lie in (0,1)")
    if (
        args.duration_seconds <= 0
        or args.duration_seconds % args.checkpoint_seconds
        or args.checkpoint_seconds % 2
        or args.concurrency <= 0
        or args.target_risk_entries <= 0
    ):
        raise ValueError("invalid checkpoint audit configuration")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    from revtrace.runtime_contract import batch_invariant_runtime_sha256

    runtime_sha256 = batch_invariant_runtime_sha256()
    compatibility: dict[str, Any] | None = None
    compatibility_sha: str | None = None
    burst_compatibility: dict[str, Any] | None = None
    burst_compatibility_sha: str | None = None
    if args.dual_lane_intermediate_authority:
        if args.cross_lane_compatibility_artifact is None:
            raise ValueError(
                "dual-lane authority requires a cross-lane artifact"
            )
        compatibility = validate_cross_lane(
            args.cross_lane_compatibility_artifact,
            current_runtime_sha256=runtime_sha256,
        )
        compatibility_sha = sha256(
            args.cross_lane_compatibility_artifact
        )
    elif args.cross_lane_compatibility_artifact is not None:
        raise ValueError(
            "cross-lane artifact supplied without dual-lane authority"
        )
    if args.burst_b2_compatibility_artifact is not None:
        if args.dual_lane_intermediate_authority:
            raise ValueError("B2 burst authority and dual lane are exclusive")
        burst_compatibility = validate_burst_b2(
            args.burst_b2_compatibility_artifact,
            current_runtime_sha256=runtime_sha256,
        )
        burst_compatibility_sha = sha256(
            args.burst_b2_compatibility_artifact
        )

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
    from revtrace.risk import AuditRiskBound

    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    verifier = context.Process(
        target=verifier_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "gpu": args.verifier_gpu,
            "model": str(args.model),
            "dtype": "float16",
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.duration_seconds,
            "concurrency": args.concurrency,
            "worker_id": 1,
            "max_model_len": args.max_model_length,
            "terminal_canonical_batch_size": args.concurrency,
            "terminal_canonical_batch_invariant": True,
        },
        name="checkpoint-risk-verifier",
    )
    verifier.start()
    ready = result_queue.get(timeout=args.timeout_seconds)
    if ready.get("kind") == "error":
        raise RuntimeError(ready["traceback"])
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier startup: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    if args.dual_lane_intermediate_authority:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
        os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
    proposer = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=args.max_model_length,
        logprobs=20,
        max_num_seqs=args.concurrency,
    )
    from vllm import SamplingParams

    local_singleton_sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=None,
    )
    sources = load_sources(args.data_manifest)
    rng = random.Random(args.seed)
    target_samples = args.duration_seconds * SAMPLE_RATE
    silence_samples = args.silence_ms * SAMPLE_RATE // 1000
    chunk_samples = 2 * SAMPLE_RATE
    risk_entries = 0
    total_events = 0
    base_audits = 0
    caught_output_errors = 0
    caught_state_errors = 0
    mandatory_verifications = 0
    provisional_holdbacks = 0
    terminal_verifications = 0
    selected_authority_violations = 0
    lane_counts = {
        "gpu0_singleton": 0,
        "gpu1_singleton": 0,
        "gpu1_burst_b2": 0,
        "gpu1_fixed": 0,
    }
    burst_histogram: dict[str, int] = {}
    audit_records: list[dict[str, Any]] = []
    episodes = 0
    ticket_counter = 0
    started = time.perf_counter()

    try:
        while risk_entries < args.target_risk_entries:
            streams = []
            for position in range(args.concurrency):
                language = ("English", "Chinese")[
                    (episodes * args.concurrency + position) % 2
                ]
                pool = sources[language]
                audio, provenance = concatenate_distinct_audio(
                    pool,
                    target_samples=target_samples,
                    start_index=(
                        args.seed
                        + episodes * 1009
                        + position * 101
                    )
                    % len(pool),
                    silence_samples=silence_samples,
                )
                streams.append(
                    {
                        "session_id": f"e{episodes:04d}-s{position:02d}",
                        "language": language,
                        "audio": audio,
                        "provenance": provenance,
                    }
                )
            states = [
                proposer.init_streaming_state(
                    language=stream["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=2.0,
                )
                for stream in streams
            ]
            histories = ["" for _ in streams]
            for chunk_index in range(args.duration_seconds // 2):
                age_end = (chunk_index + 1) * 2
                session_terminal = age_end == args.duration_seconds
                checkpoint = checkpoint_due(
                    age_end,
                    args.checkpoint_seconds,
                )
                terminal = session_terminal or checkpoint
                jobs = []
                prefixes = []
                for stream, state in zip(streams, states):
                    begin = chunk_index * chunk_samples
                    end = begin + chunk_samples
                    job, prefix = prepare_job(
                        proposer,
                        state,
                        stream["audio"][begin:end],
                        tail=terminal,
                    )
                    jobs.append(job)
                    prefixes.append(prefix)

                selected_records: list[dict[str, Any]]
                selected_projections: list[dict[str, Any]]
                if terminal:
                    items = []
                    for position, job in enumerate(jobs):
                        ticket = f"t{ticket_counter:08d}"
                        ticket_counter += 1
                        items.append({"ticket": ticket, "job": job})
                    command_queue.put(
                        {
                            "kind": "canonical_batch",
                            "batch_id": f"terminal-{episodes}-{chunk_index}",
                            "items": items,
                            "fixed_shape": args.concurrency,
                        }
                    )
                    remote = receive_many(
                        result_queue,
                        len(items),
                        timeout=args.timeout_seconds,
                    )
                    selected_records = [
                        dict(remote[str(item["ticket"])]["record"])
                        for item in items
                    ]
                    selected_projections = [
                        state_projection_record(
                            proposer,
                            state,
                            prefix,
                            record,
                            terminal=True,
                        )
                        for state, prefix, record in zip(
                            states,
                            prefixes,
                            selected_records,
                        )
                    ]
                    mandatory_verifications += len(items)
                    terminal_verifications += len(items)
                    lane_counts["gpu1_fixed"] += len(items)
                else:
                    base_coins = [
                        rng.random() < args.audit_probability
                        for _ in streams
                    ]
                    outputs = proposer.model.generate(
                        jobs,
                        sampling_params=proposer.sampling_params,
                        use_tqdm=False,
                    )
                    proposal_records = [
                        candidate_record(output) for output in outputs
                    ]
                    proposal_projections = [
                        state_projection_record(
                            proposer,
                            state,
                            prefix,
                            record,
                            terminal=False,
                        )
                        for state, prefix, record in zip(
                            states,
                            prefixes,
                            proposal_records,
                        )
                    ]
                    selected_records = list(proposal_records)
                    selected_projections = list(proposal_projections)
                    metadata: dict[int, dict[str, Any]] = {}
                    verify_positions = []
                    holdback_positions: list[int] = []
                    for position, record in enumerate(proposal_records):
                        margin = record["minimum_margin"]
                        low_margin = (
                            margin is None
                            or float(margin) <= args.margin_threshold
                        )
                        eligible = not low_margin
                        audited = eligible and base_coins[position]
                        if eligible:
                            risk_entries += 1
                            base_audits += int(audited)
                        if low_margin and args.low_margin_policy == "holdback":
                            holdback_positions.append(position)
                            provisional_holdbacks += 1
                        else:
                            mandatory_verifications += int(low_margin)
                        if (
                            audited
                            or (
                                low_margin
                                and args.low_margin_policy == "verify"
                            )
                        ):
                            verify_positions.append(position)
                            metadata[position] = {
                                "audited": audited,
                                "mandatory": low_margin,
                                "minimum_margin": margin,
                                "proposal": record,
                                "proposal_projection": proposal_projections[
                                    position
                                ],
                            }
                    burst_histogram[str(len(verify_positions))] = (
                        burst_histogram.get(str(len(verify_positions)), 0) + 1
                    )
                    remote_positions = verify_positions
                    local_positions: list[int] = []
                    if (
                        args.dual_lane_intermediate_authority
                        and len(verify_positions) >= 2
                    ):
                        remote_positions = verify_positions[::2]
                        local_positions = verify_positions[1::2]
                    remote_items = []
                    remote_waves: list[tuple[str, list[dict[str, Any]], str]] = []
                    for position in remote_positions:
                        ticket = f"v{ticket_counter:08d}"
                        ticket_counter += 1
                        remote_items.append(
                            {
                                "ticket": ticket,
                                "position": position,
                                "job": jobs[position],
                            }
                        )
                    if remote_items:
                        if (
                            burst_compatibility is not None
                            and len(remote_items) >= 2
                        ):
                            for wave_index, begin in enumerate(
                                range(0, len(remote_items), 2)
                            ):
                                wave = remote_items[begin : begin + 2]
                                kind = (
                                    "canonical_batch"
                                    if len(wave) == 2
                                    else "verify"
                                )
                                remote_waves.append(
                                    (
                                        kind,
                                        wave,
                                        f"verify-{episodes}-{chunk_index}-"
                                        f"{wave_index}",
                                    )
                                )
                        else:
                            remote_waves.append(
                                (
                                    "verify",
                                    remote_items,
                                    f"verify-{episodes}-{chunk_index}",
                                )
                            )
                        for kind, wave, batch_id in remote_waves:
                            message = {
                                "kind": kind,
                                "batch_id": batch_id,
                                "items": [
                                    {
                                        "ticket": item["ticket"],
                                        "job": item["job"],
                                    }
                                    for item in wave
                                ],
                            }
                            if kind == "canonical_batch":
                                message["fixed_shape"] = 2
                            command_queue.put(message)
                    local_by_position = {}
                    for position in local_positions:
                        output = proposer.model.generate(
                            [jobs[position]],
                            sampling_params=local_singleton_sampling_params,
                            use_tqdm=False,
                        )[0]
                        local_by_position[position] = candidate_record(output)
                        lane_counts["gpu0_singleton"] += 1
                    remote_by_position = {}
                    if remote_items:
                        received = receive_many(
                            result_queue,
                            len(remote_items),
                            timeout=args.timeout_seconds,
                        )
                        for item in remote_items:
                            remote_by_position[item["position"]] = dict(
                                received[item["ticket"]]["record"]
                            )
                    for kind, wave, _ in remote_waves:
                        lane = (
                            "gpu1_burst_b2"
                            if kind == "canonical_batch"
                            else "gpu1_singleton"
                        )
                        lane_counts[lane] += len(wave)
                    for position in verify_positions:
                        canonical = (
                            local_by_position[position]
                            if position in local_by_position
                            else remote_by_position[position]
                        )
                        canonical_projection = state_projection_record(
                            proposer,
                            states[position],
                            prefixes[position],
                            canonical,
                            terminal=False,
                        )
                        comparison = compare_records(
                            {
                                **metadata[position]["proposal"],
                                "state_projection": metadata[position][
                                    "proposal_projection"
                                ],
                            },
                            {
                                **canonical,
                                "state_projection": canonical_projection,
                            },
                        )
                        if metadata[position]["audited"]:
                            output_error = not comparison["token_exact"]
                            state_error = not comparison[
                                "state_projection_token_exact"
                            ]
                            caught_output_errors += int(output_error)
                            caught_state_errors += int(state_error)
                            audit_records.append(
                                {
                                    "episode": episodes,
                                    "chunk_index": chunk_index,
                                    "session_id": streams[position][
                                        "session_id"
                                    ],
                                    "minimum_margin": metadata[position][
                                        "minimum_margin"
                                    ],
                                    "output_error": output_error,
                                    "state_error": state_error,
                                    "lane": (
                                        "gpu0_singleton"
                                        if position in local_by_position
                                        else (
                                            "gpu1_burst_b2"
                                            if (
                                                burst_compatibility is not None
                                                and any(
                                                    position
                                                    == int(item["position"])
                                                    for kind, wave, _ in remote_waves
                                                    if kind == "canonical_batch"
                                                    for item in wave
                                                )
                                            )
                                            else "gpu1_singleton"
                                        )
                                    ),
                                }
                            )
                        selected_records[position] = canonical
                        selected_projections[position] = canonical_projection

                for position, (state, prefix, record, projection) in enumerate(
                    zip(
                        states,
                        prefixes,
                        selected_records,
                        selected_projections,
                    )
                ):
                    if record is None:
                        selected_authority_violations += 1
                        continue
                    if (
                        not terminal
                        and position in holdback_positions
                    ):
                        # The audio frontier has advanced in prepare_job, but
                        # the low-margin textual proposal remains provisional
                        # and never enters revision feedback state.
                        pass
                    else:
                        apply_candidate_record(state, record, prefix)
                    if checkpoint:
                        payload = checkpoint_payload(
                            prefix=prefix,
                            selected=record,
                            selected_projection=projection,
                        )
                        histories[position] = append_checkpoint_history(
                            histories[position],
                            payload,
                        )
                        if not session_terminal:
                            states[position] = proposer.init_streaming_state(
                                context=histories[position],
                                language=streams[position]["language"],
                                unfixed_chunk_num=2,
                                unfixed_token_num=5,
                                chunk_size_sec=2.0,
                            )
                total_events += len(streams)
            episodes += 1
            print(
                json.dumps(
                    {
                        "episodes": episodes,
                        "risk_entries": risk_entries,
                        "base_audits": base_audits,
                        "caught_state_errors": caught_state_errors,
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
                stopped = result_queue.get(timeout=30.0)
                if stopped.get("kind") == "stopped":
                    break
        except queue.Empty:
            pass
        verifier.join(timeout=30.0)
        if verifier.is_alive():
            verifier.terminate()
            verifier.join()

    bound = AuditRiskBound(args.audit_probability, args.alpha)
    upper_error_count = bound.upper_error_count(
        risk_entries,
        caught_state_errors,
    )
    upper_risk = upper_error_count / risk_entries
    passed = bool(
        risk_entries >= args.target_risk_entries
        and base_audits >= 500
        and upper_risk <= args.delta
        and selected_authority_violations == 0
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
        "study": "Checkpoint/Rebase randomized base audit",
        "decision": (
            "CHECKPOINT_ANYTIME_RISK_PASS"
            if passed
            else "CHECKPOINT_ANYTIME_RISK_FAIL"
        ),
        "model": args.model_name,
        "contract": {
            "duration_seconds": args.duration_seconds,
            "checkpoint_seconds": args.checkpoint_seconds,
            "concurrency": args.concurrency,
            "dtype": "float16",
            "margin_threshold": args.margin_threshold,
            "low_margin_policy": args.low_margin_policy,
            "intermediate_authority": (
                "dual_singleton_gpu0_gpu1_v1"
                if args.dual_lane_intermediate_authority
                else (
                    "gpu1_singleton_plus_fixed_b2_burst_v1"
                    if burst_compatibility is not None
                    else "gpu1_singleton_v1"
                )
            ),
            "terminal_authority": f"gpu1_fixed_b{args.concurrency}",
            "checkpoint_payload": "terminal_state_projection_v1",
            "cross_lane_compatibility_sha256": compatibility_sha,
            "batch_invariant_runtime_sha256": runtime_sha256,
            "cross_lane_pairs": (
                compatibility["counts"]["pairs"]
                if compatibility is not None
                else None
            ),
            "burst_b2_compatibility_sha256": burst_compatibility_sha,
            "burst_b2_pairs": (
                burst_compatibility["counts"]["pairs"]
                if burst_compatibility is not None
                else None
            ),
        },
        "audit_design": {
            "audit_probability": args.audit_probability,
            "alpha": args.alpha,
            "delta": args.delta,
            "coin_timing": (
                "drawn before proposer and canonical outcomes"
            ),
            "method": "fixed-probability mixture e-process inversion",
            "dependence": (
                "error events may depend arbitrarily across sessions, rounds, "
                "and checkpoints; only base audit coins are independent"
            ),
        },
        "counts": {
            "episodes": episodes,
            "total_revision_events": total_events,
            "risk_eligible_state_entries": risk_entries,
            "base_audits": base_audits,
            "mandatory_verifications": mandatory_verifications,
            "provisional_holdbacks": provisional_holdbacks,
            "terminal_verifications": terminal_verifications,
            "caught_output_errors": caught_output_errors,
            "caught_state_errors": caught_state_errors,
            "selected_authority_violations": selected_authority_violations,
        },
        "risk_certificate": {
            "upper_error_count": upper_error_count,
            "upper_risk": upper_risk,
            "confidence": 1.0 - args.alpha,
            "target_delta": args.delta,
            "method": "fixed-probability mixture e-process inversion",
        },
        "lane_counts": lane_counts,
        "verification_burst_histogram": burst_histogram,
        "audit_records": audit_records,
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
            "The time-uniform risk statement uses independent fixed-probability "
            "base-audit coins; revision events themselves need not be iid.",
            "Post-stage replay is not used to construct the formal risk bound.",
            "This is a statistical state-disagreement contract relative to the "
            "frozen canonical runtime, not deterministic arithmetic proof.",
            "The audit is diagnostic evidence and is not a service-latency run.",
        ],
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["risk_certificate"], sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
