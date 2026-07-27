import pytest

from revtrace.risk import (
    AuditRiskBound,
    RiskStratum,
    StratifiedAuditRiskBound,
)


def test_zero_caught_error_target_at_30k() -> None:
    bound = AuditRiskBound(0.021, 0.05)
    assert bound.upper_risk(30_000, 0) <= 0.005


def test_upper_count_is_monotone_in_caught_errors() -> None:
    bound = AuditRiskBound(0.021, 0.05)
    values = [
        bound.upper_error_count(30_000, caught)
        for caught in range(6)
    ]
    assert values == sorted(values)


def test_upper_count_contains_observed_catches() -> None:
    bound = AuditRiskBound(0.1, 0.05)
    assert bound.upper_error_count(100, 7) >= 7


def test_stratified_bound_sums_simultaneous_upper_counts() -> None:
    strata = (
        RiskStratum("near", 0.05, 0.5, 0.1, 0.5),
        RiskStratum("far", 0.5, None, 0.01, 0.5),
    )
    bound = StratifiedAuditRiskBound(strata, alpha=0.05)
    counts = {"near": (1_000, 1), "far": (29_000, 0)}
    expected = sum(
        AuditRiskBound(item.audit_probability, 0.025).upper_error_count(
            *counts[item.name]
        )
        for item in strata
    )
    assert bound.upper_error_count(counts) == expected


def test_stratum_boundaries_are_frozen_and_unique() -> None:
    bound = StratifiedAuditRiskBound(
        (
            RiskStratum("near", 0.05, 0.5, 0.1, 0.5),
            RiskStratum("far", 0.5, None, 0.01, 0.5),
        )
    )
    assert bound.stratum_for(0.5).name == "near"
    assert bound.stratum_for(0.5001).name == "far"
    with pytest.raises(ValueError):
        bound.stratum_for(0.05)
