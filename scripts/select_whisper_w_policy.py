#!/usr/bin/env python3
"""Select a Whisper fast-path policy from pre-outcome calibration traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scipy.stats import beta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--maximum-verification-fraction", type=float, default=0.20)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_sided_upper(errors: int, entries: int, alpha: float) -> float:
    if entries <= 0 or not 0 <= errors <= entries:
        return 1.0
    if errors == entries:
        return 1.0
    return float(beta.ppf(1.0 - alpha, errors + 1, entries - errors))


def main() -> int:
    args = parse_args()
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.calibration
    ]
    fingerprints = {
        (
            item["model"],
            int(item["config"]["concurrency"]),
            int(item["config"]["duration_seconds"]),
            int(item["config"]["window_seconds"]),
            str(item["config"]["model_path"]),
            str(item["config"]["precision"]),
            str(item["config"]["prompt_state_semantics"]),
            str(item["config"]["calibration_state_protocol"]),
            int(item["config"]["max_prompt_tokens"]),
            int(item["config"]["max_new_tokens"]),
            str(item["config"]["torch_version"]),
            str(item["config"]["transformers_version"]),
            str(item["config"]["cuda_runtime"]),
            str(item["config"]["gpu_name"]),
        )
        for item in payloads
    }
    if len(fingerprints) != 1:
        raise ValueError(f"calibration contract mismatch: {fingerprints}")
    rows: list[dict[str, Any]] = [
        row
        for item in payloads
        for row in item["rows"]
        if not bool(row.get("terminal", False))
    ]
    margins = sorted({
        float(row["minimum_margin"])
        for row in rows
        if row["minimum_margin"] is not None
    })
    candidates = [-1e-9] + [value + 1e-6 for value in margins]
    evaluations: list[dict[str, Any]] = []
    for threshold in candidates:
        fast = [
            row for row in rows
            if row["minimum_margin"] is not None
            and float(row["minimum_margin"]) > threshold
        ]
        errors = sum(bool(row["state_error"]) for row in fast)
        entries = len(fast)
        upper = one_sided_upper(errors, entries, args.alpha)
        verification_fraction = 1.0 - entries / len(rows)
        evaluations.append({
            "threshold": threshold,
            "fast_path_entries": entries,
            "fast_path_state_errors": errors,
            "calibration_upper_risk": upper,
            "verification_fraction": verification_fraction,
            "feasible": (
                upper <= args.delta
                and verification_fraction
                <= args.maximum_verification_fraction
            ),
        })
    feasible = [item for item in evaluations if item["feasible"]]
    selected = min(
        feasible,
        key=lambda item: (
            item["verification_fraction"],
            item["calibration_upper_risk"],
            item["threshold"],
        ),
        default=None,
    )
    output = {
        "schema_version": 1,
        "study": "Whisper W-suite pre-outcome policy selection",
        "decision": (
            "CALIBRATION_POLICY_SELECTED"
            if selected is not None else "CALIBRATION_FAIL_CLOSED"
        ),
        "contract": {
            "model": next(iter(fingerprints))[0],
            "concurrency": next(iter(fingerprints))[1],
            "duration_seconds": next(iter(fingerprints))[2],
            "window_seconds": next(iter(fingerprints))[3],
            "model_path": next(iter(fingerprints))[4],
            "precision": next(iter(fingerprints))[5],
            "prompt_state_semantics": next(iter(fingerprints))[6],
            "calibration_state_protocol": next(iter(fingerprints))[7],
            "max_prompt_tokens": next(iter(fingerprints))[8],
            "max_new_tokens": next(iter(fingerprints))[9],
            "torch_version": next(iter(fingerprints))[10],
            "transformers_version": next(iter(fingerprints))[11],
            "cuda_runtime": next(iter(fingerprints))[12],
            "gpu_name": next(iter(fingerprints))[13],
        },
        "config": {
            "delta": args.delta,
            "alpha": args.alpha,
            "maximum_verification_fraction": (
                args.maximum_verification_fraction
            ),
            "selection": (
                "lowest verification fraction among observed-margin order "
                "statistics satisfying both the calibration risk and "
                "verification budgets"
            ),
        },
        "counts": {
            "calibration_files": len(args.calibration),
            "events": len(rows),
            "state_errors": sum(bool(row["state_error"]) for row in rows),
        },
        "selected_policy": selected,
        "candidate_policies": evaluations,
        "source_files": [
            {"path": str(path), "sha256": sha256(path)}
            for path in args.calibration
        ],
        "claim_boundary": (
            "This policy is learned only from pre-outcome calibration. "
            "Independent time-uniform randomized auditing supplies the "
            "paper-facing risk certificate."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": output["decision"],
        "selected_policy": selected,
    }, sort_keys=True))
    return 0 if selected is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
