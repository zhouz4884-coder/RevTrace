#!/usr/bin/env python3
"""W6 paired long-session quality and provisional-UX evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import soundfile as sf
import torch
import transformers

from revtrace.feedback_metrics import edit_distance
from revtrace.whisper_state import (
    LocalAgreement2,
    WhisperStateAction,
    WhisperStateRiskPolicy,
    capacity_rebase_required,
    prompt_state_action,
    work_budget_requires_authority,
)

WORK_AUTHORITY_PROTOCOL = "decoder-step-saturation-extended-canonical-v1"
TARGET_CAPACITY_PROTOCOL = "target-canonical-declared-work-v1"
from whisper_batched_executor import DistinctPromptWhisper, SAMPLE_RATE


WORDS = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


@dataclass
class QualitySession:
    split: str
    audio: np.ndarray
    reference: str
    utterance_ids: tuple[str, ...]
    speaker_ids: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, required=True)
    parser.add_argument("--late-window-index", type=int)
    parser.add_argument("--late-margin-threshold", type=float)
    parser.add_argument("--high-load-prompt-tokens", type=int)
    parser.add_argument("--high-load-margin-threshold", type=float)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--bootstrap-seed", type=int, default=20260812)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--authority-max-new-tokens", type=int)
    parser.add_argument("--reference-max-new-tokens", type=int, default=96)
    parser.add_argument(
        "--deferred-risk-authority",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--deferred-terminal-authority",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--diagnostic-post-timing-state",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "after the measured trajectory, replay every admitted "
            "nonterminal fast state against repeated singleton authority"
        ),
    )
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def normalize(text: str) -> list[str]:
    return WORDS.findall(text.lower())


def word_error(reference: str, hypothesis: str) -> tuple[int, int]:
    ref = normalize(reference)
    hyp = normalize(hypothesis)
    return edit_distance(ref, hyp), len(ref)


def load_audio(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"expected 16 kHz: {path}")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.asarray(audio, dtype=np.float32)


def build_sessions(
    records: Sequence[dict[str, Any]],
    *,
    split: str,
    count: int,
    duration_seconds: int,
    seed: int,
) -> list[QualitySession]:
    rows = [row for row in records if row["split"] == split]
    random.Random(seed).shuffle(rows)
    target = duration_seconds * SAMPLE_RATE
    separator = np.zeros(SAMPLE_RATE // 10, dtype=np.float32)
    sessions: list[QualitySession] = []
    cursor = 0
    while cursor < len(rows) and len(sessions) < count:
        chunks: list[np.ndarray] = []
        texts: list[str] = []
        utterances: list[str] = []
        speakers: list[str] = []
        samples = 0
        while cursor < len(rows) and samples < target:
            row = rows[cursor]
            audio = load_audio(row["path"])
            increment = audio.size + (
                separator.size if chunks else 0
            )
            if chunks and samples + increment > target:
                break
            cursor += 1
            if chunks:
                chunks.append(separator)
                samples += separator.size
            chunks.append(audio)
            samples += audio.size
            texts.append(str(row["text"]))
            utterances.append(str(row["utterance_id"]))
            speakers.append(str(row["speaker_id"]))
        if samples < target:
            if samples < int(0.75 * target):
                break
            chunks.append(np.zeros(target - samples, dtype=np.float32))
        value = np.concatenate(chunks)
        sessions.append(QualitySession(
            split=split,
            audio=value,
            reference=" ".join(texts),
            utterance_ids=tuple(utterances),
            speaker_ids=tuple(sorted(set(speakers))),
        ))
    if len(sessions) < count:
        raise RuntimeError(
            f"only {len(sessions)} {split} long sessions; requested {count}"
        )
    return sessions


def canonical_system(
    executor: DistinctPromptWhisper,
    sessions: Sequence[QualitySession],
    windows_per_session: int,
) -> tuple[list[str], float, int, list[list[dict[str, Any]]]]:
    outputs: list[str] = []
    traces: list[list[dict[str, Any]]] = []
    capacity_rebases = 0
    started = time.perf_counter()
    for session in sessions:
        prompt: tuple[int, ...] = ()
        pieces: list[str] = []
        session_trace: list[dict[str, Any]] = []
        for window in np.array_split(
            session.audio, windows_per_session
        ):
            if capacity_rebase_required(
                len(executor.prompt_tokens(prompt)),
                declared_next_segment_tokens=executor.max_new_tokens,
                maximum_prompt_tokens=executor.max_prompt_tokens,
            ):
                prompt = ()
                capacity_rebases += 1
            record = executor.canonical(window, prompt)
            pieces.append(record.text)
            session_trace.append({
                "window_index": len(session_trace),
                "prompt_token_sha256": hashlib.sha256(
                    json.dumps(
                        list(executor.prompt_tokens(prompt)),
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                "token_sha256": record.token_sha256,
                "token_ids": list(record.token_ids),
                "generation_steps": record.generation_steps,
                "terminated_by_eos": record.terminated_by_eos,
                "text": record.text,
            })
            prompt = executor.advance_prompt(prompt, record.token_ids)
        outputs.append(" ".join(pieces))
        traces.append(session_trace)
    return (
        outputs,
        time.perf_counter() - started,
        capacity_rebases,
        traces,
    )


def batched_systems(
    executor: DistinctPromptWhisper,
    authority_executor: DistinctPromptWhisper,
    sessions: Sequence[QualitySession],
    windows_per_session: int,
    concurrency: int,
    risk_policy: WhisperStateRiskPolicy,
    *,
    deferred_risk_authority: bool,
    deferred_terminal_authority: bool,
) -> tuple[
    list[str],
    list[str],
    dict[str, Any],
    list[dict[str, Any]],
]:
    rev_prompts: list[tuple[int, ...]] = [() for _ in sessions]
    la_prompts: list[tuple[int, ...]] = [() for _ in sessions]
    rev_pieces: list[list[str]] = [[] for _ in sessions]
    la_pieces: list[list[str]] = [[] for _ in sessions]
    rev_events: list[dict[str, Any]] = []
    post_timing_candidates: list[dict[str, Any]] = []
    rev_started = time.perf_counter()
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]
    low_margin_holdbacks = 0
    deferred_risk_authorities = 0
    deferred_terminal_authorities = 0
    work_budget_authorities = 0
    capacity_rebases = 0
    local_agreement_capacity_rebases = 0
    terminal = 0
    for window_index in range(windows_per_session):
        for begin in range(0, len(sessions), concurrency):
            ids = list(range(begin, min(
                begin + concurrency, len(sessions)
            )))
            for session_id in ids:
                if capacity_rebase_required(
                    len(executor.prompt_tokens(
                        rev_prompts[session_id]
                    )),
                    # State capacity belongs to the target canonical
                    # contract, not to the speculative proposer work cap.
                    # Using max-80 here while max-96 authority/reference is
                    # active shifts the rebase frontier even when all prior
                    # output tokens are identical, creating an artificial
                    # feedback-state divergence.
                    declared_next_segment_tokens=(
                        authority_executor.max_new_tokens
                    ),
                    maximum_prompt_tokens=executor.max_prompt_tokens,
                ):
                    rev_prompts[session_id] = ()
                    capacity_rebases += 1
            audio = [windows[index][window_index] for index in ids]
            prompts = [rev_prompts[index] for index in ids]
            proposed_at = time.perf_counter()
            proposed = executor.generate(audio, prompts)
            display_latency = time.perf_counter() - proposed_at
            for position, session_id in enumerate(ids):
                is_terminal = window_index == windows_per_session - 1
                record = proposed[position]
                prior_prompt_tokens = len(
                    executor.prompt_tokens(prompts[position])
                )
                risk_reason = risk_policy.reason(
                    record.minimum_margin,
                    window_index=window_index,
                    prompt_tokens=prior_prompt_tokens,
                )
                action = prompt_state_action(
                    risk_policy,
                    record.minimum_margin,
                    window_index=window_index,
                    prompt_tokens=prior_prompt_tokens,
                    terminal=is_terminal,
                    checkpoint_due=False,
                )
                risky = action == WhisperStateAction.RISK_AUTHORITY
                work_budget_saturated = work_budget_requires_authority(
                    record.generation_steps,
                    proposer_max_new_tokens=executor.max_new_tokens,
                    authority_max_new_tokens=(
                        authority_executor.max_new_tokens
                    ),
                )
                selected = record
                authority = None
                authority_finished = None
                if risky and not is_terminal:
                    low_margin_holdbacks += 1
                needs_authority = (
                    deferred_risk_authority
                    and risky
                    and not is_terminal
                ) or (
                    deferred_terminal_authority
                    and is_terminal
                ) or (
                    work_budget_saturated
                )
                if needs_authority:
                    # The batched result is an immediately displayable
                    # provisional hypothesis.  The canonical result owns
                    # future prompt state for risky nonterminal revisions and
                    # owns the stable final transcript for terminal revisions.
                    authority = authority_executor.canonical(
                        audio[position], prompts[position]
                    )
                    authority_finished = time.perf_counter()
                    selected = authority
                    if risky and not is_terminal:
                        rev_prompts[session_id] = (
                            executor.advance_prompt(
                                rev_prompts[session_id],
                                authority.token_ids,
                            )
                        )
                        deferred_risk_authorities += 1
                    if is_terminal:
                        deferred_terminal_authorities += 1
                    if work_budget_saturated:
                        work_budget_authorities += 1
                elif not is_terminal:
                    # Retain the exact state-writing input for a diagnostic
                    # replay only after the measured trajectory completes.
                    # The oracle cannot repair or perturb the live run.
                    post_timing_candidates.append({
                        "session_id": session_id,
                        "window_index": window_index,
                        "audio": audio[position],
                        "prompt": tuple(prompts[position]),
                        "proposed_token_ids": tuple(record.token_ids),
                        "proposed_text": record.text,
                        "minimum_margin": record.minimum_margin,
                        "prior_prompt_tokens": prior_prompt_tokens,
                    })
                terminal += int(is_terminal)
                state_latency = time.perf_counter() - proposed_at
                rev_pieces[session_id].append(selected.text)
                if not is_terminal and not risky:
                    rev_prompts[session_id] = executor.advance_prompt(
                        rev_prompts[session_id], selected.token_ids
                    )
                rev_events.append({
                    "session_id": session_id,
                    "window_index": window_index,
                    "terminal": is_terminal,
                    "risky": risky,
                    "work_budget_saturated": work_budget_saturated,
                    "generation_steps": record.generation_steps,
                    "generated_token_count": len(record.token_ids),
                    "terminated_by_eos": record.terminated_by_eos,
                    "selected_source": (
                        "extended-canonical-authority"
                        if authority is not None else "batched-proposal"
                    ),
                    "selected_generation_steps": selected.generation_steps,
                    "proposed_token_sha256": record.token_sha256,
                    "selected_token_sha256": selected.token_sha256,
                    "proposed_text": record.text,
                    "selected_text": selected.text,
                    "risk_reason": risk_reason,
                    "minimum_margin": record.minimum_margin,
                    "display_latency_seconds": display_latency,
                    "stable_latency_seconds": state_latency,
                    "state_entry_committed": (
                        not is_terminal
                        and (
                            not risky
                            or authority is not None
                        )
                    ),
                    "provisional_lifetime_seconds": (
                        authority_finished - proposed_at
                        if authority_finished is not None
                        else 0.0
                    ),
                    "provisional_overwrite_percent": (
                        100.0
                        * edit_distance(
                            record.token_ids, selected.token_ids
                        )
                        / max(1, len(record.token_ids))
                        if authority is not None
                        else 0.0
                    ),
                })
    rev_seconds = time.perf_counter() - rev_started

    la_started = time.perf_counter()
    for window_index in range(windows_per_session):
        for begin in range(0, len(sessions), concurrency):
            ids = list(range(begin, min(
                begin + concurrency, len(sessions)
            )))
            for session_id in ids:
                if capacity_rebase_required(
                    len(executor.prompt_tokens(
                        la_prompts[session_id]
                    )),
                    declared_next_segment_tokens=executor.max_new_tokens,
                    maximum_prompt_tokens=executor.max_prompt_tokens,
                ):
                    la_prompts[session_id] = ()
                    local_agreement_capacity_rebases += 1
            audio = [windows[index][window_index] for index in ids]
            prompts = [la_prompts[index] for index in ids]
            partial = executor.generate(
                [value[: int(0.8 * len(value))] for value in audio],
                prompts,
            )
            full = executor.generate(audio, prompts)
            for position, session_id in enumerate(ids):
                policy = LocalAgreement2()
                policy.update(partial[position].token_ids)
                agreed = policy.update(full[position].token_ids)
                if window_index == windows_per_session - 1:
                    agreed = policy.flush(full[position].token_ids)
                text = executor.processor.decode(
                    agreed, skip_special_tokens=True
                ).strip()
                la_pieces[session_id].append(text)
                # LocalAgreement controls display confirmation.  Its native
                # previous-text feedback remains the full current hypothesis.
                la_prompts[session_id] = executor.advance_prompt(
                    la_prompts[session_id], full[position].token_ids
                )
    la_seconds = time.perf_counter() - la_started
    return (
        [" ".join(value) for value in rev_pieces],
        [" ".join(value) for value in la_pieces],
        {
            "revtrace_seconds": rev_seconds,
            "local_agreement_seconds": la_seconds,
            "low_margin_holdbacks": low_margin_holdbacks,
            "deferred_risk_authorities": deferred_risk_authorities,
            "deferred_terminal_authorities": (
                deferred_terminal_authorities
            ),
            "work_budget_authorities": work_budget_authorities,
            "capacity_rebases": capacity_rebases,
            "local_agreement_capacity_rebases": (
                local_agreement_capacity_rebases
            ),
            "terminal_revisions": terminal,
            "events": rev_events,
        },
        post_timing_candidates,
    )


def post_timing_state_diagnostic(
    executor: DistinctPromptWhisper,
    candidates: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Replay admitted state writes with a repeat-stable same-input oracle."""

    stable_roots: list[dict[str, Any]] = []
    ambiguous = 0
    output_mismatches = 0
    state_mismatches = 0
    started = time.perf_counter()
    for row in candidates:
        prompt = tuple(row["prompt"])
        proposed_ids = tuple(row["proposed_token_ids"])
        canonical = executor.canonical(row["audio"], prompt)
        proposed_state = executor.advance_prompt(prompt, proposed_ids)
        canonical_state = executor.advance_prompt(
            prompt, canonical.token_ids
        )
        output_mismatch = proposed_ids != canonical.token_ids
        state_mismatch = proposed_state != canonical_state
        output_mismatches += int(output_mismatch)
        state_mismatches += int(state_mismatch)
        if not output_mismatch and not state_mismatch:
            continue
        repeated = executor.canonical(row["audio"], prompt)
        repeat_stable = (
            repeated.token_ids == canonical.token_ids
            and executor.advance_prompt(prompt, repeated.token_ids)
            == canonical_state
        )
        if not repeat_stable:
            ambiguous += 1
            continue
        if state_mismatch:
            stable_roots.append({
                "session_id": row["session_id"],
                "window_index": row["window_index"],
                "minimum_margin": row["minimum_margin"],
                "prior_prompt_tokens": row["prior_prompt_tokens"],
                "proposed_token_ids": list(proposed_ids),
                "canonical_token_ids": list(canonical.token_ids),
                "proposed_text": row["proposed_text"],
                "canonical_text": canonical.text,
                "proposed_next_prompt": list(proposed_state),
                "canonical_next_prompt": list(canonical_state),
                "canonical_repeat_stable": True,
            })
    return {
        "eligible_fast_state_writes": len(candidates),
        "raw_output_mismatches": output_mismatches,
        "raw_state_mismatches": state_mismatches,
        "repeat_ambiguous_mismatches": ambiguous,
        "stable_state_mismatches": len(stable_roots),
        "stable_state_roots": stable_roots,
        "seconds": time.perf_counter() - started,
        "interference": "post-timing-no-live-state-mutation",
    }


def bootstrap_upper(
    values: Sequence[float],
    *,
    seed: int,
    replicates: int,
) -> float:
    rng = np.random.default_rng(seed)
    source = np.asarray(values, dtype=np.float64)
    means = np.empty(replicates, dtype=np.float64)
    for index in range(replicates):
        sample = rng.choice(source, size=source.size, replace=True)
        means[index] = sample.mean()
    return float(np.quantile(means, 0.95))


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window size")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sessions = (
        build_sessions(
            manifest["records"],
            split="test-clean",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds,
            seed=args.seed,
        )
        + build_sessions(
            manifest["records"],
            split="test-other",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds,
            seed=args.seed + 1,
        )
    )
    utterance_ids = [
        value for session in sessions for value in session.utterance_ids
    ]
    speaker_sessions: dict[tuple[str, str], int] = {}
    for session in sessions:
        for speaker in session.speaker_ids:
            key = (session.split, speaker)
            speaker_sessions[key] = speaker_sessions.get(key, 0) + 1
    executor = DistinctPromptWhisper(
        args.model,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
    )
    reference_executor = executor
    if args.reference_max_new_tokens != args.max_new_tokens:
        reference_executor = DistinctPromptWhisper(
            args.model,
            device=args.device,
            max_new_tokens=args.reference_max_new_tokens,
        )
    authority_max_new_tokens = (
        args.authority_max_new_tokens
        if args.authority_max_new_tokens is not None
        else args.max_new_tokens
    )
    if authority_max_new_tokens == args.max_new_tokens:
        authority_executor = executor
    elif authority_max_new_tokens == args.reference_max_new_tokens:
        authority_executor = reference_executor
    else:
        authority_executor = DistinctPromptWhisper(
            args.model,
            device=args.device,
            max_new_tokens=authority_max_new_tokens,
        )
    windows_per_session = (
        args.duration_seconds // args.window_seconds
    )
    (
        canonical,
        canonical_seconds,
        canonical_capacity_rebases,
        canonical_traces,
    ) = canonical_system(
        reference_executor, sessions, windows_per_session
    )
    (
        revtrace,
        local_agreement,
        runtime,
        post_timing_candidates,
    ) = batched_systems(
        executor,
        authority_executor,
        sessions,
        windows_per_session,
        args.concurrency,
        WhisperStateRiskPolicy(
            margin_threshold=args.margin_threshold,
            late_window_index=args.late_window_index,
            late_margin_threshold=args.late_margin_threshold,
            high_load_prompt_tokens=args.high_load_prompt_tokens,
            high_load_margin_threshold=args.high_load_margin_threshold,
        ),
        deferred_risk_authority=args.deferred_risk_authority,
        deferred_terminal_authority=(
            args.deferred_terminal_authority
        ),
    )
    diagnostic = None
    if args.diagnostic_post_timing_state:
        diagnostic = post_timing_state_diagnostic(
            executor, post_timing_candidates
        )
    rows: list[dict[str, Any]] = []
    deltas: list[float] = []
    catastrophic = 0
    for index, session in enumerate(sessions):
        errors_c, words = word_error(
            session.reference, canonical[index]
        )
        errors_r, _ = word_error(
            session.reference, revtrace[index]
        )
        errors_l, _ = word_error(
            session.reference, local_agreement[index]
        )
        wer_c = 100.0 * errors_c / max(1, words)
        wer_r = 100.0 * errors_r / max(1, words)
        wer_l = 100.0 * errors_l / max(1, words)
        delta = wer_r - wer_c
        is_catastrophic = (
            delta > 10.0
            or (wer_r > 2.0 * max(wer_c, 1.0) and delta > 5.0)
        )
        catastrophic += int(is_catastrophic)
        deltas.append(delta)
        rows.append({
            "session_id": index,
            "split": session.split,
            "speaker_ids": list(session.speaker_ids),
            "utterance_ids": list(session.utterance_ids),
            "reference_words": words,
            "canonical_wer": wer_c,
            "revtrace_wer": wer_r,
            "local_agreement_wer": wer_l,
            "revtrace_delta_pp": delta,
            "catastrophic_outlier": is_catastrophic,
            "canonical_text": canonical[index],
            "revtrace_text": revtrace[index],
            "local_agreement_text": local_agreement[index],
        })
    events = runtime.pop("events")
    lifetimes = [
        float(row["provisional_lifetime_seconds"]) for row in events
    ]
    overwrite = [
        float(row["provisional_overwrite_percent"]) for row in events
    ]
    mean_delta = statistics.fmean(deltas)
    upper = bootstrap_upper(
        deltas,
        seed=args.bootstrap_seed,
        replicates=args.bootstrap_replicates,
    )
    split_metrics: dict[str, dict[str, Any]] = {}
    for split in ("test-clean", "test-other"):
        split_deltas = [
            float(row["revtrace_delta_pp"])
            for row in rows
            if row["split"] == split
        ]
        split_metrics[split] = {
            "sessions": len(split_deltas),
            "mean_wer_delta_pp": statistics.fmean(split_deltas),
            "paired_bootstrap_95_upper_pp": bootstrap_upper(
                split_deltas,
                seed=args.bootstrap_seed
                + (0 if split == "test-clean" else 1),
                replicates=args.bootstrap_replicates,
            ),
        }
    passed = (
        len(sessions) >= 128
        and len(utterance_ids) == len(set(utterance_ids))
        and catastrophic == 0
        and mean_delta <= 1.0
        and upper <= 2.0
        and all(
            item["mean_wer_delta_pp"] <= 1.0
            and item["paired_bootstrap_95_upper_pp"] <= 2.0
            for item in split_metrics.values()
        )
        and float(np.quantile(lifetimes, 0.95)) <= 4.0
        and max(lifetimes, default=0.0) <= args.window_seconds
        and float(np.quantile(overwrite, 0.95)) <= 20.0
    )
    payload = {
        "schema_version": 1,
        "study": "W6 paired long-session quality and UX",
        "model": args.model_name,
        "decision": (
            "W6_QUALITY_UX_PASS"
            if passed else "W6_QUALITY_UX_FAIL"
        ),
        "config": {
            "sessions_per_split": args.sessions_per_split,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "margin_threshold": args.margin_threshold,
            "late_window_index": args.late_window_index,
            "late_margin_threshold": args.late_margin_threshold,
            "high_load_prompt_tokens": args.high_load_prompt_tokens,
            "high_load_margin_threshold": (
                args.high_load_margin_threshold
            ),
            "seed": args.seed,
            "bootstrap_seed": args.bootstrap_seed,
            "bootstrap_replicates": args.bootstrap_replicates,
            "model_path": str(args.model.resolve()),
            "precision": "float16",
            "prompt_state_semantics": (
                "raw-segment-token-history-v5-deferred-authority"
            ),
            "state_control_protocol": (
                "prompt-state-deferred-authority-checkpoint10-"
                "capacity-rebase-v2"
            ),
            "work_authority_protocol": WORK_AUTHORITY_PROTOCOL,
            "target_capacity_protocol": TARGET_CAPACITY_PROTOCOL,
            "local_agreement_capacity_protocol": (
                "declared-work-capacity-rebase-v2"
            ),
            "max_new_tokens": executor.max_new_tokens,
            "reference_max_new_tokens": (
                reference_executor.max_new_tokens
            ),
            "authority_max_new_tokens": (
                authority_executor.max_new_tokens
            ),
            "deferred_risk_authority": args.deferred_risk_authority,
            "deferred_terminal_authority": (
                args.deferred_terminal_authority
            ),
            "diagnostic_post_timing_state": (
                args.diagnostic_post_timing_state
            ),
            "max_prompt_tokens": executor.max_prompt_tokens,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(
                torch.device(args.device)
            ),
        },
        "counts": {
            "sessions": len(sessions),
            "test_clean_sessions": sum(
                session.split == "test-clean" for session in sessions
            ),
            "test_other_sessions": sum(
                session.split == "test-other" for session in sessions
            ),
            "unique_utterances": len(set(utterance_ids)),
            "utterance_reuse": (
                len(utterance_ids) - len(set(utterance_ids))
            ),
            "unique_split_speakers": len(speaker_sessions),
            "speakers_reused_across_sessions": sum(
                count > 1 for count in speaker_sessions.values()
            ),
            "catastrophic_outliers": catastrophic,
            "events": len(events),
            "low_margin_holdbacks": runtime.get(
                "low_margin_holdbacks", 0
            ),
            "capacity_rebases": runtime.get("capacity_rebases", 0),
            **{
                key: value for key, value in runtime.items()
                if key.endswith("authorities")
                or key.endswith("revisions")
            },
        },
        "metrics": {
            "canonical_mean_wer": statistics.fmean(
                row["canonical_wer"] for row in rows
            ),
            "revtrace_mean_wer": statistics.fmean(
                row["revtrace_wer"] for row in rows
            ),
            "local_agreement_mean_wer": statistics.fmean(
                row["local_agreement_wer"] for row in rows
            ),
            "mean_wer_delta_pp": mean_delta,
            "paired_bootstrap_95_upper_pp": upper,
            "per_split": split_metrics,
            "canonical_seconds": canonical_seconds,
            "canonical_capacity_rebases": (
                canonical_capacity_rebases
            ),
            **runtime,
            "provisional_lifetime_p95": float(
                np.quantile(lifetimes, 0.95)
            ),
            "provisional_lifetime_max": max(lifetimes, default=0.0),
            "provisional_overwrite_p95": float(
                np.quantile(overwrite, 0.95)
            ),
            "display_delayed_by_state_holdback_fraction": 0.0,
        },
        "sessions": rows,
        "claim_boundaries": [
            "WER deltas are paired against the same W-suite authority path",
            "LocalAgreement-2 protects display confirmation, not prompt state",
            (
                "a risky batched proposal is provisional; deferred singleton "
                "authority owns both the next prompt state and any stable "
                "correction"
            ),
            (
                (
                    "terminal batched output is provisional and the stable "
                    "final transcript is owned by singleton canonical "
                    "authority"
                )
                if args.deferred_terminal_authority
                else (
                    "the state-only terminal contract ends canonical "
                    "authority at the last feedback edge; terminal batch "
                    "quality is governed by this paired W6 bound"
                )
            ),
            "test-clean and test-other sessions share no utterance",
            (
                "speaker reuse is reported because each LibriSpeech test "
                "split contains fewer speakers than the 64-session target"
            ),
        ],
    }
    if diagnostic is not None:
        payload["post_timing_state_diagnostic"] = diagnostic
    # Event-level evidence is retained because work-budget exhaustion,
    # low-margin feedback and repetition loops can have identical aggregate
    # WER symptoms but require different repairs.  It contains public
    # LibriSpeech hypotheses only; no audio is embedded.
    payload["event_diagnostics"] = events
    payload["canonical_event_diagnostics"] = canonical_traces
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": payload["decision"],
        **payload["counts"],
        **payload["metrics"],
    }, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
