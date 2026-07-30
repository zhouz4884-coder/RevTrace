#!/usr/bin/env python3
"""Fail-closed validator for the redesigned RevTrace Figures 2--5."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "figures" / "paper"
SOURCE = ROOT / "figures" / "source_data"
FIGURES = [
    "figure2_batching_opportunity_and_state_risk",
    "figure3_deployed_efficiency_and_risk",
    "figure4_contract_adaptation_and_generality",
    "figure5_long_horizon_holdback_closure",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_exports() -> dict[str, object]:
    details: dict[str, object] = {}
    for stem in FIGURES:
        paths = {suffix: FIG_DIR / f"{stem}{suffix}" for suffix in (".svg", ".pdf", ".png", ".tiff")}
        for suffix, path in paths.items():
            require(path.is_file() and path.stat().st_size > 10_000, f"missing/small {suffix}: {path}")

        root = ET.parse(paths[".svg"]).getroot()
        text_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"]
        image_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "image"]
        require(len(text_nodes) >= 35, f"too few editable SVG text nodes: {stem}")
        require(not image_nodes, f"embedded raster image found in SVG: {stem}")

        with Image.open(paths[".png"]) as png:
            png_size = png.size
            png_dpi = png.info.get("dpi", (0, 0))
        with Image.open(paths[".tiff"]) as tiff:
            tiff_size = tiff.size
            tiff_dpi = tiff.info.get("dpi", (0, 0))
        require(min(png_size) >= 1200, f"PNG too small: {stem} {png_size}")
        require(min(png_dpi) >= 295, f"PNG below 300 dpi class: {stem} {png_dpi}")
        require(min(tiff_size) >= 2400, f"TIFF too small: {stem} {tiff_size}")
        require(min(tiff_dpi) >= 590, f"TIFF below 600 dpi class: {stem} {tiff_dpi}")
        require(paths[".pdf"].read_bytes().startswith(b"%PDF"), f"invalid PDF signature: {stem}")
        details[stem] = {
            "png_pixels": list(png_size),
            "png_dpi": [round(float(x), 2) for x in png_dpi],
            "tiff_pixels": list(tiff_size),
            "tiff_dpi": [round(float(x), 2) for x in tiff_dpi],
            "editable_svg_text_nodes": len(text_nodes),
        }
    return details


def validate_layout_qa() -> dict[str, object]:
    qa = json.loads((FIG_DIR / "QA_REPORT_V2.json").read_text(encoding="utf-8"))
    require(qa["decision"] == "PASS", "renderer QA did not pass")
    require(qa["backend"] == "Python/matplotlib only", "backend exclusivity drift")
    require(qa["manual_original_resolution_review"] == "PASS", "manual original-resolution review incomplete")
    require(len(qa["figures"]) == 4, "expected four per-figure QA records")
    for record in qa["figures"]:
        require(record["status"] == "PASS", f"automatic layout audit failed: {record}")
        require(not record["major_text_collisions"], f"major text collisions remain: {record}")
    return qa


def validate_data_contracts() -> dict[str, object]:
    opportunity = pd.read_csv(SOURCE / "figure2_opportunity.csv")
    controls = pd.read_csv(SOURCE / "figure2_same_input_controls.csv")
    reps = pd.read_csv(SOURCE / "figure3_system_replicates.csv")
    risk = pd.read_csv(SOURCE / "figure3_anytime_risk.csv")
    controller = pd.read_csv(SOURCE / "figure4_controller_trajectory.csv")
    frontier = pd.read_csv(SOURCE / "figure4_workload_frontier.csv")
    seeds = pd.read_csv(SOURCE / "figure5_five_seed_latency_energy.csv")
    quality = pd.read_csv(SOURCE / "figure5_quality.csv")
    transitions = pd.read_csv(SOURCE / "figure5_provisional_transitions.csv")

    require(len(opportunity) == 2, "opportunity model count drift")
    require(abs(opportunity["maximum_throughput_speedup"].max() - 11.073377) < 1e-5, "maximum speedup sentinel drift")
    require(controls["mismatches"].tolist() == [0, 4, 17], "same-input control sentinel drift")
    require(reps.groupby("model").size().eq(5).all(), "deployment replicate count drift")
    require((reps["p99_state_entry_seconds"] < 2.0).all(), "deployed replicate violates 2 s SLO")
    require((risk["upper_risk"] < 0.005).all(), "anytime risk exceeds 0.5% budget")
    require(set(controller["stage"]) == {"c16_initial", "c64_drift", "c16_return"}, "controller stage drift")
    require(len(frontier) == 8, "workload frontier must contain eight cells")
    require(len(seeds) == 5 and (seeds["p99_seconds"] < 1.9).all(), "five-seed tail guard failed")
    require((seeds["deadline_miss_events"] == 0).all(), "five-seed deadline miss found")
    require((seeds["online_authority_violations"] == 0).all(), "authority violation found")
    require((quality["catastrophic"] == 0).all(), "catastrophic quality event found")
    require(len(transitions) == 75, "provisional transition count drift")
    return {
        "figure2_models": len(opportunity),
        "maximum_batch_speedup": float(opportunity["maximum_throughput_speedup"].max()),
        "same_input_mismatches": controls["mismatches"].tolist(),
        "deployment_replicates_per_model": reps.groupby("model").size().to_dict(),
        "maximum_anytime_risk": float(risk["upper_risk"].max()),
        "workload_frontier_cells": len(frontier),
        "long_horizon_seeds": len(seeds),
        "provisional_transitions": len(transitions),
    }


def main() -> None:
    report = {
        "decision": "PASS",
        "exports": validate_exports(),
        "layout": validate_layout_qa(),
        "data_contracts": validate_data_contracts(),
    }
    out = FIG_DIR / "VALIDATION_REPORT_V2.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (FIG_DIR / "QA_REPORT.json").write_text(
        json.dumps(
            {
                "decision": report["decision"],
                "renderer": "plot_revtrace_paper_figures_v2.py",
                "validator": "validate_revtrace_paper_figures_v2.py",
                "figures": len(FIGURES),
                "automatic_major_text_collisions": 0,
                "manual_original_resolution_review": "PASS",
                "export_and_data_report": "figures/paper/VALIDATION_REPORT_V2.json",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
