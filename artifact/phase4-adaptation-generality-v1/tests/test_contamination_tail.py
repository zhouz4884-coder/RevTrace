from __future__ import annotations

from revtrace.amplification import (
    RevisionImpulsePair,
    summarize_contamination_tail,
)


def test_two_part_tail_summary() -> None:
    pairs = [
        RevisionImpulsePair("a", (2.0, 0.0, 0.0), False),
        RevisionImpulsePair("b", (1.0, 1.0, 1.0), True),
    ]
    summary = summarize_contamination_tail(pairs, horizon=2)
    assert summary.persistent_contamination_mass == 0.5
    assert summary.median_recovery_time_recovered == 1.0
    assert summary.tail_raf == 2.0
