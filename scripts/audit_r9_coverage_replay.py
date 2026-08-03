#!/usr/bin/env python3
"""Replay R9 coverage decisions after pure decision-function changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from revtrace.dgft import (
    boundary_adjusted_coverage_deficit,
    cross_granularity_coverage_deficit,
)


def decision_rows(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    if "coverage_decisions" in payload:
        return [list(item["segments"]) for item in payload["coverage_decisions"]]
    return [list(item["coverage_segments"]) for item in payload["sessions"]]


def replay(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    threshold = float(payload["config"]["coverage_threshold"])
    asymmetry = float(payload["config"]["coverage_asymmetry_margin"])
    changed: list[dict[str, Any]] = []
    empty_fine = 0
    segments = 0
    for session_id, rows in enumerate(decision_rows(payload)):
        fine = [str(row["fine_text"]) for row in rows]
        coarse = [str(row["coarse_text"]) for row in rows]
        for index, old in enumerate(rows):
            segments += 1
            if not fine[index].strip():
                empty_fine += 1
            adjusted, _, _ = boundary_adjusted_coverage_deficit(
                fine, coarse, index
            )
            reverse = cross_granularity_coverage_deficit(
                coarse[index], fine[index]
            )
            effective = float(old.get("effective_threshold", threshold))
            new = adjusted >= effective and adjusted - reverse >= asymmetry
            if new != bool(old["fallback_required"]):
                changed.append({
                    "session_id": session_id,
                    "segment_index": index,
                    "old": bool(old["fallback_required"]),
                    "new": new,
                    "old_adjusted": float(old["boundary_adjusted_deficit"]),
                    "new_adjusted": adjusted,
                    "fine_text": fine[index],
                    "coarse_text": coarse[index],
                })
    try:
        artifact_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        artifact_path = path.resolve().as_posix()
    return {
        "path": artifact_path,
        "segments": segments,
        "empty_fine_segments": empty_fine,
        "changed_decisions": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [replay(path) for path in args.paths]
    changed = sum(len(row["changed_decisions"]) for row in rows)
    output = {
        "schema_version": 1,
        "decision": (
            "PASS_R9_COVERAGE_REPLAY_NO_DECISION_CHANGE"
            if changed == 0 else "FAIL_R9_COVERAGE_REPLAY_DECISION_CHANGED"
        ),
        "files": len(rows),
        "segments": sum(row["segments"] for row in rows),
        "empty_fine_segments": sum(row["empty_fine_segments"] for row in rows),
        "changed_decisions": changed,
        "artifacts": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: output[key] for key in (
        "decision", "files", "segments", "empty_fine_segments",
        "changed_decisions",
    )}))
    return 0 if changed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
