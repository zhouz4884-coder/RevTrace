#!/usr/bin/env python3
"""Fail-closed audit for the RevTrace experimental evidence atlas."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "figures" / "paper"
SOURCE = ROOT / "figures" / "source_data"
STEM = PAPER / "revtrace_results_atlas_candidate"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit_rendered_artifacts() -> dict[str, object]:
    files = {
        suffix: STEM.with_suffix(suffix)
        for suffix in (".svg", ".pdf", ".png", ".tiff")
    }
    for suffix, path in files.items():
        require(path.is_file(), f"missing {suffix} artifact: {path}")
        require(path.stat().st_size > 10_000, f"suspiciously small artifact: {path}")

    with Image.open(files[".png"]) as png:
        png_size = png.size
        png_dpi = png.info.get("dpi", (0, 0))
    with Image.open(files[".tiff"]) as tiff:
        tiff_size = tiff.size
        tiff_dpi = tiff.info.get("dpi", (0, 0))

    require(png_size[0] >= 2000 and png_size[1] >= 2200, f"PNG too small: {png_size}")
    require(min(png_dpi) >= 295, f"PNG dpi below 300-class export: {png_dpi}")
    require(tiff_size[0] >= 4000 and tiff_size[1] >= 4400, f"TIFF too small: {tiff_size}")
    require(min(tiff_dpi) >= 590, f"TIFF dpi below 600-class export: {tiff_dpi}")

    svg = files[".svg"].read_text(encoding="utf-8")
    require("<text" in svg, "SVG text was converted to paths; editability lost")
    require("<image" not in svg, "SVG contains embedded raster images")
    require(svg.count("<text") >= 60, "SVG contains too little editable text")

    pdf_bytes = files[".pdf"].read_bytes()
    require(pdf_bytes.startswith(b"%PDF"), "PDF signature missing")

    return {
        "png_pixels": list(png_size),
        "png_dpi": [round(float(v), 2) for v in png_dpi],
        "tiff_pixels": list(tiff_size),
        "tiff_dpi": [round(float(v), 2) for v in tiff_dpi],
        "svg_text_nodes": svg.count("<text"),
    }


def audit_layout_qa() -> dict[str, object]:
    path = PAPER / "revtrace_results_atlas_QA.json"
    qa = json.loads(path.read_text(encoding="utf-8"))
    require(qa.get("status") == "PASS", f"automatic collision audit failed: {qa}")
    require(
        not qa.get("major_text_collisions"),
        f"major text collisions remain: {qa['major_text_collisions']}",
    )
    require(
        qa.get("manual_original_resolution_review") == "PASS",
        "original-resolution manual review is not closed",
    )
    require(len(qa.get("manual_review_criteria", [])) >= 5, "manual QA criteria incomplete")
    return qa


def audit_source_manifest() -> dict[str, object]:
    manifest_path = SOURCE / "revtrace_results_atlas_manifest.csv"
    manifest = pd.read_csv(manifest_path)
    require(len(manifest) == 12, f"expected 12 source tables, found {len(manifest)}")
    source_paths = [SOURCE / name for name in manifest["source_table"]]
    require(all(path.is_file() for path in source_paths), "manifest contains missing source tables")
    require(
        all(len(pd.read_csv(path)) > 0 for path in source_paths),
        "manifest contains empty source tables",
    )

    frontier = pd.read_csv(SOURCE / "figure4_workload_frontier.csv")
    controller = pd.read_csv(SOURCE / "figure4_controller_trajectory.csv")
    reps = pd.read_csv(SOURCE / "figure3_system_replicates.csv")
    seeds = pd.read_csv(SOURCE / "figure5_five_seed_latency_energy.csv")
    risk = pd.read_csv(SOURCE / "figure3_anytime_risk.csv")

    require(len(frontier) == 8, f"configuration frontier drifted: {len(frontier)} rows")
    require(set(controller["stage"]) == {"c16_initial", "c64_drift", "c16_return"}, "stage drift")
    require(reps.groupby("model").size().eq(5).all(), "deployment replicates must be n=5/model")
    require(len(seeds) == 5, "long-horizon seed audit must contain five seeds")
    require((seeds["p99_seconds"] < 1.9).all(), "a long-horizon seed violates the 1.9 s SLO")
    require(
        (seeds["deadline_miss_events"] == 0).all(),
        "deadline miss found in five-seed closure",
    )
    require(
        (seeds["online_authority_violations"] == 0).all(),
        "authority violation found in five-seed closure",
    )

    upper_cols = [
        col
        for col in risk.columns
        if re.search(r"(risk.*upper|upper.*risk|risk.*ucb|ucb.*risk)", col, re.I)
    ]
    if "upper_risk" in risk.columns:
        upper_cols = ["upper_risk"]
    require(upper_cols, "risk table has no upper-bound column")
    require(
        float(risk[upper_cols[0]].max()) < 0.005,
        f"risk upper bound violates 0.5% budget: {risk[upper_cols[0]].max()}",
    )
    return {
        "source_tables": len(manifest),
        "frontier_cells": len(frontier),
        "controller_stages": len(controller),
        "deployment_replicates": reps.groupby("model").size().to_dict(),
        "long_horizon_seeds": len(seeds),
        "risk_upper_max": float(risk[upper_cols[0]].max()),
    }


def main() -> None:
    report = {
        "decision": "PASS",
        "render": audit_rendered_artifacts(),
        "layout": audit_layout_qa(),
        "data": audit_source_manifest(),
    }
    output = PAPER / "revtrace_results_atlas_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
