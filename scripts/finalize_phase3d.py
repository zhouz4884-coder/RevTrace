#!/usr/bin/env python3
"""Finalize the Phase 3D second-architecture boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result",
        type=Path,
        default=(
            ROOT
            / "results"
            / "phase3"
            / "second_architecture"
            / "voxtral.json"
        ),
    )
    args = parser.parse_args()
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    compatible = payload["decision"] != "PHASE3D_COMPATIBILITY_BLOCKED"
    sufficient = (
        compatible
        and counts.get("revisions", 0) >= 10
        and counts.get("row_evaluations", 0) >= 100
        and counts.get("singleton_repeat_mismatches", 1) == 0
    )
    phase_decision = (
        "PHASE3D_SECOND_ARCHITECTURE_BOUNDARY_PASS"
        if sufficient
        else "PHASE3D_SECOND_ARCHITECTURE_GATE_NOT_MET"
    )
    summary = {
        **payload,
        "phase_decision": phase_decision,
        "gates": {
            "compatible_execution": compatible,
            "minimum_revision_events": (
                counts.get("revisions", 0) >= 10
            ),
            "minimum_execution_rows": (
                counts.get("row_evaluations", 0) >= 100
            ),
            "singleton_repeat_stable": (
                counts.get("singleton_repeat_mismatches", 1) == 0
            ),
        },
    }
    (args.result.parent / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = payload.get("metrics", {})
    input_protocol = payload.get("input_protocol", {})
    report = f"""# RevTrace Phase 3D second-architecture report

Decision: **{phase_decision}**

Architecture: **{payload.get('architecture', 'unavailable')}**

- revisions: {counts.get('revisions', 0)}
- execution rows: {counts.get('row_evaluations', 0)}
- singleton repeat mismatches: {counts.get('singleton_repeat_mismatches', 'n/a')}
- cross-shape mismatches: {counts.get('cross_shape_mismatches', 'n/a')}
- pollution half-life: {metrics.get('pollution_half_life', 'n/a')}
- RAF: {metrics.get('revision_amplification_factor', 'n/a')}
- NSE: {metrics.get('numerical_state_exposure', 'n/a')}
- input tiled to requested duration: {input_protocol.get('tiled_to_duration', 'n/a')}

The second architecture is interpreted through its actual state semantics.
Decoded text is not automatically treated as model-feedback state.  A
growing-prefix Transformers probe is a boundary experiment and is not
presented as vLLM websocket-serving performance.  Zero observed
execution-shape flips is not a deterministic certificate, and a deterministically
tiled public waveform provides revision coverage rather than dataset
generalization.
"""
    (args.result.parent / "REPORT.md").write_text(
        report, encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "decision": phase_decision,
                "gates": summary["gates"],
            }
        )
    )
    return 0 if sufficient else 2


if __name__ == "__main__":
    raise SystemExit(main())
