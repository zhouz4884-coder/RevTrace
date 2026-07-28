#!/usr/bin/env python3
"""Finalize the bounded Phase 3B dual-channel audit result."""

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
        default=ROOT / "results" / "phase3" / "idle_audit" / "replay.json",
    )
    args = parser.parse_args()
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    policies = payload["policies"]
    base = policies["base_only"]
    margin = policies["margin_idle"]
    voi = policies["voi_idle"]
    bounded_pass = payload["gates"][
        "dual_channel_drift_detection_gain"
    ]
    decision = (
        "PHASE3B_BOUNDED_DIAGNOSTIC_PASS_VOI_AND_LIVE_SLO_UNRESOLVED"
        if bounded_pass
        else "PHASE3B_DUAL_CHANNEL_NO_GO"
    )
    summary = {
        **payload,
        "phase_decision": decision,
        "derived": {
            "margin_detection_probability_gain": (
                margin["detection_probability"]
                - base["detection_probability"]
            ),
            "margin_median_verifier_request_reduction": (
                1.0
                - margin["verifier_requests_to_detection_median"]
                / base["verifier_requests_to_detection_median"]
            ),
            "voi_minus_margin_detection_probability": (
                voi["detection_probability"]
                - margin["detection_probability"]
            ),
            "voi_minus_margin_verifier_requests": (
                voi["verifier_requests_to_detection_median"]
                - margin["verifier_requests_to_detection_median"]
            ),
        },
        "unresolved_gates": [
            "live cancellable idle-audit SLO preservation",
            "VOI advantage over margin-only on multiple independent failures",
        ],
    }
    summary_path = args.result.parent / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = f"""# RevTrace Phase 3B dual-channel audit report

Decision: **{decision}**

## Retrospective randomized-label replay

| Strategy | Detection probability | Median verifier requests | Median verifier GPU-s |
|---|---:|---:|---:|
| 2% base only | {base['detection_probability']:.3f} | {base['verifier_requests_to_detection_median']:.0f} | {base['verifier_gpu_seconds_to_detection_median']:.2f} |
| uniform idle | {policies['uniform_idle']['detection_probability']:.3f} | {policies['uniform_idle']['verifier_requests_to_detection_median']:.0f} | {policies['uniform_idle']['verifier_gpu_seconds_to_detection_median']:.2f} |
| margin idle | {margin['detection_probability']:.3f} | {margin['verifier_requests_to_detection_median']:.0f} | {margin['verifier_gpu_seconds_to_detection_median']:.2f} |
| VOI idle | {voi['detection_probability']:.3f} | {voi['verifier_requests_to_detection_median']:.0f} | {voi['verifier_gpu_seconds_to_detection_median']:.2f} |

Margin-prioritized idle auditing increased detection probability by
{summary['derived']['margin_detection_probability_gain']:.3f} and reduced the
median verifier-request count by
{100 * summary['derived']['margin_median_verifier_request_reduction']:.1f}%.

## Negative boundary

VOI did not outperform margin-only: its detection-probability difference was
{summary['derived']['voi_minus_margin_detection_probability']:.3f} and it used
{summary['derived']['voi_minus_margin_verifier_requests']:.0f} more median
verifier requests.  The labelled pool contains two failures but only one unique
failing job.  This supports the dual-channel diagnostic mechanism, not an
amplification-aware VOI superiority claim.

Idle results remain excluded from the formal time-uniform confidence sequence.
The replay uses measured verifier service time but is not a live SLO
experiment; live cancellability and deadline preservation remain unresolved.
"""
    (args.result.parent / "REPORT.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps({"decision": decision, **summary["derived"]}))
    return 0 if bounded_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
