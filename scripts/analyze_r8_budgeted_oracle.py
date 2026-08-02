#!/usr/bin/env python3
"""Select complete causal R8 views under a conservative recovery budget."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from run_whisper_w_quality import bootstrap_upper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--views", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-energy-reduction", type=float, default=0.40)
    parser.add_argument(
        "--r7-minimum-energy-reduction", type=float,
        default=0.7234878364567467,
    )
    parser.add_argument("--bootstrap-seed", type=int, default=2026081201)
    parser.add_argument("--bootstrap-replicates", type=int, default=10000)
    return parser.parse_args()


def catastrophic(candidate: float, canonical: float) -> bool:
    delta = candidate - canonical
    return delta > 10.0 or (
        candidate > 2.0 * max(canonical, 1.0) and delta > 5.0
    )


def main() -> int:
    args = parse_args()
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    view_payloads = [
        json.loads(path.read_text(encoding="utf-8")) for path in args.views
    ]
    candidates: dict[int, list[dict[str, Any]]] = {}
    for payload in view_payloads:
        for row in payload["rows"]:
            candidates.setdefault(int(row["session_id"]), []).append(row)

    selected: list[dict[str, Any]] = []
    missing: list[int] = []
    total_capsule_seconds = 0.0
    for base in quality["sessions"]:
        sid = int(base["session_id"])
        canonical_wer = float(base["canonical_wer"])
        baseline = {
            "view": "efsc",
            "wer": float(base["efsc_wer"]),
            "catastrophic_outlier": bool(base["catastrophic_outlier"]),
            "capsule_seconds": 0.0,
        }
        options = [baseline, *candidates.get(sid, [])]
        feasible = [
            row for row in options
            if not catastrophic(float(row["wer"]), canonical_wer)
        ]
        if not feasible:
            missing.append(sid)
            choice = min(options, key=lambda row: float(row["wer"]))
        else:
            # First minimize background work; WER breaks equal-cost ties.  This
            # is conservative relative to a window-level reference oracle.
            choice = min(
                feasible,
                key=lambda row: (
                    float(row.get("capsule_seconds", 0.0)),
                    float(row["wer"]),
                ),
            )
        total_capsule_seconds += float(choice.get("capsule_seconds", 0.0))
        selected.append({
            "session_id": sid,
            "split": base["split"],
            "view": choice["view"],
            "canonical_wer": canonical_wer,
            "wer": float(choice["wer"]),
            "delta_pp": float(choice["wer"]) - canonical_wer,
            "catastrophic_outlier": catastrophic(
                float(choice["wer"]), canonical_wer
            ),
            "capsule_seconds": float(choice.get("capsule_seconds", 0.0)),
        })

    deltas = [float(row["delta_pp"]) for row in selected]
    canonical_seconds = float(quality["metrics"]["canonical_seconds"])
    conservative_background_fraction = total_capsule_seconds / canonical_seconds
    estimated_energy_reduction = (
        args.r7_minimum_energy_reduction - conservative_background_fraction
    )
    split_metrics: dict[str, dict[str, float]] = {}
    for split in ("test-clean", "test-other"):
        values = [
            float(row["delta_pp"]) for row in selected if row["split"] == split
        ]
        split_metrics[split] = {
            "mean_delta_pp": statistics.fmean(values),
            "bootstrap_95_upper_pp": bootstrap_upper(
                values,
                seed=args.bootstrap_seed + (0 if split == "test-clean" else 1),
                replicates=args.bootstrap_replicates,
            ),
        }
    catastrophic_count = sum(
        bool(row["catastrophic_outlier"]) for row in selected
    )
    mean_delta = statistics.fmean(deltas)
    upper = bootstrap_upper(
        deltas, seed=args.bootstrap_seed,
        replicates=args.bootstrap_replicates,
    )
    split_pass = all(
        row["mean_delta_pp"] <= 1.0 and row["bootstrap_95_upper_pp"] <= 2.0
        for row in split_metrics.values()
    )
    passed = (
        catastrophic_count == 0
        and not missing
        and mean_delta <= 1.0
        and upper <= 2.0
        and split_pass
        and estimated_energy_reduction >= args.minimum_energy_reduction
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8.1 budgeted causal recovery oracle",
        "decision": "PASS_R8_1_INFORMATION_GATE" if passed else "FAIL_R8_1_INFORMATION_GATE",
        "metrics": {
            "sessions": len(selected),
            "catastrophic_outliers": catastrophic_count,
            "unrepaired_session_ids": missing,
            "mean_delta_pp": mean_delta,
            "bootstrap_95_upper_pp": upper,
            "split_metrics": split_metrics,
            "selected_capsule_seconds": total_capsule_seconds,
            "canonical_seconds": canonical_seconds,
            "conservative_background_work_fraction": conservative_background_fraction,
            "estimated_energy_reduction": estimated_energy_reduction,
        },
        "view_counts": {
            view: sum(row["view"] == view for row in selected)
            for view in sorted({row["view"] for row in selected})
        },
        "rows": selected,
        "claim_boundary": (
            "reference-aware upper bound selecting complete causal session "
            "trajectories; capsule cost is conservatively charged against "
            "the measured all-singleton canonical time"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
