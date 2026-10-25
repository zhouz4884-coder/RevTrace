from __future__ import annotations

from scripts.remote.run_checkpoint_rebase_quality import (
    hypothesis_distance,
    paired_bootstrap,
)


def test_paired_bootstrap_is_deterministic_and_contains_observed_mean() -> None:
    result = paired_bootstrap(
        [0.01, -0.02, 0.0, 0.03],
        replicates=1000,
        seed=17,
    )
    repeated = paired_bootstrap(
        [0.01, -0.02, 0.0, 0.03],
        replicates=1000,
        seed=17,
    )
    assert result == repeated
    assert result["ci95_low"] <= result["observed_mean_delta"]
    assert result["ci95_high"] >= result["observed_mean_delta"]


def test_checkpoint_boundary_distance_uses_language_units() -> None:
    assert hypothesis_distance("a b c", "a x c", "English") == 1 / 3
    assert hypothesis_distance("你好世界", "你好世", "Chinese") == 1 / 4
