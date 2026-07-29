from __future__ import annotations

from revtrace.risk_window import (
    additive_expansion_trace,
    binomial_upper_bound,
    certify_risk_window,
    zero_error_upper_bound,
)


def test_zero_error_bound_and_continuous_window() -> None:
    records = [
        {
            "job_sha256": f"safe-{index}",
            "minimum_margin": 0.1 + index / 1000,
            "state_error": False,
        }
        for index in range(1400)
    ]
    certificate = certify_risk_window(records)
    assert certificate.certified
    assert certificate.fast_path_window > 0.99
    assert zero_error_upper_bound(700, 0.05) < 0.005


def test_independent_replay_bound_rejects_one_in_720() -> None:
    assert binomial_upper_bound(0, 720) < 0.005
    assert 0.0065 < binomial_upper_bound(1, 720) < 0.0067


def test_caught_error_raises_failure_floor() -> None:
    records = [
        {
            "job_sha256": f"safe-{index}",
            "minimum_margin": 0.2 + index / 1000,
            "state_error": False,
        }
        for index in range(1400)
    ]
    # A past canary failure may set the future window boundary.
    records[100]["job_sha256"] = "caught-calibration"
    records[100]["minimum_margin"] = 0.109375
    records[100]["state_error"] = True
    certificate = certify_risk_window(records)
    assert certificate.certified
    assert certificate.failure_floor == 0.109375
    assert certificate.caught_validation_errors == 0
    assert additive_expansion_trace(certificate.fast_path_window)[0] == 0.0


def test_validation_failure_rejects_without_moving_boundary() -> None:
    records = [
        {
            "job_sha256": f"validation-safe-{index}",
            "minimum_margin": 0.5 + index / 1000,
            "state_error": False,
        }
        for index in range(1400)
    ]
    # A future validation failure must invalidate the certificate instead of
    # becoming a retroactive new threshold.
    records[1000] = {
        "job_sha256": "caught-validation",
        "minimum_margin": 0.9,
        "state_error": True,
    }
    certificate = certify_risk_window(records)
    assert not certificate.certified
    assert certificate.threshold is None
    assert certificate.caught_validation_errors == 1
