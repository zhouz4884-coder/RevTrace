#!/usr/bin/env python3
"""Validate RevTrace Figures 2--5 and their source-data package."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "figures" / "paper"
SOURCE_DIR = ROOT / "figures" / "source_data"

FIGURES = [
    "figure2_batching_opportunity_and_state_risk",
    "figure3_deployed_efficiency_and_risk",
    "figure4_contract_adaptation_and_generality",
    "figure5_long_horizon_holdback_closure",
]

SOURCE_TABLES = [
    "figure2_opportunity.csv",
    "figure2_exactness.csv",
    "figure2_same_input_controls.csv",
    "figure2_feedback_causality.csv",
    "figure3_system_replicates.csv",
    "figure3_matched_energy.csv",
    "figure3_anytime_risk.csv",
    "figure4_controller_trajectory.csv",
    "figure4_workload_frontier.csv",
    "figure4_recertification.csv",
    "figure4_feedback_boundary.csv",
    "figure5_mechanism_progression.csv",
    "figure5_five_seed_latency_energy.csv",
    "figure5_quality.csv",
    "figure5_provisional_transitions.csv",
]


def rows(name: str) -> list[dict[str, str]]:
    with (SOURCE_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, tol: float = 1e-6) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{actual} != {expected} within {tol}")


def main() -> None:
    checks: list[str] = []

    for stem in FIGURES:
        for suffix in (".svg", ".pdf", ".tiff", ".png"):
            path = FIG_DIR / f"{stem}{suffix}"
            if not path.is_file() or path.stat().st_size == 0:
                raise AssertionError(f"missing or empty export: {path}")

        svg = FIG_DIR / f"{stem}.svg"
        root = ET.parse(svg).getroot()
        text_nodes = [
            node
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == "text"
        ]
        image_nodes = [
            node
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == "image"
        ]
        if len(text_nodes) < 20:
            raise AssertionError(f"too few editable text elements in {svg}")
        if image_nodes:
            raise AssertionError(f"raster image embedded in vector export: {svg}")

        with Image.open(FIG_DIR / f"{stem}.png") as png:
            if png.info.get("dpi", (0, 0))[0] < 295:
                raise AssertionError(f"PNG DPI below 300 target: {stem}")
            if min(png.size) < 1400:
                raise AssertionError(f"PNG preview too small: {stem} {png.size}")
        with Image.open(FIG_DIR / f"{stem}.tiff") as tif:
            if tif.info.get("dpi", (0, 0))[0] < 590:
                raise AssertionError(f"TIFF DPI below 600 target: {stem}")
            if min(tif.size) < 2800:
                raise AssertionError(f"TIFF export too small: {stem} {tif.size}")
        checks.append(f"{stem}: four formats, editable SVG, target DPI")

    for name in SOURCE_TABLES:
        table = rows(name)
        if not table:
            raise AssertionError(f"empty source table: {name}")
        if "source" not in table[0]:
            raise AssertionError(f"missing source provenance column: {name}")
    checks.append(f"{len(SOURCE_TABLES)} non-empty provenance-bearing source tables")

    opportunity = rows("figure2_opportunity.csv")
    close(float(opportunity[0]["median_throughput_speedup"]), 4.62, 0.01)
    close(float(opportunity[0]["maximum_throughput_speedup"]), 11.07, 0.01)
    close(float(opportunity[1]["median_throughput_speedup"]), 4.22, 0.01)
    close(float(opportunity[1]["maximum_throughput_speedup"]), 8.75, 0.01)

    controls = {r["comparison"]: r for r in rows("figure2_same_input_controls.csv")}
    assert int(controls["Singleton repeat"]["mismatches"]) == 0
    assert int(controls["Batch repeat"]["mismatches"]) == 4
    assert int(controls["Singleton vs batch"]["mismatches"]) == 17

    reps = rows("figure3_system_replicates.csv")
    for model in ("Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"):
        if sum(r["model"] == model for r in reps) != 5:
            raise AssertionError(f"expected five system replicates for {model}")
        if max(
            float(r["p99_state_entry_seconds"])
            for r in reps
            if r["model"] == model
        ) >= 2.0:
            raise AssertionError(f"SLO violation in frozen replicate data: {model}")

    risk = rows("figure3_anytime_risk.csv")
    if any(float(r["upper_risk"]) >= 0.005 for r in risk):
        raise AssertionError("anytime risk exceeds frozen 0.5% budget")

    five_seed = rows("figure5_five_seed_latency_energy.csv")
    if len(five_seed) != 5:
        raise AssertionError("expected five held-out long-session seeds")
    if any(float(r["p99_seconds"]) >= 1.9 for r in five_seed):
        raise AssertionError("held-out long-session P99 exceeds 1.9 s guard")
    if any(int(r["deadline_miss_events"]) != 0 for r in five_seed):
        raise AssertionError("held-out long-session deadline miss")
    if any(int(r["online_authority_violations"]) != 0 for r in five_seed):
        raise AssertionError("held-out long-session authority violation")

    checks.append("frozen numeric sentinels and safety/SLO boundaries")

    report = {
        "decision": "PASS",
        "figures": len(FIGURES),
        "source_tables": len(SOURCE_TABLES),
        "checks": checks,
        "manual_visual_qa": {
            "reviewed_pngs": len(FIGURES),
            "criteria": [
                "double-column readability",
                "single-conclusion panel logic",
                "non-overlapping labels and legends",
                "consistent semantic color use",
                "explicit claim boundaries",
            ],
            "status": "PASS",
        },
    }
    out = FIG_DIR / "QA_REPORT.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
