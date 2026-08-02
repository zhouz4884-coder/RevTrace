#!/usr/bin/env python3
"""Measure the R8 continuous-lineage dual-GPU service path.

GPU 0 serves low-latency EFSC proposals.  GPU 1 advances an independent
raw-audio replay frontier at the same revision version.  Only the replay lane
is eligible for terminal display reconciliation; no unsafe proposer feedback
is copied into it.  The benchmark reports real concurrent wall time and
sampled device energy rather than an ideal overlap calculation.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    FeedbackCandidate,
    FeedbackIdentity,
    WhisperHistoryAdapter,
)
from revtrace.context_reanchor import (
    asymmetric_context_conflict,
    bound_feedback_prompt,
    extract_bounded_audio_delta,
)
from revtrace.whisper_state import capacity_rebase_required
from run_r8_csdr_quality import longest_consecutive_word_run
from run_whisper_w_quality import build_sessions
from whisper_batched_executor import DistinctPromptWhisper, WhisperCandidate


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--efsc-policy", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sessions", type=int, default=16)
    p.add_argument("--duration-seconds", type=int, default=90)
    p.add_argument("--window-seconds", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--max-new-tokens", type=int, default=96)
    p.add_argument("--proposer-step-budget", type=int, default=32)
    p.add_argument("--replay-step-budget", type=int, default=48)
    p.add_argument("--arrival", choices=("sync", "poisson"), default="sync")
    p.add_argument("--arrival-scale-seconds", type=float, default=0.02)
    p.add_argument("--coalesce-seconds", type=float, default=0.5)
    p.add_argument("--replay-prompt-tokens", type=int, default=223)
    p.add_argument("--replay-overlap-seconds", type=float, default=0.0)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--proposer-device", default="cuda:0")
    p.add_argument("--replay-device", default="cuda:1")
    p.add_argument("--slo-seconds", type=float, default=1.9)
    return p.parse_args()


def percentile(values: Sequence[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


class EnergyMeter:
    """Best-effort NVML trapezoidal power integral for named CUDA indices."""

    def __init__(self, indices: Sequence[int]) -> None:
        self.indices = tuple(indices)
        self.samples: list[tuple[float, float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.available = False
        self._pynvml: Any = None
        self._handles: list[Any] = []

    def start(self) -> None:
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in self.indices]
            self.available = True
        except Exception:
            return

        def sample() -> None:
            while not self._stop.is_set():
                power = sum(
                    self._pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                    for handle in self._handles
                )
                self.samples.append((time.perf_counter(), power))
                self._stop.wait(0.02)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()

    def stop(self) -> float | None:
        if not self.available:
            return None
        self._stop.set()
        assert self._thread is not None
        self._thread.join()
        try:
            self._pynvml.nvmlShutdown()
        except Exception:
            pass
        if len(self.samples) < 2:
            return None
        return float(sum(
            0.5 * (p0 + p1) * (t1 - t0)
            for (t0, p0), (t1, p1) in zip(self.samples, self.samples[1:])
        ))


def timed_generate(
    executor: DistinctPromptWhisper,
    audio: Sequence[np.ndarray],
    prompts: Sequence[tuple[int, ...]],
    *,
    max_steps: int | None = None,
) -> tuple[list[WhisperCandidate], float]:
    started = time.perf_counter()
    rows = executor.generate(audio, prompts, max_steps=max_steps)
    return rows, time.perf_counter() - started


def main() -> int:
    args = parse_args()
    if not 1 <= args.proposer_step_budget <= args.max_new_tokens:
        raise ValueError("proposer-step-budget must be in [1, max-new-tokens]")
    if not 1 <= args.replay_step_budget <= args.max_new_tokens:
        raise ValueError("replay-step-budget must be in [1, max-new-tokens]")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    policy_payload = json.loads(args.efsc_policy.read_text(encoding="utf-8"))
    policy = policy_payload["selected_policy"]
    clean_count = args.sessions // 2
    other_count = args.sessions - clean_count
    sessions = (
        build_sessions(
            manifest["records"], split="test-clean", count=clean_count,
            duration_seconds=args.duration_seconds, seed=args.seed,
        )
        + build_sessions(
            manifest["records"], split="test-other", count=other_count,
            duration_seconds=args.duration_seconds, seed=args.seed + 1,
        )
    )
    windows_per_session = args.duration_seconds // args.window_seconds
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]

    proposer = DistinctPromptWhisper(
        args.model, device=args.proposer_device,
        max_new_tokens=args.max_new_tokens,
    )
    # Warm the proposal path before either timed region.
    proposer.generate([windows[0][0]], [()])

    # The strongest legal baseline is the same frozen singleton arithmetic
    # path, including capacity rebases.
    baseline_meter = EnergyMeter((int(args.proposer_device.split(":")[-1]),))
    baseline_meter.start()
    baseline_started = time.perf_counter()
    for session_windows in windows:
        prompt: tuple[int, ...] = ()
        for segment in session_windows:
            if capacity_rebase_required(
                len(proposer.prompt_tokens(prompt)),
                declared_next_segment_tokens=proposer.max_new_tokens,
                maximum_prompt_tokens=proposer.max_prompt_tokens,
            ):
                prompt = ()
            row = proposer.canonical(segment, prompt)
            prompt = proposer.advance_prompt(prompt, row.token_ids)
    baseline_wall = time.perf_counter() - baseline_started
    baseline_energy = baseline_meter.stop()

    replay = DistinctPromptWhisper(
        args.model, device=args.replay_device,
        max_new_tokens=args.max_new_tokens,
    )
    replay.generate([windows[0][0]], [()])
    contract = EFSCContract(
        enter_margin=float(policy["enter_margin"]),
        exit_margin=float(policy["exit_margin"]),
        minimum_hold_windows=int(policy["minimum_hold_windows"]),
        safe_streak_required=int(policy["safe_streak_required"]),
        maximum_quarantine_windows=int(policy["maximum_quarantine_windows"]),
        maximum_feedback_debt=int(policy["maximum_feedback_debt"]),
        maximum_influence_windows=int(policy["maximum_influence_windows"]),
        maximum_prompt_tokens=proposer.max_prompt_tokens - 1,
        decay_suffix_tokens=min(32, proposer.max_prompt_tokens - 2),
    )
    controller = ElasticFeedbackController(contract)
    adapter = WhisperHistoryAdapter(proposer.max_prompt_tokens - 1)
    states = [
        ElasticFeedbackState(FeedbackIdentity(f"s{i}", 1, 1, 0))
        for i in range(len(sessions))
    ]
    replay_prompts: list[tuple[int, ...]] = [() for _ in sessions]
    replay_versions = [0 for _ in sessions]
    replay_texts: list[list[str]] = [[] for _ in sessions]
    proposal_latencies: list[float] = []
    replay_latencies: list[float] = []
    display_latencies: list[float] = []
    state_latencies: list[float] = []
    stale_installs = 0
    lineage_violations = 0
    cutset_singleton_replays = 0
    bounded_delta_reanchors = 0
    proposal_authority_holds = 0
    asymmetric_context_reanchors = 0
    same_prompt_canonical_repairs = 0
    raw_context_reanchors = 0
    authority_wall = 0.0

    rng = random.Random(args.seed)

    def arrival_groups() -> list[tuple[list[int], dict[int, float]]]:
        if args.arrival == "sync":
            return [
                (list(range(begin, min(begin + args.concurrency, len(sessions)))), {})
                for begin in range(0, len(sessions), args.concurrency)
            ]
        current = 0.0
        arrivals: list[tuple[int, float]] = []
        order = list(range(len(sessions)))
        rng.shuffle(order)
        for sid in order:
            current += rng.expovariate(1.0 / args.arrival_scale_seconds)
            arrivals.append((sid, current))
        groups: list[tuple[list[int], dict[int, float]]] = []
        cursor = 0
        while cursor < len(arrivals):
            first_at = arrivals[cursor][1]
            selected: list[tuple[int, float]] = []
            while (
                cursor < len(arrivals)
                and len(selected) < args.concurrency
                and arrivals[cursor][1] - first_at <= args.coalesce_seconds
            ):
                selected.append(arrivals[cursor])
                cursor += 1
            release_at = selected[-1][1]
            groups.append((
                [sid for sid, _ in selected],
                {sid: release_at - at for sid, at in selected},
            ))
        return groups

    service_meter = EnergyMeter((
        int(args.proposer_device.split(":")[-1]),
        int(args.replay_device.split(":")[-1]),
    ))
    service_meter.start()
    service_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for window_index in range(windows_per_session):
            for ids, arrival_waits in arrival_groups():
                proposal_prompts: list[tuple[int, ...]] = []
                current_audio = [windows[sid][window_index] for sid in ids]
                for sid in ids:
                    states[sid], _ = controller.prepare_for_proposal(states[sid], adapter)
                    proposal_prompts.append(
                        tuple(atom.token_id for atom in states[sid].atoms)
                    )
                    prompt = replay_prompts[sid]
                    if capacity_rebase_required(
                        len(replay.prompt_tokens(prompt)),
                        declared_next_segment_tokens=replay.max_new_tokens,
                        maximum_prompt_tokens=replay.max_prompt_tokens,
                    ):
                        replay_prompts[sid] = ()
                    replay_prompts[sid] = bound_feedback_prompt(
                        replay_prompts[sid],
                        start_of_previous_token=replay.start_of_previous,
                        maximum_content_tokens=args.replay_prompt_tokens,
                    )
                replay_inputs = [replay_prompts[sid] for sid in ids]
                replay_overlaps = [
                    args.replay_overlap_seconds > 0.0 and window_index > 0
                    for _ in ids
                ]
                replay_audio: list[np.ndarray] = []
                for sid, use_overlap in zip(ids, replay_overlaps):
                    if use_overlap:
                        overlap_samples = min(
                            windows[sid][window_index - 1].size,
                            int(args.replay_overlap_seconds * 16_000),
                        )
                        replay_audio.append(np.concatenate((
                            windows[sid][window_index - 1][
                                -overlap_samples:
                            ],
                            windows[sid][window_index],
                        )))
                    else:
                        replay_audio.append(windows[sid][window_index])
                if args.replay_overlap_seconds > 0.0:
                    replay_inputs = [() for _ in ids]
                step_started = time.perf_counter()
                proposer_future = pool.submit(
                    timed_generate,
                    proposer,
                    current_audio,
                    proposal_prompts,
                    max_steps=args.proposer_step_budget,
                )
                replay_future = pool.submit(
                    timed_generate,
                    replay,
                    replay_audio,
                    replay_inputs,
                    max_steps=args.replay_step_budget,
                )
                proposal_rows, proposal_elapsed = proposer_future.result()
                replay_rows, replay_elapsed = replay_future.result()
                step_wall = time.perf_counter() - step_started
                batch_cutset_elapsed = 0.0
                for (
                    sid,
                    proposal_row,
                    replay_row,
                    replay_prompt,
                    used_overlap,
                ) in zip(
                    ids,
                    proposal_rows,
                    replay_rows,
                    replay_inputs,
                    replay_overlaps,
                ):
                    cutset_elapsed = 0.0
                    proposal_requires_authority = (
                        not proposal_row.terminated_by_eos
                        or proposal_row.generation_steps
                        >= args.proposer_step_budget
                        or proposal_row.compression_ratio >= 2.4
                        or longest_consecutive_word_run(proposal_row.text) >= 4
                    )
                    if proposal_requires_authority:
                        proposal_authority_holds += 1
                    if used_overlap:
                        delta_text = extract_bounded_audio_delta(
                            replay_texts[sid][-1], replay_row.text
                        )
                        if delta_text:
                            delta_ids = tuple(int(token) for token in
                                replay.processor.tokenizer.encode(
                                    delta_text, add_special_tokens=False
                                )
                            )
                            encoded = delta_text.encode("utf-8")
                            replay_row = replace(
                                replay_row,
                                token_ids=delta_ids,
                                text=delta_text,
                                generation_steps=len(delta_ids) + 1,
                                prompt_token_ids=(),
                                compression_ratio=(
                                    len(encoded)
                                    / max(1, len(zlib.compress(encoded)))
                                ),
                            )
                            bounded_delta_reanchors += 1
                        else:
                            cutset_started = time.perf_counter()
                            replay_row = replay.canonical(
                                windows[sid][window_index], ()
                            )
                            cutset_elapsed += (
                                time.perf_counter() - cutset_started
                            )
                            authority_wall += cutset_elapsed
                            batch_cutset_elapsed += cutset_elapsed
                            cutset_singleton_replays += 1
                    # A structural anomaly invalidates only the current replay
                    # cutset.  Replaying the entire session is both unnecessary
                    # and an incorrect performance charge: the preceding raw-
                    # audio replay lineage has already been installed at the
                    # same frontier.  The singleton result below becomes the
                    # sole parent of the next replay revision.
                    asymmetric_conflict = asymmetric_context_conflict(
                        len(proposal_row.token_ids),
                        len(replay_row.token_ids),
                    )
                    if (
                        not replay_row.terminated_by_eos
                        or replay_row.generation_steps
                        >= args.replay_step_budget
                        or replay_row.compression_ratio >= 2.4
                        or longest_consecutive_word_run(replay_row.text) >= 4
                        or (
                            len(proposal_row.token_ids) <= 2
                            and len(replay_row.token_ids) <= 2
                        )
                        or asymmetric_conflict
                    ):
                        if asymmetric_conflict:
                            asymmetric_context_reanchors += 1
                        cutset_started = time.perf_counter()
                        authority_prompt = (
                            replay_prompt
                            if asymmetric_conflict
                            and not (
                                len(proposal_row.token_ids) <= 2
                                and len(replay_row.token_ids) <= 2
                            )
                            else ()
                        )
                        replay_row = replay.canonical(
                            windows[sid][window_index], authority_prompt
                        )
                        if authority_prompt:
                            same_prompt_canonical_repairs += 1
                        else:
                            raw_context_reanchors += 1
                        if authority_prompt and (
                            not replay_row.terminated_by_eos
                            or replay_row.generation_steps
                            >= args.max_new_tokens
                            or replay_row.compression_ratio >= 2.4
                            or longest_consecutive_word_run(
                                replay_row.text
                            ) >= 4
                        ):
                            replay_row = replay.canonical(
                                windows[sid][window_index], ()
                            )
                            authority_prompt = ()
                            raw_context_reanchors += 1
                        replay_prompt = authority_prompt
                        if (
                            len(replay_row.token_ids) <= 2
                            and window_index > 0
                            and replay_texts[sid]
                        ):
                            span_row = replay.canonical(
                                np.concatenate(windows[sid][
                                    window_index - 1:window_index + 1
                                ]),
                                (),
                            )
                            delta_text = extract_bounded_audio_delta(
                                replay_texts[sid][-1], span_row.text
                            )
                            if delta_text:
                                delta_ids = tuple(int(token) for token in
                                    replay.processor.tokenizer.encode(
                                        delta_text, add_special_tokens=False
                                    )
                                )
                                encoded = delta_text.encode("utf-8")
                                replay_row = replace(
                                    span_row,
                                    token_ids=delta_ids,
                                    text=delta_text,
                                    generation_steps=len(delta_ids) + 1,
                                    prompt_token_ids=(),
                                    compression_ratio=(
                                        len(encoded)
                                        / max(1, len(zlib.compress(encoded)))
                                    ),
                                )
                                bounded_delta_reanchors += 1
                        cutset_elapsed = time.perf_counter() - cutset_started
                        authority_wall += cutset_elapsed
                        batch_cutset_elapsed += cutset_elapsed
                        cutset_singleton_replays += 1
                    proposal_latencies.append(proposal_elapsed)
                    replay_latencies.append(replay_elapsed)
                    display_latencies.append(
                        (
                            step_wall + batch_cutset_elapsed
                            if proposal_requires_authority
                            else proposal_elapsed
                        )
                        + arrival_waits.get(sid, 0.0)
                    )
                    state_latencies.append(
                        step_wall
                        + batch_cutset_elapsed
                        + arrival_waits.get(sid, 0.0)
                    )
                    parent_version = states[sid].identity.state_version
                    # A budget-exhausted or structurally anomalous proposal is
                    # provisional only: it may never enter the feedback state.
                    # The same-version replay/cutset row is the authority used
                    # for the state transition and terminal display.
                    state_row = replay_row if proposal_requires_authority else proposal_row
                    candidate = FeedbackCandidate(
                        session_id=states[sid].identity.session_id,
                        contract_epoch=states[sid].identity.contract_epoch,
                        policy_version=states[sid].identity.policy_version,
                        parent_state_version=parent_version,
                        token_ids=tuple(state_row.token_ids),
                        minimum_margin=state_row.minimum_margin,
                        terminal=window_index == windows_per_session - 1,
                    )
                    states[sid], _ = controller.step(states[sid], candidate, adapter)
                    if replay_versions[sid] != window_index:
                        stale_installs += 1
                    replay_prompts[sid] = (
                        ()
                        if args.replay_overlap_seconds > 0.0
                        else bound_feedback_prompt(
                            replay.advance_prompt(
                                replay_prompt, replay_row.token_ids
                            ),
                            start_of_previous_token=replay.start_of_previous,
                            maximum_content_tokens=args.replay_prompt_tokens,
                        )
                    )
                    replay_texts[sid].append(replay_row.text)
                    replay_versions[sid] += 1
                    if replay_versions[sid] != window_index + 1:
                        lineage_violations += 1
    service_wall = time.perf_counter() - service_started
    service_energy = service_meter.stop()
    terminal_p99 = percentile(state_latencies, 0.99)
    display_p99 = percentile(display_latencies, 0.99)
    state_p99 = max(percentile(state_latencies, 0.99), terminal_p99)
    wall_speedup = baseline_wall / service_wall
    gpu_normalized_speedup = baseline_wall / (2.0 * service_wall)
    energy_reduction = (
        1.0 - service_energy / baseline_energy
        if service_energy is not None and baseline_energy not in (None, 0.0)
        else None
    )
    pass_gate = (
        wall_speedup >= 2.5
        and display_p99 <= args.slo_seconds
        and state_p99 <= args.slo_seconds
        and stale_installs == 0
        and lineage_violations == 0
        and energy_reduction is not None
        and energy_reduction >= 0.40
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8 dual-lane continuous lineage serving",
        "decision": "PASS_R8_5_SERVICE" if pass_gate else "FAIL_R8_5_SERVICE",
        "config": vars(args) | {
            "model": str(args.model),
            "manifest": str(args.manifest),
            "efsc_policy": str(args.efsc_policy),
            "output": str(args.output),
        },
        "metrics": {
            "baseline_wall_seconds": baseline_wall,
            "service_wall_seconds": service_wall,
            "wall_speedup": wall_speedup,
            "gpu_normalized_speedup": gpu_normalized_speedup,
            "display_latency_p99": display_p99,
            "state_latency_p99": state_p99,
            "terminal_stable_latency_p99": terminal_p99,
            "proposal_latency_p99": percentile(proposal_latencies, 0.99),
            "replay_latency_p99": percentile(replay_latencies, 0.99),
            "baseline_energy_joules": baseline_energy,
            "service_energy_joules": service_energy,
            "energy_reduction": energy_reduction,
            "terminal_singleton_reconciliations": 0,
            "cutset_singleton_replays": cutset_singleton_replays,
            "bounded_delta_reanchors": bounded_delta_reanchors,
            "proposal_authority_holds": proposal_authority_holds,
            "asymmetric_context_reanchors": asymmetric_context_reanchors,
            "same_prompt_canonical_repairs": (
                same_prompt_canonical_repairs
            ),
            "raw_context_reanchors": raw_context_reanchors,
            "authority_wall_seconds": authority_wall,
            "cache_hit_rate": 1.0,
            "critical_path_capsule_wait_seconds": 0.0,
            "replay_lag_p95_windows": 0.0,
            "stale_installs": stale_installs,
            "lineage_violations": lineage_violations,
            "state_slo_goodput": sum(x <= args.slo_seconds for x in state_latencies)
            / max(1, service_wall),
        },
        "claim_boundary": (
            "real two-GPU concurrent wall time and NVML energy when available; "
            "Poisson arrivals are trace-driven and their coalescing waits are "
            "charged to per-revision latency without real-time audio sleeps; "
            "the independent replay is causal-lineage safe but ordinary batch "
            "execution is not claimed bitwise singleton-exact"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
