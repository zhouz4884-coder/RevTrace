from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "finalize_whisper_w0_w7.py"
)
SPEC = importlib.util.spec_from_file_location(
    "finalize_whisper_w0_w7", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(name: str, system: str = "revtrace") -> dict:
    return {
        "_path": f"/results/{name}",
        "model": "whisper-base.en",
        "system": system,
    }


def test_formal_matrix_selector_excludes_probe_suffixes() -> None:
    assert MODULE.is_formal_matrix_row(
        row(
            f"base-W1-seed{MODULE.W5_SEED_EPOCH}01-revtrace.json"
        ),
        model="whisper-base.en",
        cell="W1",
        system="revtrace",
    )
    assert not MODULE.is_formal_matrix_row(
        row(
            f"base-W1-seed{MODULE.W5_SEED_EPOCH}01-"
            "revtrace-dual-probe.json"
        ),
        model="whisper-base.en",
        cell="W1",
        system="revtrace",
    )


def test_formal_matrix_selector_requires_numeric_seed() -> None:
    assert not MODULE.is_formal_matrix_row(
        row("base-W1-seedpilot-revtrace.json"),
        model="whisper-base.en",
        cell="W1",
        system="revtrace",
    )


def test_formal_matrix_selector_rejects_excluded_seed_epochs() -> None:
    assert not MODULE.is_formal_matrix_row(
        row("base-W1-seed20260801-revtrace.json"),
        model="whisper-base.en",
        cell="W1",
        system="revtrace",
    )
    assert not MODULE.is_formal_matrix_row(
        row("base-W1-seed20272601-revtrace.json"),
        model="whisper-base.en",
        cell="W1",
        system="revtrace",
    )
    assert not MODULE.is_formal_matrix_row(
        row("base-W3-seed20272841-revtrace.json"),
        model="whisper-base.en",
        cell="W3",
        system="revtrace",
    )


def test_multi_part_risk_requires_one_policy_and_distinct_seeds() -> None:
    def audit(seed: int, digest: str = "a" * 64) -> dict:
        return {
            "config": {
                "policy_sha256": digest,
                "policy_source": "/results/frozen-policy.json",
                "seed": seed,
            }
        }

    assert MODULE.fixed_policy_independent_audit_streams([
        audit(20272700),
        audit(20272750),
    ])
    assert not MODULE.fixed_policy_independent_audit_streams([
        audit(20272700),
        audit(20272700),
    ])
    assert not MODULE.fixed_policy_independent_audit_streams([
        audit(20272700),
        audit(20272750, digest="b" * 64),
    ])
def test_summary_preserves_state_control_fingerprint() -> None:
    workload = {
        "metrics": {
            "wall_speedup": 4.0,
            "gpu_normalized_speedup": 2.0,
                "slo_goodput_speedup": 4.0,
                "display_slo_goodput_speedup": 4.5,
                "latency_p99": 1.0,
                "display_latency_p99": 0.5,
            "energy_reduction": 0.5,
            "verification_fraction": 0.1,
        },
        "counts": {
            "low_margin_authorities": 1,
            "terminal_authorities": 1,
            "checkpoint_authorities": 1,
            "capacity_rebases": 1,
            "state_violations": 0,
            "stale_commits": 0,
                "deadline_misses": 0,
                "display_deadline_misses": 0,
        },
        "config": {
            "sessions": 16,
            "concurrency": 16,
            "margin_threshold": 0.05,
            "late_window_index": None,
            "late_margin_threshold": None,
            "high_load_prompt_tokens": 111,
            "high_load_margin_threshold": 0.0859385,
            "prompt_state_semantics": MODULE.PROMPT_STATE_SEMANTICS,
            "precision": "float16",
            "baseline_capacity_protocol": (
                "declared-work-capacity-rebase-v2"
            ),
            "state_control_protocol": MODULE.STATE_CONTROL_PROTOCOL,
            "work_authority_protocol": MODULE.WORK_AUTHORITY_PROTOCOL,
            "target_capacity_protocol": MODULE.TARGET_CAPACITY_PROTOCOL,
                "post_timing_validation": (
                    "exhaustive-same-state-replay-with-repeat-control-v2"
                ),
                "terminal_contract": "state-only",
        },
    }
    summary = MODULE.summarize_group([workload])
    assert summary["state_control_protocol_values"] == [
        MODULE.STATE_CONTROL_PROTOCOL
    ]
    assert summary["work_authority_protocol_values"] == [
        MODULE.WORK_AUTHORITY_PROTOCOL
    ]
    assert summary["target_capacity_protocol_values"] == [
        MODULE.TARGET_CAPACITY_PROTOCOL
    ]
    assert summary["baseline_capacity_protocol_values"] == [
        "declared-work-capacity-rebase-v2"
    ]
    assert summary["post_timing_validation_values"] == [
        "exhaustive-same-state-replay-with-repeat-control-v2"
    ]
    assert summary["session_count_values"] == [16]
    assert summary["high_load_prompt_tokens_values"] == [111]
    assert summary["high_load_margin_threshold_values"] == [0.0859385]
