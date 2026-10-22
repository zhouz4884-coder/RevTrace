from __future__ import annotations

import pytest

from revtrace.amplification import (
    RevisionImpulsePair,
    summarize_impulses,
    token_edit_distance,
)


def test_token_edit_distance() -> None:
    assert token_edit_distance([1, 2, 3], [1, 4, 3]) == 1
    assert token_edit_distance([], [1, 2]) == 2
    assert token_edit_distance([1, 2], [1, 2]) == 0


def test_impulse_summary_reports_half_life_and_nse() -> None:
    pairs = [
        RevisionImpulsePair("a", (1.0, 1.0, 0.0), False),
        RevisionImpulsePair("b", (2.0, 1.0, 0.0), False),
        RevisionImpulsePair("c", (1.0, 2.0, 1.0), True),
        RevisionImpulsePair("d", (1.0, 0.0, 0.0), False),
    ]
    summary = summarize_impulses(pairs, flip_rate=0.02)
    assert summary.survival_curve == (1.0, 0.75, 0.25)
    assert summary.pollution_half_life == 2
    assert not summary.half_life_right_censored
    assert summary.terminal_difference_rate == 0.25
    assert summary.numerical_state_exposure == pytest.approx(
        0.02 * summary.mean_raf
    )


def test_no_recovery_is_right_censored_not_infinite() -> None:
    summary = summarize_impulses(
        [
            RevisionImpulsePair("a", (1.0, 1.0, 1.0), True),
            RevisionImpulsePair("b", (1.0, 2.0, 2.0), True),
        ],
        flip_rate=0.01,
    )
    assert summary.pollution_half_life is None
    assert summary.half_life_right_censored
    assert summary.reconverged_fraction == 0.0


def test_survival_uses_right_censored_risk_sets() -> None:
    summary = summarize_impulses(
        [
            RevisionImpulsePair("short-recovery", (1.0, 0.0), False),
            RevisionImpulsePair(
                "short-censored", (1.0, 1.0), True
            ),
            RevisionImpulsePair(
                "long-censored", (1.0, 1.0, 1.0, 1.0), True
            ),
        ],
        flip_rate=0.01,
    )
    assert summary.survival_curve == pytest.approx(
        (1.0, 2 / 3, 2 / 3, 2 / 3)
    )
    assert all(
        left >= right
        for left, right in zip(
            summary.survival_curve,
            summary.survival_curve[1:],
        )
    )
