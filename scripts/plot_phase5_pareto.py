#!/usr/bin/env python3
"""Create the Phase 5 paper-facing workload/energy Pareto figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
    }
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-stem", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cells = payload["phase5c"]["cells"]
    if not cells:
        raise RuntimeError("no workload cells")

    source_root = Path(args.input).parent / "workload_matrix"
    raw = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in source_root.glob("*.json")
    }
    if set(raw) != {row["cell"] for row in cells}:
        raise RuntimeError("summary/raw workload cell mismatch")

    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.85))
    palette = {
        "Qwen3-ASR-0.6B": "#4C78A8",
        "Qwen3-ASR-1.7B": "#E07B39",
    }
    markers = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "s"}

    ax = axes[0]
    for row in cells:
        run = raw[row["cell"]]
        summary = run["summary"]
        color = palette[row["model"]]
        ax.scatter(
            summary["service_energy"]["joules_per_audio_second"],
            summary["deployed_slo_goodput_events_per_second"],
            marker=markers[row["model"]],
            s=32,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            zorder=3,
        )
        ax.scatter(
            summary["canonical_audit_energy"]["joules_per_audio_second"],
            summary["canonical_slo_goodput_events_per_second"],
            marker=markers[row["model"]],
            s=24,
            facecolor="none",
            edgecolor=color,
            linewidth=0.9,
            alpha=0.8,
            zorder=2,
        )
    ax.set_xlabel("Energy (J per processed audio-second)")
    ax.set_ylabel("SLO-compliant goodput (events s$^{-1}$)")
    ax.set_title("a  Energy–goodput frontier", loc="left", fontweight="bold")
    ax.grid(axis="both", color="#E5E7EB", linewidth=0.5, zorder=0)
    ax.text(
        0.02,
        0.98,
        "filled: RevTrace live service\nopen: canonical replay",
        transform=ax.transAxes,
        va="top",
        fontsize=6.3,
        color="#4B5563",
    )

    ax = axes[1]
    energies = [row["joules_per_audio_second"] for row in cells]
    scatter = None
    for model in palette:
        subset = [row for row in cells if row["model"] == model]
        scatter = ax.scatter(
            [row["gpu_normalized_speedup"] for row in subset],
            [row["p99_seconds"] for row in subset],
            c=[row["joules_per_audio_second"] for row in subset],
            cmap="viridis_r",
            vmin=min(energies),
            vmax=max(energies),
            marker=markers[model],
            s=40,
            edgecolors=[
                "#B91C1C" if row["deadline_misses"] else "white"
                for row in subset
            ],
            linewidths=[
                1.2 if row["deadline_misses"] else 0.5
                for row in subset
            ],
            label=model,
            zorder=3,
        )
    ax.axhline(2.0, color="#B91C1C", linestyle="--", linewidth=0.8)
    ax.text(
        0.98,
        2.03,
        "2 s state-entry deadline",
        ha="right",
        va="bottom",
        fontsize=6.2,
        color="#991B1B",
    )
    ax.set_xlabel("GPU-normalized throughput speedup")
    ax.set_ylabel("State-entry P99 (s)")
    ax.set_title("b  Throughput–tail-latency frontier", loc="left", fontweight="bold")
    ax.grid(axis="both", color="#E5E7EB", linewidth=0.5, zorder=0)
    ax.legend(loc="best", fontsize=6.2)
    if scatter is not None:
        colorbar = fig.colorbar(scatter, ax=ax, fraction=0.05, pad=0.03)
        colorbar.set_label("Energy (J/audio-s)")

    fig.text(
        0.01,
        0.01,
        "All points are live two-GPU cells; red outlines denote any measured deadline miss.",
        fontsize=6.1,
        color="#4B5563",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1), w_pad=2.0)
    stem = Path(args.output_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
