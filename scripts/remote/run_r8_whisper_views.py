#!/usr/bin/env python3
"""Run causal Whisper context-recovery views for the frozen R7 sessions.

Each view is an entire causal session trajectory.  The script never chooses a
window using its reference.  References are used only after execution to score
the completed trajectory.  Recent-audio capsules read raw audio strictly before
the window they condition; snapshot-delta views use a frozen canonical anchor
and transcribe only the subsequent audio delta.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from revtrace.whisper_state import capacity_rebase_required
from run_whisper_w_quality import build_sessions, word_error
from whisper_batched_executor import DistinctPromptWhisper, WhisperCandidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quality-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--view",
        choices=("vacc-10", "vacc-20", "vacc-30", "snapshot-delta"),
        required=True,
    )
    parser.add_argument("--snapshot-interval", type=int, default=3)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--seed", type=int, default=2026080701)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--selection", choices=("catastrophic", "all"), default="catastrophic"
    )
    return parser.parse_args()


def catastrophic(candidate: float, canonical: float) -> bool:
    delta = candidate - canonical
    return delta > 10.0 or (
        candidate > 2.0 * max(canonical, 1.0) and delta > 5.0
    )


def score(reference: str, text: str) -> float:
    errors, words = word_error(reference, text)
    return 100.0 * errors / max(1, words)


def digest_audio(audio: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(audio, dtype=np.float32).tobytes(order="C")
    ).hexdigest()


def canonical_prompts(
    executor: DistinctPromptWhisper,
    trace: Sequence[dict[str, Any]],
) -> tuple[list[tuple[int, ...]], list[tuple[int, ...]]]:
    before: list[tuple[int, ...]] = []
    after: list[tuple[int, ...]] = []
    prompt: tuple[int, ...] = ()
    for event in trace:
        if capacity_rebase_required(
            len(executor.prompt_tokens(prompt)),
            declared_next_segment_tokens=executor.max_new_tokens,
            maximum_prompt_tokens=executor.max_prompt_tokens,
        ):
            prompt = ()
        before.append(prompt)
        prompt = executor.advance_prompt(prompt, event["token_ids"])
        after.append(prompt)
    return before, after


def concatenate(rows: Sequence[np.ndarray]) -> np.ndarray:
    if not rows:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate([np.asarray(row, dtype=np.float32) for row in rows])


def build_capsule(
    executor: DistinctPromptWhisper,
    audio: np.ndarray,
    prompt: Sequence[int],
) -> tuple[WhisperCandidate | None, float]:
    if audio.size == 0:
        return None, 0.0
    started = time.perf_counter()
    record = executor.canonical(audio, prompt)
    return record, time.perf_counter() - started


def run_view(
    executor: DistinctPromptWhisper,
    sessions: Sequence[Any],
    source_rows: Sequence[dict[str, Any]],
    session_ids: Sequence[int],
    *,
    view: str,
    windows_per_session: int,
    window_seconds: int,
    concurrency: int,
    snapshot_interval: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    windows = {
        sid: list(np.array_split(sessions[sid].audio, windows_per_session))
        for sid in session_ids
    }
    canonical_after: dict[int, list[tuple[int, ...]]] = {}
    if view == "snapshot-delta":
        for sid in session_ids:
            _, after = canonical_prompts(
                executor, source_rows[sid]["canonical_trace"]
            )
            canonical_after[sid] = after

    pieces: dict[int, list[str]] = {sid: [] for sid in session_ids}
    traces: dict[int, list[dict[str, Any]]] = {sid: [] for sid in session_ids}
    per_session_capsule_seconds = {sid: 0.0 for sid in session_ids}
    per_session_proposal_seconds = {sid: 0.0 for sid in session_ids}
    capsule_jobs = 0
    capsule_seconds = 0.0
    proposal_seconds = 0.0
    span_windows = (
        int(view.split("-")[1]) // window_seconds
        if view.startswith("vacc-") else 0
    )

    for window_index in range(windows_per_session):
        for begin in range(0, len(session_ids), concurrency):
            ids = list(session_ids[begin : begin + concurrency])
            prompts: list[tuple[int, ...]] = []
            capsule_debug: list[dict[str, Any]] = []
            for sid in ids:
                prompt: tuple[int, ...] = ()
                capsule: WhisperCandidate | None = None
                capsule_audio = np.zeros(0, dtype=np.float32)
                anchor_window: int | None = None
                delta_start: int | None = None
                if view.startswith("vacc-") and window_index > 0:
                    start = max(0, window_index - span_windows)
                    capsule_audio = concatenate(windows[sid][start:window_index])
                    capsule, elapsed = build_capsule(
                        executor, capsule_audio, ()
                    )
                    capsule_jobs += 1
                    capsule_seconds += elapsed
                    per_session_capsule_seconds[sid] += elapsed
                    prompt = (
                        executor.prompt_tokens(capsule.token_ids)
                        if capsule is not None else ()
                    )
                    delta_start = start
                elif view == "snapshot-delta" and window_index > 0:
                    anchor_window = (
                        (window_index - 1) // snapshot_interval
                    ) * snapshot_interval
                    prompt = canonical_after[sid][anchor_window]
                    delta_start = anchor_window + 1
                    if delta_start < window_index:
                        capsule_audio = concatenate(
                            windows[sid][delta_start:window_index]
                        )
                        capsule, elapsed = build_capsule(
                            executor, capsule_audio, prompt
                        )
                        capsule_jobs += 1
                        capsule_seconds += elapsed
                        per_session_capsule_seconds[sid] += elapsed
                        if capsule is not None:
                            prompt = executor.advance_prompt(
                                prompt, capsule.token_ids
                            )
                prompts.append(prompt)
                capsule_debug.append({
                    "anchor_window": anchor_window,
                    "audio_start_window": delta_start,
                    "audio_end_window_exclusive": window_index,
                    "audio_sha256": (
                        digest_audio(capsule_audio)
                        if capsule_audio.size else None
                    ),
                    "capsule_token_ids": (
                        list(capsule.token_ids) if capsule is not None else []
                    ),
                    "capsule_text": capsule.text if capsule is not None else "",
                    "prompt_token_count": len(prompt),
                })
            audio = [windows[sid][window_index] for sid in ids]
            started = time.perf_counter()
            records = executor.generate(audio, prompts)
            elapsed = time.perf_counter() - started
            proposal_seconds += elapsed
            share = elapsed / len(ids)
            for position, sid in enumerate(ids):
                per_session_proposal_seconds[sid] += share
                record = records[position]
                pieces[sid].append(record.text)
                traces[sid].append({
                    "window_index": window_index,
                    **capsule_debug[position],
                    "candidate_token_ids": list(record.token_ids),
                    "candidate_text": record.text,
                    "minimum_margin": record.minimum_margin,
                    "generation_steps": record.generation_steps,
                    "terminated_by_eos": record.terminated_by_eos,
                })

    rows: list[dict[str, Any]] = []
    for sid in session_ids:
        text = " ".join(pieces[sid])
        canonical_wer = float(source_rows[sid]["canonical_wer"])
        value = score(sessions[sid].reference, text)
        rows.append({
            "session_id": sid,
            "split": sessions[sid].split,
            "view": view,
            "reference_words": len(sessions[sid].reference.split()),
            "canonical_wer": canonical_wer,
            "wer": value,
            "delta_pp": value - canonical_wer,
            "catastrophic_outlier": catastrophic(value, canonical_wer),
            "text": text,
            "capsule_seconds": per_session_capsule_seconds[sid],
            "proposal_seconds": per_session_proposal_seconds[sid],
            "trace": traces[sid],
        })
    return rows, {
        "capsule_jobs": capsule_jobs,
        "capsule_seconds": capsule_seconds,
        "proposal_seconds": proposal_seconds,
    }


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window size")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    quality = json.loads(args.quality_trace.read_text(encoding="utf-8"))
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
    if len(sessions) != len(quality["sessions"]):
        raise AssertionError("quality/session reconstruction mismatch")
    for session, row in zip(sessions, quality["sessions"]):
        if tuple(session.utterance_ids) != tuple(row["utterance_ids"]):
            raise AssertionError("quality manifest reconstruction mismatch")
    session_ids = [
        int(row["session_id"])
        for row in quality["sessions"]
        if args.selection == "all" or bool(row["catastrophic_outlier"])
    ]
    executor = DistinctPromptWhisper(
        args.model, device=args.device, max_new_tokens=args.max_new_tokens
    )
    windows_per_session = args.duration_seconds // args.window_seconds
    rows, timing = run_view(
        executor, sessions, quality["sessions"], session_ids,
        view=args.view, windows_per_session=windows_per_session,
        window_seconds=args.window_seconds, concurrency=args.concurrency,
        snapshot_interval=args.snapshot_interval,
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8.1 causal context-recovery view",
        "view": args.view,
        "selection": args.selection,
        "sessions": len(rows),
        "source_quality_sha256": hashlib.sha256(
            args.quality_trace.read_bytes()
        ).hexdigest(),
        "config": {
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "snapshot_interval": args.snapshot_interval,
            "seed": args.seed,
            "device": args.device,
        },
        "metrics": {
            **timing,
            "mean_wer": statistics.fmean(row["wer"] for row in rows),
            "catastrophic_outliers": sum(
                bool(row["catastrophic_outlier"]) for row in rows
            ),
        },
        "rows": rows,
        "claim_boundary": (
            "complete causal session view over frozen R7 roots; references "
            "score the completed trajectory but never select a window input"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["metrics"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
