from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_compiler():
    path = ROOT / "scripts" / "compile_policy_envelope.py"
    spec = importlib.util.spec_from_file_location("policy_envelope", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def payload(*, caught_low_margin: int) -> dict:
    return {
        "study": "test audit",
        "model": "test",
        "config": {"audit_probability": 0.05},
        "margin_strata": {
            "(0.05,0.10]": {
                "entries": 3000,
                "audits": 150,
                "caught_state_errors": caught_low_margin,
            },
            "(0.10,0.20]": {
                "entries": 3000,
                "audits": 150,
                "caught_state_errors": 0,
            },
            "(0.20,0.50]": {
                "entries": 3000,
                "audits": 150,
                "caught_state_errors": 0,
            },
            "(0.50,1.00]": {
                "entries": 3000,
                "audits": 150,
                "caught_state_errors": 0,
            },
            "(1.00,inf)": {
                "entries": 20000,
                "audits": 1000,
                "caught_state_errors": 0,
            },
        },
    }


def compile_case(caught: int):
    module = load_compiler()
    return module.compile_envelope(
        payload(caught_low_margin=caught),
        thresholds=(0.05, 0.10, 0.20, 0.50, 1.0),
        alpha=0.05,
        delta=0.005,
        minimum_audits=500,
        risk_price=1.0,
        queue_price=1.0,
        frozen_caught_margins=(),
    )


def test_simultaneous_envelope_selects_aggressive_safe_policy() -> None:
    result = compile_case(0)
    assert result["decision"] == "ADAPTIVE_POLICY_ENVELOPE_PASS"
    assert result["selected_policy"]["threshold"] == 0.05


def test_low_margin_error_forces_automatic_policy_repair() -> None:
    result = compile_case(1)
    policies = {
        item["threshold"]: item for item in result["policies"]
    }
    assert not policies[0.05]["certified"]
    assert policies[0.10]["certified"]
    assert result["selected_policy"]["threshold"] == 0.10


def test_frozen_failure_cannot_be_diluted_by_fresh_safe_events() -> None:
    module = load_compiler()
    result = module.compile_envelope(
        payload(caught_low_margin=0),
        thresholds=(0.05, 0.10, 0.20, 0.50, 1.0),
        alpha=0.05,
        delta=0.005,
        minimum_audits=500,
        risk_price=1.0,
        queue_price=1.0,
        frozen_caught_margins=(0.078125,),
    )
    policies = {
        item["threshold"]: item for item in result["policies"]
    }
    assert policies[0.05]["frozen_failure_excluded"]
    assert result["selected_policy"]["threshold"] == 0.10
