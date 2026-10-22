"""Scoring utilities for diversity-aware revision state-pair mining."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MiningFeatures:
    """Observable features available before an expensive shape probe."""

    minimum_margin: float
    minimum_margin_position: int
    output_length: int
    spectral_flatness: float
    zero_crossing_rate: float
    canonical_signature_count: int = 0


def acoustic_uncertainty(audio: np.ndarray) -> tuple[float, float]:
    """Return bounded spectral-flatness and zero-crossing proxies."""

    values = np.asarray(audio, dtype=np.float64).reshape(-1)
    if values.size < 2:
        return 0.0, 0.0
    windowed = values * np.hanning(values.size)
    power = np.abs(np.fft.rfft(windowed)) ** 2
    positive = power + np.finfo(np.float64).tiny
    flatness = float(
        np.exp(np.mean(np.log(positive))) / np.mean(positive)
    )
    crossings = float(np.mean(np.signbit(values[1:]) != np.signbit(values[:-1])))
    return min(1.0, max(0.0, flatness)), min(
        1.0, max(0.0, crossings)
    )


def active_mining_score(features: MiningFeatures) -> float:
    """Rank likely, novel, consequential numerical state flips.

    This is an acquisition heuristic, not a calibrated probability.  Margin
    drives flip sensitivity, novelty discounts repeated canonical states, and
    an early vulnerable token receives a larger future-damage proxy.
    """

    if features.minimum_margin < 0:
        raise ValueError("minimum margin cannot be negative")
    if features.output_length < 1:
        raise ValueError("output length must be positive")
    if not 0 <= features.minimum_margin_position < features.output_length:
        raise ValueError("minimum margin position is outside the output")
    if features.canonical_signature_count < 0:
        raise ValueError("signature count cannot be negative")
    flip_proxy = 1.0 / max(features.minimum_margin, 1e-4)
    novelty = 1.0 / (1.0 + features.canonical_signature_count)
    remaining = (
        features.output_length - features.minimum_margin_position
    )
    future_damage = 1.0 + remaining / features.output_length
    acoustic = 1.0 + 0.25 * features.spectral_flatness + 0.10 * math.sqrt(
        features.zero_crossing_rate
    )
    return flip_proxy * novelty * future_damage * acoustic
