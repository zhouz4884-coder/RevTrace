#!/usr/bin/env python3
"""Physical pre-gate for cancellable live idle auditing."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDLE = ROOT / "results" / "phase3" / "idle_audit" / "summary.json"
DEPLOYED = (
    ROOT
    / "results"
    / "phase3"
    / "adaptive_control"
    / "deployed"
    / "stage1-0p6b-c16-initial.json"
)
OUT = ROOT / "results" / "phase4" / "slackguard"


def main() -> int:
    idle = json.loads(IDLE.read_text(encoding="utf-8"))
    deployed = json.loads(DEPLOYED.read_text(encoding="utf-8"))
    quantum = float(
        idle["config"]["verifier_request_seconds_p50"]
    )
    baseline_p99 = float(
        deployed["summary"]["state_entry_latency_seconds_p99"]
    )
    allowed = baseline_p99 * 0.02
    candidate_gain = 1.0 - (
        idle["policies"]["margin_idle"][
            "candidate_records_to_detection_median"
        ]
        / idle["policies"]["base_only"][
            "candidate_records_to_detection_median"
        ]
    )
    full_request_safe = quantum <= allowed
    payload = {
        "schema_version": 1,
        "study": "Phase 4C SlackGuard physical quantum gate",
        "decision": (
            "PHASE4C_FULL_REQUEST_QUANTUM_PASS"
            if full_request_safe
            else "PHASE4C_FULL_REQUEST_QUANTUM_NO_GO_FINE_GRAINED_UNRESOLVED"
        ),
        "measurements": {
            "baseline_state_entry_p99_seconds": baseline_p99,
            "maximum_two_percent_intrusion_seconds": allowed,
            "measured_full_audit_request_p50_seconds": quantum,
            "quantum_to_intrusion_budget_ratio": quantum / allowed,
            "offline_median_detection_time_improvement": candidate_gain,
        },
        "gates": {
            "offline_detection_improvement_at_least_25_percent": (
                candidate_gain >= 0.25
            ),
            "full_request_quantum_can_bound_p99_to_two_percent": (
                full_request_safe
            ),
            "live_gate_executed": False,
        },
        "root_cause": (
            "CUDA stream priority cannot preempt a running full-request "
            "audit; the measured 309.9 ms request quantum exceeds the "
            "27.5 ms P99 intrusion budget."
        ),
        "legal_repair": (
            "Expose token/block/encoder-decoder checkpoint quanta below the "
            "measured intrusion budget, then rerun the live no-idle versus "
            "SlackGuard SLO gate."
        ),
        "claim_boundaries": [
            "this is a measured physical impossibility gate, not a live SLO result",
            "Phase 3B remains retrospective diagnostic evidence",
            "stream priority is a scheduling hint, not running-kernel preemption",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
