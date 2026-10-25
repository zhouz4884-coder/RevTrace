"""Anytime-valid risk bounds for randomized state-entry audits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping


DEFAULT_LAMBDAS = (
    -20.0,
    -10.0,
    -5.0,
    -2.0,
    -1.0,
    -0.5,
    -0.25,
    -0.1,
    -0.05,
    -0.02,
    -0.01,
)


def _logsumexp(values: Iterable[float]) -> float:
    items = tuple(values)
    maximum = max(items)
    return maximum + math.log(
        sum(math.exp(value - maximum) for value in items)
    )


@dataclass(frozen=True)
class AuditRiskBound:
    """Mixture e-process inversion for a fixed base audit probability.

    Each true unsafe state entry is caught independently with probability
    ``audit_probability``.  If ``M_t`` is the unobserved cumulative unsafe
    count and ``S_t`` is the observed caught-unsafe count, then for every
    negative betting parameter lambda,

        exp(lambda S_t) / (1-p+p exp(lambda))**M_t

    is a nonnegative martingale in the error-event clock.  A fixed mixture is
    therefore an e-process, so Ville's inequality makes its inversion valid at
    arbitrary stopping times and under arbitrary temporal drift in the error
    sequence.
    """

    audit_probability: float
    alpha: float = 0.05
    lambdas: tuple[float, ...] = DEFAULT_LAMBDAS
    leading_weight: float = 0.9

    def __post_init__(self) -> None:
        if not 0.0 < self.audit_probability < 1.0:
            raise ValueError("audit_probability must lie in (0, 1)")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie in (0, 1)")
        if not self.lambdas or any(value >= 0.0 for value in self.lambdas):
            raise ValueError("all betting parameters must be negative")
        if not 0.0 < self.leading_weight <= 1.0:
            raise ValueError("leading_weight must lie in (0, 1]")

    @property
    def log_weights(self) -> tuple[float, ...]:
        if len(self.lambdas) == 1:
            return (0.0,)
        tail_weight = (1.0 - self.leading_weight) / (
            len(self.lambdas) - 1
        )
        if tail_weight == 0.0:
            return (0.0,) + tuple(
                float("-inf") for _ in self.lambdas[1:]
            )
        return (math.log(self.leading_weight),) + tuple(
            math.log(tail_weight) for _ in self.lambdas[1:]
        )

    def log_e_value(self, error_count: int, caught_errors: int) -> float:
        if error_count < caught_errors or caught_errors < 0:
            raise ValueError("counts must satisfy 0 <= caught <= errors")
        p = self.audit_probability
        return _logsumexp(
            log_weight
            + betting_parameter * caught_errors
            - error_count
            * math.log1p(p * (math.exp(betting_parameter) - 1.0))
            for betting_parameter, log_weight in zip(
                self.lambdas, self.log_weights
            )
        )

    def upper_error_count(
        self,
        total_entries: int,
        caught_errors: int,
    ) -> int:
        if total_entries < 0:
            raise ValueError("total_entries cannot be negative")
        if not 0 <= caught_errors <= total_entries:
            raise ValueError("invalid caught error count")
        threshold = math.log(1.0 / self.alpha)
        if self.log_e_value(total_entries, caught_errors) < threshold:
            return total_entries
        low = caught_errors
        high = total_entries
        while low < high:
            middle = (low + high) // 2
            if self.log_e_value(middle, caught_errors) >= threshold:
                high = middle
            else:
                low = middle + 1
        return max(caught_errors, low - 1)

    def upper_risk(
        self,
        total_entries: int,
        caught_errors: int,
    ) -> float:
        if total_entries == 0:
            return 1.0
        return self.upper_error_count(
            total_entries, caught_errors
        ) / total_entries


@dataclass(frozen=True)
class RiskStratum:
    """A frozen fast-path stratum and its independent audit probability."""

    name: str
    lower_margin_exclusive: float
    upper_margin_inclusive: float | None
    audit_probability: float
    alpha_weight: float

    def contains(self, margin: float) -> bool:
        return (
            margin > self.lower_margin_exclusive
            and (
                self.upper_margin_inclusive is None
                or margin <= self.upper_margin_inclusive
            )
        )


@dataclass(frozen=True)
class StratifiedAuditRiskBound:
    """Bonferroni-composed anytime bounds over frozen margin strata.

    The construction deliberately favors a simple, auditable guarantee over
    an aggressive off-policy estimator.  Each stratum owns a fixed audit coin
    and an ``alpha_weight``.  The global upper error count is the sum of
    stratum bounds; simultaneous time-uniform coverage follows from Ville's
    inequality within each stratum and a union bound across strata.
    """

    strata: tuple[RiskStratum, ...]
    alpha: float = 0.05

    def __post_init__(self) -> None:
        if not self.strata:
            raise ValueError("at least one stratum is required")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie in (0,1)")
        weight_sum = sum(item.alpha_weight for item in self.strata)
        if any(item.alpha_weight <= 0.0 for item in self.strata):
            raise ValueError("alpha weights must be positive")
        if weight_sum > 1.0 + 1e-12:
            raise ValueError("alpha weights cannot sum above one")
        previous = float("-inf")
        for item in self.strata:
            if item.lower_margin_exclusive < previous:
                raise ValueError("strata must be ordered")
            if (
                item.upper_margin_inclusive is not None
                and item.upper_margin_inclusive
                <= item.lower_margin_exclusive
            ):
                raise ValueError("invalid stratum interval")
            previous = (
                item.upper_margin_inclusive
                if item.upper_margin_inclusive is not None
                else float("inf")
            )

    def stratum_for(self, margin: float) -> RiskStratum:
        matches = [item for item in self.strata if item.contains(margin)]
        if len(matches) != 1:
            raise ValueError(
                f"margin {margin} belongs to {len(matches)} strata"
            )
        return matches[0]

    def upper_error_count(
        self,
        counts: Mapping[str, tuple[int, int]],
    ) -> int:
        total = 0
        for item in self.strata:
            entries, caught = counts.get(item.name, (0, 0))
            if entries == 0:
                continue
            total += AuditRiskBound(
                item.audit_probability,
                self.alpha * item.alpha_weight,
            ).upper_error_count(entries, caught)
        return total

    def upper_risk(
        self,
        counts: Mapping[str, tuple[int, int]],
    ) -> float:
        entries = sum(value[0] for value in counts.values())
        if entries == 0:
            return 1.0
        return self.upper_error_count(counts) / entries
