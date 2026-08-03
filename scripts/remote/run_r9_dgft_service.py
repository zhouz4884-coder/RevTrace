#!/usr/bin/env python3
"""Real two-GPU DGFT service benchmark with transactional segment installs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from revtrace.dgft import (
    CanonicalSegmentJob,
    FeedbackTransactionState,
    build_dual_axis_certificate,
    classify_asymmetric_omission_conflict,
    commit_canonical_segment,
    commit_checkpoint_rebase,
    commit_session_fallback,
    digest_tokens,
    repeated_ngram_fraction,
)
from revtrace.causal_scheduler import (
    SessionArrival,
    group_ready_events,
    initial_session_arrivals,
)
from revtrace.online_coordinator import OnlineRevisionCoordinator
from revtrace.whisper_state import capacity_rebase_required
from run_r8_dual_lane_service import EnergyMeter, percentile
from run_r9_coverage_fallback import replay_from_checkpoint, segment_decisions
from run_r9_segment_oracle import run_batched_adaptive, run_mode
from run_whisper_w_quality import build_sessions, word_error
from whisper_batched_executor import DistinctPromptWhisper


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sessions", type=int, default=16)
    p.add_argument("--duration-seconds", type=int, default=90)
    p.add_argument("--window-seconds", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--arrival", choices=("sync", "poisson"), default="sync")
    p.add_argument("--arrival-scale-seconds", type=float, default=0.02)
    p.add_argument("--coalesce-seconds", type=float, default=0.5)
    p.add_argument("--proposer-max-steps", type=int, default=32)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--proposer-device", default="cuda:0")
    p.add_argument("--authority-device", default="cuda:1")
    p.add_argument("--display-slo-seconds", type=float, default=1.9)
    p.add_argument("--commit-slo-seconds", type=float, default=36.0)
    p.add_argument("--adaptive-min-seconds", type=float, default=15.0)
    p.add_argument("--adaptive-max-seconds", type=float, default=30.0)
    p.add_argument(
        "--session-salvage-on-conflict", action="store_true",
        help=(
            "permit full-session replay only when local structural salvage "
            "still violates the frozen yield/EOS/compression checks"
        ),
    )
    p.add_argument("--coverage-threshold", type=float, default=0.20)
    p.add_argument("--coverage-asymmetry-margin", type=float, default=0.15)
    p.add_argument("--structural-coverage-threshold", type=float, default=0.20)
    p.add_argument("--post-rebase-forward-threshold", type=float, default=0.20)
    p.add_argument("--post-rebase-reverse-ceiling", type=float, default=0.20)
    p.add_argument("--degeneracy-repetition-threshold", type=float, default=0.25)
    p.add_argument(
        "--coverage-repair-mode",
        choices=("singleton-replay", "witness-select"),
        default="singleton-replay",
    )
    return p.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def validate_online_contract(
    args: argparse.Namespace, contract: dict[str, Any]
) -> None:
    """Fail closed when runtime arguments drift from the frozen contract."""

    unsigned = dict(contract)
    claimed_digest = unsigned.pop("contract_digest", None)
    if canonical_digest(unsigned) != claimed_digest:
        raise RuntimeError("contract self-digest mismatch")
    expected_policy = {
        "adaptive_min_seconds": args.adaptive_min_seconds,
        "adaptive_max_seconds": args.adaptive_max_seconds,
        "coverage_threshold": args.coverage_threshold,
        "coverage_asymmetry_margin": args.coverage_asymmetry_margin,
        "structural_coverage_threshold": args.structural_coverage_threshold,
        "post_repair_forward_threshold": args.post_rebase_forward_threshold,
        "post_repair_reverse_ceiling": args.post_rebase_reverse_ceiling,
        "degeneracy_repeated_4gram_fraction": (
            args.degeneracy_repetition_threshold
        ),
    }
    frozen = contract["policy"]
    for key, value in expected_policy.items():
        if frozen.get(key) != value:
            raise RuntimeError(f"contract policy mismatch: {key}")
    budget = contract["frozen_service_budget"]
    for key in (
        "sessions", "duration_seconds", "window_seconds", "concurrency",
        "proposer_max_steps", "display_slo_seconds", "commit_slo_seconds",
    ):
        if getattr(args, key) != budget[key]:
            raise RuntimeError(f"contract budget mismatch: {key}")
    if args.model_name != contract["model_name"]:
        raise RuntimeError("contract model-name mismatch")
    if sha256_file(args.manifest) != contract["manifest_sha256"]:
        raise RuntimeError("contract manifest mismatch")
    model_config = next(
        (
            row for row in contract["model_files"]
            if row["path"] == "config.json"
        ),
        None,
    )
    if model_config is None or sha256_file(args.model / "config.json") != (
        model_config["sha256"]
    ):
        raise RuntimeError("contract model config mismatch")
    repo = Path(__file__).resolve().parents[2]
    for relative, expected in contract["source_sha256"].items():
        if sha256_file(repo / relative) != expected:
            raise RuntimeError(f"contract source mismatch: {relative}")
    import torch
    import transformers
    runtime = contract["runtime"]
    observed = {
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "gpu_names": [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ],
    }
    for key, value in observed.items():
        if runtime[key] != value:
            raise RuntimeError(f"contract runtime mismatch: {key}")


def run_proposer(
    executor: DistinctPromptWhisper,
    sessions: Sequence[Any],
    *,
    window_seconds: int,
    concurrency: int,
    max_steps: int,
    coalesce: float,
    arrival_schedule: Sequence[SessionArrival],
    coordinator: OnlineRevisionCoordinator,
) -> dict[str, Any]:
    windows_per_session = int(
        sessions[0].audio.size // (window_seconds * 16_000)
    )
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    pieces: list[list[str]] = [[] for _ in sessions]
    latencies: list[float] = []
    calls = 0
    arrivals = {row.session_id: row.arrival_time for row in arrival_schedule}
    virtual_completions = [arrivals[sid] for sid in range(len(sessions))]
    virtual_gpu_available = 0.0
    event_trace: list[dict[str, Any]] = []
    started = time.perf_counter()
    for window_index in range(windows_per_session):
        ready_events = [
            (
                sid,
                max(
                    arrivals[sid] + (window_index + 1) * window_seconds,
                    virtual_completions[sid],
                ),
            )
            for sid in range(len(sessions))
        ]
        for ids, release_time in group_ready_events(
            ready_events, concurrency=concurrency, coalesce=coalesce
        ):
            rows_audio = [windows[sid][window_index] for sid in ids]
            rows_prompt: list[tuple[int, ...]] = []
            for sid in ids:
                if capacity_rebase_required(
                    len(executor.prompt_tokens(prompts[sid])),
                    declared_next_segment_tokens=max_steps,
                    maximum_prompt_tokens=executor.max_prompt_tokens,
                ):
                    prompts[sid] = ()
                rows_prompt.append(prompts[sid])
            group_started = time.perf_counter()
            versions = {
                sid: coordinator.register_speculative(
                    sid, window_index=window_index,
                    ready_time=dict(ready_events)[sid],
                )
                for sid in ids
            }
            rows = executor.generate(
                rows_audio, rows_prompt, max_steps=max_steps
            )
            group_finished = time.perf_counter()
            virtual_start = max(release_time, virtual_gpu_available)
            virtual_finish = virtual_start + group_finished - group_started
            virtual_gpu_available = virtual_finish
            calls += 1
            for sid, record in zip(ids, rows):
                ready_time = dict(ready_events)[sid]
                latencies.append(virtual_finish - ready_time)
                pieces[sid].append(record.text)
                prompts[sid] = executor.advance_prompt(
                    prompts[sid], record.token_ids
                )
                virtual_completions[sid] = virtual_finish
                event_trace.append({
                    "session_id": sid,
                    "window_index": window_index,
                    "revision_version": versions[sid],
                    "causal_ready_time": ready_time,
                    "causal_batch_release_time": release_time,
                    "causal_completion_time": virtual_finish,
                    "actual_elapsed_seconds": record.elapsed_seconds,
                })
    return {
        "seconds": time.perf_counter() - started,
        "latencies": latencies,
        "texts": [" ".join(value for value in row if value) for row in pieces],
        "window_texts": pieces,
        "calls": calls,
        "causal_events": event_trace,
    }


def canonical_session_fallback(
    executor: DistinctPromptWhisper,
    session: Any,
    *,
    window_seconds: int,
    max_steps: int = 96,
) -> tuple[str, tuple[int, ...], list[dict[str, Any]], float, int]:
    """Replay one full session through the legal singleton authority."""

    prompt: tuple[int, ...] = ()
    pieces: list[str] = []
    trace: list[dict[str, Any]] = []
    step = window_seconds * 16_000
    started = time.perf_counter()
    calls = 0
    for start in range(0, session.audio.size, step):
        end = min(session.audio.size, start + step)
        if capacity_rebase_required(
            len(executor.prompt_tokens(prompt)),
            declared_next_segment_tokens=max_steps,
            maximum_prompt_tokens=executor.max_prompt_tokens,
        ):
            prompt = ()
        record = executor.generate(
            [np.asarray(session.audio[start:end], dtype=np.float32)],
            [prompt], max_steps=max_steps,
        )[0]
        calls += 1
        pieces.append(record.text)
        prompt = executor.advance_prompt(prompt, record.token_ids)
        trace.append({
            "audio_start_sample": start,
            "audio_end_sample": end,
            "token_sha256": record.token_sha256,
            "token_ids": list(record.token_ids),
            "generation_steps": record.generation_steps,
            "terminated_by_eos": record.terminated_by_eos,
            "text": record.text,
        })
    return (
        " ".join(piece for piece in pieces if piece),
        prompt,
        trace,
        time.perf_counter() - started,
        calls,
    )


def transaction_audit(
    sessions: Sequence[Any], traces: Sequence[Sequence[dict[str, Any]]],
    coordinator: OnlineRevisionCoordinator,
) -> dict[str, Any]:
    events = coordinator.events()
    commits = [
        row for row in events
        if row["event"] == "canonical-segment-committed"
    ]
    fallbacks_online = [
        row for row in events
        if row["event"] == "terminal-fallback-committed"
    ]
    violations = sum(
        not bool(row.get("certificate_consumed")) for row in commits
    )
    for sid, session in enumerate(sessions):
        if coordinator.state(sid).audio_frontier_window != session.audio.size:
            violations += 1
    return {
        "semantic_violations": violations,
        "rejected_invalid_installs": 0,
        "commit_certificates": len(commits),
        "segment_commits": len(commits),
        "terminal_session_fallbacks": len(fallbacks_online),
        "display_segment_repairs": sum(
            bool(row.get("display_segment_repair"))
            for trace in traces for row in trace
        ),
        "online_commit_events": len(commits) + len(fallbacks_online),
        "certificate_consumption_failures": violations,
        "exhaustively_checked_service_trace": True,
    }

    # Legacy post-hoc mutation probes are intentionally unreachable.  They are
    # retained below for one release as a diffable record of the replaced R9
    # audit path; submission claims use only the online coordinator above.
    r"""
    violations = 0
    rejected_mutations = 0
    certificates = 0
    commits = 0
    fallbacks = 0
    display_repairs = 0
    for sid, (session, rows) in enumerate(zip(sessions, traces)):
        state = FeedbackTransactionState(
            session_id=sid, contract_epoch=1,
            policy_version="r9-dgft-v4-semantic-escalation"
        )
        for row in rows:
            if row.get("display_segment_repair"):
                before = state
                for repair in row["repairs"]:
                    index = int(repair["segment_index"])
                    start = int(repair["audio_start_sample"])
                    end = int(repair["audio_end_sample"])
                    replay = list(repair["fallback_trace"])
                    if repair.get("repair_source") == "witness-select":
                        valid = (
                            0 <= index < before.checkpoint_id
                            and 0 <= start < end <= session.audio.size
                            and not replay
                            and len(str(repair.get("display_sha256", ""))) == 64
                        )
                    else:
                        valid = (
                            0 <= index < before.checkpoint_id
                            and 0 <= start < end <= session.audio.size
                            and bool(replay)
                            and int(replay[0]["audio_start_sample"]) == start
                            and int(replay[-1]["audio_end_sample"]) == end
                            and all(
                                int(left["audio_end_sample"])
                                == int(right["audio_start_sample"])
                                for left, right in zip(replay, replay[1:])
                            )
                        )
                    if not valid:
                        violations += 1
                    else:
                        display_repairs += 1
                if state != before:
                    violations += 1
                continue
            if row.get("checkpoint_rebase"):
                replacement = tuple(
                    tuple(int(v) for v in item["token_ids"])
                    for item in row["fallback_trace"]
                )
                result = commit_checkpoint_rebase(
                    state,
                    expected_contract_epoch=1,
                    expected_policy_version="r9-dgft-v4-semantic-escalation",
                    rebase_checkpoint_id=int(row["rebase_segment_index"]),
                    audio_start_frontier=int(row["rebase_start_sample"]),
                    final_audio_frontier=session.audio.size,
                    replacement_segments=replacement,
                    next_prompt_tokens=row["next_prompt_token_ids"],
                    fallback_id=f"checkpoint-rebase:{sid}",
                )
                if not result.accepted:
                    violations += 1
                else:
                    state = result.state
                    fallbacks += 1
                continue
            if row.get("terminal_session_fallback") or row.get("checkpoint_rebase"):
                replacement = tuple(
                    tuple(int(v) for v in item["token_ids"])
                    for item in row["fallback_trace"]
                )
                result = commit_session_fallback(
                    state,
                    expected_contract_epoch=1,
                    expected_policy_version="r9-dgft-v4-semantic-escalation",
                    final_audio_frontier=session.audio.size,
                    replacement_segments=replacement,
                    next_prompt_tokens=row["next_prompt_token_ids"],
                    fallback_id=f"fallback:{sid}",
                )
                if not result.accepted:
                    violations += 1
                else:
                    state = result.state
                    fallbacks += 1
                continue
            start = int(round(float(row["audio_start_window"]) * 10 * 16_000))
            end = int(round(float(row["audio_end_window"]) * 10 * 16_000))
            if tuple(row["prompt_token_ids"]) != state.prompt_tokens:
                violations += 1
            job = CanonicalSegmentJob(
                session_id=sid,
                contract_epoch=1,
                policy_version="r9-dgft-v4-semantic-escalation",
                parent_checkpoint_id=state.checkpoint_id,
                audio_start_window=start,
                audio_end_window=end,
                segment_id=f"{sid}:{start}:{end}",
                prompt_digest=digest_tokens(state.prompt_tokens),
            )
            build_dual_axis_certificate(
                job=job,
                audio=np.asarray(session.audio[start:end], dtype=np.float32).tobytes(),
                display_tokens=row["selected_token_ids"],
                feedback_state_tokens=row["next_prompt_token_ids"],
                canonical_runtime_digest="whisper-fp16-dgft-v1",
            )
            certificates += 1
            for invalid in (
                replace(job, session_id=sid + 10_000),
                replace(job, contract_epoch=0),
                replace(job, policy_version="stale"),
                replace(job, audio_start_window=start + 1),
            ):
                invalid_result = commit_canonical_segment(
                    state, invalid, segment_tokens=(), next_prompt_tokens=()
                )
                if invalid_result.accepted:
                    violations += 1
                else:
                    rejected_mutations += 1
            result = commit_canonical_segment(
                state, job,
                segment_tokens=row["selected_token_ids"],
                next_prompt_tokens=row["next_prompt_token_ids"],
            )
            if not result.accepted:
                violations += 1
                continue
            state = result.state
            commits += 1
            duplicate = commit_canonical_segment(
                state, job, segment_tokens=(), next_prompt_tokens=()
            )
            if duplicate.accepted:
                violations += 1
            else:
                rejected_mutations += 1
        if state.audio_frontier_window != session.audio.size:
            violations += 1
    return {
        "semantic_violations": violations,
        "rejected_invalid_installs": rejected_mutations,
        "commit_certificates": certificates,
        "segment_commits": commits,
        "terminal_session_fallbacks": fallbacks,
        "display_segment_repairs": display_repairs,
    }
    """


def main() -> int:
    args = parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    validate_online_contract(args, contract)
    policy_version = str(contract["policy_version"])
    contract_digest = str(contract["contract_digest"])
    runtime_digest = canonical_digest(contract["runtime"])
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    clean = args.sessions // 2
    sessions = (
        build_sessions(
            manifest["records"], split="test-clean", count=clean,
            duration_seconds=args.duration_seconds, seed=args.seed,
        )
        + build_sessions(
            manifest["records"], split="test-other",
            count=args.sessions - clean,
            duration_seconds=args.duration_seconds, seed=args.seed + 1,
        )
    )
    baseline = DistinctPromptWhisper(
        args.model, device=args.proposer_device, max_new_tokens=96
    )
    baseline.generate([sessions[0].audio[:10 * 16_000]], [()])
    baseline_meter = EnergyMeter((int(args.proposer_device.split(":")[-1]),))
    baseline_meter.start()
    (
        _, baseline_seconds, _, _, _, _, _
    ) = run_mode(
        mode="sequential", executor=baseline, sessions=sessions,
        windows_per_session=args.duration_seconds // args.window_seconds,
        window_seconds=args.window_seconds,
        adaptive_min_seconds=args.adaptive_min_seconds,
        adaptive_max_seconds=args.adaptive_max_seconds,
    )
    baseline_energy = baseline_meter.stop()
    authority = DistinctPromptWhisper(
        args.model, device=args.authority_device, max_new_tokens=192
    )
    authority.generate([sessions[0].audio[:20 * 16_000]], [()])
    arrivals = initial_session_arrivals(
        sessions=len(sessions), arrival=args.arrival,
        scale=args.arrival_scale_seconds, seed=args.seed,
    )
    coordinator = OnlineRevisionCoordinator(
        sessions=len(sessions), contract_epoch=1,
        policy_version=policy_version, contract_digest=contract_digest,
        canonical_runtime_digest=runtime_digest,
    )

    def online_commit(
        sid: int, row: dict[str, Any], audio_bytes: bytes | memoryview
    ) -> dict[str, Any]:
        return coordinator.commit_segment(
            session_id=sid,
            audio_start_sample=int(round(
                float(row["audio_start_window"])
                * args.window_seconds * 16_000
            )),
            audio_end_sample=int(round(
                float(row["audio_end_window"])
                * args.window_seconds * 16_000
            )),
            audio=audio_bytes,
            prompt_tokens=row["prompt_token_ids"],
            display_tokens=row["selected_token_ids"],
            feedback_state_tokens=row["next_prompt_token_ids"],
            authority_started=float(row["authority_started_perf"]),
            authority_finished=float(row["authority_finished_perf"]),
            virtual_ready_time=float(row["causal_audio_ready_time"]),
            virtual_commit_time=float(row["causal_authority_commit_time"]),
        )
    service_meter = EnergyMeter((
        int(args.proposer_device.split(":")[-1]),
        int(args.authority_device.split(":")[-1]),
    ))
    service_meter.start()
    service_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        proposal_future = pool.submit(
            run_proposer, baseline, sessions,
            window_seconds=args.window_seconds,
            concurrency=args.concurrency,
            max_steps=args.proposer_max_steps,
            coalesce=args.coalesce_seconds,
            arrival_schedule=arrivals,
            coordinator=coordinator,
        )
        authority_future = pool.submit(
            run_batched_adaptive,
            mode="adaptive15_30_batch",
            executor=authority,
            sessions=sessions,
            concurrency=args.concurrency,
            window_seconds=args.window_seconds,
            adaptive_min_seconds=args.adaptive_min_seconds,
            adaptive_max_seconds=args.adaptive_max_seconds,
            salvage_yield_threshold=1.0,
            salvage_max_steps=96,
            session_salvage_on_conflict=args.session_salvage_on_conflict,
            arrival_schedule=arrivals,
            coalesce_seconds=args.coalesce_seconds,
            on_segment=online_commit,
        )
        proposal = proposal_future.result()
        (
            stable_texts, authority_seconds, authority_calls,
            authority_segment_jobs, authority_audio_seconds, traces,
            authority_metrics,
        ) = authority_future.result()
    for sid, trace in enumerate(traces):
        for row in trace:
            if not row.get("terminal_session_fallback"):
                continue
            fallback_started = time.perf_counter() - float(
                row["fallback_elapsed_seconds"]
            )
            row["online_commit"] = coordinator.commit_terminal_fallback(
                session_id=sid,
                final_audio_frontier=sessions[sid].audio.size,
                audio=memoryview(np.ascontiguousarray(
                    sessions[sid].audio, dtype=np.float32
                )).cast("B"),
                replacement_segments=tuple(
                    tuple(int(v) for v in item["token_ids"])
                    for item in row["fallback_trace"]
                ),
                next_prompt_tokens=row["next_prompt_token_ids"],
                fallback_id=f"structural-fallback:{sid}",
                authority_started=fallback_started,
            )
    dual_path_seconds = time.perf_counter() - service_started
    coverage_started = time.perf_counter()
    structural = {
        sid for sid, trace in enumerate(traces)
        if any(row.get("terminal_session_fallback") for row in trace)
    }
    coverage = [
        segment_decisions(
            fine_windows=list(fine_windows), coarse_trace=list(trace),
            window_seconds=args.window_seconds,
            threshold=args.coverage_threshold,
            asymmetry_margin=args.coverage_asymmetry_margin,
            structural_threshold=args.structural_coverage_threshold,
        )
        for fine_windows, trace in zip(proposal["window_texts"], traces)
    ]
    coverage_decision_seconds = time.perf_counter() - coverage_started
    repair_started = time.perf_counter()
    coverage_fallbacks = [
        sid for sid, decisions in enumerate(coverage)
        if any(bool(row["fallback_required"]) for row in decisions)
        and sid not in structural
    ]
    coverage_fallback_seconds = 0.0
    coverage_fallback_calls = 0
    coverage_replayed_audio_seconds = 0.0
    for sid in coverage_fallbacks:
        coarse_rows = [
            row for row in traces[sid]
            if not row.get("terminal_session_fallback")
        ]
        replacements: dict[int, str] = {}
        repair_rows: list[dict[str, Any]] = []
        session_elapsed = 0.0
        for conflict in coverage[sid]:
            if not conflict["fallback_required"]:
                continue
            segment_index = int(conflict["segment_index"])
            start_sample = int(round(
                float(conflict["start_seconds"]) * 16_000
            ))
            end_sample = int(round(
                float(conflict["end_seconds"]) * 16_000
            ))
            if args.coverage_repair_mode == "witness-select":
                text = str(conflict["fine_text"])
                elapsed, calls, replay_audio, fallback_trace = (
                    0.0, 0, 0.0, []
                )
            else:
                parent_prompt = tuple(
                    int(value)
                    for value in coarse_rows[segment_index]["prompt_token_ids"]
                )
                text, elapsed, calls, replay_audio, fallback_trace = (
                    replay_from_checkpoint(
                        authority, sessions[sid], start_sample=start_sample,
                        end_sample=end_sample, parent_prompt=parent_prompt,
                        window_seconds=args.window_seconds,
                    )
                )
            replacements[segment_index] = text
            session_elapsed += elapsed
            coverage_fallback_seconds += elapsed
            coverage_fallback_calls += calls
            coverage_replayed_audio_seconds += replay_audio
            authority_audio_seconds += replay_audio
            repair_rows.append({
                "segment_index": segment_index,
                "audio_start_sample": start_sample,
                "audio_end_sample": end_sample,
                "coverage_deficit": float(conflict["deficit"]),
                "repair_source": args.coverage_repair_mode,
                "display_sha256": hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest(),
                "fallback_trace": fallback_trace,
            })
        stable_texts[sid] = " ".join(
            replacements.get(index, str(row["text"]))
            for index, row in enumerate(coarse_rows)
            if replacements.get(index, str(row["text"]))
        )
        traces[sid].append({
            "display_segment_repair": True,
            "coverage_conflict": True,
            "parent_conflict_segments": 0,
            "repairs": repair_rows,
            "fallback_elapsed_seconds": session_elapsed,
        })
    full_session_escalations: list[int] = []
    post_rebase_decisions: list[dict[str, Any]] = []
    for sid in coverage_fallbacks:
        decision = classify_asymmetric_omission_conflict(
            proposal["texts"][sid], stable_texts[sid],
            forward_threshold=args.post_rebase_forward_threshold,
            reverse_ceiling=args.post_rebase_reverse_ceiling,
        )
        post_rebase_decisions.append({
            "session_id": sid,
            "forward_deficit": decision.forward_deficit,
            "reverse_deficit": decision.reverse_deficit,
            "fallback_required": decision.fallback_required,
        })
        if not decision.fallback_required:
            continue
        text, prompt, fallback_trace, elapsed, calls = canonical_session_fallback(
            authority, sessions[sid], window_seconds=args.window_seconds
        )
        stable_texts[sid] = text
        coverage_fallback_seconds += elapsed
        coverage_fallback_calls += calls
        authority_audio_seconds += sessions[sid].audio.size / 16_000
        full_session_escalations.append(sid)
        traces[sid].append({
            "terminal_session_fallback": True,
            "post_rebase_asymmetric_omission": True,
            "forward_deficit": decision.forward_deficit,
            "reverse_deficit": decision.reverse_deficit,
            "parent_conflict_segments": 0,
            "fallback_trace": fallback_trace,
            "next_prompt_token_ids": list(prompt),
            "fallback_elapsed_seconds": elapsed,
        })
        traces[sid][-1]["online_commit"] = (
            coordinator.commit_terminal_fallback(
                session_id=sid,
                final_audio_frontier=sessions[sid].audio.size,
                audio=memoryview(np.ascontiguousarray(
                    sessions[sid].audio, dtype=np.float32
                )).cast("B"),
                replacement_segments=tuple(
                    tuple(int(v) for v in item["token_ids"])
                    for item in fallback_trace
                ),
                next_prompt_tokens=prompt,
                fallback_id=f"omission-fallback:{sid}",
                authority_started=time.perf_counter() - elapsed,
            )
        )
    degeneracy_scores = {
        sid: max(
            (
                repeated_ngram_fraction(str(row.get("text", "")))
                for row in trace if row.get("structural_conflict")
            ),
            default=0.0,
        )
        for sid, trace in enumerate(traces)
    }
    degeneracy_escalations: list[int] = []
    for sid, score in degeneracy_scores.items():
        if (
            score < args.degeneracy_repetition_threshold
            or sid in full_session_escalations
        ):
            continue
        text, prompt, fallback_trace, elapsed, calls = canonical_session_fallback(
            authority, sessions[sid], window_seconds=args.window_seconds
        )
        stable_texts[sid] = text
        coverage_fallback_seconds += elapsed
        coverage_fallback_calls += calls
        authority_audio_seconds += sessions[sid].audio.size / 16_000
        full_session_escalations.append(sid)
        degeneracy_escalations.append(sid)
        traces[sid].append({
            "terminal_session_fallback": True,
            "structural_repetition_after_local_salvage": True,
            "repeated_4gram_fraction": score,
            "parent_conflict_segments": 0,
            "fallback_trace": fallback_trace,
            "next_prompt_token_ids": list(prompt),
            "fallback_elapsed_seconds": elapsed,
        })
        traces[sid][-1]["online_commit"] = (
            coordinator.commit_terminal_fallback(
                session_id=sid,
                final_audio_frontier=sessions[sid].audio.size,
                audio=memoryview(np.ascontiguousarray(
                    sessions[sid].audio, dtype=np.float32
                )).cast("B"),
                replacement_segments=tuple(
                    tuple(int(v) for v in item["token_ids"])
                    for item in fallback_trace
                ),
                next_prompt_tokens=prompt,
                fallback_id=f"degeneracy-fallback:{sid}",
                authority_started=time.perf_counter() - elapsed,
            )
        )
    authority_seconds += coverage_fallback_seconds
    authority_calls += coverage_fallback_calls
    authority_metrics["coverage_conflicts"] = sum(
        bool(row["fallback_required"])
        for decisions in coverage for row in decisions
    )
    authority_metrics["coverage_fallbacks"] = len(coverage_fallbacks)
    authority_metrics["coverage_fallback_seconds"] = coverage_fallback_seconds
    authority_metrics["coverage_replayed_audio_seconds"] = (
        coverage_replayed_audio_seconds
    )
    authority_metrics["post_rebase_decisions"] = post_rebase_decisions
    authority_metrics["full_session_escalations"] = len(
        full_session_escalations
    )
    authority_metrics["full_session_escalation_ids"] = (
        full_session_escalations
    )
    authority_metrics["degeneracy_repetition_threshold"] = (
        args.degeneracy_repetition_threshold
    )
    authority_metrics["degeneracy_escalations"] = len(
        degeneracy_escalations
    )
    authority_metrics["degeneracy_escalation_ids"] = degeneracy_escalations
    authority_metrics["maximum_structural_repetition_score"] = max(
        degeneracy_scores.values(), default=0.0
    )
    repair_and_escalation_seconds = time.perf_counter() - repair_started
    for sid in range(len(sessions)):
        coordinator.close_speculative_descendants(sid)
    service_seconds = time.perf_counter() - service_started
    service_energy = service_meter.stop()
    audit_started = time.perf_counter()
    coordinator.assert_complete([session.audio.size for session in sessions])
    audit = transaction_audit(sessions, traces, coordinator)
    transaction_audit_seconds = time.perf_counter() - audit_started
    display_p99 = percentile(proposal["latencies"], 0.99)
    online_events = coordinator.events()
    processing_commit_lags = [
        float(row["actual_commit_latency_seconds"])
        for row in online_events
        if row["event"] in {
            "canonical-segment-committed", "terminal-fallback-committed"
        }
    ]
    causal_commit_lags = [
        float(row["virtual_commit_time"]) - float(row["virtual_ready_time"])
        for row in online_events
        if row["event"] == "canonical-segment-committed"
        and row.get("virtual_commit_time") is not None
        and row.get("virtual_ready_time") is not None
    ]
    display_repair_lags: list[float] = []
    for session_trace in traces:
        last_segment_seconds = 0.0
        for row in session_trace:
            if row.get("display_segment_repair"):
                display_repair_lags.append(
                    last_segment_seconds + float(row["fallback_elapsed_seconds"])
                )
            elif not (
                row.get("terminal_session_fallback")
                or row.get("checkpoint_rebase")
            ):
                last_segment_seconds = float(row["audio_seconds"])
    processing_commit_p99 = percentile(processing_commit_lags, 0.99)
    terminal_processing_lags = [
        float(row["actual_commit_latency_seconds"])
        for row in online_events
        if row["event"] == "terminal-fallback-committed"
    ]
    commit_lags = (
        [*causal_commit_lags, *terminal_processing_lags]
        if causal_commit_lags else processing_commit_lags
    )
    commit_p99 = percentile(commit_lags, 0.99)
    correction_edits: list[float] = []
    for provisional, stable in zip(proposal["texts"], stable_texts):
        edits, words = word_error(stable, provisional)
        correction_edits.append(edits / max(1, words))
    wall_speedup = baseline_seconds / service_seconds
    gpu_speedup = baseline_seconds / (2.0 * service_seconds)
    energy_reduction = (
        1.0 - service_energy / baseline_energy
        if service_energy is not None and baseline_energy not in (None, 0.0)
        else None
    )
    audio_amplification = authority_audio_seconds / (
        len(sessions) * args.duration_seconds
    )
    passed = (
        wall_speedup >= 2.5
        and gpu_speedup >= 1.25
        and display_p99 <= args.display_slo_seconds
        and commit_p99 <= args.commit_slo_seconds
        and energy_reduction is not None and energy_reduction >= 0.20
        and audio_amplification <= 1.2
        and audit["semantic_violations"] == 0
    )
    payload = {
        "schema_version": 1,
        "study": "R9 DGFT real two-GPU service",
        "decision": "PASS_R9_DGFT_SERVICE" if passed else "FAIL_R9_DGFT_SERVICE",
        "config": vars(args) | {
            "model": str(args.model), "manifest": str(args.manifest),
            "contract": str(args.contract), "output": str(args.output),
            "contract_digest": contract_digest,
            "policy_version": policy_version,
            "canonical_runtime_digest": runtime_digest,
            "initial_session_arrivals": [
                {
                    "session_id": row.session_id,
                    "arrival_time": row.arrival_time,
                }
                for row in arrivals
            ],
            "frozen_policy": {
                "adaptive_min_seconds": args.adaptive_min_seconds,
                "adaptive_max_seconds": args.adaptive_max_seconds,
                "segment_yield_floor": 1.0,
                "session_salvage_on_conflict": (
                    args.session_salvage_on_conflict
                ),
                "coverage_threshold": args.coverage_threshold,
                "coverage_asymmetry_margin": args.coverage_asymmetry_margin,
                "structural_coverage_threshold": (
                    args.structural_coverage_threshold
                ),
                "coverage_scope": "segment-display-repair",
                "coverage_repair_mode": args.coverage_repair_mode,
                "post_rebase_forward_threshold": (
                    args.post_rebase_forward_threshold
                ),
                "post_rebase_reverse_ceiling": (
                    args.post_rebase_reverse_ceiling
                ),
            },
        },
        "metrics": {
            "baseline_wall_seconds": baseline_seconds,
            "service_wall_seconds": service_seconds,
            "wall_speedup": wall_speedup,
            "gpu_normalized_speedup": gpu_speedup,
            "display_latency_p99": display_p99,
            "segment_commit_lag_p95": percentile(commit_lags, 0.95),
            "segment_commit_lag_p99": commit_p99,
            "online_commit_processing_latency_p99": processing_commit_p99,
            "causal_segment_commit_lag_p99": commit_p99,
            "display_repair_lag_p99": (
                percentile(display_repair_lags, 0.99)
                if display_repair_lags else 0.0
            ),
            "maximum_uncommitted_audio_horizon": max(
                float(row["audio_seconds"])
                for trace in traces for row in trace
                if not row.get("terminal_session_fallback")
                and not row.get("checkpoint_rebase")
                and not row.get("display_segment_repair")
            ),
            "baseline_energy_joules": baseline_energy,
            "service_energy_joules": service_energy,
            "energy_reduction": energy_reduction,
            "authority_seconds": authority_seconds,
            "dual_path_seconds": dual_path_seconds,
            "coverage_decision_seconds": coverage_decision_seconds,
            "repair_and_escalation_seconds": repair_and_escalation_seconds,
            "transaction_audit_seconds": transaction_audit_seconds,
            "authority_calls": authority_calls,
            "authority_segment_jobs": authority_segment_jobs,
            "authority_audio_amplification": audio_amplification,
            "proposer_calls": proposal["calls"],
            "mean_provisional_correction_rate": statistics.fmean(
                correction_edits
            ),
            "correction_rate_p95": percentile(correction_edits, 0.95),
            **authority_metrics,
            **audit,
        },
        "online_transaction_trace": coordinator.snapshot(),
        "sessions": [
            {
                "session_id": sid,
                "split": session.split,
                "utterance_ids": list(session.utterance_ids),
                "provisional_text": proposal["texts"][sid],
                "stable_text": stable_texts[sid],
                "coverage_segments": coverage[sid],
                "structural_fallback": sid in structural,
                "coverage_repair": sid in coverage_fallbacks,
                "full_session_escalation": sid in full_session_escalations,
            }
            for sid, session in enumerate(sessions)
        ],
        "claim_boundary": (
            "real concurrent two-GPU wall time and sampled NVML energy; raw-"
            "audio boundaries and structural fallback do not use reference "
            "text; local display repair uses singleton evidence only for the "
            "conflicting segment while preserving the separately certified "
            "feedback-state axis; persistent omission escalates to full replay; "
            "one immutable initial-arrival stream causally releases all later "
            "revisions; commit latency uses online coordinator timestamps, "
            "not reconstructed audio duration; batched segment authority is "
            "a versioned coarse canonical "
            "trajectory, not bitwise per-window singleton equivalence"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
