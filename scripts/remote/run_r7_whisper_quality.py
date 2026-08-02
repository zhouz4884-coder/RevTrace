#!/usr/bin/env python3
"""R7.5 paired quality and feedback-amplification evaluation for EFSC."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    WhisperHistoryAdapter,
)
from revtrace.feedback_metrics import edit_distance
from run_whisper_w_quality import (
    QualitySession,
    bootstrap_upper,
    build_sessions,
    canonical_system,
    normalize,
    word_error,
)
from whisper_batched_executor import DistinctPromptWhisper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--seed", type=int, default=2026080701)
    parser.add_argument("--bootstrap-seed", type=int, default=2026080702)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def longest_equal_run(rows: Sequence[str]) -> int:
    longest = 0
    current = 0
    previous: tuple[str, ...] | None = None
    for text in rows:
        value = tuple(normalize(text))
        if value and value == previous:
            current += 1
        else:
            current = 1 if value else 0
        longest = max(longest, current)
        previous = value
    return longest


def run_batched_quality(
    executor: DistinctPromptWhisper,
    sessions: Sequence[QualitySession],
    *,
    windows_per_session: int,
    concurrency: int,
    contract: EFSCContract,
) -> tuple[list[str], list[str], dict[str, Any]]:
    adapter = WhisperHistoryAdapter(executor.max_prompt_tokens - 1)
    controller = ElasticFeedbackController(contract)
    states = [
        ElasticFeedbackState(FeedbackIdentity(f"s{i}", 1, 1, 0))
        for i in range(len(sessions))
    ]
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    efsc_pieces: list[list[str]] = [[] for _ in sessions]
    off_pieces: list[list[str]] = [[] for _ in sessions]
    efsc_segments: list[list[str]] = [[] for _ in sessions]
    off_segments: list[list[str]] = [[] for _ in sessions]
    session_traces: list[list[dict[str, Any]]] = [[] for _ in sessions]
    actions = {action.value: 0 for action in FeedbackAction}
    preparations = {action.value: 0 for action in FeedbackAction}
    violations = 0
    maximum_age = 0
    maximum_debt = 0
    recovery_windows: list[int] = []
    reset_at: dict[int, int] = {}
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]
    started = time.perf_counter()
    for window_index in range(windows_per_session):
        for begin in range(0, len(sessions), concurrency):
            ids = list(range(begin, min(begin + concurrency, len(sessions))))
            preparation_debug: dict[int, dict[str, Any]] = {}
            for session_id in ids:
                prompt_before_prepare = prompts[session_id]
                state_before_prepare = states[session_id]
                state, preparation = controller.prepare_for_proposal(
                    states[session_id], adapter
                )
                states[session_id] = state
                prompts[session_id] = tuple(
                    atom.token_id for atom in state.atoms
                )
                if preparation.action is not None:
                    preparations[preparation.action.value] += 1
                    if preparation.action == FeedbackAction.SAFE_RESET:
                        reset_at[session_id] = window_index
                preparation_debug[session_id] = {
                    "prompt_tokens_before_prepare": len(prompt_before_prepare),
                    "state_version_before_prepare": (
                        state_before_prepare.identity.state_version
                    ),
                    "prepare_action": (
                        preparation.action.value
                        if preparation.action is not None else None
                    ),
                    "prepare_reason": preparation.reason,
                }
            audio = [windows[index][window_index] for index in ids]
            prompt_rows = [prompts[index] for index in ids]
            proposed = executor.generate(audio, prompt_rows)
            feedback_off = executor.generate(audio, [() for _ in ids])
            for position, session_id in enumerate(ids):
                record = proposed[position]
                off_record = feedback_off[position]
                terminal = window_index == windows_per_session - 1
                current = states[session_id]
                old_ancestors = current.ancestors
                candidate = FeedbackCandidate(
                    session_id=current.identity.session_id,
                    contract_epoch=current.identity.contract_epoch,
                    policy_version=current.identity.policy_version,
                    parent_state_version=current.identity.state_version,
                    token_ids=tuple(record.token_ids),
                    minimum_margin=record.minimum_margin,
                    terminal=terminal,
                )
                next_state, decision = controller.step(
                    current, candidate, adapter
                )
                states[session_id] = next_state
                prompts[session_id] = tuple(
                    atom.token_id for atom in next_state.atoms
                )
                actions[decision.action.value] += 1
                if (
                    decision.action != FeedbackAction.FAST_COMMIT
                    and next_state.ancestors - old_ancestors
                ):
                    violations += 1
                if (
                    not decision.candidate_became_ancestor
                    and next_state.identity.state_version
                    in next_state.ancestors
                ):
                    violations += 1
                if next_state.feedback_debt > contract.maximum_feedback_debt:
                    violations += 1
                if next_state.oldest_ancestor_age > contract.maximum_influence_windows:
                    violations += 1
                maximum_age = max(maximum_age, next_state.oldest_ancestor_age)
                maximum_debt = max(maximum_debt, next_state.feedback_debt)
                if decision.action == FeedbackAction.SAFE_RESET:
                    reset_at[session_id] = window_index
                if (
                    decision.action == FeedbackAction.FAST_COMMIT
                    and session_id in reset_at
                ):
                    recovery_windows.append(
                        window_index - reset_at.pop(session_id)
                    )
                efsc_pieces[session_id].append(record.text)
                off_pieces[session_id].append(off_record.text)
                efsc_segments[session_id].append(record.text)
                off_segments[session_id].append(off_record.text)
                debug = preparation_debug[session_id]
                session_traces[session_id].append({
                    "window_index": window_index,
                    **debug,
                    "prompt_tokens_for_proposal": len(prompt_rows[position]),
                    "minimum_margin": record.minimum_margin,
                    "generation_steps": record.generation_steps,
                    "terminated_by_eos": record.terminated_by_eos,
                    "candidate_token_ids": list(record.token_ids),
                    "candidate_text": record.text,
                    "feedback_off_text": off_record.text,
                    "decision_action": decision.action.value,
                    "decision_reason": decision.reason,
                    "candidate_became_ancestor": (
                        decision.candidate_became_ancestor
                    ),
                    "prompt_tokens_after_decision": len(prompts[session_id]),
                    "feedback_debt_after_decision": next_state.feedback_debt,
                    "oldest_ancestor_age_after_decision": (
                        next_state.oldest_ancestor_age
                    ),
                })

    repetition = [longest_equal_run(row) for row in efsc_segments]
    repetition_off = [longest_equal_run(row) for row in off_segments]
    amplification: list[float] = []
    for left, right in zip(efsc_segments, off_segments):
        distances = [
            edit_distance(normalize(a), normalize(b))
            for a, b in zip(left, right)
        ]
        first = next((i for i, value in enumerate(distances) if value), None)
        if first is not None:
            amplification.append(
                sum(distances[first:]) / max(1, distances[first])
            )
    return (
        [" ".join(row) for row in efsc_pieces],
        [" ".join(row) for row in off_pieces],
        {
            "seconds": time.perf_counter() - started,
            "actions": actions,
            "pre_proposal_actions": preparations,
            "semantic_violations": violations,
            "maximum_prompt_state_age": maximum_age,
            "maximum_feedback_debt": maximum_debt,
            "reset_recovery_windows_p95": (
                float(np.quantile(recovery_windows, 0.95))
                if recovery_windows else 0.0
            ),
            "repetition_loop_rate": statistics.fmean(
                value >= 3 for value in repetition
            ),
            "feedback_off_repetition_loop_rate": statistics.fmean(
                value >= 3 for value in repetition_off
            ),
            "longest_repetition_run": max(repetition, default=0),
            "feedback_off_longest_repetition_run": max(
                repetition_off, default=0
            ),
            "feedback_amplification_factor_mean": (
                statistics.fmean(amplification) if amplification else 0.0
            ),
            "session_traces": session_traces,
        },
    )


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window size")
    policy_payload = json.loads(args.policy.read_text(encoding="utf-8"))
    policy = policy_payload["selected_policy"]
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sessions = (
        build_sessions(
            manifest["records"], split="test-clean",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds, seed=args.seed,
        )
        + build_sessions(
            manifest["records"], split="test-other",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds, seed=args.seed + 1,
        )
    )
    utterance_ids = [
        item for session in sessions for item in session.utterance_ids
    ]
    executor = DistinctPromptWhisper(
        args.model, device=args.device, max_new_tokens=args.max_new_tokens
    )
    windows_per_session = args.duration_seconds // args.window_seconds
    canonical, canonical_seconds, capacity_rebases, canonical_traces = canonical_system(
        executor, sessions, windows_per_session
    )
    contract = EFSCContract(
        enter_margin=float(policy["enter_margin"]),
        exit_margin=float(policy["exit_margin"]),
        minimum_hold_windows=int(policy["minimum_hold_windows"]),
        safe_streak_required=int(policy["safe_streak_required"]),
        maximum_quarantine_windows=int(policy["maximum_quarantine_windows"]),
        maximum_feedback_debt=int(policy["maximum_feedback_debt"]),
        maximum_influence_windows=int(policy["maximum_influence_windows"]),
        maximum_prompt_tokens=executor.max_prompt_tokens - 1,
        decay_suffix_tokens=min(32, executor.max_prompt_tokens - 2),
    )
    efsc, feedback_off, runtime = run_batched_quality(
        executor, sessions, windows_per_session=windows_per_session,
        concurrency=args.concurrency, contract=contract
    )
    canonical_repetition = [
        longest_equal_run([str(event["text"]) for event in trace])
        for trace in canonical_traces
    ]
    rows: list[dict[str, Any]] = []
    deltas: list[float] = []
    catastrophic = 0
    for index, session in enumerate(sessions):
        errors_c, words = word_error(session.reference, canonical[index])
        errors_e, _ = word_error(session.reference, efsc[index])
        errors_o, _ = word_error(session.reference, feedback_off[index])
        wer_c = 100.0 * errors_c / max(1, words)
        wer_e = 100.0 * errors_e / max(1, words)
        wer_o = 100.0 * errors_o / max(1, words)
        delta = wer_e - wer_c
        outlier = delta > 10.0 or (
            wer_e > 2.0 * max(wer_c, 1.0) and delta > 5.0
        )
        catastrophic += int(outlier)
        deltas.append(delta)
        rows.append({
            "session_id": index,
            "split": session.split,
            "utterance_ids": list(session.utterance_ids),
            "reference_words": words,
            "canonical_wer": wer_c,
            "efsc_wer": wer_e,
            "feedback_off_wer": wer_o,
            "efsc_delta_pp": delta,
            "catastrophic_outlier": outlier,
            "canonical_text": canonical[index],
            "efsc_text": efsc[index],
            "feedback_off_text": feedback_off[index],
            "canonical_repetition_run": canonical_repetition[index],
            "canonical_trace": canonical_traces[index],
            "efsc_trace": runtime["session_traces"][index],
        })
    mean_delta = statistics.fmean(deltas)
    upper = bootstrap_upper(
        deltas, seed=args.bootstrap_seed,
        replicates=args.bootstrap_replicates
    )
    split_metrics: dict[str, dict[str, float | int]] = {}
    for split in ("test-clean", "test-other"):
        split_rows = [row for row in rows if row["split"] == split]
        split_deltas = [float(row["efsc_delta_pp"]) for row in split_rows]
        split_metrics[split] = {
            "sessions": len(split_rows),
            "canonical_mean_wer": statistics.fmean(
                float(row["canonical_wer"]) for row in split_rows
            ),
            "efsc_mean_wer": statistics.fmean(
                float(row["efsc_wer"]) for row in split_rows
            ),
            "feedback_off_mean_wer": statistics.fmean(
                float(row["feedback_off_wer"]) for row in split_rows
            ),
            "mean_wer_delta_pp": statistics.fmean(split_deltas),
            "paired_bootstrap_95_upper_pp": bootstrap_upper(
                split_deltas,
                seed=args.bootstrap_seed + (0 if split == "test-clean" else 1),
                replicates=args.bootstrap_replicates,
            ),
        }
    canonical_repetition_loop_rate = statistics.fmean(
        value >= 3 for value in canonical_repetition
    )
    split_quality_pass = all(
        float(metrics["mean_wer_delta_pp"]) <= 1.0
        and float(metrics["paired_bootstrap_95_upper_pp"]) <= 2.0
        for metrics in split_metrics.values()
    )
    passed = (
        len(sessions) >= 128
        and len(utterance_ids) == len(set(utterance_ids))
        and mean_delta <= 1.0
        and upper <= 2.0
        and catastrophic == 0
        and runtime["semantic_violations"] == 0
        and runtime["repetition_loop_rate"]
        <= canonical_repetition_loop_rate
        and split_quality_pass
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R7.5 Whisper EFSC paired quality",
        "decision": "PASS_R7_5_QUALITY" if passed else "FAIL_R7_5_QUALITY",
        "model": args.model_name,
        "config": {
            "sessions_per_split": args.sessions_per_split,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "seed": args.seed,
            "bootstrap_seed": args.bootstrap_seed,
            "bootstrap_replicates": args.bootstrap_replicates,
            "model_path": str(args.model.resolve()),
            "policy_path": str(args.policy.resolve()),
            "policy_sha256": hashlib.sha256(args.policy.read_bytes()).hexdigest(),
            "contract": contract.__dict__,
        },
        "counts": {
            "sessions": len(sessions),
            "unique_utterances": len(set(utterance_ids)),
            "utterance_reuse": len(utterance_ids) - len(set(utterance_ids)),
            "catastrophic_outliers": catastrophic,
            "actions": runtime["actions"],
            "pre_proposal_actions": runtime["pre_proposal_actions"],
            "semantic_violations": runtime["semantic_violations"],
        },
        "metrics": {
            "canonical_mean_wer": statistics.fmean(row["canonical_wer"] for row in rows),
            "efsc_mean_wer": statistics.fmean(row["efsc_wer"] for row in rows),
            "feedback_off_mean_wer": statistics.fmean(row["feedback_off_wer"] for row in rows),
            "mean_wer_delta_pp": mean_delta,
            "paired_bootstrap_95_upper_pp": upper,
            "split_metrics": split_metrics,
            "split_quality_pass": split_quality_pass,
            "canonical_seconds": canonical_seconds,
            "canonical_capacity_rebases": capacity_rebases,
            "canonical_repetition_loop_rate": canonical_repetition_loop_rate,
            "canonical_longest_repetition_run": max(
                canonical_repetition, default=0
            ),
            **{
                key: value for key, value in runtime.items()
                if key != "session_traces"
            },
        },
        "sessions": rows,
        "claim_boundary": (
            "repetition is an exact normalized-segment loop metric; lower "
            "rate supports containment but is not a hallucination guarantee"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}, default=str))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
