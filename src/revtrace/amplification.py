"""Revision Impulse Response and Numerical State Exposure metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


def token_edit_distance(left: Sequence[int], right: Sequence[int]) -> int:
    """Levenshtein distance with linear memory."""

    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row, left_token in enumerate(left, start=1):
        current = [row]
        for column, right_token in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1]
                    + int(left_token != right_token),
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class RevisionImpulsePair:
    """One legal state-entry flip followed under identical future inputs."""

    pair_id: str
    distances: tuple[float, ...]
    terminal_different: bool

    def __post_init__(self) -> None:
        if not self.pair_id:
            raise ValueError("pair id must be non-empty")
        if not self.distances or self.distances[0] <= 0:
            raise ValueError("the impulse distance D(0) must be positive")
        if any(value < 0 for value in self.distances):
            raise ValueError("distances cannot be negative")

    def normalized_response(self) -> tuple[float, ...]:
        baseline = self.distances[0]
        return tuple(value / baseline for value in self.distances)

    def reconvergence_time(self) -> int | None:
        for index, value in enumerate(self.distances[1:], start=1):
            if value == 0:
                return index
        return None

    def raf(self, discount: float = 1.0) -> float:
        if not 0.0 < discount <= 1.0:
            raise ValueError("discount must lie in (0,1]")
        return sum(
            discount**index * value
            for index, value in enumerate(self.normalized_response())
        )


@dataclass(frozen=True)
class RevisionImpulseSummary:
    pairs: int
    horizon: int
    survival_curve: tuple[float, ...]
    pollution_half_life: int | None
    half_life_right_censored: bool
    mean_raf: float
    median_raf: float
    terminal_difference_rate: float
    reconverged_fraction: float
    numerical_state_exposure: float

    def to_dict(self) -> dict:
        return asdict(self)


def summarize_impulses(
    pairs: Sequence[RevisionImpulsePair],
    *,
    flip_rate: float,
    discount: float = 1.0,
) -> RevisionImpulseSummary:
    if not pairs:
        raise ValueError("at least one impulse pair is required")
    if not 0.0 <= flip_rate <= 1.0:
        raise ValueError("flip rate must lie in [0,1]")
    horizon = max(len(item.distances) for item in pairs) - 1
    # Kaplan-Meier estimate for the time until the state difference recovers.
    # A trajectory that ends without recovery is right-censored at its final
    # observed offset.  The resulting survival curve must be monotone.
    recovery_times = [item.reconvergence_time() for item in pairs]
    censor_times = [len(item.distances) - 1 for item in pairs]
    survival = [1.0]
    probability = 1.0
    for offset in range(1, horizon + 1):
        at_risk = sum(
            (
                (recovery is None and censor >= offset)
                or (
                    recovery is not None
                    and recovery >= offset
                )
            )
            for recovery, censor in zip(
                recovery_times, censor_times
            )
        )
        events = sum(
            recovery == offset for recovery in recovery_times
        )
        if at_risk:
            probability *= 1.0 - events / at_risk
        survival.append(probability)
    half_life = next(
        (
            offset
            for offset, probability in enumerate(survival)
            if probability <= 0.5
        ),
        None,
    )
    raf_values = sorted(item.raf(discount) for item in pairs)
    middle = len(raf_values) // 2
    median = (
        raf_values[middle]
        if len(raf_values) % 2
        else (raf_values[middle - 1] + raf_values[middle]) / 2
    )
    mean_raf = sum(raf_values) / len(raf_values)
    return RevisionImpulseSummary(
        pairs=len(pairs),
        horizon=horizon,
        survival_curve=tuple(survival),
        pollution_half_life=half_life,
        half_life_right_censored=half_life is None,
        mean_raf=mean_raf,
        median_raf=median,
        terminal_difference_rate=(
            sum(item.terminal_different for item in pairs) / len(pairs)
        ),
        reconverged_fraction=(
            sum(item.reconvergence_time() is not None for item in pairs)
            / len(pairs)
        ),
        numerical_state_exposure=flip_rate * mean_raf,
    )
