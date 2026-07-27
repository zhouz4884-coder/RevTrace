#!/usr/bin/env python3
"""Regression simulation for the RevTrace randomized-audit risk contract."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from revtrace.risk import AuditRiskBound


@dataclass(frozen=True)
class Scenario:
    name: str
    before_rate: float
    after_rate: float
    drift_at: int
    optional_stop: bool
    adaptive_extra_audit: bool

    def rate(self, index: int) -> float:
        return self.before_rate if index < self.drift_at else self.after_rate


def wilson_upper(successes: int, trials: int, z: float = 1.96) -> float:
    if trials == 0:
        return 1.0
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = proportion + z * z / (2.0 * trials)
    radius = z * math.sqrt(
        proportion * (1.0 - proportion) / trials
        + z * z / (4.0 * trials * trials)
    )
    return min(1.0, (center + radius) / denominator)


def simulate_once(
    scenario: Scenario,
    *,
    entries: int,
    audit_probability: float,
    alpha: float,
    delta: float,
    seed: int,
) -> dict[str, float | int | bool]:
    rng = np.random.default_rng(seed)
    bound = AuditRiskBound(audit_probability, alpha)
    indexes = np.arange(entries)
    rates = np.where(
        indexes < scenario.drift_at,
        scenario.before_rate,
        scenario.after_rate,
    )
    errors = rng.random(entries) < rates
    base_audit_flags = rng.random(entries) < audit_probability
    caught_flags = errors & base_audit_flags
    cumulative_errors = np.cumsum(errors, dtype=np.int64)
    cumulative_caught = np.cumsum(caught_flags, dtype=np.int64)

    if scenario.adaptive_extra_audit:
        near_drift = indexes >= max(
            0, scenario.drift_at - entries // 20
        )
        extra_probabilities = np.where(near_drift, 0.15, 0.01)
        extra_audit_flags = (
            rng.random(entries) < extra_probabilities
        )
    else:
        extra_audit_flags = np.zeros(entries, dtype=np.bool_)

    stopped_at = entries
    if scenario.optional_stop:
        for count in range(max(100, entries // 4), entries + 1, 100):
            caught = int(cumulative_caught[count - 1])
            upper_count = bound.upper_error_count(
                count, caught
            )
            if upper_count / count <= delta:
                stopped_at = count
                break

    true_errors = int(cumulative_errors[stopped_at - 1])
    caught_errors = int(cumulative_caught[stopped_at - 1])
    last_upper = (
        bound.upper_error_count(stopped_at, caught_errors) / stopped_at
    )

    # Evaluate the e-process at the true latent error count at every time.
    # This is equivalent to checking whether the time-uniform confidence
    # sequence ever excludes the truth, but avoids thousands of integer
    # inversions per repetition.
    error_path = cumulative_errors[:stopped_at].astype(np.float64)
    caught_path = cumulative_caught[:stopped_at].astype(np.float64)
    log_e_path = np.full(stopped_at, -np.inf, dtype=np.float64)
    p = audit_probability
    for betting_parameter, log_weight in zip(
        bound.lambdas, bound.log_weights
    ):
        normalizer = math.log1p(
            p * (math.exp(betting_parameter) - 1.0)
        )
        component = (
            log_weight
            + betting_parameter * caught_path
            - error_path * normalizer
        )
        log_e_path = np.logaddexp(log_e_path, component)
    coverage_violation = bool(
        np.any(log_e_path >= math.log(1.0 / alpha))
    )
    return {
        "coverage_violation": coverage_violation,
        "true_errors": true_errors,
        "caught_errors": caught_errors,
        "base_audits": int(
            np.count_nonzero(base_audit_flags[:stopped_at])
        ),
        "extra_audits": int(
            np.count_nonzero(extra_audit_flags[:stopped_at])
        ),
        "stopped_at": stopped_at,
        "upper_risk": last_upper,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entries", type=int, default=30_000)
    parser.add_argument("--repetitions", type=int, default=500)
    parser.add_argument("--audit-probability", type=float, default=0.021)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=20260727)
    args = parser.parse_args()

    scenarios = (
        Scenario("zero", 0.0, 0.0, args.entries, False, False),
        Scenario("rare", 0.001, 0.001, args.entries, True, False),
        Scenario("boundary", 0.005, 0.005, args.entries, True, True),
        Scenario("unsafe", 0.01, 0.01, args.entries, False, True),
        Scenario(
            "sudden_drift",
            0.0005,
            0.02,
            args.entries // 2,
            False,
            True,
        ),
    )
    summaries = []
    total_violations = 0
    total_trials = 0
    for scenario_index, scenario in enumerate(scenarios):
        records = [
            simulate_once(
                scenario,
                entries=args.entries,
                audit_probability=args.audit_probability,
                alpha=args.alpha,
                delta=args.delta,
                seed=args.seed
                + scenario_index * args.repetitions
                + repetition,
            )
            for repetition in range(args.repetitions)
        ]
        violations = sum(
            bool(record["coverage_violation"]) for record in records
        )
        total_violations += violations
        total_trials += len(records)
        summaries.append(
            {
                "scenario": scenario.name,
                "repetitions": len(records),
                "coverage_violations": violations,
                "coverage_violation_rate": violations / len(records),
                "coverage_violation_wilson_upper_95": wilson_upper(
                    violations, len(records)
                ),
                "mean_base_audits": sum(
                    int(record["base_audits"]) for record in records
                )
                / len(records),
                "mean_extra_audits": sum(
                    int(record["extra_audits"]) for record in records
                )
                / len(records),
                "mean_final_upper_risk": sum(
                    float(record["upper_risk"]) for record in records
                )
                / len(records),
                "mean_stopped_at": sum(
                    int(record["stopped_at"]) for record in records
                )
                / len(records),
            }
        )

    zero_error_bound = AuditRiskBound(
        args.audit_probability, args.alpha
    ).upper_risk(args.entries, 0)
    # The theorem, not a binomial confidence interval over a finite Monte
    # Carlo sample, supplies the <= alpha guarantee.  The simulation is a
    # regression check: its observed failure frequency must not exceed alpha.
    # Wilson upper bounds are retained as diagnostics and deliberately are
    # not used as a second, much more conservative hypothesis test.
    passed = (
        all(
            summary["coverage_violation_rate"] <= args.alpha
            for summary in summaries
        )
        and zero_error_bound <= args.delta
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace S1 anytime randomized-audit simulation",
        "decision": (
            "S1_ANYTIME_RISK_SIMULATION_PASS"
            if passed
            else "S1_ANYTIME_RISK_SIMULATION_FAIL"
        ),
        "config": {
            "entries": args.entries,
            "repetitions_per_scenario": args.repetitions,
            "audit_probability": args.audit_probability,
            "alpha": args.alpha,
            "delta": args.delta,
            "seed": args.seed,
        },
        "zero_caught_error_upper_risk": zero_error_bound,
        "overall_coverage_violation_rate": (
            total_violations / total_trials
        ),
        "scenarios": summaries,
        "formal_scope": {
            "base_audit": (
                "fixed independent coin decided before canonical outcome"
            ),
            "drift": "arbitrary error order is allowed",
            "adaptive_extra_audits": (
                "excluded from the formal e-process; diagnostics only"
            ),
            "guarantee": "time-uniform cumulative fast-path error count",
            "simulation_acceptance": (
                "observed violation rate <= alpha; Wilson upper is "
                "diagnostic because the theorem supplies coverage"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
