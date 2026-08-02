#!/usr/bin/env python3
"""Freeze the one-calibration/one-adaptation Whisper EFSC policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from revtrace.feedback_coherence import calibrate_hysteresis_margins


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("rows")
    if not isinstance(result, list) or not result:
        raise ValueError(f"calibration artifact has no rows: {path}")
    return result


def main() -> int:
    args = parse_args()
    calibration_rows = rows(args.calibration)
    adaptation_rows = rows(args.adaptation)
    all_rows = [*calibration_rows, *adaptation_rows]
    margins = [
        float(row["minimum_margin"])
        for row in all_rows
        if row.get("minimum_margin") is not None
        and math.isfinite(float(row["minimum_margin"]))
    ]
    failures = [
        float(row["minimum_margin"])
        for row in all_rows
        if bool(row.get("state_error"))
        and row.get("minimum_margin") is not None
    ]
    policy = calibrate_hysteresis_margins(margins, failures)
    payload = {
        "schema_version": 1,
        "study": "RevTrace R7.2 frozen Whisper EFSC policy",
        "model": args.model_name,
        "selected_policy": {
            "enter_margin": policy.enter_margin,
            "exit_margin": policy.exit_margin,
            "minimum_hold_windows": 1,
            "safe_streak_required": 2,
            "maximum_quarantine_windows": 3,
            "maximum_feedback_debt": 3,
            "maximum_influence_windows": 3,
        },
        "evidence": {
            "calibration": {
                "path": str(args.calibration.resolve()),
                "sha256": digest(args.calibration),
                "rows": len(calibration_rows),
            },
            "adaptation": {
                "path": str(args.adaptation.resolve()),
                "sha256": digest(args.adaptation),
                "rows": len(adaptation_rows),
            },
            "eligible_margins": len(margins),
            "failure_roots": len(failures),
            "known_failure_ceiling": policy.known_failure_ceiling,
            "exit_quantile": policy.eligible_quantile,
        },
        "frozen_boundaries": {
            "calibration_and_adaptation_are_excluded_from_formal_audit": True,
            "performance_and_quality_seeds_may_not_update_this_policy": True,
            "model_specific_controller_branches": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["selected_policy"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
