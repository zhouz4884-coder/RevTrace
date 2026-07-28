"""Certified fast-path windows for feedback-driven revision serving."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class WindowCertificate:
    threshold: float | None
    fast_path_window: float
    validation_audits: int
    admitted_validation_audits: int
    caught_validation_errors: int
    upper_risk: float
    certified: bool
    failure_floor: float | None


def zero_error_upper_bound(sample_size: int, alpha: float) -> float:
    """One-sided exact binomial upper bound after zero observed errors."""

    if sample_size < 1:
        return 1.0
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0,1)")
    return 1.0 - alpha ** (1.0 / sample_size)


def certify_risk_window(
    records: Iterable[Mapping[str, object]],
    *,
    delta: float = 0.005,
    alpha: float = 0.05,
    calibration_fraction: float = 0.55,
) -> WindowCertificate:
    """Split-sample window selection with a fail-closed failure ledger.

    A preregistered temporal prefix selects the margin boundary; the later
    suffix can only accept or reject it. This models an online controller that
    learns from past canaries and never retroactively changes a boundary after
    observing a certification outcome.
    """

    items = list(records)
    if len(items) < 2:
        return WindowCertificate(None, 0.0, 0, 0, 0, 1.0, False, None)
    if not 0.0 < calibration_fraction < 1.0:
        raise ValueError("calibration_fraction must lie in (0,1)")
    split = max(
        1,
        min(len(items) - 1, int(len(items) * calibration_fraction)),
    )
    calibration = items[:split]
    validation = items[split:]
    if not calibration or not validation:
        return WindowCertificate(None, 0.0, 0, 0, 0, 1.0, False, None)
    caught = [
        float(item["minimum_margin"])
        for item in calibration
        if bool(item["state_error"])
    ]
    failure_floor = max(caught) if caught else None
    threshold = (
        failure_floor
        if failure_floor is not None
        else math.nextafter(
            min(float(item["minimum_margin"]) for item in calibration),
            float("-inf"),
        )
    )
    admitted_validation = [
        item
        for item in validation
        if float(item["minimum_margin"]) > threshold
    ]
    validation_errors = int(sum(
        bool(item["state_error"]) for item in admitted_validation
    ))
    upper = (
        zero_error_upper_bound(len(admitted_validation), alpha)
        if validation_errors == 0
        else 1.0
    )
    window = sum(
        float(item["minimum_margin"]) > threshold for item in items
    ) / len(items)
    certified = bool(admitted_validation) and upper <= delta
    return WindowCertificate(
        threshold=threshold if certified else None,
        fast_path_window=window if certified else 0.0,
        validation_audits=len(validation),
        admitted_validation_audits=len(admitted_validation),
        caught_validation_errors=validation_errors,
        upper_risk=upper,
        certified=certified,
        failure_floor=failure_floor,
    )


def additive_expansion_trace(
    certified_window: float,
    *,
    step: float = 0.1,
) -> tuple[float, ...]:
    """Fail closed, then expand only up to the certified canary window."""

    if not 0.0 <= certified_window <= 1.0 or not 0.0 < step <= 1.0:
        raise ValueError("invalid window or step")
    values = [0.0]
    while values[-1] + step < certified_window:
        values.append(values[-1] + step)
    if values[-1] != certified_window:
        values.append(certified_window)
    return tuple(values)
