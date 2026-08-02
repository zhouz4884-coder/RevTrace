#!/usr/bin/env python3
"""Evaluate the frozen reference-free CSDR recovery policy.

The CSM sees only current audio/candidate/state features.  A bounded structural
reanchor horizon is retained because a monitor cannot certify the absence of
an information-loss root.  Every installed context capsule is transcribed by
the canonical singleton path from raw audio strictly preceding the revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import zlib
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
    install_authoritative_feedback_capsule,
)
from revtrace.context_reanchor import (
    asymmetric_context_conflict,
    bound_feedback_prompt,
    extract_bounded_audio_delta,
    safe_display_override_candidate,
)
from revtrace.sufficiency import csm_forest_score
from revtrace.whisper_state import capacity_rebase_required
from run_r7_whisper_quality import longest_equal_run
from run_whisper_w_quality import bootstrap_upper, build_sessions, word_error
from whisper_batched_executor import DistinctPromptWhisper, WhisperCandidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-quality", type=Path, required=True)
    parser.add_argument("--efsc-policy", type=Path, required=True)
    parser.add_argument("--csm-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument(
        "--replay-step-budget",
        type=int,
        default=48,
        help=(
            "Maximum steps in a shared replay batch. Rows that exhaust the "
            "budget fail closed to the full singleton cutset authority."
        ),
    )
    parser.add_argument("--seed", type=int, default=2026080701)
    parser.add_argument("--bootstrap-seed", type=int, default=2026081301)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--selector",
        choices=(
            "yield",
            "min-score",
            "agreement-score",
            "acoustic-score",
            "canonical-replay",
            "segmented-20",
            "segmented-30",
        ),
        default="yield",
    )
    parser.add_argument(
        "--disable-structural-rules",
        action="store_true",
        help="Use only the frozen forest operating point for recovery scheduling.",
    )
    parser.add_argument(
        "--structural-rule-mode",
        choices=("full", "absolute", "none"),
        default="full",
    )
    parser.add_argument("--agreement-threshold", type=float, default=1.0)
    parser.add_argument("--recovery-score-threshold", type=float, default=0.05)
    parser.add_argument(
        "--canonical-lease-windows",
        type=int,
        default=0,
        help="Canonical windows after a trigger; zero leases through terminal.",
    )
    parser.add_argument(
        "--csm-trigger-threshold",
        type=float,
        default=None,
        help="Optional development-calibrated session-escalation threshold.",
    )
    parser.add_argument(
        "--lineage-reconciliation",
        action="store_true",
        help=(
            "Atomically replace the provisional display prefix with the "
            "independent raw-audio replay lineage whenever replay catches "
            "up.  At terminal, reconcile every session in one batched pass."
        ),
    )
    parser.add_argument(
        "--continuous-lineage-replay",
        action="store_true",
        help=(
            "Advance the independent replay frontier for every active session "
            "on every window, avoiding terminal catch-up microbatches."
        ),
    )
    parser.add_argument(
        "--replay-prompt-tokens",
        type=int,
        default=223,
        help=(
            "Maximum independent replay content tokens retained across "
            "windows; rejected proposer text is never copied into this lane."
        ),
    )
    parser.add_argument(
        "--replay-overlap-seconds",
        type=float,
        default=0.0,
        help=(
            "Raw-audio overlap prepended to each replay window.  Positive "
            "values use empty-prompt acoustic delta reanchoring instead of "
            "text feedback across replay windows."
        ),
    )
    return parser.parse_args()


def frame_rms(audio: np.ndarray, frame_samples: int = 320) -> np.ndarray:
    usable = audio[: audio.size // frame_samples * frame_samples]
    if not usable.size:
        return np.zeros(1, dtype=np.float64)
    frames = usable.reshape(-1, frame_samples).astype(np.float64)
    return np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)


def candidate_features(
    audio: np.ndarray,
    record: WhisperCandidate,
    previous_yields: Sequence[float],
    state: ElasticFeedbackState,
) -> dict[str, float]:
    rms = frame_rms(audio)
    noise = float(np.quantile(rms, 0.20))
    threshold = max(noise * 2.5, 1e-4)
    speech_ratio = float(np.mean(rms >= threshold))
    active_seconds = max(0.02, speech_ratio * (audio.size / 16_000.0))
    token_count = len(record.token_ids)
    token_yield = token_count / active_seconds
    prior = (
        statistics.median(previous_yields[-2:])
        if previous_yields else token_yield
    )
    return {
        "generation_steps": float(record.generation_steps),
        "token_count": float(token_count),
        "token_yield": token_yield,
        "relative_yield_drop": max(
            0.0, 1.0 - token_yield / max(prior, 1e-6)
        ),
        "speech_active_ratio": speech_ratio,
        "speech_token_mismatch": speech_ratio / (1.0 + token_count),
        "terminated_by_eos": float(record.terminated_by_eos),
        "minimum_margin": float(record.minimum_margin or 0.0),
        "feedback_debt": float(state.feedback_debt),
        "state_age": float(state.oldest_ancestor_age),
        "first_step_no_speech_probability": float(
            record.first_step_no_speech_probability or 0.0
        ),
        "average_token_log_probability": float(
            record.average_token_log_probability or 0.0
        ),
        "compression_ratio": float(record.compression_ratio or 0.0),
    }


def install_recent_capsule(
    executor: DistinctPromptWhisper,
    state: ElasticFeedbackState,
    prior_audio: np.ndarray,
    current_audio: np.ndarray,
) -> tuple[ElasticFeedbackState, WhisperCandidate, WhisperCandidate, float]:
    started = time.perf_counter()
    capsule = executor.canonical(prior_audio, ())
    recovered = executor.canonical(current_audio, capsule.token_ids)
    elapsed = time.perf_counter() - started
    return (
        install_authoritative_feedback_capsule(state, capsule.token_ids),
        capsule,
        recovered,
        elapsed,
    )


def concatenate(rows: Sequence[np.ndarray]) -> np.ndarray:
    if not rows:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate([np.asarray(row, dtype=np.float32) for row in rows])


def normalized_words(text: str) -> tuple[str, ...]:
    return tuple(
        word.strip(".,!?;:\"'()[]{}-").lower()
        for word in text.split()
        if word.strip(".,!?;:\"'()[]{}-")
    )


def word_edit_distance(left: Sequence[str], right: Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for row_index, left_word in enumerate(left, 1):
        current = [row_index]
        for column_index, right_word in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[column_index] + 1,
                previous[column_index - 1] + (left_word != right_word),
            ))
        previous = current
    return previous[-1]


def agreement(left: str, right: str) -> float:
    left_words = normalized_words(left)
    right_words = normalized_words(right)
    denominator = max(1, len(left_words), len(right_words))
    return 1.0 - word_edit_distance(left_words, right_words) / denominator


def longest_consecutive_word_run(text: str) -> int:
    longest = 0
    current = 0
    previous: str | None = None
    for word in normalized_words(text):
        if word == previous:
            current += 1
        else:
            current = 1
            previous = word
        longest = max(longest, current)
    return longest


def sufficiency_trigger(
    *,
    csm: dict[str, Any],
    features: dict[str, float],
    csm_score: float,
    structural_mode: str,
    trigger_threshold: float,
) -> tuple[bool, bool]:
    hard_rules = csm["structural_sufficiency_rules"]
    hard_trigger = (
        structural_mode != "none"
        and (
            features["token_count"]
            <= float(hard_rules["absolute_token_floor"])
            or (
                structural_mode == "full"
                and features["token_count"]
                <= float(hard_rules["conditional_token_floor"])
                and csm_score
                >= float(hard_rules["conditional_forest_score"])
            )
        )
    )
    return csm_score > trigger_threshold or hard_trigger, hard_trigger


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source = json.loads(args.source_quality.read_text(encoding="utf-8"))
    efsc_payload = json.loads(args.efsc_policy.read_text(encoding="utf-8"))
    csm_payload = json.loads(args.csm_policy.read_text(encoding="utf-8"))
    policy = efsc_payload["selected_policy"]
    csm = csm_payload["frozen_policy"]
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
    if len(sessions) != len(source["sessions"]):
        raise AssertionError("source quality/session count mismatch")
    for session, row in zip(sessions, source["sessions"]):
        if tuple(session.utterance_ids) != tuple(row["utterance_ids"]):
            raise AssertionError("source quality utterance reconstruction mismatch")

    executor = DistinctPromptWhisper(
        args.model, device=args.device, max_new_tokens=args.max_new_tokens
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
    controller = ElasticFeedbackController(contract)
    adapter = WhisperHistoryAdapter(executor.max_prompt_tokens - 1)
    states = [
        ElasticFeedbackState(FeedbackIdentity(f"s{i}", 1, 1, 0))
        for i in range(len(sessions))
    ]
    windows_per_session = args.duration_seconds // args.window_seconds
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]
    pieces: list[list[str]] = [[] for _ in sessions]
    traces: list[list[dict[str, Any]]] = [[] for _ in sessions]
    previous_yields: list[list[float]] = [[] for _ in sessions]
    accepted_recoveries: list[int] = [0 for _ in sessions]
    canonical_lease_remaining: list[int] = [0 for _ in sessions]
    replay_prompts: list[tuple[int, ...]] = [() for _ in sessions]
    replay_frontiers: list[int] = [0 for _ in sessions]
    replay_pieces: list[list[str]] = [[] for _ in sessions]
    replay_lineage_unsafe: list[bool] = [False for _ in sessions]
    display_overrides: dict[tuple[int, int], str] = {}
    display_reconciliations = 0
    dominated_display_overrides = 0
    cutset_singleton_replays = 0
    bounded_delta_reanchors = 0
    asymmetric_context_reanchors = 0
    same_prompt_canonical_repairs = 0
    raw_context_reanchors = 0
    terminal_singleton_reconciliations = 0
    horizon = int(csm["structural_reanchor_horizon_windows"])
    capsule_seconds = 0.0
    proposal_seconds = 0.0
    authority_seconds = 0.0
    structural_capsules = 0
    monitor_capsules = 0
    monitor_triggers = 0
    terminal_authorities = 0
    semantic_violations = 0
    independent_replay_batches = 0
    independent_replay_windows = 0
    independent_replay_sessions: set[int] = set()
    started = time.perf_counter()

    for window_index in range(windows_per_session):
        for begin in range(0, len(sessions), args.concurrency):
            ids = list(range(begin, min(begin + args.concurrency, len(sessions))))
            # The horizon is a freshness/backstop contract, not authority to
            # blindly install a context.  The first R8.4 diagnostic showed
            # that unconditional VACC installation can create new quality
            # outliers.  Capsules acquire authority only after independent
            # sufficiency improvement below.
            structural = False
            prompts: list[tuple[int, ...]] = []
            for sid in ids:
                states[sid], _ = controller.prepare_for_proposal(
                    states[sid], adapter
                )
                prompts.append(tuple(atom.token_id for atom in states[sid].atoms))
            audio = [windows[sid][window_index] for sid in ids]
            proposed_at = time.perf_counter()
            records = executor.generate(audio, prompts)
            proposal_seconds += time.perf_counter() - proposed_at

            batched_replays: dict[
                int,
                tuple[ElasticFeedbackState, WhisperCandidate, float],
            ] = {}
            if args.selector == "canonical-replay":
                replay_ids: list[int] = []
                for position, sid in enumerate(ids):
                    replay_features = candidate_features(
                        audio[position], records[position],
                        previous_yields[sid], states[sid],
                    )
                    replay_score = csm_forest_score(csm, replay_features)
                    replay_mode = (
                        "none"
                        if args.disable_structural_rules
                        else args.structural_rule_mode
                    )
                    replay_trigger, _ = sufficiency_trigger(
                        csm=csm,
                        features=replay_features,
                        csm_score=replay_score,
                        structural_mode=replay_mode,
                        trigger_threshold=float(
                            csm["score_threshold"]
                            if args.csm_trigger_threshold is None
                            else args.csm_trigger_threshold
                        ),
                    )
                    planned_lease = canonical_lease_remaining[sid]
                    if args.continuous_lineage_replay:
                        planned_lease = max(planned_lease, 1)
                        canonical_lease_remaining[sid] = max(
                            canonical_lease_remaining[sid], planned_lease
                        )
                    if replay_trigger:
                        planned_lease = max(
                            planned_lease,
                            (
                                windows_per_session - window_index
                                if args.canonical_lease_windows == 0
                                else args.canonical_lease_windows
                            ),
                        )
                    if (
                        args.lineage_reconciliation
                        and window_index == windows_per_session - 1
                    ):
                        # Terminal reconciliation is a display-commit
                        # backstop, not a claim that the monitor certified
                        # every preceding proposal.  The replay still starts
                        # at the raw-audio origin and therefore cannot inherit
                        # unsafe feedback state.
                        planned_lease = max(planned_lease, 1)
                        canonical_lease_remaining[sid] = max(
                            canonical_lease_remaining[sid], planned_lease
                        )
                    if planned_lease > 0:
                        replay_ids.append(sid)

                pending = set(replay_ids)
                while pending:
                    round_ids = sorted(
                        sid for sid in pending
                        if replay_frontiers[sid] <= window_index
                    )
                    if not round_ids:
                        raise AssertionError("replay frontier advanced past window")
                    round_audio: list[np.ndarray] = []
                    round_prompts: list[tuple[int, ...]] = []
                    round_windows: list[int] = []
                    round_overlaps: list[bool] = []
                    for sid in round_ids:
                        replay_window = replay_frontiers[sid]
                        replay_prompt = replay_prompts[sid]
                        if capacity_rebase_required(
                            len(executor.prompt_tokens(replay_prompt)),
                            declared_next_segment_tokens=executor.max_new_tokens,
                            maximum_prompt_tokens=executor.max_prompt_tokens,
                        ):
                            replay_prompt = ()
                            replay_prompts[sid] = ()
                        replay_prompt = bound_feedback_prompt(
                            replay_prompt,
                            start_of_previous_token=executor.start_of_previous,
                            maximum_content_tokens=args.replay_prompt_tokens,
                        )
                        replay_prompts[sid] = replay_prompt
                        use_overlap = (
                            args.replay_overlap_seconds > 0.0
                            and replay_window > 0
                        )
                        if use_overlap:
                            overlap_samples = min(
                                windows[sid][replay_window - 1].size,
                                int(args.replay_overlap_seconds * 16_000),
                            )
                            round_audio.append(np.concatenate((
                                windows[sid][replay_window - 1][
                                    -overlap_samples:
                                ],
                                windows[sid][replay_window],
                            )))
                            round_prompts.append(())
                        else:
                            round_audio.append(windows[sid][replay_window])
                            round_prompts.append(replay_prompt)
                        round_windows.append(replay_window)
                        round_overlaps.append(use_overlap)
                    replay_at = time.perf_counter()
                    round_records = executor.generate(
                        round_audio,
                        round_prompts,
                        max_steps=args.replay_step_budget,
                    )
                    capsule_seconds += time.perf_counter() - replay_at
                    independent_replay_batches += 1
                    independent_replay_windows += len(round_ids)
                    independent_replay_sessions.update(round_ids)
                    for (
                        sid,
                        replay_window,
                        replay_prompt,
                        replay_record,
                        used_overlap,
                    ) in zip(
                        round_ids,
                        round_windows,
                        round_prompts,
                        round_records,
                        round_overlaps,
                    ):
                        if used_overlap:
                            delta_text = extract_bounded_audio_delta(
                                replay_pieces[sid][-1], replay_record.text
                            )
                            if delta_text:
                                delta_ids = tuple(int(token) for token in
                                    executor.processor.tokenizer.encode(
                                        delta_text, add_special_tokens=False
                                    )
                                )
                                encoded = delta_text.encode("utf-8")
                                replay_record = replace(
                                    replay_record,
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
                                authority_at = time.perf_counter()
                                replay_record = executor.canonical(
                                    windows[sid][replay_window], ()
                                )
                                authority_seconds += (
                                    time.perf_counter() - authority_at
                                )
                                cutset_singleton_replays += 1
                            replay_prompts[sid] = ()
                        else:
                            replay_prompts[sid] = bound_feedback_prompt(
                                executor.advance_prompt(
                                    replay_prompt, replay_record.token_ids
                                ),
                                start_of_previous_token=(
                                    executor.start_of_previous
                                ),
                                maximum_content_tokens=(
                                    args.replay_prompt_tokens
                                ),
                            )
                        replay_pieces[sid].append(replay_record.text)
                        replay_frontiers[sid] = replay_window + 1
                        if replay_window == window_index:
                            replay_state_tokens = (
                                replay_prompt[1:]
                                if replay_prompt
                                and replay_prompt[0]
                                == executor.start_of_previous
                                else replay_prompt
                            )
                            recovered_state = (
                                install_authoritative_feedback_capsule(
                                    states[sid], replay_state_tokens
                                )
                            )
                            recovered_features = candidate_features(
                                windows[sid][window_index], replay_record,
                                previous_yields[sid], recovered_state,
                            )
                            recovered_score = csm_forest_score(
                                csm, recovered_features
                            )
                            # The learned CSM is a high-recall scheduler, not
                            # authority to reject a causally independent replay.
                            # Escalate to expensive singleton reconciliation
                            # only on reference-free hard failure evidence or
                            # strict counterfactual dominance by the original
                            # candidate at the same audio frontier.
                            current_position = (
                                ids.index(sid)
                                if replay_window == window_index and sid in ids
                                else None
                            )
                            original_record = (
                                records[current_position]
                                if current_position is not None
                                else None
                            )
                            original_features = (
                                candidate_features(
                                    windows[sid][window_index],
                                    original_record,
                                    previous_yields[sid],
                                    states[sid],
                                )
                                if original_record is not None
                                else None
                            )
                            original_score = (
                                csm_forest_score(csm, original_features)
                                if original_features is not None
                                else None
                            )
                            dominated_replay = (
                                original_record is not None
                                and original_score is not None
                                and safe_display_override_candidate(
                                    terminated_by_eos=(
                                        original_record.terminated_by_eos
                                    ),
                                    generation_steps=(
                                        original_record.generation_steps
                                    ),
                                    maximum_generation_steps=(
                                        args.max_new_tokens
                                    ),
                                    compression_ratio=(
                                        original_record.compression_ratio
                                    ),
                                    longest_repetition_run=(
                                        longest_consecutive_word_run(
                                            original_record.text
                                        )
                                    ),
                                )
                                and len(original_record.token_ids) >= 8
                                and len(replay_record.token_ids)
                                < 0.5 * len(original_record.token_ids)
                                and recovered_score >= original_score + 0.25
                            )
                            shared_collapse = (
                                original_record is not None
                                and original_score is not None
                                and len(original_record.token_ids) <= 2
                                and len(replay_record.token_ids) <= 2
                                and max(original_score, recovered_score) >= 0.5
                            )
                            asymmetric_conflict = (
                                original_record is not None
                                and asymmetric_context_conflict(
                                    len(original_record.token_ids),
                                    len(replay_record.token_ids),
                                )
                            )
                            if dominated_replay and original_record is not None:
                                # Display arbitration is side-effect free: the
                                # independent replay remains the only feedback
                                # lineage, while the strictly dominating
                                # same-frontier candidate is retained in the
                                # terminal transcript transaction.
                                replay_pieces[sid][-1] = original_record.text
                                display_overrides[(sid, replay_window)] = (
                                    original_record.text
                                )
                                dominated_display_overrides += 1
                            replay_authority_required = (
                                not replay_record.terminated_by_eos
                                or replay_record.generation_steps
                                >= args.replay_step_budget
                                or replay_record.compression_ratio >= 2.4
                                or longest_consecutive_word_run(
                                    replay_record.text
                                ) >= 4
                                or shared_collapse
                                or asymmetric_conflict
                            )
                            if replay_authority_required:
                                if asymmetric_conflict:
                                    asymmetric_context_reanchors += 1
                                authority_at = time.perf_counter()
                                # An asymmetric short/long conflict can be a
                                # batch-shape token/EOS flip even when the
                                # prompt is still the correct context.  First
                                # preserve that context and change only the
                                # arithmetic path.  Dropping the prompt first
                                # can turn a one-token continuation into a
                                # full-window retranscription and duplicate
                                # content in the session transcript.
                                authority_prompt = (
                                    replay_prompt
                                    if asymmetric_conflict
                                    and not shared_collapse
                                    else ()
                                )
                                replay_record = executor.canonical(
                                    windows[sid][replay_window],
                                    authority_prompt,
                                )
                                if authority_prompt:
                                    same_prompt_canonical_repairs += 1
                                else:
                                    raw_context_reanchors += 1
                                # A same-prompt singleton that is itself
                                # structurally invalid has shown that the
                                # context, not just batch arithmetic, is bad.
                                # Only then fail closed to the raw-audio
                                # cutset.
                                if authority_prompt and (
                                    not replay_record.terminated_by_eos
                                    or replay_record.generation_steps
                                    >= args.max_new_tokens
                                    or replay_record.compression_ratio >= 2.4
                                    or longest_consecutive_word_run(
                                        replay_record.text
                                    ) >= 4
                                ):
                                    replay_record = executor.canonical(
                                        windows[sid][replay_window], ()
                                    )
                                    authority_prompt = ()
                                    raw_context_reanchors += 1
                                if (
                                    shared_collapse
                                    and len(replay_record.token_ids) <= 2
                                    and replay_window > 0
                                ):
                                    span_record = executor.canonical(
                                        concatenate(windows[sid][
                                            replay_window - 1:
                                            replay_window + 1
                                        ]),
                                        (),
                                    )
                                    delta_text = extract_bounded_audio_delta(
                                        replay_pieces[sid][-2],
                                        span_record.text,
                                    )
                                    if delta_text:
                                        delta_ids = tuple(int(token) for token in
                                            executor.processor.tokenizer.encode(
                                                delta_text,
                                                add_special_tokens=False,
                                            )
                                        )
                                        encoded = delta_text.encode("utf-8")
                                        replay_record = replace(
                                            span_record,
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
                                authority_seconds += (
                                    time.perf_counter() - authority_at
                                )
                                cutset_singleton_replays += 1
                                replay_prompts[sid] = executor.advance_prompt(
                                    authority_prompt,
                                    replay_record.token_ids,
                                )
                                replay_pieces[sid][-1] = replay_record.text
                                if (sid, replay_window) in display_overrides:
                                    del display_overrides[(sid, replay_window)]
                                    dominated_display_overrides -= 1
                                recovered_features = candidate_features(
                                    windows[sid][window_index], replay_record,
                                    previous_yields[sid], recovered_state,
                                )
                                recovered_score = csm_forest_score(
                                    csm, recovered_features
                                )
                            batched_replays[sid] = (
                                recovered_state,
                                replay_record,
                                recovered_score,
                            )
                            pending.remove(sid)

            for position, sid in enumerate(ids):
                record = records[position]
                before = states[sid]
                features = candidate_features(
                    audio[position], record, previous_yields[sid], before
                )
                csm_score = csm_forest_score(csm, features)
                structural_mode = (
                    "none"
                    if args.disable_structural_rules
                    else args.structural_rule_mode
                )
                csm_trigger, hard_sufficiency_trigger = sufficiency_trigger(
                    csm=csm,
                    features=features,
                    csm_score=csm_score,
                    structural_mode=structural_mode,
                    trigger_threshold=float(
                        csm["score_threshold"]
                        if args.csm_trigger_threshold is None
                        else args.csm_trigger_threshold
                    ),
                )
                terminal = window_index == windows_per_session - 1
                recovery_kind: str | None = (
                    "structural" if structural else None
                )
                recovery_debug: list[dict[str, Any]] = []
                if args.selector == "canonical-replay" and csm_trigger:
                    canonical_lease_remaining[sid] = max(
                        canonical_lease_remaining[sid],
                        (
                            windows_per_session - window_index
                            if args.canonical_lease_windows == 0
                            else args.canonical_lease_windows
                        ),
                    )
                recovery_requested = (
                    csm_trigger
                    or (
                        args.selector == "canonical-replay"
                        and canonical_lease_remaining[sid] > 0
                    )
                )
                if recovery_requested and (
                    window_index > 0 or args.selector == "canonical-replay"
                ):
                    if csm_trigger:
                        monitor_triggers += 1
                    active_seconds = max(
                        0.02,
                        features["speech_active_ratio"] * args.window_seconds,
                    )
                    expected_tokens = (
                        statistics.median(previous_yields[sid][-2:])
                        * active_seconds
                        if previous_yields[sid]
                        else float(len(record.token_ids))
                    )

                    def objective(
                        candidate: WhisperCandidate, score: float
                    ) -> float:
                        if (
                            not candidate.terminated_by_eos
                            or candidate.generation_steps >= args.max_new_tokens
                        ):
                            return float("inf")
                        length_error = abs(np.log(
                            (len(candidate.token_ids) + 1.0)
                            / (expected_tokens + 1.0)
                        ))
                        return float(
                            length_error
                            + 0.15 * score
                            / max(float(csm["score_threshold"]), 1e-9)
                        )

                    alternatives: list[tuple[
                        float,
                        str,
                        ElasticFeedbackState,
                        WhisperCandidate,
                        float,
                    ]] = [(
                        objective(record, csm_score),
                        "original",
                        before,
                        record,
                        csm_score,
                    )]
                    spans = (
                        (int(args.selector.split("-")[1]) // args.window_seconds,)
                        if args.selector.startswith("segmented-")
                        else (() if args.selector == "canonical-replay" else (1, 2))
                    )
                    if args.selector == "canonical-replay":
                        if sid not in batched_replays:
                            raise AssertionError(
                                "requested independent replay was not prepared"
                            )
                        (
                            recovered_state,
                            replay_record,
                            recovered_score,
                        ) = batched_replays[sid]
                        alternatives.append((
                            0.0,
                            "independent-replay",
                            recovered_state,
                            replay_record,
                            recovered_score,
                        ))
                    for span in spans:
                        start = max(0, window_index - span)
                        if args.selector.startswith("segmented-"):
                            capsule_at = time.perf_counter()
                            segment_records = [
                                executor.canonical(segment_audio, ())
                                for segment_audio
                                in windows[sid][start:window_index]
                            ]
                            capsule_tokens = tuple(
                                token
                                for segment_record in segment_records
                                for token in segment_record.token_ids
                            )[-(executor.max_prompt_tokens - 1):]
                            recovered_state = (
                                install_authoritative_feedback_capsule(
                                    before, capsule_tokens
                                )
                            )
                            recovered = executor.canonical(
                                audio[position], capsule_tokens
                            )
                            elapsed = time.perf_counter() - capsule_at
                        else:
                            prior = concatenate(
                                windows[sid][start:window_index]
                            )
                            recovered_state, _, recovered, elapsed = (
                                install_recent_capsule(
                                    executor, before, prior, audio[position]
                                )
                            )
                        capsule_seconds += elapsed
                        recovered_features = candidate_features(
                            audio[position], recovered,
                            previous_yields[sid], recovered_state,
                        )
                        recovered_score = csm_forest_score(
                            csm, recovered_features
                        )
                        candidate_objective = objective(
                            recovered, recovered_score
                        )
                        alternatives.append((
                            candidate_objective,
                            (
                                args.selector
                                if args.selector.startswith("segmented-")
                                else f"vacc-{span * args.window_seconds}"
                            ),
                            recovered_state,
                            recovered,
                            recovered_score,
                        ))
                    recovery_debug = [
                        {
                            "view": view,
                            "objective": value,
                            "score": score,
                            "token_count": len(candidate.token_ids),
                            "generation_steps": candidate.generation_steps,
                            "terminated_by_eos": candidate.terminated_by_eos,
                            "average_token_log_probability": (
                                candidate.average_token_log_probability
                            ),
                            "compression_ratio": candidate.compression_ratio,
                            "text": candidate.text,
                            "token_ids": list(candidate.token_ids),
                            "expected_token_count": expected_tokens,
                        }
                        for value, view, _, candidate, score in alternatives
                    ]
                    acoustic_scores: list[dict[str, float]] = []
                    if args.selector == "canonical-replay":
                        selected = alternatives[1]
                        # This is an independent raw-audio replay proposal.
                        # Ordinary batching does not make it bitwise equal to
                        # singleton execution; its authority here is causal
                        # lineage independence plus the explicit display
                        # transaction below, not a numerical certificate.
                        accept = True
                    elif args.selector == "acoustic-score":
                        acoustic_scores = executor.acoustic_candidate_scores(
                            audio[position],
                            [item[3].token_ids for item in alternatives],
                        )
                        for debug, acoustic_score in zip(
                            recovery_debug, acoustic_scores
                        ):
                            debug["acoustic_score"] = acoustic_score
                    selected = min(alternatives, key=lambda item: item[0])
                    accept = (
                        selected[1] != "original"
                        and selected[0] + 0.05 < alternatives[0][0]
                    )
                    if args.selector == "acoustic-score":
                        selected_index = max(
                            range(len(alternatives)),
                            key=lambda index: acoustic_scores[index][
                                "mean_log_probability"
                            ],
                        )
                        selected = alternatives[selected_index]
                        accept = (
                            selected[1] != "original"
                            and selected[3].terminated_by_eos
                            and selected[3].generation_steps < args.max_new_tokens
                        )
                    elif args.selector.startswith("segmented-"):
                        selected = alternatives[1]
                        accept = (
                            selected[3].terminated_by_eos
                            and selected[3].generation_steps < args.max_new_tokens
                        )
                    elif args.selector == "min-score":
                        selected = min(
                            alternatives,
                            key=lambda item: (
                                not item[3].terminated_by_eos
                                or item[3].generation_steps >= args.max_new_tokens,
                                item[4],
                            ),
                        )
                        accept = (
                            selected[1] != "original"
                            and selected[3].terminated_by_eos
                            and selected[3].generation_steps < args.max_new_tokens
                            and selected[4] <= args.recovery_score_threshold
                            and selected[4] < alternatives[0][4]
                        )
                    elif args.selector == "agreement-score":
                        recovered_alternatives = alternatives[1:]
                        consensus = agreement(
                            recovered_alternatives[0][3].text,
                            recovered_alternatives[1][3].text,
                        )
                        eligible = [
                            item for item in recovered_alternatives
                            if item[3].terminated_by_eos
                            and item[3].generation_steps < args.max_new_tokens
                        ]
                        if eligible:
                            selected = min(eligible, key=lambda item: item[4])
                            recovered_differs = (
                                normalized_words(selected[3].text)
                                != normalized_words(alternatives[0][3].text)
                            )
                            accept = recovered_differs and (
                                consensus >= args.agreement_threshold
                                or (
                                    selected[4]
                                    <= args.recovery_score_threshold
                                    and selected[4] < alternatives[0][4]
                                )
                            )
                        else:
                            selected = alternatives[0]
                            accept = False
                    (
                        selected_objective,
                        selected_view,
                        recovered_state,
                        recovered,
                        recovered_score,
                    ) = selected
                    if accept:
                        states[sid] = recovered_state
                        record = recovered
                        if (
                            args.lineage_reconciliation
                            and selected_view == "independent-replay"
                        ):
                            if len(replay_pieces[sid]) != window_index + 1:
                                raise AssertionError(
                                    "replay display lineage did not catch up"
                                )
                            # The current piece is appended below.  Everything
                            # before it remains provisional until this atomic
                            # lineage install, so replace rather than append to
                            # a mixed unsafe/safe transcript.
                            pieces[sid] = list(replay_pieces[sid][:-1])
                            display_reconciliations += 1
                        monitor_capsules += 1
                        accepted_recoveries[sid] += 1
                        recovery_kind = f"monitor-{selected_view}"
                        authority_seconds += 0.0
                        if args.selector == "canonical-replay":
                            canonical_lease_remaining[sid] = max(
                                0,
                                canonical_lease_remaining[sid] - 1,
                            )
                    else:
                        recovery_kind = "monitor-rejected"
                # Terminal output has no successor feedback state under the
                # frozen state-only contract.  A session whose state was
                # reanchored nevertheless receives one canonical terminal
                # closure, preventing a capsule-induced suffix from escaping
                # the recovery transaction.  Unaffected sessions keep the
                # original authority-free terminal path.
                if (
                    terminal
                    and accepted_recoveries[sid] > 0
                    and not (
                        recovery_kind is not None
                        and recovery_kind.startswith("monitor-")
                        and recovery_kind != "monitor-rejected"
                    )
                ):
                    authority_at = time.perf_counter()
                    record = executor.canonical(
                        audio[position],
                        tuple(atom.token_id for atom in states[sid].atoms),
                    )
                    authority_seconds += time.perf_counter() - authority_at
                    terminal_authorities += 1

                current = states[sid]
                candidate = FeedbackCandidate(
                    session_id=current.identity.session_id,
                    contract_epoch=current.identity.contract_epoch,
                    policy_version=current.identity.policy_version,
                    parent_state_version=current.identity.state_version,
                    token_ids=tuple(record.token_ids),
                    minimum_margin=record.minimum_margin,
                    terminal=terminal,
                )
                next_state, decision = controller.step(current, candidate, adapter)
                states[sid] = next_state
                if (
                    not decision.candidate_became_ancestor
                    and next_state.identity.state_version in next_state.ancestors
                ):
                    semantic_violations += 1
                active_seconds = max(
                    0.02,
                    features["speech_active_ratio"] * args.window_seconds,
                )
                previous_yields[sid].append(
                    len(record.token_ids) / active_seconds
                )
                display_text = display_overrides.get(
                    (sid, window_index), record.text
                )
                pieces[sid].append(display_text)
                traces[sid].append({
                    "window_index": window_index,
                    "recovery_kind": recovery_kind,
                    "csm_score": csm_score,
                    "csm_trigger": csm_trigger,
                    "hard_sufficiency_trigger": hard_sufficiency_trigger,
                    "recovery_alternatives": recovery_debug,
                    "features": features,
                    "selected_token_ids": list(record.token_ids),
                    "selected_text": record.text,
                    "display_text": display_text,
                    "decision_action": decision.action.value,
                    "feedback_lineage_version": next_state.identity.state_version,
                    "audio_frontier_version": window_index + 1,
                    "provisional_ancestor_count": len(next_state.ancestors),
                })

    # A monitor-positive replay cannot safely serve as its own recovery
    # authority.  Reconcile only those lineages through the frozen singleton
    # reference.  This is a selective terminal safety net; all other sessions
    # retain the cheaper causally independent batched replay.
    if args.lineage_reconciliation:
        for sid, unsafe in enumerate(replay_lineage_unsafe):
            if not unsafe:
                continue
            authority_at = time.perf_counter()
            prompt: tuple[int, ...] = ()
            authoritative_pieces: list[str] = []
            for segment_audio in windows[sid]:
                if capacity_rebase_required(
                    len(executor.prompt_tokens(prompt)),
                    declared_next_segment_tokens=executor.max_new_tokens,
                    maximum_prompt_tokens=executor.max_prompt_tokens,
                ):
                    prompt = ()
                authoritative = executor.canonical(segment_audio, prompt)
                authoritative_pieces.append(authoritative.text)
                prompt = executor.advance_prompt(prompt, authoritative.token_ids)
            authority_seconds += time.perf_counter() - authority_at
            pieces[sid] = authoritative_pieces
            terminal_singleton_reconciliations += 1

    elapsed_total = time.perf_counter() - started
    rows: list[dict[str, Any]] = []
    deltas: list[float] = []
    for sid, (session, base) in enumerate(zip(sessions, source["sessions"])):
        text = " ".join(pieces[sid])
        errors, words = word_error(session.reference, text)
        wer = 100.0 * errors / max(1, words)
        canonical = float(base["canonical_wer"])
        delta = wer - canonical
        outlier = delta > 10.0 or (
            wer > 2.0 * max(canonical, 1.0) and delta > 5.0
        )
        deltas.append(delta)
        rows.append({
            "session_id": sid,
            "split": session.split,
            "utterance_ids": list(session.utterance_ids),
            "canonical_wer": canonical,
            "wer": wer,
            "delta_pp": delta,
            "catastrophic_outlier": outlier,
            "text": text,
            "repetition_run": longest_equal_run(pieces[sid]),
            "trace": traces[sid],
        })
    split_metrics: dict[str, Any] = {}
    for split_offset, split in enumerate(("test-clean", "test-other")):
        values = [row["delta_pp"] for row in rows if row["split"] == split]
        split_metrics[split] = {
            "mean_delta_pp": statistics.fmean(values),
            "bootstrap_95_upper_pp": bootstrap_upper(
                values,
                seed=args.bootstrap_seed + split_offset,
                replicates=args.bootstrap_replicates,
            ),
        }
    mean_delta = statistics.fmean(deltas)
    upper = bootstrap_upper(
        deltas, seed=args.bootstrap_seed,
        replicates=args.bootstrap_replicates,
    )
    catastrophic = sum(row["catastrophic_outlier"] for row in rows)
    estimated_energy_reduction = 1.0 - (
        proposal_seconds + capsule_seconds + authority_seconds
    ) / float(source["metrics"]["canonical_seconds"])
    passed = (
        catastrophic == 0
        and mean_delta <= 1.0
        and upper <= 2.0
        and all(
            metric["mean_delta_pp"] <= 1.0
            and metric["bootstrap_95_upper_pp"] <= 2.0
            for metric in split_metrics.values()
        )
        and max(row["repetition_run"] for row in rows) < 3
        and semantic_violations == 0
        and estimated_energy_reduction >= 0.40
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8 CSM plus bounded safe context reanchoring",
        "decision": "PASS_R8_4_FROZEN_QUALITY" if passed else "FAIL_R8_4_FROZEN_QUALITY",
        "config": {
            "seed": args.seed,
            "horizon": horizon,
            "selector": args.selector,
            "structural_rule_mode": (
                "none"
                if args.disable_structural_rules
                else args.structural_rule_mode
            ),
            "agreement_threshold": args.agreement_threshold,
            "recovery_score_threshold": args.recovery_score_threshold,
            "canonical_lease_windows": args.canonical_lease_windows,
            "lineage_reconciliation": args.lineage_reconciliation,
            "continuous_lineage_replay": args.continuous_lineage_replay,
            "csm_trigger_threshold": (
                csm["score_threshold"]
                if args.csm_trigger_threshold is None
                else args.csm_trigger_threshold
            ),
            "csm_policy_sha256": hashlib.sha256(args.csm_policy.read_bytes()).hexdigest(),
            "source_quality_sha256": hashlib.sha256(args.source_quality.read_bytes()).hexdigest(),
        },
        "metrics": {
            "sessions": len(rows),
            "catastrophic_outliers": catastrophic,
            "mean_delta_pp": mean_delta,
            "bootstrap_95_upper_pp": upper,
            "split_metrics": split_metrics,
            "maximum_repetition_run": max(row["repetition_run"] for row in rows),
            "semantic_violations": semantic_violations,
            "structural_capsules": structural_capsules,
            "monitor_triggers": monitor_triggers,
            "monitor_capsules": monitor_capsules,
            "terminal_authorities": terminal_authorities,
            "independent_replay_batches": independent_replay_batches,
            "independent_replay_windows": independent_replay_windows,
            "independent_replay_sessions": len(independent_replay_sessions),
            "display_reconciliations": display_reconciliations,
            "dominated_display_overrides": dominated_display_overrides,
            "cutset_singleton_replays": cutset_singleton_replays,
            "bounded_delta_reanchors": bounded_delta_reanchors,
            "asymmetric_context_reanchors": asymmetric_context_reanchors,
            "same_prompt_canonical_repairs": (
                same_prompt_canonical_repairs
            ),
            "raw_context_reanchors": raw_context_reanchors,
            "terminal_singleton_reconciliations": (
                terminal_singleton_reconciliations
            ),
            "proposal_seconds": proposal_seconds,
            "capsule_seconds": capsule_seconds,
            "authority_seconds": authority_seconds,
            "wall_seconds": elapsed_total,
            "estimated_energy_reduction": estimated_energy_reduction,
        },
        "sessions": rows,
        "claim_boundary": (
            "reference-free frozen scheduling policy; independent replay starts "
            "from raw-audio lineage rather than unsafe feedback state; ordinary "
            "batched replay is not a bitwise singleton certificate; energy is "
            "conservatively estimated from measured GPU work time; when enabled, "
            "display reconciliation atomically replaces provisional history and "
            "does not retroactively certify the scheduling monitor"
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
