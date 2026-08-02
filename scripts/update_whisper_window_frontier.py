#!/usr/bin/env python3
"""Fail-closed incremental compiler for the Whisper state-age frontier.

Unlike the exploratory combinatorial policy search, this compiler preserves a
frozen policy epoch and adds only the smallest exact-window thresholds needed
to cover newly observed repeat-stable adaptation roots.  Adaptation roots never
enter the independent risk certificate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_whisper_w_state_age_policy import sha256, upper, verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--adaptation-audit", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--maximum-verification-fraction", type=float, default=0.20)
    args = parser.parse_args()

    base = json.loads(args.policy.read_text(encoding="utf-8"))
    calibration_paths = [
        Path(row["path"])
        for row in base["source_files"]
        if row["role"] == "calibration"
    ]
    inherited_root_paths = [
        Path(row["path"])
        for row in base["source_files"]
        if row["role"] == "adaptation-only-root"
    ]
    root_paths = list(dict.fromkeys([*inherited_root_paths, *args.adaptation_audit]))
    rows = [
        row
        for path in calibration_paths
        for row in json.loads(path.read_text(encoding="utf-8"))["rows"]
        if not bool(row.get("terminal", False))
    ]
    roots: list[dict[str, Any]] = []
    for path in root_paths:
        roots.extend(
            row
            for row in json.loads(path.read_text(encoding="utf-8"))["audit_rows"]
            if bool(row["state_error"])
        )
    if not roots:
        raise ValueError("no state-error adaptation roots")

    policy = dict(base["selected_policy"])
    rules = {
        int(row["window_index"]): float(row["margin_threshold"])
        for row in policy.get("window_margin_rules", [])
    }
    keys = (
        "threshold", "age_window_index", "age_margin_threshold",
        "late_window_index", "late_margin_threshold",
        "high_load_prompt_tokens", "high_load_margin_threshold",
        "window_margin_rules",
    )
    for root in roots:
        kwargs = {key: policy.get(key) for key in keys}
        kwargs["window_margin_rules"] = [
            {"window_index": window, "margin_threshold": margin}
            for window, margin in sorted(rules.items())
        ]
        if verify(root, **kwargs):
            continue
        window = int(root["window_index"])
        rules[window] = max(
            rules.get(window, float(policy["threshold"])),
            float(root["minimum_margin"]) + 1e-6,
        )
    policy["window_margin_rules"] = [
        {"window_index": window, "margin_threshold": margin}
        for window, margin in sorted(rules.items())
    ]
    kwargs = {key: policy.get(key) for key in keys}
    if not all(verify(root, **kwargs) for root in roots):
        raise AssertionError("incremental frontier failed to cover every root")
    admitted = [row for row in rows if not verify(row, **kwargs)]
    errors = sum(bool(row["state_error"]) for row in admitted)
    fraction = 1.0 - len(admitted) / len(rows)
    risk_upper = upper(errors, len(admitted), args.alpha)
    feasible = (
        errors == 0
        and risk_upper <= args.delta
        and fraction <= args.maximum_verification_fraction
    )
    policy.update({
        "fast_path_entries": len(admitted),
        "fast_path_state_errors": errors,
        "calibration_upper_risk": risk_upper,
        "verification_fraction": fraction,
        "caught_roots_covered": len(roots),
        "feasible": feasible,
    })
    output = {
        "schema_version": 1,
        "study": "incremental learned Whisper revision-window risk frontier",
        "decision": "WINDOW_FRONTIER_UPDATED" if feasible else "WINDOW_FRONTIER_FAIL_CLOSED",
        "contract": base["contract"],
        "config": {
            "delta": args.delta,
            "alpha": args.alpha,
            "maximum_verification_fraction": args.maximum_verification_fraction,
            "selection": "minimal exact-window expansion covering every repeat-stable adaptation root",
        },
        "counts": {
            "calibration_events": len(rows),
            "adaptation_roots": len(roots),
            "candidate_policies": 1,
        },
        "adaptation_root_summaries": [
            {
                "window_index": int(row["window_index"]),
                "minimum_margin": float(row["minimum_margin"]),
                "prior_prompt_tokens": int(row.get("prior_prompt_tokens", 0)),
                "next_prompt_tokens": int(row.get("next_prompt_tokens", 0)),
                "terminal": bool(row.get("terminal", False)),
            }
            for row in roots
        ],
        "selected_policy": policy,
        "candidate_policies": [policy],
        "source_files": [
            {"role": "initial-policy", "path": str(args.policy), "sha256": sha256(args.policy)},
            *(
                {"role": "calibration", "path": str(path), "sha256": sha256(path)}
                for path in calibration_paths
            ),
            *(
                {"role": "adaptation-only-root", "path": str(path), "sha256": sha256(path)}
                for path in root_paths
            ),
        ],
        "claim_boundary": (
            "Adaptation roots update the policy epoch and are excluded from "
            "the subsequent independent time-uniform risk audit."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "selected_policy": policy}, sort_keys=True))
    return 0 if feasible else 2


if __name__ == "__main__":
    raise SystemExit(main())
