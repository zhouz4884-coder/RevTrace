"""Phase 7 reviewer-defense analysis primitives.

This module only transforms frozen experimental evidence.  Counterfactual
performance rows are explicitly tagged as estimates and never promoted to
live-serving measurements.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class GuaranteeRow:
    mechanism: str
    guarantee: str
    prevents_batch_difference: bool
    rejects_stale_or_wrong_epoch: bool
    adaptive_evidence: bool
    joint_risk_slo_admission: bool
    evidence_scope: str


@dataclass(frozen=True)
class MarginGateInspiredRevisionPolicy:
    """Faithful adaptation: per-config margin trigger, no state transaction."""

    threshold: float

    def requires_canonical(self, *, margin: float, terminal: bool) -> bool:
        return terminal or margin <= self.threshold


@dataclass
class OwnerVersionOnlyState:
    """RW-TTT-inspired owner/version commit without numerical certification."""

    owner: str
    version: int = 0

    def commit(self, *, owner: str, parent_version: int) -> bool:
        if owner != self.owner or parent_version != self.version:
            return False
        self.version += 1
        return True


@dataclass(frozen=True)
class LLM42StyleRevisionPolicy:
    """Faithful revision adaptation: canonical-check every feedback edge."""

    def requires_canonical(self, *, terminal: bool) -> bool:
        del terminal
        return True


def minimum_zero_error_samples(delta: float, alpha: float = 0.05) -> int:
    """Minimum zero-error trials whose exact one-sided bound is <= delta."""
    if not 0 < delta < 1 or not 0 < alpha < 1:
        raise ValueError("delta and alpha must lie in (0, 1)")
    return math.ceil(math.log(alpha) / math.log(1.0 - delta))


def one_sided_binomial_upper(
    errors: int, trials: int, alpha: float = 0.05
) -> float:
    """Exact Clopper-Pearson upper endpoint by binomial-CDF bisection."""
    if not 0 <= errors <= trials or trials < 1:
        raise ValueError("invalid error count")
    if errors == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(80):
        p = (low + high) / 2.0
        cdf = sum(
            math.comb(trials, k)
            * p**k
            * (1.0 - p) ** (trials - k)
            for k in range(errors + 1)
        )
        if cdf > alpha:
            low = p
        else:
            high = p
    return high


def failure_floor_threshold(
    failures: Iterable[Mapping[str, object]], epsilon: float = 1e-6
) -> float:
    margins = [
        float(row["minimum_margin"])
        for row in failures
        if bool(row["state_error"])
    ]
    if not margins:
        raise ValueError("a sound failure floor needs at least one failure")
    return max(margins) + epsilon


def evaluate_threshold(
    events: Iterable[Mapping[str, object]], threshold: float
) -> dict[str, object]:
    rows = list(events)
    fast = [r for r in rows if float(r["minimum_margin"]) > threshold]
    unsafe = sum(bool(r["state_error"]) for r in fast)
    verified = sum(
        bool(r.get("terminal", False))
        or float(r["minimum_margin"]) <= threshold
        for r in rows
    )
    return {
        "events": len(rows),
        "fast_path_events": len(fast),
        "unsafe_fast_path_events": unsafe,
        "verification_fraction": verified / len(rows) if rows else 1.0,
    }


def sota_rows() -> list[dict[str, object]]:
    rows = [
        GuaranteeRow("ordinary FP16 batch", "none", False, False, False, False, "live ASR"),
        GuaranteeRow("FP16 singleton canonical", "canonical execution", True, False, False, False, "live ASR"),
        GuaranteeRow("batch-invariant ops / TBIK", "operator arithmetic", True, False, False, False, "source operator/subgraph"),
        GuaranteeRow("LLM-42-style revision", "verify every feedback transition", True, True, False, False, "faithful revision adaptation"),
        GuaranteeRow("MarginGate-inspired revision", "empirical low-margin verification", False, False, False, False, "faithful revision adaptation"),
        GuaranteeRow("owner/version-only state", "single-writer state ownership", False, True, False, False, "faithful RW-TTT adaptation"),
        GuaranteeRow("RevTrace strict", "canonical state transition", True, True, False, True, "live ASR"),
        GuaranteeRow("RevTrace risk-limited", "statistical state-risk contract", False, True, True, True, "live ASR"),
    ]
    return [asdict(row) for row in rows]


def ablation_rows() -> list[dict[str, object]]:
    """Frozen counterexample replay; values are counts, not inferred rates."""
    return [
        {"mechanism": "margin only", "unsafe_certificate_reuse": 1, "known_failure_recurrence": 1, "stale_commit": 2, "joint_slo": False},
        {"mechanism": "+ session version", "unsafe_certificate_reuse": 1, "known_failure_recurrence": 1, "stale_commit": 2, "joint_slo": False},
        {"mechanism": "+ contract epoch fence", "unsafe_certificate_reuse": 1, "known_failure_recurrence": 1, "stale_commit": 0, "joint_slo": False},
        {"mechanism": "+ contextual failure ledger", "unsafe_certificate_reuse": 1, "known_failure_recurrence": 0, "stale_commit": 0, "joint_slo": False},
        {"mechanism": "+ exact-contract renewal", "unsafe_certificate_reuse": 0, "known_failure_recurrence": 0, "stale_commit": 0, "joint_slo": False},
        {"mechanism": "+ joint risk-SLO admission", "unsafe_certificate_reuse": 0, "known_failure_recurrence": 0, "stale_commit": 0, "joint_slo": True},
        {"mechanism": "full RevTrace", "unsafe_certificate_reuse": 0, "known_failure_recurrence": 0, "stale_commit": 0, "joint_slo": True},
    ]
