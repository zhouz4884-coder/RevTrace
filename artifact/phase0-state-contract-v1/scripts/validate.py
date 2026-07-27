#!/usr/bin/env python3
"""Validate frozen RevGuard state-contract results and claim boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.summary.read_text(encoding="utf-8"))

    assert (
        payload["decision"]
        == "LIVE_MECHANISM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED"
    )
    projection = payload["default_bf16_state_projection"]
    assert projection["full_mismatch_events"] == 17
    assert projection["state_projection_mismatch_events"] == 16
    assert projection["rollback_absorbed_mismatch_events"] == 1
    assert len(payload["probes"]) == 16
    assert len(payload["live_runs"]) == 2
    for run in payload["live_runs"]:
        assert run["event_count"] == 240
        assert run["policy_violation_events"] == 0
        assert run["policy_state_projection_violation_events"] == 0
        assert run["verification_fraction"] <= 0.1
        assert run["verifier_to_proposer_service_ratio"] <= 0.8
        assert run["single_gpu_policy_speedup"] >= 2.0
    assert (
        payload["gates"]["deterministic_margin_certificate"]
        == "NOT_ESTABLISHED"
    )
    print("RevGuard state-contract validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
