from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_qwen_gate_precedes_whisper_performance_and_shares_controller() -> None:
    config = load("configs/revtrace_r7_efsc_gate.json")
    assert config["phases"]["R7.Q0"]["must_complete_before"] == "R7.3"
    thresholds = config["shared_controller"]["threshold_rule"]
    assert thresholds["model_specific_values_allowed"] is True
    assert thresholds["model_specific_control_branches_allowed"] is False
    assert thresholds["type"] == "calibration-derived-hysteresis"


def test_cross_architecture_semantic_artifact_is_not_serving_evidence() -> None:
    row = load("results/r7_efsc/semantic_gate.json")
    assert row["decision"] == "PASS_R7_1_SEMANTICS"
    assert row["not_serving_evidence"] is True
    assert row["shared_action_sequence"] is True
    assert row["qwen_gate_is_mandatory_before_whisper_performance"] is True
    architectures = {item["adapter"]: item for item in row["architectures"]}
    assert set(architectures) == {
        "qwen-rollback-prefix",
        "whisper-previous-text",
    }
    assert all(not item["violations"] for item in architectures.values())
    assert all(item["all_actions_observed"] for item in architectures.values())


def test_authority_headroom_artifact_is_paired_and_source_bound() -> None:
    row = load("results/r7_efsc/authority_lower_bound.json")
    assert row["decision"] == "PASS_X0_HEADROOM_FOR_2_5X"
    assert row["not_efsc_serving_result"] is True
    assert row["scope"] == {
        "arrival": "sync",
        "concurrency": 8,
        "duration_seconds": 180,
        "precision": "float16",
        "seed": 20274001,
        "window_seconds": 10,
    }
    assert row["measured_headroom"]["unprotected_wall_speedup"] >= 2.5
    for source in row["source_files"]:
        path = ROOT / source["path"]
        assert path.exists()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

