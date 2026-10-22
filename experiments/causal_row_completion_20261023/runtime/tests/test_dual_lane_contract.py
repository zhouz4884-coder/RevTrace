from __future__ import annotations

import json

import pytest

from scripts.remote.run_phase5a_live_adaptive import (
    validate_burst_b2_artifact,
    validate_cross_lane_artifact,
)


def compatible_payload() -> dict:
    return {
        "decision": "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS",
        "config": {
            "gpu0_engine_logprobs": 20,
            "gpu0_singleton_logprobs": None,
            "gpu1_singleton_logprobs": None,
            "gpu0_batch_invariant_runtime": True,
            "gpu1_batch_invariant_runtime": True,
        },
        "counts": {
            "pairs": 720,
            "token_exact_mismatches": 0,
            "text_exact_mismatches": 0,
            "state_projection_token_exact_mismatches": 0,
            "state_projection_text_exact_mismatches": 0,
        },
        "environment": {
            "batch_invariant_runtime_sha256": "a" * 64,
        },
    }


def compatible_burst_payload() -> dict:
    return {
        "decision": "BURST_B2_AUTHORITY_COMPATIBILITY_PASS",
        "config": {
            "batch_invariant_runtime": True,
            "singleton_shape": 1,
            "burst_fixed_shape": 2,
            "batch_invariant_runtime_sha256": "c" * 64,
        },
        "counts": {
            "pairs": 720,
            "token_exact_mismatches": 0,
            "text_exact_mismatches": 0,
            "state_projection_token_exact_mismatches": 0,
            "state_projection_text_exact_mismatches": 0,
        },
    }


def test_cross_lane_artifact_must_close_every_semantic_gate(tmp_path) -> None:
    path = tmp_path / "cross_lane.json"
    path.write_text(json.dumps(compatible_payload()), encoding="utf-8")
    observed = validate_cross_lane_artifact(path)
    assert observed["counts"]["pairs"] == 720


def test_cross_lane_artifact_fails_closed_on_projection_mismatch(
    tmp_path,
) -> None:
    payload = compatible_payload()
    payload["counts"]["state_projection_token_exact_mismatches"] = 1
    path = tmp_path / "cross_lane.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="semantic mismatch"):
        validate_cross_lane_artifact(path)


def test_cross_lane_artifact_fails_closed_on_runtime_drift(tmp_path) -> None:
    payload = compatible_payload()
    payload["config"]["gpu1_batch_invariant_runtime"] = False
    path = tmp_path / "cross_lane.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        validate_cross_lane_artifact(path)


def test_cross_lane_artifact_binds_runtime_hash(tmp_path) -> None:
    path = tmp_path / "cross_lane.json"
    path.write_text(json.dumps(compatible_payload()), encoding="utf-8")
    observed = validate_cross_lane_artifact(
        path,
        current_runtime_sha256="a" * 64,
    )
    assert observed["environment"]["batch_invariant_runtime_sha256"] == "a" * 64


def test_cross_lane_artifact_fails_closed_on_runtime_hash_drift(
    tmp_path,
) -> None:
    path = tmp_path / "cross_lane.json"
    path.write_text(json.dumps(compatible_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="runtime hash"):
        validate_cross_lane_artifact(
            path,
            current_runtime_sha256="b" * 64,
        )


def test_burst_artifact_closes_b1_b2_gate(tmp_path) -> None:
    path = tmp_path / "burst.json"
    path.write_text(json.dumps(compatible_burst_payload()), encoding="utf-8")
    observed = validate_burst_b2_artifact(
        path,
        current_runtime_sha256="c" * 64,
    )
    assert observed["counts"]["pairs"] == 720


def test_burst_artifact_fails_closed_on_state_mismatch(tmp_path) -> None:
    payload = compatible_burst_payload()
    payload["counts"]["state_projection_text_exact_mismatches"] = 1
    path = tmp_path / "burst.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="semantic mismatch"):
        validate_burst_b2_artifact(path)


def test_burst_artifact_fails_closed_on_runtime_hash_drift(tmp_path) -> None:
    path = tmp_path / "burst.json"
    path.write_text(json.dumps(compatible_burst_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="runtime hash"):
        validate_burst_b2_artifact(
            path,
            current_runtime_sha256="d" * 64,
        )
