#!/usr/bin/env python3
"""Build a contextual Whisper risk policy from caught failure roots.

Adaptation roots may move the policy but never enter its final confidence
certificate.  This script searches a base margin plus optional state-age and
prompt-load margin frontiers, requires every caught root to be covered, and
rejects candidates that exceed either the calibration risk or verification
budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scipy.stats import beta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument(
        "--calibration", type=Path, action="append", required=True
    )
    parser.add_argument(
        "--adaptation-audit", type=Path, action="append", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--maximum-verification-fraction", type=float, default=0.20
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upper(errors: int, entries: int, alpha: float) -> float:
    if entries <= 0 or not 0 <= errors <= entries:
        return 1.0
    if errors == entries:
        return 1.0
    return float(beta.ppf(1.0 - alpha, errors + 1, entries - errors))


def verify(
    row: dict[str, Any],
    *,
    threshold: float,
    late_window_index: int | None,
    late_margin_threshold: float | None,
    high_load_prompt_tokens: int | None,
    high_load_margin_threshold: float | None,
) -> bool:
    margin = row.get("minimum_margin")
    if margin is None or float(margin) <= threshold:
        return True
    late = (
        late_window_index is not None
        and late_margin_threshold is not None
        and
        int(row["window_index"]) >= late_window_index
        and float(margin) <= late_margin_threshold
    )
    high_load = (
        high_load_prompt_tokens is not None
        and high_load_margin_threshold is not None
        and int(row.get("prior_prompt_tokens", 0))
        >= high_load_prompt_tokens
        and float(margin) <= high_load_margin_threshold
    )
    return late or high_load


def select_recovery_policy(
    feasible: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Choose fail-closed risk first, then the cheapest such policy."""

    return min(
        feasible,
        key=lambda row: (
            row["fast_path_state_errors"],
            row["verification_fraction"],
            row["calibration_upper_risk"],
            (
                -1 if row["late_window_index"] is None
                else row["late_window_index"]
            ),
            (
                -1.0 if row["late_margin_threshold"] is None
                else row["late_margin_threshold"]
            ),
            (
                -1 if row["high_load_prompt_tokens"] is None
                else row["high_load_prompt_tokens"]
            ),
            (
                -1.0 if row["high_load_margin_threshold"] is None
                else row["high_load_margin_threshold"]
            ),
            row["threshold"],
        ),
        default=None,
    )


def main() -> int:
    args = parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    calibration_payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.calibration
    ]
    rows = [
        row
        for payload in calibration_payloads
        for row in payload["rows"]
        if not bool(row.get("terminal", False))
    ]
    roots = []
    for path in args.adaptation_audit:
        payload = json.loads(path.read_text(encoding="utf-8"))
        roots.extend(
            row for row in payload["audit_rows"] if row["state_error"]
        )
    if not roots:
        raise ValueError("no caught state-error roots")

    original = float(policy["selected_policy"]["threshold"])
    base_candidates = sorted({
        original,
        *(
            float(row["minimum_margin"]) + 1e-6
            for row in roots
        ),
    })
    late_windows: list[int | None] = [None, *sorted({
        int(row["window_index"]) for row in roots
    })]
    late_thresholds: list[float | None] = [None, *sorted({
        float(row["minimum_margin"]) + 1e-6 for row in roots
    })]
    high_load_prompts: list[int | None] = [None, *sorted({
        int(row.get("prior_prompt_tokens", 0))
        for row in roots
        if int(row.get("prior_prompt_tokens", 0)) > 0
    })]
    high_load_thresholds: list[float | None] = [None, *sorted({
        float(row["minimum_margin"]) + 1e-6 for row in roots
    })]

    evaluations: list[dict[str, Any]] = []
    for threshold in base_candidates:
        for late_window in late_windows:
            for late_threshold in late_thresholds:
                if (late_window is None) != (late_threshold is None):
                    continue
                if (
                    late_threshold is not None
                    and late_threshold < threshold
                ):
                    continue
                for high_load_prompt in high_load_prompts:
                    for high_load_threshold in high_load_thresholds:
                        if (
                            (high_load_prompt is None)
                            != (high_load_threshold is None)
                        ):
                            continue
                        if (
                            high_load_threshold is not None
                            and high_load_threshold < threshold
                        ):
                            continue
                        if not all(verify(
                            row,
                            threshold=threshold,
                            late_window_index=late_window,
                            late_margin_threshold=late_threshold,
                            high_load_prompt_tokens=high_load_prompt,
                            high_load_margin_threshold=high_load_threshold,
                        ) for row in roots):
                            continue
                        admitted = [
                            row for row in rows if not verify(
                                row,
                                threshold=threshold,
                                late_window_index=late_window,
                                late_margin_threshold=late_threshold,
                                high_load_prompt_tokens=high_load_prompt,
                                high_load_margin_threshold=(
                                    high_load_threshold
                                ),
                            )
                        ]
                        errors = sum(
                            bool(row["state_error"]) for row in admitted
                        )
                        verification_fraction = (
                            1.0 - len(admitted) / len(rows)
                        )
                        risk_upper = upper(
                            errors, len(admitted), args.alpha
                        )
                        evaluations.append({
                            "threshold": threshold,
                            "late_window_index": late_window,
                            "late_margin_threshold": late_threshold,
                            "high_load_prompt_tokens": high_load_prompt,
                            "high_load_margin_threshold": (
                                high_load_threshold
                            ),
                            "fast_path_entries": len(admitted),
                            "fast_path_state_errors": errors,
                            "calibration_upper_risk": risk_upper,
                            "verification_fraction": verification_fraction,
                            "caught_roots_covered": len(roots),
                            "feasible": (
                                risk_upper <= args.delta
                                and verification_fraction
                                <= args.maximum_verification_fraction
                            ),
                        })
    feasible = [row for row in evaluations if row["feasible"]]
    # Recovery is fail-closed: within the predeclared verification budget,
    # first minimize observed state-entry errors and only then minimize
    # verification work.  The previous performance-first ordering could pick
    # a statistically feasible policy that knowingly admitted a calibration
    # state error, which is unsuitable for an exact committed-state contract.
    selected = select_recovery_policy(feasible)
    output = {
        "schema_version": 1,
        "study": "Whisper contextual state-risk contract renewal",
        "decision": (
            "STATE_AGE_POLICY_SELECTED"
            if selected is not None else "STATE_AGE_POLICY_FAIL_CLOSED"
        ),
        "contract": policy["contract"],
        "config": {
            "delta": args.delta,
            "alpha": args.alpha,
            "maximum_verification_fraction": (
                args.maximum_verification_fraction
            ),
            "selection": (
                "minimum observed state-entry errors, then minimum "
                "calibration verification, among contextual margin-age-load "
                "policies covering every adaptation-only failure root"
            ),
        },
        "counts": {
            "calibration_events": len(rows),
            "adaptation_roots": len(roots),
            "candidate_policies": len(evaluations),
        },
        "adaptation_root_summaries": [
            {
                "window_index": int(row["window_index"]),
                "minimum_margin": float(row["minimum_margin"]),
                "prior_prompt_tokens": int(
                    row.get("prior_prompt_tokens", 0)
                ),
                "next_prompt_tokens": int(
                    row.get("next_prompt_tokens", 0)
                ),
                "terminal": bool(row.get("terminal", False)),
            }
            for row in roots
        ],
        "selected_policy": selected,
        "candidate_policies": evaluations,
        "source_files": [
            {
                "role": "initial-policy",
                "path": str(args.policy),
                "sha256": sha256(args.policy),
            },
            *(
                {
                    "role": "calibration",
                    "path": str(path),
                    "sha256": sha256(path),
                }
                for path in args.calibration
            ),
            *(
                {
                    "role": "adaptation-only-root",
                    "path": str(path),
                    "sha256": sha256(path),
                }
                for path in args.adaptation_audit
            ),
        ],
        "claim_boundary": (
            "Caught roots select a new policy epoch but are excluded from "
            "the independent time-uniform validation run."
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
