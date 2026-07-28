#!/usr/bin/env python3
"""Persistent-process c16 -> c64 -> c16 live adaptation gate.

The proposer and verifier are loaded once.  A contract switch creates a fresh
controller epoch, immediately forces all state entries through the fixed-shape
canonical path, and expands the fast path only after the new epoch has enough
split-sample evidence.  Post-stage canonical replay is excluded from service
timing and checks every selected state transition.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import queue
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-audits", type=int, default=1350)
    parser.add_argument("--episode-seconds", type=int, default=30)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--canonical-batch-size", type=int, default=16)
    parser.add_argument(
        "--canonical-dtype",
        choices=("float16", "float32"),
        default="float32",
    )
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="LABEL:CONCURRENCY:EPISODES",
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


class PowerSampler:
    def __init__(self, gpu_ids: tuple[int, ...], interval: float = 0.1) -> None:
        self.gpu_ids = gpu_ids
        self.interval = interval
        self.samples: list[dict[str, float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        started = time.perf_counter()

        def collect() -> None:
            while not self._stop.is_set():
                completed = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,power.draw",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                total = 0.0
                if completed.returncode == 0:
                    for line in completed.stdout.splitlines():
                        fields = [item.strip() for item in line.split(",")]
                        if len(fields) == 2 and int(fields[0]) in self.gpu_ids:
                            total += float(fields[1])
                    self.samples.append(
                        {
                            "time": time.perf_counter() - started,
                            "power_watts": total,
                        }
                    )
                self._stop.wait(self.interval)

        self._thread = threading.Thread(target=collect, daemon=True)
        self._thread.start()

    def stop(self) -> list[dict[str, float]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        return self.samples


def parse_stages(values: list[str]) -> list[tuple[str, int, int]]:
    source = values or [
        "c16_initial:16:8",
        "c64_drift:64:3",
        "c16_return:16:8",
    ]
    stages = []
    for value in source:
        label, concurrency, episodes = value.split(":")
        stages.append((label, int(concurrency), int(episodes)))
    return stages


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
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
        compare_records,
        state_projection_record,
    )
    from run_revtrace_dual_gpu import (
        build_asr,
        receive_or_raise,
        verifier_worker,
    )
    from revtrace.phase5 import (
        LiveRiskWindowController,
        summarize_energy,
    )

    stages = parse_stages(args.stage)
    max_concurrency = max(item[1] for item in stages)
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
            "dtype": args.canonical_dtype,
            "gpu_memory_utilization": 0.82,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.episode_seconds,
            "concurrency": max_concurrency,
            "worker_id": 0,
            "max_model_len": 4096,
            "terminal_canonical_batch_size": max_concurrency,
            "terminal_canonical_batch_invariant": (
                args.canonical_dtype != "float32"
            ),
        },
        name="phase5a-canonical-verifier",
    )
    verifier.start()
    ready = receive_or_raise(result_queue, args.result_timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier ready message: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    asr = build_asr(str(args.model), "float16", 0.82)
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    controller = LiveRiskWindowController(
        minimum_audits=args.minimum_audits
    )
    batch_id = 0

    def dispatch_canonical_batch(
        jobs: list[dict[str, Any]],
        *,
        fixed_shape: int,
    ) -> tuple[int, int]:
        nonlocal batch_id
        if not jobs or len(jobs) > fixed_shape:
            raise ValueError("canonical dispatch must fit one fixed shape")
        current_batch_id = batch_id
        items = [
            {
                "ticket": {
                    "session_id": f"canonical-{batch_id}-{position}",
                    "revision_id": f"canonical-{batch_id}-{position}",
                    "parent_version": 0,
                    "next_version": 1,
                },
                "job": job,
            }
            for position, job in enumerate(jobs)
        ]
        command_queue.put(
            {
                "kind": "canonical_batch",
                "batch_id": batch_id,
                "items": items,
                "fixed_shape": fixed_shape,
            }
        )
        batch_id += 1
        return current_batch_id, len(items)

    def collect_canonical_batch(
        dispatched: tuple[int, int],
    ) -> tuple[list[dict[str, Any]], float]:
        expected_batch_id, item_count = dispatched
        elapsed = 0.0
        by_position: list[dict[str, Any] | None] = [
            None for _ in range(item_count)
        ]
        for _ in range(item_count):
            message = receive_or_raise(
                result_queue, args.result_timeout_seconds
            )
            if (
                message.get("kind") != "verified_item"
                or int(message["batch_id"]) != expected_batch_id
            ):
                raise RuntimeError(
                    f"unexpected canonical result: {message}"
                )
            by_position[int(message["position"])] = message["record"]
            elapsed += float(message["elapsed_seconds"])
        if any(record is None for record in by_position):
            raise AssertionError("incomplete canonical batch")
        return (
            [record for record in by_position if record is not None],
            elapsed,
        )

    def canonical_batch(
        jobs: list[dict[str, Any]],
        *,
        fixed_shape: int,
    ) -> tuple[list[dict[str, Any]], float]:
        return collect_canonical_batch(
            dispatch_canonical_batch(
                jobs,
                fixed_shape=fixed_shape,
            )
        )

    # Compile/profile every proposer and canonical contract shape before the
    # measured switch sequence.  A shape's first-use compilation is deployment
    # initialization, not state-entry latency.
    warmup_started = time.perf_counter()
    for warmup_concurrency in sorted({item[1] for item in stages}):
        warmup_streams = make_streams(
            sources,
            duration=2,
            concurrency=warmup_concurrency,
        )
        warmup_states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in warmup_streams
        ]
        warmup_jobs = []
        for stream, state in zip(warmup_streams, warmup_states):
            job, _ = prepare_job(
                asr,
                state,
                stream["audio"][: 2 * SAMPLE_RATE],
                tail=False,
            )
            warmup_jobs.append(job)
        dispatched = dispatch_canonical_batch(
            warmup_jobs,
            fixed_shape=warmup_concurrency,
        )
        asr.model.generate(
            warmup_jobs,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        collect_canonical_batch(dispatched)
    warmup_seconds_excluded = time.perf_counter() - warmup_started

    stage_payloads: list[dict[str, Any]] = []
    global_event = 0
    for stage_index, (label, concurrency, episodes) in enumerate(stages):
        fingerprint = (
            f"{args.model_name}/fp16/c{concurrency}/"
            f"{args.canonical_dtype}-fixed-canonical-b{concurrency}"
        )
        epoch = controller.switch(fingerprint)
        stage_started = time.perf_counter()
        sampler = PowerSampler((int(args.proposer_gpu), int(args.verifier_gpu)))
        sampler.start()
        service_seconds = 0.0
        proposer_seconds = 0.0
        required_verifier_seconds = 0.0
        service_events: list[dict[str, Any]] = []
        episode_snapshots: list[dict[str, Any]] = []
        selected_by_episode: list[list[dict[str, Any]]] = []
        certified_before_episode: int | None = None

        for episode in range(episodes):
            streams = make_streams(
                sources,
                duration=args.episode_seconds,
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
            rounds = args.episode_seconds // 2
            episode_selected: list[dict[str, Any]] = []
            episode_round_latencies: list[float] = []
            episode_service_started = time.perf_counter()
            for chunk_index in range(rounds):
                terminal = chunk_index == rounds - 1
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
                preverify_all = controller.fail_closed or terminal
                overlapped_dispatch = (
                    dispatch_canonical_batch(
                        jobs,
                        fixed_shape=concurrency,
                    )
                    if preverify_all
                    else None
                )
                proposal_started = time.perf_counter()
                outputs = asr.model.generate(
                    jobs,
                    sampling_params=asr.sampling_params,
                    use_tqdm=False,
                )
                proposal_elapsed = time.perf_counter() - proposal_started
                proposer_seconds += proposal_elapsed
                proposals = [candidate_record(output) for output in outputs]
                verified_by_position: dict[int, dict[str, Any]] = {}
                if overlapped_dispatch is not None:
                    verified, elapsed = collect_canonical_batch(
                        overlapped_dispatch
                    )
                    verify_positions = list(range(len(jobs)))
                    required_verifier_seconds += elapsed
                    verified_by_position.update(
                        zip(verify_positions, verified)
                    )
                else:
                    verify_positions = [
                        position
                        for position, proposal in enumerate(proposals)
                        if controller.requires_verification(
                            minimum_margin=proposal["minimum_margin"],
                            terminal=terminal,
                        )
                    ]
                if verify_positions and overlapped_dispatch is None:
                    verified, elapsed = canonical_batch(
                        [jobs[position] for position in verify_positions],
                        fixed_shape=concurrency,
                    )
                    required_verifier_seconds += elapsed
                    verified_by_position.update(zip(verify_positions, verified))
                round_started = time.perf_counter()
                for position, (
                    stream,
                    state,
                    prefix,
                    proposal,
                ) in enumerate(zip(streams, states, prefixes, proposals)):
                    selected = verified_by_position.get(position, proposal)
                    proposal_projection = state_projection_record(
                        asr,
                        state,
                        prefix,
                        proposal,
                        terminal=terminal,
                    )
                    proposal["state_projection"] = proposal_projection
                    selected_projection = state_projection_record(
                        asr,
                        state,
                        prefix,
                        selected,
                        terminal=terminal,
                    )
                    selected["state_projection"] = selected_projection
                    if position in verified_by_position:
                        comparison = compare_records(
                            verified_by_position[position],
                            proposal,
                        )
                        certificate = controller.observe(
                            minimum_margin=(
                                float(proposal["minimum_margin"])
                                if proposal["minimum_margin"] is not None
                                else float("-inf")
                            ),
                            state_error=not comparison[
                                "state_projection_token_exact"
                            ],
                        )
                        if (
                            certificate is not None
                            and certificate.certified
                            and certified_before_episode is None
                        ):
                            certified_before_episode = episode
                    event = {
                        "stage": label,
                        "stage_index": stage_index,
                        "episode": episode,
                        "session_id": stream["session_id"],
                        "chunk_index": chunk_index,
                        "global_event": global_event,
                        "terminal": terminal,
                        "verified": position in verified_by_position,
                        "fail_closed": epoch.certificate is None,
                        "threshold": epoch.threshold,
                        "proposal_minimum_margin": proposal["minimum_margin"],
                        "proposal_token_ids": proposal["token_ids"],
                        "proposal_state_projection": proposal_projection,
                        "selected_token_ids": selected["token_ids"],
                        "selected_text": selected["text"],
                        "selected_state_projection": selected_projection,
                    }
                    service_events.append(event)
                    episode_selected.append(event)
                    if selected is proposal:
                        apply_output(state, outputs[position], prefix)
                    else:
                        from run_revtrace_dual_gpu import apply_candidate_record

                        # Rebuild the selected state using the same helper as the
                        # deployed transaction engine.
                        apply_candidate_record(state, selected, prefix)
                    global_event += 1
                round_commit_elapsed = time.perf_counter() - round_started
                round_state_entry_latency = (
                    time.perf_counter() - proposal_started
                )
                episode_round_latencies.append(round_state_entry_latency)
                for event in episode_selected[-len(streams) :]:
                    event["state_entry_latency_seconds"] = (
                        round_state_entry_latency
                    )
                service_seconds += (
                    proposal_elapsed
                    + (
                        required_verifier_seconds
                        - sum(
                            snapshot["required_verifier_seconds"]
                            for snapshot in episode_snapshots
                        )
                        if False
                        else 0.0
                    )
                    + round_commit_elapsed
                )
            episode_wall = time.perf_counter() - episode_service_started
            episode_snapshots.append(
                {
                    "episode": episode,
                    "events": len(episode_selected),
                    "wall_seconds": episode_wall,
                    "goodput_events_per_second": (
                        len(episode_selected) / episode_wall
                    ),
                    "state_entry_latency_seconds_p50": statistics.median(
                        episode_round_latencies
                    ),
                    "state_entry_latency_seconds_p95": percentile(
                        episode_round_latencies, 0.95
                    ),
                    "state_entry_latency_seconds_p99": percentile(
                        episode_round_latencies, 0.99
                    ),
                    "deadline_miss_rounds": sum(
                        value > 2.0 for value in episode_round_latencies
                    ),
                    "certified": epoch.certificate is not None,
                    "threshold": epoch.threshold,
                    "fast_path_window": epoch.fast_path_window,
                    "required_verifier_seconds": required_verifier_seconds,
                }
            )
            selected_by_episode.append(episode_selected)

        energy_samples = sampler.stop()
        stage_wall = time.perf_counter() - stage_started

        # Fresh canonical replay after the service interval.  This is excluded
        # from service timing and never supplies controller evidence.
        audit_started = time.perf_counter()
        output_violations = 0
        state_violations = 0
        audit_events = 0
        selected_cursor = 0
        for episode in range(episodes):
            streams = make_streams(
                sources,
                duration=args.episode_seconds,
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
            for chunk_index in range(args.episode_seconds // 2):
                terminal = chunk_index == args.episode_seconds // 2 - 1
                jobs = []
                prefixes = []
                for stream, state in zip(streams, states):
                    begin = chunk_index * 2 * SAMPLE_RATE
                    end = begin + 2 * SAMPLE_RATE
                    job, prefix = prepare_job(
                        asr,
                        state,
                        stream["audio"][begin:end],
                        tail=False,
                    )
                    jobs.append(job)
                    prefixes.append(prefix)
                canonical, _ = canonical_batch(
                    jobs,
                    fixed_shape=concurrency,
                )
                for state, prefix, record in zip(states, prefixes, canonical):
                    selected = service_events[selected_cursor]
                    record["state_projection"] = state_projection_record(
                        asr,
                        state,
                        prefix,
                        record,
                        terminal=terminal,
                    )
                    comparison = compare_records(
                        record,
                        {
                            "token_ids": selected["selected_token_ids"],
                            "text": selected["selected_text"],
                            "state_projection": selected[
                                "selected_state_projection"
                            ],
                        },
                    )
                    output_violations += int(not comparison["token_exact"])
                    state_violations += int(
                        not comparison["state_projection_token_exact"]
                    )
                    apply_output(state, type("Output", (), {})(), prefix) if False else None
                    from run_revtrace_dual_gpu import apply_candidate_record

                    apply_candidate_record(state, record, prefix)
                    selected_cursor += 1
                    audit_events += 1
        audit_seconds = time.perf_counter() - audit_started
        latencies = [
            float(event["state_entry_latency_seconds"])
            for event in service_events
        ]
        energy = summarize_energy(
            energy_samples,
            completed_audio_seconds=len(service_events) * 2.0,
        )
        stage_payloads.append(
            {
                "label": label,
                "fingerprint": fingerprint,
                "concurrency": concurrency,
                "episodes": episodes,
                "events": len(service_events),
                "switch_action": "fast_path_window=0; all state entries verified",
                "certified_after_episode": certified_before_episode,
                "certified_after_events": (
                    epoch.certified_at_event - epoch.switched_at_event
                    if epoch.certified_at_event is not None
                    else None
                ),
                "threshold": epoch.threshold,
                "fast_path_window": epoch.fast_path_window,
                "risk_upper_bound": (
                    epoch.certificate.upper_risk
                    if epoch.certificate is not None
                    else 1.0
                ),
                "service_wall_seconds": stage_wall,
                "proposer_seconds": proposer_seconds,
                "required_verifier_seconds": required_verifier_seconds,
                "goodput_events_per_second": len(service_events) / stage_wall,
                "state_entry_latency_seconds_p50": statistics.median(latencies),
                "state_entry_latency_seconds_p95": percentile(latencies, 0.95),
                "state_entry_latency_seconds_p99": percentile(latencies, 0.99),
                "deadline_miss_events": sum(
                    value > 2.0 for value in latencies
                ),
                "verification_fraction": sum(
                    event["verified"] for event in service_events
                )
                / len(service_events),
                "output_violations": output_violations,
                "state_violations": state_violations,
                "audit_events": audit_events,
                "audit_seconds_excluded_from_service": audit_seconds,
                "episodes_detail": episode_snapshots,
                "energy": energy,
            }
        )

    command_queue.put({"kind": "stop"})
    stopped = receive_or_raise(result_queue, args.result_timeout_seconds)
    if stopped.get("kind") != "stopped":
        raise RuntimeError(f"unexpected verifier shutdown: {stopped}")
    verifier.join(timeout=30.0)
    if verifier.is_alive():
        verifier.terminate()
        verifier.join(timeout=10.0)
        raise RuntimeError("verifier did not stop")

    passed = all(
        stage["threshold"] is not None
        and stage["risk_upper_bound"] <= 0.005
        and stage["output_violations"] == 0
        and stage["state_violations"] == 0
        and stage["deadline_miss_events"] == 0
        for stage in stage_payloads
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 5A persistent live adaptive controller",
        "decision": (
            "PHASE5A_LIVE_ADAPTIVE_CONTROL_PASS"
            if passed
            else "PHASE5A_LIVE_ADAPTIVE_CONTROL_FAIL"
        ),
        "model": args.model_name,
        "canonical_dtype": args.canonical_dtype,
        "shape_warmup_seconds_excluded_from_service": (
            warmup_seconds_excluded
        ),
        "stages": stage_payloads,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "UNRECORDED"
            ),
            "proposer_gpu": args.proposer_gpu,
            "verifier_gpu": args.verifier_gpu,
            "proposer_pid": os.getpid(),
            "verifier_pid": ready.get("pid"),
        },
        "claim_boundaries": [
            "models remain loaded across the c16-c64-c16 sequence",
            "each fingerprint switch starts a fresh fail-closed epoch",
            "post-stage replay is excluded from service timing",
            "risk is statistical state-entry disagreement, not bitwise determinism",
            (
                "the canonical dtype is a versioned service reference and "
                "is not claimed to reproduce the official BF16 trajectory"
            ),
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], "stages": stage_payloads}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
