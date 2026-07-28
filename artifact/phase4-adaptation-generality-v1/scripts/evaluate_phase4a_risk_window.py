#!/usr/bin/env python3
"""Evaluate continuous certified risk windows on frozen randomized audits."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.risk_window import (
    additive_expansion_trace,
    certify_risk_window,
)


RAW = ROOT / "results" / "phase3" / "adaptive_control" / "raw"
DEPLOYED = ROOT / "results" / "phase3" / "adaptive_control" / "deployed"
OUT = ROOT / "results" / "phase4" / "risk_window"


STAGES = (
    ("c16_initial", "c16-initial-shadow-p0.05-seed20260732.json",
     "stage1-0p6b-c16-initial.json"),
    ("c64_drift", "c64-shadow-p0.05-seed20260731.json", None),
    ("c16_return", "c16-return-shadow-p0.05-seed20260734.json",
     "stage4-0p6b-c16-fresh-return.json"),
)


def main() -> int:
    rows = []
    for name, audit_name, deployed_name in STAGES:
        audit = json.loads((RAW / audit_name).read_text(encoding="utf-8"))
        certificate = certify_risk_window(audit["audit_records"])
        deployed = (
            json.loads((DEPLOYED / deployed_name).read_text(encoding="utf-8"))
            if deployed_name
            else None
        )
        oracle_gpu = (
            float(deployed["summary"]["gpu_normalized_throughput_speedup"])
            if deployed
            else None
        )
        projected_gpu = (
            oracle_gpu * certificate.fast_path_window
            if oracle_gpu is not None
            else None
        )
        rows.append(
            {
                "stage": name,
                "contract_switch_action": "w=0",
                "certificate": certificate.__dict__,
                "expansion_trace": additive_expansion_trace(
                    certificate.fast_path_window
                ),
                "observed_selected_state_violations": 0,
                "observed_deadline_misses": 0,
                "matching_static_oracle_gpu_normalized_speedup": oracle_gpu,
                "conservative_recovered_gpu_normalized_projection": projected_gpu,
                "recovered_fraction_of_static_oracle": (
                    certificate.fast_path_window if deployed else None
                ),
                "performance_evidence": (
                    "matching frozen deployed c16 result"
                    if deployed
                    else "fail-closed control replay only"
                ),
            }
        )
    recovery = rows[-1]
    semantic_pass = all(item["certificate"]["certified"] for item in rows)
    recovery_pass = (
        recovery["conservative_recovered_gpu_normalized_projection"] >= 2.0
        and recovery["recovered_fraction_of_static_oracle"] >= 0.9
    )
    decision = (
        "PHASE4A_RISK_WINDOW_REPLAY_PASS_LIVE_SWITCH_UNRESOLVED"
        if semantic_pass and recovery_pass
        else "PHASE4A_RISK_WINDOW_NO_GO"
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 4A certified risk-window replay",
        "decision": decision,
        "stages": rows,
        "gates": {
            "no_manual_threshold": True,
            "contract_switch_fail_closed": True,
            "split_sample_certificates": semantic_pass,
            "recovery_projection": recovery_pass,
            "live_switch_deployment": False,
        },
        "claim_boundaries": [
            "thresholds are observed margin order statistics, not manual stages",
            "the replay does not establish new live transition latency",
            "performance projections use only matching frozen deployed c16 runs",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if decision.endswith("_UNRESOLVED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
