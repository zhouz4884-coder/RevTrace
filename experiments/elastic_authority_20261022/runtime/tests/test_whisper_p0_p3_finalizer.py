from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "finalize_whisper_p0_p3.py"
)
SPEC = importlib.util.spec_from_file_location(
    "finalize_whisper_p0_p3", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_c16_headline_survives_disclosed_c8_capacity_boundary() -> None:
    assert MODULE.classify_closure(
        c8_gate=False, c16_w1_gate=True, c16_w2_gate=True
    ) == "P0_P3_HEADLINE_PASS_C8_CAPACITY_BOUNDARY"


def test_c16_replication_failure_is_paper_threatening() -> None:
    assert MODULE.classify_closure(
        c8_gate=True, c16_w1_gate=True, c16_w2_gate=False
    ) == "P0_P3_PAPER_THREATENING_C16_HEADLINE_FAIL"


def test_c16_performance_does_not_mask_failed_risk_contract() -> None:
    assert MODULE.classify_closure(
        c8_gate=False,
        c16_w1_gate=True,
        c16_w2_gate=True,
        c16_risk_gate=False,
    ) == "P0_P3_C16_PERFORMANCE_PASS_RISK_CONTRACT_FAIL"


def test_completed_jsons_excludes_resumable_checkpoints(tmp_path) -> None:
    final = tmp_path / "c16-seed1.json"
    checkpoint = tmp_path / "c16-seed1.checkpoint.json"
    final.write_text("{}", encoding="utf-8")
    checkpoint.write_text("{}", encoding="utf-8")
    assert MODULE.completed_jsons(tmp_path, "c16-*.json") == [final]
