from __future__ import annotations

import math

from scripts.audit_paper_submission import contract_inventory, denominator_audit
from scripts.audit_r9_coverage_replay import legacy_deficit
from revtrace.dgft import cross_granularity_coverage_deficit


def test_legacy_and_cjk_coverage_semantics_are_explicit() -> None:
    assert math.isclose(
        legacy_deficit("alpha beta gamma", "alpha gamma"), 1 / 3
    )
    assert math.isclose(
        cross_granularity_coverage_deficit(
            "alpha beta gamma", "alpha gamma"
        ),
        1 / 3,
    )
    assert legacy_deficit("配置 测试", "配置") == 0.0
    assert cross_granularity_coverage_deficit("配置 测试", "配置") == 0.5


def test_submission_denominator_is_recomputed_from_raw_pairs() -> None:
    audit = denominator_audit()
    assert audit["decision"] == "PASS_PAPER_DENOMINATOR_AUDIT"
    assert audit["counts"] == {
        "legal_pairs": 21,
        "feedback_on_propagating_pairs": 8,
        "feedback_off_propagating_pairs": 0,
        "persistent_pairs": 6,
        "persistent_maximum_raf": 153.0,
    }
    assert not audit["manuscript_scan"]["forbidden_claims"]


def test_submission_contract_inventory_binds_all_evidence_strata() -> None:
    inventory = contract_inventory()
    assert inventory["decision"] == "PASS_PAPER_CONTRACT_INVENTORY"
    assert {group["id"] for group in inventory["groups"]} == {
        "r9e_whisper_service",
        "r10_qwen_service",
        "v100_qwen_scaleout",
        "sg_anytime_risk",
        "qwen_quality",
        "whisper_quality",
    }
    for group in inventory["groups"]:
        assert group["artifacts"]
        assert all(len(item["sha256"]) == 64 for item in group["artifacts"])
