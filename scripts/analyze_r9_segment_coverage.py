#!/usr/bin/env python3
"""Audit segment-level cross-granularity coverage thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.remote.run_r9_coverage_fallback import segment_decisions


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--models", nargs="+", default=["tiny", "base", "small"])
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    payload: dict[str, object] = {"models": {}}
    for model in args.models:
        probe = json.loads(
            (args.root / f"{model}-cross-granularity-development.json").read_text()
        )
        coarse = json.loads(
            (args.root / f"{model}-tailfix15-30-diagnostic.json").read_text()
        )
        mode = next(iter(coarse["modes"].values()))
        sessions = []
        for sid, (probe_row, trace, quality_row) in enumerate(zip(
            probe["rows"], mode["traces"], mode["sessions"]
        )):
            decisions = segment_decisions(
                fine_windows=probe_row["fine_window_texts"],
                coarse_trace=trace, window_seconds=10, threshold=0.0,
            )
            sessions.append({
                "session_id": sid,
                "outlier": quality_row["catastrophic_outlier"],
                "segments": decisions,
            })
        thresholds = []
        for threshold in [value / 100 for value in range(5, 51)]:
            selected = [
                row for row in sessions
                if any(seg["deficit"] >= threshold for seg in row["segments"])
            ]
            misses = sum(
                row["outlier"] and row not in selected for row in sessions
            )
            replay_seconds = sum(
                50.0 - min(
                    seg["start_seconds"] for seg in row["segments"]
                    if seg["deficit"] >= threshold
                )
                for row in selected
            )
            thresholds.append({
                "threshold": threshold,
                "selected_sessions": len(selected),
                "missed_outliers": misses,
                "replay_seconds": replay_seconds,
            })
        payload["models"][model] = {
            "outlier_segments": [
                {
                    "session_id": row["session_id"],
                    "segments": row["segments"],
                }
                for row in sessions if row["outlier"]
            ],
            "thresholds": thresholds,
        }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
