from types import SimpleNamespace

import numpy as np
import pytest

from revtrace.long_horizon import (
    assert_provisional_holdback_transition,
    feedback_state_snapshot,
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
