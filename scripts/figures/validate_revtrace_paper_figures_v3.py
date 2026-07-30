#!/usr/bin/env python3
"""Fail-closed validator for hierarchy-first RevTrace Figures 2--5."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
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
        paths = {
            suffix: FIG_DIR / f"{stem}{suffix}"
            for suffix in (".svg", ".pdf", ".png", ".tiff")
        }
        for suffix, path in paths.items():
            require(
                path.is_file() and path.stat().st_size > 10_000,
                f"missing/small {suffix}: {path}",
            )

        root = ET.parse(paths[".svg"]).getroot()
        text_nodes = [
            node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"
        ]
        image_nodes = [
            node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "image"
        ]
        require(len(text_nodes) >= 55, f"too few editable text nodes: {stem}")
        require(not image_nodes, f"embedded raster image found in SVG: {stem}")

        with Image.open(paths[".png"]) as png:
            png_size = png.size
            png_dpi = png.info.get("dpi", (0, 0))
            rgb = np.asarray(png.convert("RGB"), dtype=np.uint8)
        with Image.open(paths[".tiff"]) as tiff:
            tiff_size = tiff.size
            tiff_dpi = tiff.info.get("dpi", (0, 0))

        # Guard against the evidence-free whitespace seen in the rejected draft.
        nonwhite = np.any(rgb < 247, axis=2)
        dark_ink = np.any(rgb < 215, axis=2)
        nonwhite_fraction = float(nonwhite.mean())
        dark_ink_fraction = float(dark_ink.mean())
        require(nonwhite_fraction >= 0.16, f"insufficient visual occupancy: {stem}")
        require(dark_ink_fraction >= 0.055, f"insufficient information ink: {stem}")
        require(min(png_size) >= 1200, f"PNG too small: {stem} {png_size}")
        require(min(png_dpi) >= 295, f"PNG below 300 dpi class: {stem} {png_dpi}")
        require(min(tiff_size) >= 2400, f"TIFF too small: {stem} {tiff_size}")
        require(min(tiff_dpi) >= 590, f"TIFF below 600 dpi class: {stem} {tiff_dpi}")
        require(paths[".pdf"].read_bytes().startswith(b"%PDF"), f"bad PDF: {stem}")
        details[stem] = {
            "png_pixels": list(png_size),
            "png_dpi": [round(float(x), 2) for x in png_dpi],
            "tiff_pixels": list(tiff_size),
            "tiff_dpi": [round(float(x), 2) for x in tiff_dpi],
            "editable_svg_text_nodes": len(text_nodes),
            "embedded_svg_images": len(image_nodes),
            "nonwhite_fraction": round(nonwhite_fraction, 4),
            "dark_ink_fraction": round(dark_ink_fraction, 4),
        }
    return details


def validate_layout() -> dict[str, object]:
    qa = json.loads((FIG_DIR / "QA_REPORT_V3.json").read_text(encoding="utf-8"))
    require(qa["decision"] == "PASS", "renderer QA did not pass")
    require(qa["backend"] == "Python/matplotlib only", "backend exclusivity drift")
    require(
        qa["manual_original_resolution_review"] == "PASS",
        "original-resolution review is not complete",
    )
    require(len(qa["figures"]) == 4, "expected four figure QA records")
    for record in qa["figures"]:
        require(record["status"] == "PASS", f"layout audit failed: {record}")
        require(
            not record["major_text_collisions"],
            f"major title collision remains: {record}",
        )
    return qa


def validate_data_contracts() -> dict[str, object]:
    opportunity = pd.read_csv(SOURCE / "figure2_opportunity.csv")
    controls = pd.read_csv(SOURCE / "figure2_same_input_controls.csv")
    feedback = pd.read_csv(SOURCE / "figure2_feedback_causality.csv")
    reps = pd.read_csv(SOURCE / "figure3_system_replicates.csv")
    energy = pd.read_csv(SOURCE / "figure3_matched_energy.csv")
    risk = pd.read_csv(SOURCE / "figure3_anytime_risk.csv")
    controller = pd.read_csv(SOURCE / "figure4_controller_trajectory.csv")
    frontier = pd.read_csv(SOURCE / "figure4_workload_frontier.csv")
    generality = pd.read_csv(SOURCE / "figure4_architecture_generality.csv")
    recert = pd.read_csv(SOURCE / "figure4_recertification.csv")
    progression = pd.read_csv(SOURCE / "figure5_mechanism_progression.csv")
    seeds = pd.read_csv(SOURCE / "figure5_five_seed_latency_energy.csv")
    quality = pd.read_csv(SOURCE / "figure5_quality.csv")
    transitions = pd.read_csv(SOURCE / "figure5_provisional_transitions.csv")

    require(abs(opportunity.maximum_throughput_speedup.max() - 11.0733768) < 1e-6, "Fig2 speed sentinel drift")
    require(controls.mismatches.tolist() == [0, 4, 17], "Fig2 control sentinel drift")
    require(feedback.propagating_pairs.tolist() == [8, 0], "Fig2 feedback sentinel drift")
    require(reps.groupby("model").size().eq(5).all(), "Fig3 replicate count drift")
    require((reps.p99_state_entry_seconds < 2.0).all(), "Fig3 SLO drift")
    reduction = 100 * (
        1
        - energy.pivot(index="model", columns="mode", values="joules_per_audio_second")[
            "RevTrace"
        ]
        / energy.pivot(index="model", columns="mode", values="joules_per_audio_second")[
            "All-canonical"
        ]
    )
    require(reduction.min() > 73.0, "Fig3 energy advantage drift")
    require((risk.upper_risk < 0.005).all(), "Fig3 risk budget drift")
    require(len(frontier) == 8, "Fig4 workload frontier cell drift")
    safe = frontier[
        (frontier.deadline_misses == 0) & (frontier.state_violations == 0)
    ]
    require(abs(safe.wall_speedup.max() - 5.20675947) < 1e-6, "Fig4 safe frontier drift")
    require(
        controller.stage.tolist() == ["c16_initial", "c64_drift", "c16_return"],
        "Fig4 controller ordering drift",
    )
    require(recert.events.tolist() == [1358, 64], "Fig4 renewal sentinel drift")
    require(
        generality.family.tolist()
        == ["Qwen3-ASR", "Whisper-feedback", "Voxtral Realtime"],
        "Fig4 generality layer drift",
    )
    whisper = generality.loc[generality.family == "Whisper-feedback"].iloc[0]
    require(
        whisper.feedback_pairs == 21
        and whisper.propagating_on == 8
        and whisper.propagating_off == 0,
        "Whisper causal-transfer sentinel drift",
    )
    require(len(seeds) == 5 and (seeds.p99_seconds < 1.9).all(), "Fig5 seed guard drift")
    require((seeds.deadline_miss_events == 0).all(), "Fig5 deadline miss found")
    require((seeds.online_authority_violations == 0).all(), "Fig5 authority violation found")
    require(abs(progression.iloc[-1].p99_seconds - 1.41381102) < 1e-6, "Fig5 P99 drift")
    require((quality.catastrophic == 0).all(), "Fig5 catastrophic event found")
    require(len(transitions) == 75, "Fig5 transition count drift")

    return {
        "maximum_batch_speedup": float(opportunity.maximum_throughput_speedup.max()),
        "same_input_mismatches": controls.mismatches.tolist(),
        "deployment_replicates_per_model": reps.groupby("model").size().to_dict(),
        "energy_reduction_percent": {
            key: round(float(value), 3) for key, value in reduction.items()
        },
        "maximum_anytime_risk_percent": float(100 * risk.upper_risk.max()),
        "best_joint_contract_speedup": float(safe.wall_speedup.max()),
        "generality_layers": generality.family.tolist(),
        "long_horizon_seed_count": len(seeds),
        "provisional_transition_count": len(transitions),
    }


def main() -> None:
    report = {
        "decision": "PASS",
        "exports": validate_exports(),
        "layout": validate_layout(),
        "data_contracts": validate_data_contracts(),
    }
    out = FIG_DIR / "VALIDATION_REPORT_V3.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (FIG_DIR / "QA_REPORT.json").write_text(
        json.dumps(
            {
                "decision": "PASS",
                "renderer": "plot_revtrace_paper_figures_v3.py",
                "validator": "validate_revtrace_paper_figures_v3.py",
                "figures": len(FIGURES),
                "automatic_major_text_collisions": 0,
                "manual_original_resolution_review": "PASS",
                "export_and_data_report": "figures/paper/VALIDATION_REPORT_V3.json",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
