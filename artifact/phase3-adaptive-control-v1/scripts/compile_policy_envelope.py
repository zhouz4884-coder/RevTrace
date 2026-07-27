#!/usr/bin/env python3
"""Compile a simultaneous adaptive-policy envelope from frozen shadow audits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from revtrace.risk import AuditRiskBound


STRATA = (
    ("(0.05,0.10]", 0.05),
    ("(0.10,0.20]", 0.10),
    ("(0.20,0.50]", 0.20),
    ("(0.50,1.00]", 0.50),
    ("(1.00,inf)", 1.00),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--thresholds", default="0.05,0.10,0.20,0.50,1.00"
    )
    parser.add_argument("--familywise-alpha", type=float, default=0.05)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--minimum-base-audits", type=int, default=500)
    parser.add_argument("--risk-price", type=float, default=1.0)
    parser.add_argument("--queue-price", type=float, default=1.0)
    parser.add_argument(
        "--frozen-caught-margin",
        type=float,
        action="append",
        default=[],
        help=(
            "a previously caught real state disagreement that this epoch "
            "must retain as a hard policy exclusion"
        ),
    )
    return parser.parse_args()


def compile_envelope(
    payload: dict,
    *,
    thresholds: tuple[float, ...],
    alpha: float,
    delta: float,
    minimum_audits: int,
    risk_price: float,
    queue_price: float,
    frozen_caught_margins: tuple[float, ...] = (),
) -> dict:
    if tuple(threshold for _, threshold in STRATA) != thresholds:
        raise ValueError(
            "the frozen runner exposes exactly the preregistered "
            "0.05/0.10/0.20/0.50/1.00 policy family"
        )
    strata = payload.get("margin_strata")
    if not strata:
        raise ValueError("source audit has no margin-stratum evidence")
    audit_probability = float(payload["config"]["audit_probability"])
    simultaneous_alpha = alpha / len(thresholds)
    policies = []
    exclusion_floor = (
        max(frozen_caught_margins)
        if frozen_caught_margins
        else None
    )
    for policy_index, threshold in enumerate(thresholds):
        included = [
            strata[name]
            for name, lower_bound in STRATA
            if lower_bound >= threshold
        ]
        entries = sum(int(item["entries"]) for item in included)
        audits = sum(int(item["audits"]) for item in included)
        caught = sum(
            int(item["caught_state_errors"]) for item in included
        )
        bound = AuditRiskBound(audit_probability, simultaneous_alpha)
        upper_count = bound.upper_error_count(entries, caught)
        upper_risk = upper_count / entries if entries else 1.0
        frozen_failure_excluded = (
            exclusion_floor is not None and threshold < exclusion_floor
        )
        policies.append(
            {
                "threshold": threshold,
                "eligible_entries": entries,
                "base_audits": audits,
                "caught_state_errors": caught,
                "upper_error_count": upper_count,
                "upper_risk": upper_risk,
                "simultaneous_alpha": simultaneous_alpha,
                "frozen_failure_excluded": frozen_failure_excluded,
                "certified": (
                    not frozen_failure_excluded
                    and
                    audits >= minimum_audits and upper_risk <= delta
                ),
            }
        )
    maximum_entries = max(item["eligible_entries"] for item in policies)
    for item in policies:
        item["verifier_fraction_proxy"] = (
            1.0 - item["eligible_entries"] / maximum_entries
            if maximum_entries
            else 1.0
        )
        item["risk_price_objective"] = (
            risk_price * item["upper_risk"]
            + queue_price * item["verifier_fraction_proxy"]
        )
    certified = [item for item in policies if item["certified"]]
    selected = (
        min(
            certified,
            key=lambda item: (
                item["risk_price_objective"],
                item["threshold"],
            ),
        )
        if certified
        else None
    )
    return {
        "schema_version": 1,
        "study": "RevControl simultaneous adaptive policy envelope",
        "source_study": payload["study"],
        "source_model": payload["model"],
        "source_config": payload["config"],
        "familywise_alpha": alpha,
        "simultaneous_method": (
            "Bonferroni-composed fixed-probability mixture e-process "
            "inversions over a preregistered monotone policy family"
        ),
        "target_delta": delta,
        "frozen_caught_margins": list(frozen_caught_margins),
        "policies": policies,
        "selected_policy": selected,
        "decision": (
            "ADAPTIVE_POLICY_ENVELOPE_PASS"
            if selected
            else "ADAPTIVE_POLICY_ENVELOPE_FAIL_CLOSED"
        ),
        "claim_boundaries": {
            "source": (
                "compiled from one fixed-probability randomized shadow "
                "audit; no post-outcome threshold was added"
            ),
            "failure_ledger": (
                "previously caught real failures are hard exclusions and "
                "cannot be diluted by later zero-error evidence"
            ),
            "selection": (
                "threshold is selected only after simultaneous confidence "
                "allocation is frozen"
            ),
            "grid": (
                "finite policy grid is an implementation approximation; "
                "risk-price optimization is the method abstraction"
            ),
            "idle_audits": "excluded from all formal counts",
            "performance": "no serving performance claim is made here",
        },
    }


def main() -> int:
    args = parse_args()
    thresholds = tuple(
        float(item)
        for item in args.thresholds.split(",")
        if item.strip()
    )
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = compile_envelope(
        payload,
        thresholds=thresholds,
        alpha=args.familywise_alpha,
        delta=args.delta,
        minimum_audits=args.minimum_base_audits,
        risk_price=args.risk_price,
        queue_price=args.queue_price,
        frozen_caught_margins=tuple(args.frozen_caught_margin),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["selected_policy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
