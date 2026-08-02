from types import SimpleNamespace

import numpy as np
import pytest

from revtrace.long_horizon import (
    assert_provisional_holdback_transition,
    feedback_state_snapshot,
)
from revtrace.whisper_state import (
    WhisperStateRiskPolicy,
    checkpoint_due_for_session,
    paired_slo_goodput_speedup,
)


def test_state_age_frontier_is_local_not_global() -> None:
    policy = WhisperStateRiskPolicy(
        margin_threshold=0.01,
        age_window_index=2,
        age_margin_threshold=0.13,
    )
    assert policy.reason(0.12, window_index=2) == "state-age-margin"
    assert policy.reason(0.12, window_index=1) is None
    assert policy.reason(0.12, window_index=3) is None


def test_window_margin_frontier_is_piecewise_and_local() -> None:
    policy = WhisperStateRiskPolicy(
        margin_threshold=0.01,
        window_margin_rules=((1, 0.07), (5, 0.11), (6, 0.11)),
    )
    assert policy.reason(0.06, window_index=1) == "window-state-margin"
    assert policy.reason(0.10, window_index=5) == "window-state-margin"
    assert policy.reason(0.10, window_index=6) == "window-state-margin"
    assert policy.reason(0.10, window_index=4) is None


def test_window_margin_frontier_rejects_duplicate_windows() -> None:
    with pytest.raises(ValueError, match="unique"):
        WhisperStateRiskPolicy(
            margin_threshold=0.01,
            window_margin_rules=((2, 0.05), (2, 0.06)),
        )


def state() -> SimpleNamespace:
    return SimpleNamespace(
        audio_accum=np.zeros(32, dtype=np.float32),
        buffer=np.zeros(0, dtype=np.float32),
        _raw_decoded="stable",
        text="stable",
        language="English",
        chunk_id=3,
    )


def test_holdback_advances_only_audio_frontier() -> None:
    value = state()
    before = feedback_state_snapshot(value)
    value.audio_accum = np.zeros(64, dtype=np.float32)
    after = feedback_state_snapshot(value)
    assert_provisional_holdback_transition(
        before, after, expected_audio_samples=32
    )


def test_holdback_rejects_textual_feedback_mutation() -> None:
    value = state()
    before = feedback_state_snapshot(value)
    value.audio_accum = np.zeros(64, dtype=np.float32)
    value.chunk_id += 1
    with pytest.raises(AssertionError, match="chunk_id"):
        assert_provisional_holdback_transition(
            before,
            feedback_state_snapshot(value),
            expected_audio_samples=32,
        )


def test_display_goodput_uses_matching_terminal_scope() -> None:
    baseline, method, speedup = paired_slo_goodput_speedup(
        [0.1] * 18,
        18.0,
        [0.1] * 18,
        9.0,
        1.9,
    )
    assert baseline == 1.0
    assert method == 2.0
    assert speedup == 2.0


def test_staggered_checkpoints_preserve_period_without_burst() -> None:
    synchronized = [
        session
        for session in range(8)
        if checkpoint_due_for_session(
            9, session, revisions=10,
            phase_policy="synchronized", terminal=False,
        )
    ]
    staggered_counts = []
    for window in range(10):
        staggered_counts.append(sum(
            checkpoint_due_for_session(
                window, session, revisions=10,
                phase_policy="session-staggered", terminal=False,
                total_nonterminal_revisions=17,
            )
            for session in range(8)
        ))
    assert synchronized == list(range(8))
    assert max(staggered_counts) == 3
    assert sum(staggered_counts) == 8

    # Across the full 17-revision state horizon, every session still receives
    # exactly one checkpoint and no authority age exceeds ten revisions.
    per_session = []
    for session in range(8):
        checkpoints = [
            window + 1
            for window in range(17)
            if checkpoint_due_for_session(
                window,
                session,
                revisions=10,
                phase_policy="session-staggered",
                terminal=False,
                total_nonterminal_revisions=17,
            )
        ]
        assert len(checkpoints) == 1
        gaps = [checkpoints[0], 17 - checkpoints[-1]]
        assert max(gaps) <= 10
        per_session.append(checkpoints)
    assert len(per_session) == 8


def test_staggering_adds_no_checkpoint_for_short_horizon() -> None:
    assert not any(
        checkpoint_due_for_session(
            window,
            session,
            revisions=10,
            phase_policy="session-staggered",
            terminal=False,
            total_nonterminal_revisions=8,
        )
        for window in range(8)
        for session in range(16)
    )
