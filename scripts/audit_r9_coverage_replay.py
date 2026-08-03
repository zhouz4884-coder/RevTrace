#!/usr/bin/env python3
"""Replay R9 coverage decisions after pure decision-function changes."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from revtrace.dgft import (
    boundary_adjusted_coverage_deficit,
    cross_granularity_coverage_deficit,
)


_LEGACY_WORD = re.compile(r"[A-Za-z0-9']+")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def legacy_coverage_units(text: str) -> list[str]:
    """Return the Latin/digit units used before mixed-script coverage."""

    return [match.group(0).lower() for match in _LEGACY_WORD.finditer(text)]


def legacy_deficit(fine_text: str, coarse_text: str) -> float:
    fine = legacy_coverage_units(fine_text)
    coarse = legacy_coverage_units(coarse_text)
    if not fine:
        return 0.0
    matched = sum(
        block.size
        for block in SequenceMatcher(
            None, fine, coarse, autojunk=False
        ).get_matching_blocks()
    )
    return 1.0 - matched / len(fine)


def legacy_boundary_adjusted_deficit(
    fine_segments: list[str], coarse_segments: list[str], index: int
) -> float:
    """Reproduce the pre-CJK boundary-adjusted directional deficit."""

    def missing(fine: list[str], coarse: list[str]) -> int:
        matched = sum(
            block.size
            for block in SequenceMatcher(
                None, fine, coarse, autojunk=False
            ).get_matching_blocks()
        )
        return max(0, len(fine) - matched)

    local_fine = legacy_coverage_units(fine_segments[index])
    local_coarse = legacy_coverage_units(coarse_segments[index])
    if not local_fine:
        return 0.0
    residual = missing(local_fine, local_coarse)
    for neighbor in (index - 1, index + 1):
        if not 0 <= neighbor < len(fine_segments):
            continue
        low, high = sorted((index, neighbor))
        pair_fine = legacy_coverage_units(
            " ".join(fine_segments[low:high + 1])
        )
        pair_coarse = legacy_coverage_units(
            " ".join(coarse_segments[low:high + 1])
        )
        residual = min(residual, missing(pair_fine, pair_coarse))
    return residual / len(local_fine)


def decision_rows(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    if "coverage_decisions" in payload:
        return [list(item["segments"]) for item in payload["coverage_decisions"]]
    return [list(item["coverage_segments"]) for item in payload["sessions"]]


def replay(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    threshold = float(payload["config"]["coverage_threshold"])
    asymmetry = float(payload["config"]["coverage_asymmetry_margin"])
    changed: list[dict[str, Any]] = []
    legacy_changed: list[dict[str, Any]] = []
    empty_fine = 0
    latin_only = 0
    cjk = 0
    segments = 0
    for session_id, rows in enumerate(decision_rows(payload)):
        fine = [str(row["fine_text"]) for row in rows]
        coarse = [str(row["coarse_text"]) for row in rows]
        for index, old in enumerate(rows):
            segments += 1
            if not fine[index].strip():
                empty_fine += 1
            has_cjk = bool(_CJK.search(fine[index]) or _CJK.search(coarse[index]))
            if has_cjk:
                cjk += 1
            else:
                latin_only += 1
            adjusted, _, _ = boundary_adjusted_coverage_deficit(
                fine, coarse, index
            )
            reverse = cross_granularity_coverage_deficit(
                coarse[index], fine[index]
            )
            effective = float(old.get("effective_threshold", threshold))
            new = adjusted >= effective and adjusted - reverse >= asymmetry
            old_adjusted = legacy_boundary_adjusted_deficit(
                fine, coarse, index
            )
            old_reverse = legacy_deficit(coarse[index], fine[index])
            legacy = (
                old_adjusted >= effective
                and old_adjusted - old_reverse >= asymmetry
            )
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
            if not has_cjk and new != legacy:
                legacy_changed.append({
                    "session_id": session_id,
                    "segment_index": index,
                    "legacy": legacy,
                    "current": new,
                    "legacy_adjusted": old_adjusted,
                    "current_adjusted": adjusted,
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
        "latin_only_segments": latin_only,
        "cjk_segments": cjk,
        "empty_fine_segments": empty_fine,
        "recorded_decision_changes": changed,
        "legacy_current_decision_changes": legacy_changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help=(
            "Prior replay JSON whose artifacts (schema v2) or input_files "
            "(legacy schema) provide the frozen source paths."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = list(args.paths)
    if args.manifest is not None:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        manifest_rows = manifest.get("artifacts", manifest.get("input_files", []))
        paths.extend(Path(row["path"]) for row in manifest_rows)
    if not paths:
        parser.error("provide at least one path or --manifest")
    unique_paths = list(dict.fromkeys(path.resolve() for path in paths))
    rows = [replay(path) for path in unique_paths]
    changed = sum(len(row["recorded_decision_changes"]) for row in rows)
    legacy_changed = sum(
        len(row["legacy_current_decision_changes"]) for row in rows
    )
    output = {
        "schema_version": 2,
        "decision": (
            "PASS_R9_COVERAGE_REPLAY_NO_DECISION_CHANGE"
            if changed == 0 and legacy_changed == 0
            else "FAIL_R9_COVERAGE_REPLAY_DECISION_CHANGED"
        ),
        "files": len(rows),
        "segments": sum(row["segments"] for row in rows),
        "latin_only_segments": sum(
            row["latin_only_segments"] for row in rows
        ),
        "cjk_segments": sum(row["cjk_segments"] for row in rows),
        "empty_fine_segments": sum(row["empty_fine_segments"] for row in rows),
        "changed_decisions": changed,
        "recorded_decision_changes": changed,
        "legacy_current_latin_decision_changes": legacy_changed,
        "claim_boundary": (
            "This regression replays historical English Whisper coverage "
            "segments. It proves that the CJK-aware tokenizer preserves "
            "legacy decisions on these Latin-only traces; it does not "
            "measure Chinese scheduling quality."
        ),
        "artifacts": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: output[key] for key in (
        "decision", "files", "segments", "empty_fine_segments",
        "latin_only_segments", "cjk_segments", "changed_decisions",
        "legacy_current_latin_decision_changes",
    )}))
    return 0 if changed == 0 and legacy_changed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
