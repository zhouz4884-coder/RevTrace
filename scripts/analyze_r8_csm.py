#!/usr/bin/env python3
"""Cross-validated Cross-Modal Sufficiency Monitor for R8.

References and the canonical trace define development labels only.  Every
online feature is computed from the current audio window, candidate decoding,
or already-visible EFSC state counters.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from run_whisper_w_quality import SAMPLE_RATE, build_sessions


FEATURE_DIRECTIONS: tuple[tuple[str, bool], ...] = (
    ("generation_steps", False),
    ("token_count", False),
    ("token_yield", False),
    ("relative_yield_drop", True),
    ("speech_token_mismatch", True),
    ("terminated_by_eos", True),
    ("first_step_no_speech_probability", True),
    ("average_token_log_probability", False),
    ("compression_ratio", False),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=2026080701)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--false-trigger-budget", type=float, default=0.10)
    return parser.parse_args()


def frame_rms(audio: np.ndarray, frame_samples: int = 320) -> np.ndarray:
    usable = audio[: audio.size // frame_samples * frame_samples]
    if not usable.size:
        return np.zeros(1, dtype=np.float64)
    frames = usable.reshape(-1, frame_samples).astype(np.float64)
    return np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)


def empirical_p(
    calibration: Sequence[float], value: float, *, high: bool
) -> float:
    if high:
        count = sum(item >= value for item in calibration)
    else:
        count = sum(item <= value for item in calibration)
    return (1.0 + count) / (1.0 + len(calibration))


def higher_quantile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.inf
    index = min(
        len(ordered) - 1,
        max(0, math.ceil(quantile * len(ordered)) - 1),
    )
    return ordered[index]


def score_rows(
    calibration: Sequence[dict[str, Any]],
    rows: Sequence[dict[str, Any]],
) -> list[float]:
    pools = {
        name: [float(row[name]) for row in calibration]
        for name, _ in FEATURE_DIRECTIONS
    }
    return [
        -sum(
            math.log(max(1e-12, empirical_p(
                pools[name], float(row[name]), high=high
            )))
            for name, high in FEATURE_DIRECTIONS
        )
        for row in rows
    ]


def assign_folds(session_rows: Sequence[dict[str, Any]], folds: int) -> dict[int, int]:
    positive = [
        int(row["session_id"]) for row in session_rows
        if bool(row["catastrophic_outlier"])
    ]
    negative = [
        int(row["session_id"]) for row in session_rows
        if not bool(row["catastrophic_outlier"])
    ]
    result: dict[int, int] = {}
    for index, sid in enumerate(positive):
        result[sid] = index % folds
    for index, sid in enumerate(negative):
        result[sid] = index % folds
    return result


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
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
    windows_per_session = args.duration_seconds // args.window_seconds
    rows: list[dict[str, Any]] = []
    for session, recorded in zip(sessions, quality["sessions"]):
        windows = list(np.array_split(session.audio, windows_per_session))
        previous_yields: list[float] = []
        for window, event, canonical in zip(
            windows, recorded["efsc_trace"], recorded["canonical_trace"]
        ):
            rms = frame_rms(window)
            # A deployment monitor cannot use the future windows of the same
            # session to estimate its noise floor.  Calibrate from the current
            # observed window only; the reference and canonical trace remain
            # label-only inputs below.
            noise = float(np.quantile(rms, 0.20))
            speech_threshold = max(noise * 2.5, 1e-4)
            speech_ratio = float(np.mean(rms >= speech_threshold))
            active_seconds = max(
                0.02, speech_ratio * args.window_seconds
            )
            token_count = len(event["candidate_token_ids"])
            token_yield = token_count / active_seconds
            prior = (
                statistics.median(previous_yields[-2:])
                if previous_yields else token_yield
            )
            relative_drop = max(0.0, 1.0 - token_yield / max(prior, 1e-6))
            previous_yields.append(token_yield)
            canonical_text = str(canonical["text"])
            candidate_text = str(event["candidate_text"])
            root = bool(recorded["catastrophic_outlier"]) and (
                int(event["generation_steps"]) <= 10
                or len(canonical_text) - len(candidate_text) >= 50
            )
            rows.append({
                "session_id": int(recorded["session_id"]),
                "window_index": int(event["window_index"]),
                "split": recorded["split"],
                "root": root,
                "generation_steps": float(event["generation_steps"]),
                "token_count": float(token_count),
                "token_yield": token_yield,
                "relative_yield_drop": relative_drop,
                "speech_active_ratio": speech_ratio,
                "speech_token_mismatch": speech_ratio / (1.0 + token_count),
                "terminated_by_eos": float(bool(event["terminated_by_eos"])),
                "minimum_margin": event["minimum_margin"],
                "first_step_no_speech_probability": float(
                    event["first_step_no_speech_probability"]
                ),
                "average_token_log_probability": float(
                    event["average_token_log_probability"]
                ),
                "compression_ratio": float(event["compression_ratio"]),
                "feedback_debt": int(event["feedback_debt_after_decision"]),
                "state_age": int(event["oldest_ancestor_age_after_decision"]),
                "online_feature_only": True,
            })

    fold_by_session = assign_folds(quality["sessions"], args.folds)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for fold in range(args.folds):
        calibration = [
            row for row in rows if fold_by_session[row["session_id"]] != fold
        ]
        holdout = [
            row for row in rows if fold_by_session[row["session_id"]] == fold
        ]
        calibration_scores = score_rows(calibration, calibration)
        negative_scores = [
            value for value, row in zip(calibration_scores, calibration)
            if not row["root"]
        ]
        threshold = higher_quantile(
            negative_scores, 1.0 - args.false_trigger_budget
        )
        holdout_scores = score_rows(calibration, holdout)
        fold_rows: list[dict[str, Any]] = []
        for row, value in zip(holdout, holdout_scores):
            record = {
                **row,
                "fold": fold,
                "score": value,
                "threshold": threshold,
                "trigger": value > threshold,
            }
            predictions.append(record)
            fold_rows.append(record)
        positives = [row for row in fold_rows if row["root"]]
        negatives = [row for row in fold_rows if not row["root"]]
        fold_summaries.append({
            "fold": fold,
            "threshold": threshold,
            "roots": len(positives),
            "root_recall": (
                statistics.fmean(row["trigger"] for row in positives)
                if positives else None
            ),
            "false_trigger_rate": statistics.fmean(
                row["trigger"] for row in negatives
            ),
        })

    positives = [row for row in predictions if row["root"]]
    negatives = [row for row in predictions if not row["root"]]
    root_recall = statistics.fmean(row["trigger"] for row in positives)
    false_trigger_rate = statistics.fmean(
        row["trigger"] for row in negatives
    )
    root_sessions = {row["session_id"] for row in positives}
    caught_sessions = {
        row["session_id"] for row in positives if row["trigger"]
    }
    session_root_recall = len(caught_sessions) / max(1, len(root_sessions))
    # The preregistered gate is session-level: one timely root trigger is
    # sufficient to launch reanchoring for the affected session.  Event-level
    # recall remains reported as a stricter diagnostic and is not substituted
    # for the frozen endpoint.
    passed = session_root_recall >= 0.90 and false_trigger_rate <= 0.10
    frozen_scores = score_rows(rows, rows)
    frozen_negative_scores = [
        value for value, row in zip(frozen_scores, rows) if not row["root"]
    ]
    frozen_threshold = higher_quantile(
        frozen_negative_scores, 1.0 - args.false_trigger_budget
    )
    frozen_triggers = [value > frozen_threshold for value in frozen_scores]
    frozen_caught_sessions = {
        row["session_id"]
        for row, trigger in zip(rows, frozen_triggers)
        if row["root"] and trigger
    }
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8.2 cross-modal sufficiency monitor",
        "decision": "PASS_R8_2_CSM" if passed else "FAIL_R8_2_CSM",
        "metrics": {
            "events": len(predictions),
            "root_events": len(positives),
            "root_sessions": len(root_sessions),
            "root_recall": root_recall,
            "session_root_recall": session_root_recall,
            "false_trigger_rate": false_trigger_rate,
            "folds": args.folds,
        },
        "folds": fold_summaries,
        "frozen_policy": {
            "schema_version": 1,
            "feature_directions": [
                {"name": name, "high_is_risky": high}
                for name, high in FEATURE_DIRECTIONS
            ],
            "calibration_pools": {
                name: sorted(float(row[name]) for row in rows)
                for name, _ in FEATURE_DIRECTIONS
            },
            "score_threshold": frozen_threshold,
            "development_session_root_recall": (
                len(frozen_caught_sessions) / max(1, len(root_sessions))
            ),
            "development_event_false_trigger_rate": statistics.fmean(
                trigger
                for trigger, row in zip(frozen_triggers, rows)
                if not row["root"]
            ),
        },
        "rows": predictions,
        "label_boundary": (
            "canonical/reference-derived root labels are development-only; "
            "all monitor features are available online without a reference"
        ),
        "authority_boundary": (
            "CSM schedules recovery work and never grants feedback authority"
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
