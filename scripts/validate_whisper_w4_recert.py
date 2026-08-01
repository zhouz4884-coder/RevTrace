#!/usr/bin/env python3
"""Fail-closed validation for a concrete Whisper W4 recertification artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--max-new-tokens", type=int, required=True)
    args = parser.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    config = result["config"]
    counts = result["counts"]
    selected = policy["selected_policy"]

    assert result["decision"] == "W4_RISK_CERTIFICATE_PASS"
    assert args.model in str(result.get("model", config.get("model", "")))
    assert int(config["concurrency"]) == args.concurrency
    assert int(config["max_new_tokens"]) == args.max_new_tokens
    assert int(config["authority_max_new_tokens"]) == 96
    assert config["policy_source"] == str(args.policy)
    assert config["state_control_protocol"] == (
        "prompt-state-deferred-authority-checkpoint10-capacity-rebase-v2"
    )
    assert config["audit_interference"] == (
        "shadow-canonical-no-state-mutation"
    )
    assert config["work_authority_protocol"] == (
        "decoder-step-saturation-extended-canonical-v1"
    )
    assert config["target_capacity_protocol"] == (
        "target-canonical-declared-work-v1"
    )
    assert int(counts["risk_eligible_entries"]) >= 30_000
    assert int(counts["pre_outcome_randomized_audits"]) >= 500
    assert int(counts["caught_state_errors"]) == 0
    assert int(selected["fast_path_state_errors"]) == 0
    assert float(selected["verification_fraction"]) <= 0.20
    print(json.dumps({
        "decision": "RECERTIFICATION_VALIDATED",
        "result": str(args.result),
        "policy": str(args.policy),
        "risk_eligible_entries": counts["risk_eligible_entries"],
        "audits": counts["pre_outcome_randomized_audits"],
        "caught_state_errors": counts["caught_state_errors"],
        "calibration_verification_fraction": (
            selected["verification_fraction"]
        ),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
