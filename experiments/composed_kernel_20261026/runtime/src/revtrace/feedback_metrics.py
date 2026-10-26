"""Metrics for counterfactual feedback trajectories."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def edit_distance(left: list[int], right: list[int]) -> int:
    previous = list(range(len(right) + 1))
    for row, item in enumerate(left, start=1):
        current = [row]
        for column, other in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + int(item != other),
                )
            )
        previous = current
    return previous[-1]


def repetition_score(text: str) -> float:
    words = text.lower().split()
    if len(words) < 6:
        return 0.0
    trigrams = [
        tuple(words[index : index + 3])
        for index in range(len(words) - 2)
    ]
    return 1.0 - len(set(trigrams)) / len(trigrams)


def pack_disjoint_audio(
    sources: Sequence[np.ndarray],
    *,
    target_samples: int,
    max_sessions: int,
    separator_samples: int = 0,
) -> list[np.ndarray]:
    """Pack source audio into fixed streams without reusing any sample."""

    if target_samples < 1 or max_sessions < 1:
        raise ValueError("target samples and max sessions must be positive")
    if separator_samples < 0:
        raise ValueError("separator length cannot be negative")
    sessions: list[np.ndarray] = []
    current: list[np.ndarray] = []
    current_samples = 0
    separator = np.zeros(separator_samples, dtype=np.float32)
    for source in sources:
        values = np.asarray(source, dtype=np.float32).reshape(-1)
        pieces = (values, separator) if separator_samples else (values,)
        for piece in pieces:
            offset = 0
            while offset < piece.size and len(sessions) < max_sessions:
                take = min(
                    target_samples - current_samples,
                    piece.size - offset,
                )
                current.append(piece[offset : offset + take])
                current_samples += take
                offset += take
                if current_samples == target_samples:
                    sessions.append(np.concatenate(current))
                    current = []
                    current_samples = 0
            if len(sessions) >= max_sessions:
                break
        if len(sessions) >= max_sessions:
            break
    return sessions
