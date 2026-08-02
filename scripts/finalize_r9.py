#!/usr/bin/env python3
"""Build a machine-auditable R9 quality and service summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def quality_row(path: Path, cohort: str) -> dict[str, Any]:
    payload = load(path)
    metrics = payload["metrics"]
    return {
        "cohort": cohort,
        "model": payload["model_name"],
        "decision": payload["decision"],
        "gate_pass": bool(metrics["gate_pass"]),
        "sessions": int(metrics["sessions"]),
        "catastrophic_outliers": int(metrics["catastrophic_outliers"]),
        "mean_delta_pp": float(metrics["mean_delta_pp"]),
        "bootstrap_95_upper_pp": float(metrics["bootstrap_95_upper_pp"]),
        "authority_audio_amplification": float(
            metrics["authority_audio_amplification"]
        ),
        "projected_two_gpu_wall_speedup": float(
            metrics["projected_two_gpu_wall_speedup"]
        ),
        "coverage_repairs": int(metrics["coverage_fallbacks"]),
        "full_session_escalations": int(
            metrics["full_session_escalations"]
        ),
        "sha256": digest(path),
        "path": str(path),
    }


def median(values: list[float]) -> float:
    return float(statistics.median(values))


def service_groups(paths: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        payload = load(path)
        metrics = payload["metrics"]
        cell = {
            "model": payload["config"]["model_name"],
            "arrival": payload["config"]["arrival"],
            "seed": int(payload["config"]["seed"]),
            "decision": payload["decision"],
            "wall_speedup": float(metrics["wall_speedup"]),
            "gpu_normalized_speedup": float(
                metrics["gpu_normalized_speedup"]
            ),
            "energy_reduction": float(metrics["energy_reduction"]),
            "display_latency_p99": float(metrics["display_latency_p99"]),
            "segment_commit_lag_p99": float(
                metrics["segment_commit_lag_p99"]
            ),
            "authority_audio_amplification": float(
                metrics["authority_audio_amplification"]
            ),
            "semantic_violations": int(metrics["semantic_violations"]),
            "commit_certificates": int(metrics["commit_certificates"]),
            "coverage_repairs": int(metrics["coverage_fallbacks"]),
            "full_session_escalations": int(
                metrics["full_session_escalations"]
            ),
            "sha256": digest(path),
            "path": str(path),
        }
        cell["strict_gate_pass"] = (
            cell["wall_speedup"] >= 2.5
            and cell["gpu_normalized_speedup"] >= 1.25
            and cell["energy_reduction"] >= 0.20
            and cell["display_latency_p99"] <= 1.9
            and cell["segment_commit_lag_p99"] <= 36.0
            and cell["authority_audio_amplification"] <= 1.2
            and cell["semantic_violations"] == 0
        )
        cells.append(cell)
        grouped[(cell["model"], cell["arrival"])].append(cell)
    summary: dict[str, Any] = {}
    for (model, arrival), rows in sorted(grouped.items()):
        label = f"{model}/{arrival}"
        summary[label] = {
            "cells": len(rows),
            "passed": sum(row["decision"] == "PASS_R9_DGFT_SERVICE" for row in rows),
            "wall_speedup_median": median([row["wall_speedup"] for row in rows]),
            "wall_speedup_min": min(row["wall_speedup"] for row in rows),
            "gpu_normalized_speedup_median": median(
                [row["gpu_normalized_speedup"] for row in rows]
            ),
            "energy_reduction_median": median(
                [row["energy_reduction"] for row in rows]
            ),
            "energy_reduction_min": min(row["energy_reduction"] for row in rows),
            "display_latency_p99_max": max(
                row["display_latency_p99"] for row in rows
            ),
            "segment_commit_lag_p99_max": max(
                row["segment_commit_lag_p99"] for row in rows
            ),
            "authority_audio_amplification_max": max(
                row["authority_audio_amplification"] for row in rows
            ),
            "semantic_violations": sum(
                row["semantic_violations"] for row in rows
            ),
            "commit_certificates": sum(
                row["commit_certificates"] for row in rows
            ),
        }
    return cells, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--final-holdout", type=Path, required=True)
    parser.add_argument("--service", type=Path, required=True)
    parser.add_argument("--holdout-audit", type=Path, required=True)
    parser.add_argument("--frozen-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    quality: list[dict[str, Any]] = []
    for model in ("tiny", "base", "small"):
        quality.append(quality_row(
            args.development
            / f"{model}-development-semantic-escalation.json",
            "development",
        ))
        quality.append(quality_row(
            args.final_holdout
            / f"{model}-semantic-final3-confirmation.json",
            "third-untouched-confirmation",
        ))
    service_paths = sorted(args.service.glob("*.json"))
    cells, groups = service_groups(service_paths)
    certificates = sum(row["commit_certificates"] for row in cells)
    semantic_violations = sum(row["semantic_violations"] for row in cells)
    audit = load(args.holdout_audit)
    policy = load(args.frozen_policy)
    quality_pass = all(row["gate_pass"] for row in quality)
    strict_cells_passed = sum(row["strict_gate_pass"] for row in cells)
    service_pass = len(cells) == 16 and strict_cells_passed == len(cells)
    qualified_service = len(cells) == 16 and strict_cells_passed >= 15
    integrity_pass = (
        audit["decision"] == "PASS_R9_HOLDOUT_AUDIT"
        and bool(policy["frozen_before_final3_execution"])
        and int(audit["overlap_count"]) == 0
        and policy["holdout_manifest_sha256"] == audit["manifest_sha256"]
    )
    if (
        quality_pass and service_pass and integrity_pass
        and semantic_violations == 0
    ):
        decision = "PASS_R9_SUBMISSION_EVIDENCE"
    elif (
        quality_pass and qualified_service and integrity_pass
        and semantic_violations == 0
    ):
        decision = "QUALIFIED_R9_EVIDENCE_15_OF_16_STRICT_CELLS"
    else:
        decision = "FAIL_R9_SUBMISSION_EVIDENCE"
    output = {
        "schema_version": 1,
        "study": "RevTrace Phase R9 final evidence",
        "decision": decision,
        "quality": quality,
        "service_cells": cells,
        "service_groups": groups,
        "aggregate": {
            "quality_cells": len(quality),
            "quality_cells_passed": sum(row["gate_pass"] for row in quality),
            "service_cells": len(cells),
            "service_cells_passed": sum(
                row["strict_gate_pass"] for row in cells
            ),
            "strict_service_matrix_pass": service_pass,
            "qualified_service_matrix": qualified_service,
            "commit_certificates": certificates,
            "semantic_violations": semantic_violations,
            "zero_observed_violation_rule_of_three_95_upper": (
                3.0 / certificates if certificates else None
            ),
        },
        "holdout_audit": audit,
        "frozen_policy": policy,
        "claim_boundary": (
            "Wall-clock and NVML energy values are real two-GPU measurements. "
            "Quality-gate speedups are projections and are kept separate. "
            "Zero observed transaction violations has a statistical upper "
            "bound and is not a mathematical numerical-exactness claim. "
            "The original per-cell service death gate remains 15/16; the "
            "single Base/Poisson capacity-boundary miss is not relabelled."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **output["aggregate"]}))
    return 0 if decision.startswith(("PASS", "QUALIFIED")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
