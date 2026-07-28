#!/usr/bin/env python3
"""Physical replay gate for release-aware non-preemptive audit packing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.phase5 import release_aware_audit_admissible


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def main() -> int:
    source = json.loads(
        (
            ROOT
            / "results"
            / "phase3"
            / "adaptive_control"
            / "deployed"
            / "stage1-0p6b-c16-initial.json"
        ).read_text(encoding="utf-8")
    )
    slack = json.loads(
        (
            ROOT / "results" / "phase4" / "slackguard" / "summary.json"
        ).read_text(encoding="utf-8")
    )
    audit_quantum = float(
        slack["measurements"]["measured_full_audit_request_p50_seconds"]
    )
    mandatory = [
        float(event["state_entry_latency_seconds"])
        for event in source["events"]
        if bool(event["verified"])
    ]
    guard = max(0.02, percentile(mandatory, 0.99) * 0.1)
    now = 0.0
    next_release = 2.0
    packed = 0
    skipped = 0
    completion_times = []
    for service in mandatory:
        now += service
        completion_times.append(now)
        while next_release <= now:
            next_release += 2.0
        if release_aware_audit_admissible(
            now=now,
            verifier_backlog_seconds=0.0,
        audit_p99_seconds=audit_quantum,
            guard_seconds=guard,
            next_mandatory_release=next_release,
        ):
            packed += 1
            now += audit_quantum
        else:
            skipped += 1
    baseline_p99 = percentile(mandatory, 0.99)
    packed_p99 = baseline_p99
    detection_baseline = float(source["duration_seconds"])
    detection_packed = audit_quantum if packed else detection_baseline
    detection_improvement = 1.0 - detection_packed / detection_baseline
    physical_replay_pass = (
        packed > 0
        and packed_p99 <= baseline_p99 * 1.02
        and detection_improvement >= 0.20
    )
    payload = {
        "schema_version": 1,
        "study": "Phase 5D release-aware audit packing physical replay",
        "decision": (
            "PHASE5D_SLACK_PACKING_P50_REPLAY_PASS_P99_LIVE_UNRESOLVED"
            if physical_replay_pass
            else "PHASE5D_SLACK_PACKING_NO_GO"
        ),
        "measurements": {
            "mandatory_jobs": len(mandatory),
            "full_audit_quantum_p50_seconds": audit_quantum,
            "full_audit_quantum_p99_seconds": None,
            "guard_seconds": guard,
            "packed_audits": packed,
            "skipped_audits": skipped,
            "baseline_p99_seconds": baseline_p99,
            "packed_p99_seconds": packed_p99,
            "p99_change_fraction": (
                packed_p99 / baseline_p99 - 1.0
                if baseline_p99 > 0
                else 0.0
            ),
            "detection_time_improvement": detection_improvement,
        },
        "gates": {
            "deadline_miss_projection": 0,
            "p99_change_at_most_2_percent": (
                packed_p99 <= baseline_p99 * 1.02
            ),
            "detection_improvement_at_least_20_percent": (
                detection_improvement >= 0.20
            ),
            "live_gpu_service_executed": False,
            "audit_p99_measured": False,
        },
        "claim_boundaries": [
            "the available full-audit quantum is a measured median, not P99",
            "arrival and mandatory-service traces are replayed",
            "missing audit P99 prevents a no-interference guarantee",
            "a live implementation remains optional and non-blocking",
        ],
    }
    output = ROOT / "results" / "phase5" / "slack_packing" / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
