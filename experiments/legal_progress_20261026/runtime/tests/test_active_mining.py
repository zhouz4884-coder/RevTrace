from __future__ import annotations

import numpy as np
import pytest

from revtrace.mining import (
    MiningFeatures,
    acoustic_uncertainty,
    active_mining_score,
)


def test_lower_margin_and_novel_state_rank_higher() -> None:
    low = MiningFeatures(0.01, 1, 10, 0.2, 0.1, 0)
    high = MiningFeatures(0.10, 1, 10, 0.2, 0.1, 0)
    duplicate = MiningFeatures(0.01, 1, 10, 0.2, 0.1, 4)
    assert active_mining_score(low) > active_mining_score(high)
    assert active_mining_score(low) > active_mining_score(duplicate)


def test_acoustic_uncertainty_is_bounded() -> None:
    signal = np.sin(np.linspace(0, 20 * np.pi, 32000))
    flatness, crossings = acoustic_uncertainty(signal)
    assert 0 <= flatness <= 1
    assert 0 <= crossings <= 1


def test_invalid_position_fails_closed() -> None:
    with pytest.raises(ValueError):
        active_mining_score(MiningFeatures(0.1, 5, 5, 0.1, 0.1))
