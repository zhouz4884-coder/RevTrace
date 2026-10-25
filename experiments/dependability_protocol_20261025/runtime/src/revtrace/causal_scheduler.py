"""Deterministic virtual-time causal arrival schedules for R9.E."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class SessionArrival:
    session_id: int
    arrival_time: float


def initial_session_arrivals(
    *, sessions: int, arrival: str, scale: float, seed: int
) -> tuple[SessionArrival, ...]:
    """Generate exactly one arrival for each session.

    Poisson arrivals are cumulative exponential inter-arrivals.  The schedule
    is immutable and shared by proposer and authority; it is never regenerated
    for later revision windows.
    """

    if sessions <= 0:
        raise ValueError("sessions must be positive")
    if arrival not in {"sync", "poisson"}:
        raise ValueError("unsupported arrival process")
    if arrival == "sync":
        return tuple(SessionArrival(sid, 0.0) for sid in range(sessions))
    if scale <= 0:
        raise ValueError("Poisson arrival scale must be positive")
    rng = random.Random(seed)
    order = list(range(sessions))
    rng.shuffle(order)
    current = 0.0
    values: list[SessionArrival] = []
    for sid in order:
        current += rng.expovariate(1.0 / scale)
        values.append(SessionArrival(sid, current))
    return tuple(sorted(values, key=lambda row: row.session_id))


def group_ready_events(
    events: list[tuple[int, float]], *, concurrency: int, coalesce: float
) -> list[tuple[list[int], float]]:
    """Group a fixed causal ready stream without modifying release times."""

    ordered = sorted(events, key=lambda row: (row[1], row[0]))
    groups: list[tuple[list[int], float]] = []
    cursor = 0
    while cursor < len(ordered):
        first = ordered[cursor][1]
        selected: list[tuple[int, float]] = []
        while (
            cursor < len(ordered)
            and len(selected) < concurrency
            and ordered[cursor][1] - first <= coalesce
        ):
            selected.append(ordered[cursor])
            cursor += 1
        groups.append(([sid for sid, _ in selected], selected[-1][1]))
    return groups
