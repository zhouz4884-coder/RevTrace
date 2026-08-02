#!/usr/bin/env python3
"""Quantify the measured authority tax that motivates R7.

The output is a causal attribution over already completed Whisper P1 runs.  It
is not an EFSC serving result and is not extrapolated from c8/180 s to the R7
c16/90 s production cells.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("results/whisper_p0_p3/p1"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/r7_efsc/authority_lower_bound.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = (
        "unprotected",
        "risk-only",
        "checkpoint-only",
        "full-verify",
        "feedback-off",
    )
    paths = {name: args.input_dir / f"{name}.json" for name in names}
    rows = {name: load(path) for name, path in paths.items()}
    reference = rows["unprotected"]["config"]
    for name, row in rows.items():
        config = row["config"]
        for key in (
            "model_path",
            "precision",
            "duration_seconds",
            "concurrency",
            "arrival",
            "seed",
            "window_seconds",
            "max_new_tokens",
        ):
            if config.get(key) != reference.get(key):
                raise AssertionError(f"{name} is not paired on {key}")
        if row["metrics"]["baseline_wall_seconds"] != rows[
            "unprotected"
        ]["metrics"]["baseline_wall_seconds"]:
            raise AssertionError("baseline replay is not paired")

    wall = {name: rows[name]["metrics"]["wall_seconds"] for name in names}
    baseline_wall = rows["unprotected"]["metrics"]["baseline_wall_seconds"]
    no_authority = wall["unprotected"]
    full_tax = wall["full-verify"] - no_authority
    risk_tax = wall["risk-only"] - no_authority
    checkpoint_tax = wall["checkpoint-only"] - no_authority
    interaction = full_tax - risk_tax - checkpoint_tax
    target_wall_25 = baseline_wall / 2.5
    target_wall_27 = baseline_wall / 2.7
    report = {
        "experiment_id": "revtrace-r7-x0-authority-cost-attribution",
        "evidence_tier": "paired real-serving attribution from frozen P1",
        "not_efsc_serving_result": True,
        "scope": {
            key: reference[key]
            for key in (
                "duration_seconds",
                "concurrency",
                "arrival",
                "seed",
                "precision",
                "window_seconds",
            )
        },
        "source_files": [
            {
                "role": name,
                "path": path.as_posix(),
                "sha256": sha256(path),
            }
            for name, path in paths.items()
        ],
        "paired_wall_seconds": wall,
        "baseline_wall_seconds": baseline_wall,
        "authority_tax_seconds": {
            "risk_only_increment": risk_tax,
            "checkpoint_only_increment": checkpoint_tax,
            "full_authority_increment": full_tax,
            "nonadditive_interaction": interaction,
        },
        "measured_headroom": {
            "unprotected_wall_speedup": rows["unprotected"]["metrics"][
                "wall_speedup"
            ],
            "unprotected_energy_reduction": rows["unprotected"]["metrics"][
                "energy_reduction"
            ],
            "feedback_off_wall_speedup": rows["feedback-off"]["metrics"][
                "wall_speedup"
            ],
            "feedback_off_energy_reduction": rows["feedback-off"]["metrics"][
                "energy_reduction"
            ],
            "wall_budget_for_2_5x": target_wall_25,
            "incremental_budget_over_unprotected_for_2_5x": (
                target_wall_25 - no_authority
            ),
            "wall_budget_for_2_7x": target_wall_27,
            "incremental_budget_over_unprotected_for_2_7x": (
                target_wall_27 - no_authority
            ),
        },
        "interpretation": (
            "The paired c8/180 s experiment contains enough measured physical "
            "headroom for a 2.5x authority-free design, but it does not prove "
            "the R7 c16/90 s performance gate. The 2.7x target leaves almost "
            "no overhead relative to the measured unprotected path."
        ),
        "decision": (
            "PASS_X0_HEADROOM_FOR_2_5X"
            if rows["unprotected"]["metrics"]["wall_speedup"] >= 2.5
            else "FAIL_X0_HEADROOM_FOR_2_5X"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(report["decision"] != "PASS_X0_HEADROOM_FOR_2_5X")


if __name__ == "__main__":
    raise SystemExit(main())

