#!/usr/bin/env python3
"""Add full offered-load accounting to the real active-16 c64 wave run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    stage = raw["stages"][0]
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from revtrace.phase7_1 import (
        classify_postrun_disagreements,
        guarded_capacity,
    )

    taxonomy = classify_postrun_disagreements(stage)
    episodes = stage["episodes_detail"]
    offered = 64
    active = 16
    audio_per_session = 30.0

    elapsed = 0.0
    admission_latencies: list[float] = []
    end_to_end: list[float] = []
    queue_trace = [{"time_seconds": 0.0, "queued": offered - active, "active": active}]
    for index, episode in enumerate(episodes):
        admission_latencies.extend([elapsed] * active)
        end_to_end.extend(
            [elapsed + float(episode["state_entry_latency_seconds_p99"])] * active
        )
        elapsed += float(episode["wall_seconds"])
        remaining = max(0, offered - active * (index + 2))
        next_active = active if index + 1 < len(episodes) else 0
        queue_trace.append(
            {"time_seconds": elapsed, "queued": remaining, "active": next_active}
        )

    result = {
        "schema_version": 1,
        "study": "Phase 7D full c64 offered-load accounting",
        "measurement": "live two-GPU run; 64 sessions declared at time zero and admitted in four measured active-16 waves",
        "offered_sessions": offered,
        "active_capacity": active,
        "initial_queued_sessions": offered - active,
        "admission_latency_seconds_p50": percentile(admission_latencies, 0.5),
        "admission_latency_seconds_p95": percentile(admission_latencies, 0.95),
        "admission_latency_seconds_p99": percentile(admission_latencies, 0.99),
        "queue_depth_trace": queue_trace,
        "completion_wall_seconds": elapsed,
        "completion_goodput_sessions_per_second": offered / elapsed,
        "completed_audio_seconds": offered * audio_per_session,
        "completed_audio_goodput_per_wall_second": offered * audio_per_session / elapsed,
        "active_state_entry_latency_seconds_p99": stage["state_entry_latency_seconds_p99"],
        "end_to_end_latency_seconds_p99": percentile(end_to_end, 0.99),
        "active_deadline_miss_events": stage["deadline_miss_events"],
        "energy_joules_per_completed_audio_second": stage["energy"]["joules_per_audio_second"],
        "output_violations": stage["output_violations"],
        "state_violations": stage["state_violations"],
        "legacy_field_mapping": (
            "output_violations/state_violations compare selected results with "
            "a later post-run replay; they are not transaction violations"
        ),
        "violation_taxonomy": taxonomy,
        "realized_postrun_state_disagreement_rate": (
            stage["state_violations"] / stage["events"]
        ),
        "formal_time_uniform_risk_bound": None,
        "risk_claim_boundary": (
            "Finite correlated trace only. No iid Clopper-Pearson population "
            "claim and no replacement for the Phase 2 anytime-risk audit."
        ),
        "capacity_contract": guarded_capacity(
            measured_p99_seconds=stage[
                "state_entry_latency_seconds_p99"
            ],
            guard_seconds=0.1,
            deadline_seconds=2.0,
        ),
        "claim_boundary": "Active P99 excludes admission wait; end-to-end P99 includes measured wave admission wait. This is finite-wave overload handling, not unconstrained c64 residency.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
