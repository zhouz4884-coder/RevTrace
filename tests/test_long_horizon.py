from __future__ import annotations

import numpy as np
import pytest

from revtrace.long_horizon import (
    append_checkpoint_history,
    checkpoint_due,
    concatenate_distinct_audio,
    long_horizon_scope,
    upper_bucket,
)


def test_checkpoint_helpers_are_explicit_and_monotone() -> None:
    assert checkpoint_due(30, 30)
    assert not checkpoint_due(28, 30)
    assert not checkpoint_due(30, 0)
    assert append_checkpoint_history("", " first ") == "first"
    assert append_checkpoint_history("first", "second") == "first second"


def test_upper_bucket_is_inclusive_and_stable() -> None:
    assert upper_bucket(1, quantum=30, prefix="age") == "age_le_30"
    assert upper_bucket(30, quantum=30, prefix="age") == "age_le_30"
    assert upper_bucket(31, quantum=30, prefix="age") == "age_le_60"


def test_long_horizon_scope_separates_duration_and_authority() -> None:
    short = long_horizon_scope(
        duration_seconds=30,
        maximum_audio_samples=480_000,
        maximum_prefix_tokens=128,
        maximum_input_tokens=4096,
        service_mode="full_selective",
        intermediate_authority="fp16_singleton",
        terminal_authority="fp16_fixed_b12",
    )
    long = long_horizon_scope(
        duration_seconds=120,
        maximum_audio_samples=1_920_000,
        maximum_prefix_tokens=128,
        maximum_input_tokens=4096,
        service_mode="full_selective",
        intermediate_authority="fp16_singleton",
        terminal_authority="fp16_fixed_b12",
    )
    assert short != long
    assert short["duration"] == "duration_le_30"
    assert long["session_age"] == "age_le_120"


def test_checkpoint_scope_bounds_age_without_hiding_total_duration() -> None:
    scoped = long_horizon_scope(
        duration_seconds=120,
        maximum_session_age_seconds=30,
        maximum_audio_samples=480_000,
        maximum_prefix_tokens=512,
        maximum_input_tokens=4096,
        service_mode="full-selective",
        intermediate_authority="fp16_singleton",
        terminal_authority="fp16_fixed_b12",
        checkpoint_seconds=30,
    )
    assert scoped["duration"] == "duration_le_120"
    assert scoped["session_age"] == "age_le_30"
    assert scoped["checkpoint"] == "checkpoint_le_30"


def test_concatenate_distinct_audio_has_no_roll_or_repetition() -> None:
    sources = [
        np.full((4,), 1.0, dtype=np.float32),
        np.full((4,), 2.0, dtype=np.float32),
        np.full((4,), 3.0, dtype=np.float32),
    ]
    audio, provenance = concatenate_distinct_audio(
        sources,
        target_samples=10,
        start_index=1,
        silence_samples=1,
    )
    assert audio.tolist() == [2, 2, 2, 2, 0, 3, 3, 3, 3, 0]
    assert provenance["source_count"] == 2
    assert provenance["sample_level_roll"] is False
    assert provenance["source_repetition"] is False


def test_concatenate_distinct_audio_fails_if_pool_is_too_short() -> None:
    with pytest.raises(ValueError, match="too short"):
        concatenate_distinct_audio(
            [np.ones((3,), dtype=np.float32)],
            target_samples=10,
            start_index=0,
            silence_samples=0,
        )
