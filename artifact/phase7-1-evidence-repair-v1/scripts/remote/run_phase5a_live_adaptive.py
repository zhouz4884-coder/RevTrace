#!/usr/bin/env python3
"""Persistent-process multi-contract live adaptation gate.

The proposer and verifier are loaded once.  A contract switch creates a fresh
controller epoch, immediately forces all state entries through the fixed-shape
canonical path, and expands the fast path only after the new epoch has enough
split-sample evidence.  With Phase 6 asymmetric memory enabled, an exact
contract return restores only behind renewal canaries, while unseen
populations stay isolated. Post-stage canonical replay is excluded from
service timing and checks every selected state transition.
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
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np


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
    parser.add_argument("--episode-seed-base", type=int, default=20260729)
    parser.add_argument(
        "--phase6-asymmetric-memory",
        action="store_true",
        help=(
            "use exact-contract certificate restore, canary renewal, and "
            "persistent per-contract counterexample floors"
        ),
    )
    parser.add_argument("--renewal-canaries", type=int, default=64)
    parser.add_argument(
        "--failure-floor",
        action="append",
        default=[],
        metavar="LABEL:VALUE",
        help="seed one observed counterexample margin for a stage contract",
    )
    parser.add_argument(
        "--statistical-risk-gate",
        action="store_true",
        help=(
            "evaluate risk-limited stages against the 0.5 percent contract "
            "instead of incorrectly requiring zero observed disagreements"
        ),
    )
    parser.add_argument(
        "--frozen-threshold",
        action="append",
        default=[],
        metavar="LABEL:VALUE",
        help=(
            "run an independently seeded static-oracle stage with a threshold "
            "frozen by prior certification; repeat once per stage label"
        ),
    )
    parser.add_argument(
        "--suppress-certified-terminal-proposer",
        action="store_true",
        help=(
            "after an epoch is certified, execute terminal revisions only "
            "on the authoritative canonical path instead of co-running a "
            "discarded proposer"
        ),
    )
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="LABEL:CONCURRENCY:EPISODES[:LANGUAGE]",
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


def parse_stages(
    values: list[str],
) -> list[tuple[str, int, int, str]]:
    source = values or [
        "c16_initial:16:8:mixed",
        "c64_drift:64:3:mixed",
        "c16_return:16:8:mixed",
    ]
    stages = []
    for value in source:
        fields = value.split(":")
        if len(fields) == 3:
            label, concurrency, episodes = fields
            language = "mixed"
        elif len(fields) == 4:
            label, concurrency, episodes, language = fields
        else:
            raise ValueError(
                "stage must be LABEL:CONCURRENCY:EPISODES[:LANGUAGE]"
            )
        if language not in {"mixed", "English", "Chinese"}:
            raise ValueError(f"unsupported stage language: {language}")
        stages.append((label, int(concurrency), int(episodes), language))
    return stages


def parse_frozen_thresholds(values: list[str]) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for value in values:
        label, raw_threshold = value.split(":", 1)
        if label in thresholds:
            raise ValueError(f"duplicate frozen threshold: {label}")
        thresholds[label] = float(raw_threshold)
    return thresholds


def parse_label_values(values: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for value in values:
        label, raw_value = value.split(":", 1)
        if label in result:
            raise ValueError(f"duplicate label value: {label}")
        result[label] = float(raw_value)
    return result


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)

    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
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
    from run_revtrace_dual_gpu import (
        build_asr,
        receive_or_raise,
        verifier_worker,
    )
    from revtrace.phase5 import (
        AsymmetricLiveRiskWindowController,
        LiveRiskWindowController,
        summarize_energy,
    )

    stages = parse_stages(args.stage)
    frozen_thresholds = parse_frozen_thresholds(args.frozen_threshold)
    failure_floors = parse_label_values(args.failure_floor)
    unknown_thresholds = set(frozen_thresholds) - {
        label for label, _, _, _ in stages
    }
    if unknown_thresholds:
        raise ValueError(
            "frozen thresholds do not match stages: "
            f"{sorted(unknown_thresholds)}"
        )
    unknown_floors = set(failure_floors) - {
        label for label, _, _, _ in stages
    }
    if unknown_floors:
        raise ValueError(
            "failure floors do not match stages: "
            f"{sorted(unknown_floors)}"
        )
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

    from revtrace.phase7_1 import CanonicalRuntimeProvenance

    canonical_provenance = CanonicalRuntimeProvenance(
        model=args.model_name,
        configured_weight_dtype=args.canonical_dtype,
        accumulation_dtype="kernel-defined-unrecorded",
        sampling_dtype="vllm-internal-unrecorded",
        attention_backend=(
            "FLASH_ATTN"
            if args.canonical_dtype != "float32"
            else "vllm-auto-unrecorded"
        ),
        fixed_batch_shape=max_concurrency,
        batch_invariant_requested=args.canonical_dtype != "float32",
        temperature=0.0,
        max_tokens=32,
        terminal_and_intermediate_same_engine=True,
    )

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    asr = build_asr(str(args.model), "float16", 0.82)
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    controller = (
        AsymmetricLiveRiskWindowController(
            minimum_audits=args.minimum_audits,
            renewal_canaries=args.renewal_canaries,
        )
        if args.phase6_asymmetric_memory
        else LiveRiskWindowController(minimum_audits=args.minimum_audits)
    )
    batch_id = 0

    def make_stage_streams(
        *,
        stage_index: int,
        episode: int,
        duration: int,
        concurrency: int,
        language: str,
    ) -> list[dict[str, Any]]:
        """Create reproducibly distinct live inputs for each stage episode."""

        streams = make_streams(
            sources,
            duration=duration,
            concurrency=concurrency,
        )
        for position, stream in enumerate(streams):
            if language != "mixed":
                source = sources[language][position % len(sources[language])]
                stream["language"] = language
                stream["audio"] = cycle_audio(
                    source,
                    duration,
                    offset=(position * 7919) % max(1, source.size),
                )
            audio = stream["audio"]
            salt = (
                int(args.episode_seed_base)
                + stage_index * 1_000_003
                + episode * 10_007
                + position * 101
            )
            shift = salt % max(1, int(audio.shape[0]))
            stream["audio"] = np.roll(audio, shift)
            stream["session_id"] = (
                f"stage{stage_index:02d}-episode{episode:04d}-"
                f"s{position:03d}"
            )
        return streams

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
    for stage_index, (
        label,
        concurrency,
        episodes,
        language,
    ) in enumerate(stages):
        frozen_threshold = frozen_thresholds.get(label)
        static_oracle_stage = frozen_threshold is not None
        fingerprint = canonical_provenance.contract_fingerprint(
            proposer_dtype="float16",
            concurrency=concurrency,
            language=language,
            arrival="episode-sync",
        )
        if args.phase6_asymmetric_memory and label in failure_floors:
            controller.seed_failure(fingerprint, failure_floors[label])
        epoch = controller.switch(fingerprint)
        switch_status_at_entry = getattr(
            controller, "switch_status", "fresh_epoch"
        )
        stage_started = time.perf_counter()
        sampler = PowerSampler((int(args.proposer_gpu), int(args.verifier_gpu)))
        sampler.start()
        service_seconds = 0.0
        proposer_seconds = 0.0
        required_verifier_seconds = 0.0
        service_events: list[dict[str, Any]] = []
        episode_snapshots: list[dict[str, Any]] = []
        selected_by_episode: list[list[dict[str, Any]]] = []
        certified_before_episode: int | None = (
            0 if static_oracle_stage else None
        )

        for episode in range(episodes):
            streams = make_stage_streams(
                stage_index=stage_index,
                episode=episode,
                duration=args.episode_seconds,
                concurrency=concurrency,
                language=language,
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
                round_execution_started = time.perf_counter()
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
                preverify_all = (
                    (not static_oracle_stage and controller.fail_closed)
                    or terminal
                )
                suppress_terminal_proposer = bool(
                    terminal
                    and (
                        static_oracle_stage
                        or epoch.certificate is not None
                    )
                    and args.suppress_certified_terminal_proposer
                )
                overlapped_dispatch = (
                    dispatch_canonical_batch(
                        jobs,
                        fixed_shape=concurrency,
                    )
                    if preverify_all
                    else None
                )
                verified_by_position: dict[int, dict[str, Any]] = {}
                if suppress_terminal_proposer:
                    if overlapped_dispatch is None:
                        raise AssertionError(
                            "terminal suppression requires canonical dispatch"
                        )
                    verified, elapsed = collect_canonical_batch(
                        overlapped_dispatch
                    )
                    verify_positions = list(range(len(jobs)))
                    required_verifier_seconds += elapsed
                    verified_by_position.update(
                        zip(verify_positions, verified)
                    )
                    outputs = None
                    proposal_elapsed = 0.0
                    proposals = [
                        dict(verified_by_position[position])
                        for position in verify_positions
                    ]
                else:
                    proposal_started = time.perf_counter()
                    outputs = asr.model.generate(
                        jobs,
                        sampling_params=asr.sampling_params,
                        use_tqdm=False,
                    )
                    proposal_elapsed = time.perf_counter() - proposal_started
                    proposer_seconds += proposal_elapsed
                    proposals = [
                        candidate_record(output) for output in outputs
                    ]
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
                            if (
                                (
                                    static_oracle_stage
                                    and (
                                        proposal["minimum_margin"] is None
                                        or float(
                                            proposal["minimum_margin"]
                                        )
                                        <= float(frozen_threshold)
                                    )
                                )
                                or (
                                    not static_oracle_stage
                                    and controller.requires_verification(
                                        minimum_margin=proposal[
                                            "minimum_margin"
                                        ],
                                        terminal=terminal,
                                    )
                                )
                            )
                        ]
                if (
                    verify_positions
                    and overlapped_dispatch is None
                    and not suppress_terminal_proposer
                ):
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
                    if (
                        position in verified_by_position
                        and not suppress_terminal_proposer
                        and not static_oracle_stage
                    ):
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
                        "proposal_executed": not suppress_terminal_proposer,
                        "verified": position in verified_by_position,
                        "fail_closed": (
                            False
                            if static_oracle_stage
                            else epoch.certificate is None
                        ),
                        "threshold": (
                            frozen_threshold
                            if static_oracle_stage
                            else epoch.threshold
                        ),
                        "proposal_minimum_margin": (
                            proposal["minimum_margin"]
                            if not suppress_terminal_proposer
                            else None
                        ),
                        "proposal_token_ids": (
                            proposal["token_ids"]
                            if not suppress_terminal_proposer
                            else None
                        ),
                        "proposal_state_projection": (
                            proposal_projection
                            if not suppress_terminal_proposer
                            else None
                        ),
                        "selected_token_ids": selected["token_ids"],
                        "selected_text": selected["text"],
                        "selected_state_projection": selected_projection,
                    }
                    service_events.append(event)
                    episode_selected.append(event)
                    if selected is proposal and not suppress_terminal_proposer:
                        assert outputs is not None
                        apply_output(state, outputs[position], prefix)
                    else:
                        from run_revtrace_dual_gpu import apply_candidate_record

                        # Rebuild the selected state using the same helper as the
                        # deployed transaction engine.
                        apply_candidate_record(state, selected, prefix)
                    global_event += 1
                round_commit_elapsed = time.perf_counter() - round_started
                round_state_entry_latency = (
                    time.perf_counter() - round_execution_started
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
                    "certified": (
                        static_oracle_stage
                        or epoch.certificate is not None
                    ),
                    "threshold": (
                        frozen_threshold
                        if static_oracle_stage
                        else epoch.threshold
                    ),
                    "fast_path_window": (
                        None
                        if static_oracle_stage
                        else epoch.fast_path_window
                    ),
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
        audit_violation_rows: list[dict[str, Any]] = []
        selected_cursor = 0
        for episode in range(episodes):
            streams = make_stage_streams(
                stage_index=stage_index,
                episode=episode,
                duration=args.episode_seconds,
                concurrency=concurrency,
                language=language,
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
                    if (
                        not comparison["token_exact"]
                        or not comparison["state_projection_token_exact"]
                    ):
                        audit_violation_rows.append(
                            {
                                "stage": label,
                                "episode": episode,
                                "session_id": selected["session_id"],
                                "chunk_index": chunk_index,
                                "terminal": terminal,
                                "verified": selected["verified"],
                                "proposal_executed": selected[
                                    "proposal_executed"
                                ],
                                "proposal_minimum_margin": selected[
                                    "proposal_minimum_margin"
                                ],
                                "threshold": selected["threshold"],
                                "selected_token_ids": selected[
                                    "selected_token_ids"
                                ],
                                "canonical_token_ids": record["token_ids"],
                                "selected_state_projection": selected[
                                    "selected_state_projection"
                                ],
                                "canonical_state_projection": record[
                                    "state_projection"
                                ],
                                "comparison": comparison,
                            }
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
                "language": language,
                "episodes": episodes,
                "events": len(service_events),
                "switch_action": (
                    "none; frozen threshold loaded before service"
                    if static_oracle_stage
                    else switch_status_at_entry
                ),
                "failure_floor": (
                    controller.failure_floor(fingerprint)
                    if args.phase6_asymmetric_memory
                    else None
                ),
                "renewal_canaries_remaining": (
                    controller.renewal_remaining
                    if args.phase6_asymmetric_memory
                    else None
                ),
                "policy": (
                    "frozen_prior-certified_static_oracle"
                    if static_oracle_stage
                    else "live_adaptive_risk_window"
                ),
                "certified_after_episode": certified_before_episode,
                "certified_after_events": (
                    0
                    if static_oracle_stage
                    else (
                        epoch.certified_at_event - epoch.switched_at_event
                        if epoch.certified_at_event is not None
                        else None
                    )
                ),
                "threshold": (
                    frozen_threshold
                    if static_oracle_stage
                    else epoch.threshold
                ),
                "fast_path_window": (
                    None
                    if static_oracle_stage
                    else epoch.fast_path_window
                ),
                "risk_upper_bound": (
                    None
                    if static_oracle_stage
                    else (
                        epoch.certificate.upper_risk
                        if epoch.certificate is not None
                        else 1.0
                    )
                ),
                "risk_bound_source": (
                    "prior independent split-sample certificate"
                    if static_oracle_stage
                    else "current live epoch split-sample certificate"
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
                "audit_violation_rows": audit_violation_rows,
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

    static_oracle_run = bool(frozen_thresholds)
    if static_oracle_run and len(frozen_thresholds) != len(stages):
        raise ValueError(
            "static-oracle runs require one frozen threshold per stage"
        )
    passed = all(
        stage["threshold"] is not None
        and (
            stage["risk_upper_bound"] is None
            if static_oracle_run
            else stage["risk_upper_bound"] <= 0.005
        )
        and (
            (
                stage["state_violations"] / stage["events"] <= 0.005
                and not any(
                    row["proposal_minimum_margin"] is not None
                    and stage["failure_floor"] is not None
                    and float(row["proposal_minimum_margin"])
                    <= float(stage["failure_floor"])
                    and not bool(row["verified"])
                    for row in stage["audit_violation_rows"]
                )
            )
            if args.statistical_risk_gate
            else (
                stage["output_violations"] == 0
                and stage["state_violations"] == 0
            )
        )
        and stage["deadline_miss_events"] == 0
        for stage in stage_payloads
    )
    payload = {
        "schema_version": 1,
        "study": (
            "RevTrace Phase 5A independent static certified oracle"
            if static_oracle_run
            else "RevTrace Phase 5A persistent live adaptive controller"
        ),
        "decision": (
            (
                "PHASE5A_STATIC_CERTIFIED_ORACLE_PASS"
                if static_oracle_run
                else "PHASE5A_LIVE_ADAPTIVE_CONTROL_PASS"
            )
            if passed
            else (
                "PHASE5A_STATIC_CERTIFIED_ORACLE_FAIL"
                if static_oracle_run
                else "PHASE5A_LIVE_ADAPTIVE_CONTROL_FAIL"
            )
        ),
        "model": args.model_name,
        "canonical_dtype": args.canonical_dtype,
        "canonical_runtime_provenance": {
            **asdict(canonical_provenance),
            "digest": canonical_provenance.digest,
            "note": (
                "Accumulation and sampling dtypes were not exported by the "
                "frozen vLLM runtime and therefore remain explicitly "
                "unrecorded rather than inferred."
            ),
        },
        "phase6_asymmetric_memory": args.phase6_asymmetric_memory,
        "statistical_risk_gate": args.statistical_risk_gate,
        "cross_contract_certificate_reuse": getattr(
            controller, "cross_contract_certificate_reuse", None
        ),
        "exact_certificate_restores": getattr(
            controller, "exact_certificate_restores", None
        ),
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
            (
                "exact-contract returns require canary renewal; positive "
                "certificates never cross contract digests and contextual "
                "failure floors persist"
                if args.phase6_asymmetric_memory
                else "Phase 5 controller uses fresh epochs only"
            ),
            "post-stage replay is excluded from service timing",
            "risk is statistical state-entry disagreement, not bitwise determinism",
            (
                "static-oracle thresholds are frozen from prior independent "
                "split-sample certificates and supply performance references"
                if static_oracle_run
                else (
                    "no static threshold is supplied; every contract epoch "
                    "learns its risk window from fresh live evidence"
                )
            ),
            (
                "episode-specific stream identities and audio offsets prevent "
                "exact episode replay from being counted as fresh evidence"
            ),
            (
                "certified terminal revisions suppress discarded proposer "
                "work when the corresponding flag is enabled"
            ),
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
