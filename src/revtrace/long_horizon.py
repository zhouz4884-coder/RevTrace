"""Long-horizon contract scoping and natural audio composition helpers."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np


def checkpoint_due(age_seconds: int, checkpoint_seconds: int) -> bool:
    """Return whether a positive age is an authoritative checkpoint."""

    if age_seconds <= 0 or checkpoint_seconds < 0:
        raise ValueError("invalid checkpoint age or interval")
    return bool(
        checkpoint_seconds and age_seconds % checkpoint_seconds == 0
    )


def append_checkpoint_history(history: str, segment_text: str) -> str:
    """Append one finalized segment without introducing empty separators."""

    return " ".join(
        part for part in (history.strip(), segment_text.strip()) if part
    )


def checkpoint_payload(
    *,
    prefix: str,
    selected: dict[str, Any],
    selected_projection: dict[str, Any],
) -> str:
    """Return the unique authoritative text stored at a checkpoint.

    A checkpoint is a terminal transition for the current segment.  Its
    payload must therefore be the full terminal state projection, not merely
    the newly generated candidate suffix.
    """

    if not bool(selected_projection.get("terminal")):
        raise ValueError("checkpoint requires a terminal state projection")
    if "text" not in selected or "projection_text" not in selected_projection:
        raise ValueError("checkpoint payload is missing authoritative text")
    expected = (str(prefix) + str(selected["text"])).strip()
    actual = str(selected_projection["projection_text"]).strip()
    if actual != expected:
        raise AssertionError(
            "checkpoint projection mismatch: "
            f"{actual!r} != {expected!r}"
        )
    return actual


def upper_bucket(value: int, *, quantum: int, prefix: str) -> str:
    """Return a stable inclusive upper bucket such as ``age_le_60``."""

    if value < 0 or quantum <= 0 or not prefix:
        raise ValueError("invalid bucket parameters")
    upper = max(quantum, int(math.ceil(value / quantum) * quantum))
    return f"{prefix}_le_{upper}"


def long_horizon_scope(
    *,
    duration_seconds: int,
    maximum_audio_samples: int,
    maximum_prefix_tokens: int,
    maximum_input_tokens: int,
    service_mode: str,
    intermediate_authority: str,
    terminal_authority: str,
    maximum_session_age_seconds: int | None = None,
    checkpoint_seconds: int = 0,
    batch_invariant_runtime_sha256: str | None = None,
) -> dict[str, str]:
    """Build the population fields that prevent 30 s evidence reuse at 120 s."""

    if duration_seconds <= 0:
        raise ValueError("duration must be positive")
    maximum_age = maximum_session_age_seconds or duration_seconds
    scope = {
        "duration": upper_bucket(
            duration_seconds, quantum=30, prefix="duration"
        ),
        "session_age": upper_bucket(
            maximum_age, quantum=30, prefix="age"
        ),
        "audio_samples": upper_bucket(
            maximum_audio_samples,
            quantum=30 * 16_000,
            prefix="audio_samples",
        ),
        "prefix_tokens": upper_bucket(
            maximum_prefix_tokens, quantum=128, prefix="prefix_tokens"
        ),
        "input_tokens": upper_bucket(
            maximum_input_tokens, quantum=512, prefix="input_tokens"
        ),
        "service_mode": service_mode,
        "intermediate_authority": intermediate_authority,
        "terminal_authority": terminal_authority,
        "checkpoint": (
            "none"
            if checkpoint_seconds <= 0
            else f"checkpoint_s_{checkpoint_seconds}"
        ),
    }
    if batch_invariant_runtime_sha256 is not None:
        if len(batch_invariant_runtime_sha256) != 64:
            raise ValueError("runtime SHA-256 must contain 64 hex characters")
        scope["batch_invariant_runtime_sha256"] = (
            batch_invariant_runtime_sha256
        )
    return scope


def concatenate_distinct_audio(
    sources: Sequence[np.ndarray],
    *,
    target_samples: int,
    start_index: int,
    silence_samples: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Concatenate distinct utterances with silence and no sample-level roll.

    The function fails instead of cycling when the available distinct
    utterances cannot fill the requested horizon.
    """

    if target_samples <= 0 or silence_samples < 0:
        raise ValueError("invalid target or silence length")
    if not sources:
        raise ValueError("at least one source utterance is required")
    ordered = [
        np.asarray(sources[(start_index + offset) % len(sources)])
        .astype(np.float32, copy=False)
        .reshape(-1)
        for offset in range(len(sources))
    ]
    pieces: list[np.ndarray] = []
    used = 0
    total = 0
    silence = np.zeros((silence_samples,), dtype=np.float32)
    for source in ordered:
        if source.size == 0:
            continue
        if used and silence_samples:
            pieces.append(silence)
            total += silence_samples
            if total >= target_samples:
                break
        pieces.append(source)
        total += int(source.size)
        used += 1
        if total >= target_samples:
            break
    if total < target_samples:
        raise ValueError(
            "distinct source pool is too short for the requested horizon"
        )
    audio = np.concatenate(pieces)[:target_samples]
    return audio.astype(np.float32, copy=False), {
        "construction": "distinct_utterance_sequence",
        "source_count": used,
        "silence_samples": silence_samples,
        "sample_level_roll": False,
        "source_repetition": False,
    }
