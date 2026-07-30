#!/usr/bin/env python3
"""Build RevTrace paper Figures 2--5 from frozen repository evidence."""

from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "figures" / "paper"
SOURCE = ROOT / "figures" / "source_data"

# Editable text is mandatory for the paper SVG.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7.2
plt.rcParams["axes.labelsize"] = 7.5
plt.rcParams["axes.titlesize"] = 8.2
plt.rcParams["xtick.labelsize"] = 6.8
plt.rcParams["ytick.labelsize"] = 6.8
plt.rcParams["legend.fontsize"] = 6.6
plt.rcParams["axes.linewidth"] = 0.75
plt.rcParams["xtick.major.width"] = 0.7
plt.rcParams["ytick.major.width"] = 0.7
plt.rcParams["xtick.major.size"] = 3
plt.rcParams["ytick.major.size"] = 3
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["legend.frameon"] = False

COL = {
    "navy": "#35456B",
    "blue": "#5577A8",
    "blue_soft": "#B9C9E2",
    "teal": "#4B9B91",
    "teal_soft": "#B9DDD8",
    "coral": "#C55A61",
    "coral_soft": "#F1C8C7",
    "gold": "#D2A84A",
    "ink": "#28313B",
    "mid": "#75808C",
    "light": "#DDE2E7",
    "pale": "#F3F5F7",
    "green": "#4B8B63",
}


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def panel(ax, label: str, title: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="top",
        ha="left",
        color=COL["ink"],
    )
    ax.set_title(title, loc="left", pad=7, fontweight="semibold", color=COL["ink"])
    ax.grid(axis="y", color=COL["light"], lw=0.55, alpha=0.75, zorder=0)
    ax.set_axisbelow(True)


def save_figure(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / name
    svg_path = base.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.03)
    # Matplotlib writes path commands with line-ending spaces. Normalize them
    # so generated vector artifacts remain clean under git diff --check.
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.03)
    raw_tiff = base.with_suffix(".raw.tiff")
    final_tiff = base.with_suffix(".tiff")
    fig.savefig(
        raw_tiff,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.03,
        # Pillow's compressed-TIFF codecs crash in the current Windows runtime,
        # so render a standards-compliant raw TIFF before optional tiffcp LZW.
        pil_kwargs={"compression": "raw"},
    )
    tiffcp = shutil.which("tiffcp")
    if tiffcp:
        packed_tiff = base.with_suffix(".packed.tiff")
        subprocess.run(
            [tiffcp, "-c", "lzw", str(raw_tiff), str(packed_tiff)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        packed_tiff.replace(final_tiff)
        raw_tiff.unlink()
    else:
        raw_tiff.replace(final_tiff)
    fig.savefig(
        base.with_suffix(".png"),
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.03,
        facecolor="white",
    )
    plt.close(fig)


def write_source(name: str, rows: list[dict]) -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"empty source table: {name}")
    keys = list(rows[0])
    with (SOURCE / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mean_ci95(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    mean = float(values.mean())
    if len(values) < 2:
        return mean, 0.0
    # Frozen figures use n=5; t_0.975,4 = 2.776.
    tcrit = 2.776 if len(values) == 5 else 1.96
    half = tcrit * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, half


def figure2_problem() -> None:
    phase0 = load_json("results/phase0/revbatch/revbatch_v1/summary.json")
    revguard = load_json("results/phase0/revguard/revguard_n1/summary.json")
    phase4 = load_json("results/phase4/summary.json")
    models = ["Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"]
    short = ["0.6B", "1.7B"]

    opportunity_rows = []
    exact_rows = []
    for model in models:
        cells = [c for c in phase0["cells"] if c["model"] == model]
        opportunity_rows.append(
            {
                "model": model,
                "median_throughput_speedup": float(
                    np.median([c["audio_throughput_speedup"] for c in cells])
                ),
                "maximum_throughput_speedup": float(
                    max(c["audio_throughput_speedup"] for c in cells)
                ),
                "source": "results/phase0/revbatch/revbatch_v1/summary.json",
            }
        )
        gate = phase0["gate_b"]["models"][model]
        exact_rows.append(
            {
                "model": model,
                "token_exact_percent": 100 * gate["token_exact_match_rate"],
                "partial_exact_percent": 100 * gate["transcript_exact_match_rate"],
                "final_exact_percent": 100 * gate["final_exact_match_rate"],
                "events": gate["event_count"],
                "source": "results/phase0/revbatch/revbatch_v1/summary.json",
            }
        )
    same = revguard["default_bf16_state_projection"]
    control_rows = [
        {
            "comparison": "Singleton repeat",
            "mismatches": 0,
            "events": same["event_count"],
            "source": "results/phase0/revguard/revguard_n1/summary.json",
        },
        {
            "comparison": "Batch repeat",
            "mismatches": 4,
            "events": same["event_count"],
            "source": "docs/reports/revguard_mechanism_gate_report.md",
        },
        {
            "comparison": "Singleton vs batch",
            "mismatches": same["full_mismatch_events"],
            "events": same["event_count"],
            "source": "results/phase0/revguard/revguard_n1/summary.json",
        },
    ]
    whisper = phase4["stages"]["phase4b_whisper_feedback"]
    feedback_rows = [
        {
            "condition": "Feedback on",
            "propagating_pairs": whisper["feedback_on_propagating_pairs"],
            "distinct_pairs": whisper["distinct_pairs"],
            "source": "results/phase4/summary.json",
        },
        {
            "condition": "Feedback off",
            "propagating_pairs": whisper["feedback_off_propagating_pairs"],
            "distinct_pairs": whisper["distinct_pairs"],
            "source": "results/phase4/summary.json",
        },
    ]
    write_source("figure2_opportunity.csv", opportunity_rows)
    write_source("figure2_exactness.csv", exact_rows)
    write_source("figure2_same_input_controls.csv", control_rows)
    write_source("figure2_feedback_causality.csv", feedback_rows)

    fig = plt.figure(figsize=(7.2, 5.05), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 0.95], hspace=0.24, wspace=0.28)
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0])
    axd = fig.add_subplot(gs[1, 1])

    x = np.arange(2)
    width = 0.32
    median = [r["median_throughput_speedup"] for r in opportunity_rows]
    maximum = [r["maximum_throughput_speedup"] for r in opportunity_rows]
    b1 = axa.bar(
        x - width / 2,
        median,
        width,
        color=COL["blue_soft"],
        edgecolor=COL["navy"],
        linewidth=0.8,
        label="Median",
        zorder=3,
    )
    b2 = axa.bar(
        x + width / 2,
        maximum,
        width,
        color=COL["navy"],
        edgecolor=COL["navy"],
        linewidth=0.8,
        label="Maximum",
        zorder=3,
    )
    for bars in (b1, b2):
        for bar in bars:
            axa.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.25,
                f"{bar.get_height():.2f}×",
                ha="center",
                va="bottom",
                fontsize=6.4,
            )
    axa.set_xticks(x, short)
    axa.set_ylim(0, 12.4)
    axa.set_ylabel("Audio-throughput speedup")
    axa.legend(loc="upper right", ncol=2, handlelength=1.2)
    panel(axa, "a", "Batching exposes a large performance opportunity")

    metrics = ["Token", "Partial", "Final"]
    for i, row in enumerate(exact_rows):
        vals = [
            row["token_exact_percent"],
            row["partial_exact_percent"],
            row["final_exact_percent"],
        ]
        axb.plot(
            metrics,
            vals,
            marker="o" if i == 0 else "s",
            ms=5,
            lw=1.8,
            color=[COL["blue"], COL["teal"]][i],
            label=short[i],
            zorder=3,
        )
    axb.axhline(100, color=COL["mid"], ls=(0, (3, 2)), lw=0.9)
    axb.set_ylim(90, 100.8)
    axb.set_ylabel("Exact match (%)")
    axb.legend(loc="lower left")
    panel(axb, "b", "Ordinary batching changes revision semantics")

    names = ["Singleton\nrepeat", "Batch\nrepeat", "Singleton\nvs batch"]
    vals = [r["mismatches"] for r in control_rows]
    bars = axc.bar(
        np.arange(3),
        vals,
        color=[COL["teal_soft"], COL["coral_soft"], COL["coral"]],
        edgecolor=[COL["teal"], COL["coral"], COL["coral"]],
        linewidth=0.9,
        zorder=3,
    )
    for bar, value in zip(bars, vals):
        axc.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.55,
            f"{value}/720",
            ha="center",
            fontsize=6.6,
        )
    axc.set_xticks(np.arange(3), names)
    axc.set_ylabel("Mismatched revision events")
    axc.set_ylim(0, 20.5)
    panel(axc, "c", "Same-input controls isolate execution-shape drift")

    vals = [r["propagating_pairs"] for r in feedback_rows]
    bars = axd.bar(
        [0, 1],
        vals,
        color=[COL["coral"], COL["teal_soft"]],
        edgecolor=[COL["coral"], COL["teal"]],
        linewidth=0.9,
        width=0.58,
        zorder=3,
    )
    for bar, value in zip(bars, vals):
        axd.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.25,
            f"{value}/21",
            ha="center",
            fontsize=7,
            fontweight="semibold",
        )
    axd.set_xticks([0, 1], ["Previous text\nfed back", "Feedback\ndisabled"])
    axd.set_ylabel("Pairs propagating to future state")
    axd.set_ylim(0, 9.5)
    panel(axd, "d", "Feedback is the causal propagation edge")

    save_figure(fig, "figure2_batching_opportunity_and_state_risk")


def figure3_system() -> None:
    reps = pd.read_csv(ROOT / "results/phase2/system_replicates.csv")
    risk = pd.read_csv(ROOT / "results/phase2/risk_v1/risk_metrics.csv")
    energy = load_json("results/final_closure/energy/summary.json")["rows"]
    models = ["Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"]
    short = ["0.6B", "1.7B"]

    write_source(
        "figure3_system_replicates.csv",
        reps.assign(source="results/phase2/system_replicates.csv").to_dict("records"),
    )
    energy_rows = []
    for row in energy:
        energy_rows.extend(
            [
                {
                    "model": row["model"],
                    "mode": "RevTrace",
                    "joules_per_audio_second": row[
                        "revtrace_joules_per_audio_second"
                    ]["mean"],
                    "std": row["revtrace_joules_per_audio_second"]["std"],
                    "replicates": row["replicates"],
                    "source": "results/final_closure/energy/summary.json",
                },
                {
                    "model": row["model"],
                    "mode": "All-canonical",
                    "joules_per_audio_second": row[
                        "all_canonical_joules_per_audio_second"
                    ]["mean"],
                    "std": row["all_canonical_joules_per_audio_second"]["std"],
                    "replicates": row["replicates"],
                    "source": "results/final_closure/energy/summary.json",
                },
            ]
        )
    write_source("figure3_matched_energy.csv", energy_rows)
    write_source(
        "figure3_anytime_risk.csv",
        risk.assign(source="results/phase2/risk_v1/risk_metrics.csv").to_dict(
            "records"
        ),
    )

    fig = plt.figure(figsize=(7.2, 5.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, hspace=0.22, wspace=0.30)
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0])
    axd = fig.add_subplot(gs[1, 1])

    jitter = np.array([-0.06, -0.03, 0.0, 0.03, 0.06])
    for i, model in enumerate(models):
        vals = reps.loc[reps.model == model, "wall_speedup"].to_numpy()
        mean, half = mean_ci95(vals)
        color = [COL["blue"], COL["teal"]][i]
        axa.scatter(
            np.full(len(vals), i) + jitter,
            vals,
            s=22,
            facecolor="white",
            edgecolor=color,
            lw=1,
            zorder=4,
        )
        axa.errorbar(
            i,
            mean,
            yerr=half,
            fmt="D",
            ms=5,
            color=color,
            capsize=4,
            lw=1.5,
            zorder=5,
        )
        axa.text(i, mean + half + 0.08, f"{mean:.2f}×", ha="center", fontsize=7)
    axa.axhline(1, color=COL["mid"], ls=(0, (3, 2)), lw=0.9)
    axa.set_xticks([0, 1], short)
    axa.set_ylabel("Two-GPU wall-clock speedup")
    axa.set_ylim(0.7, 6.55)
    axa.text(
        0.03,
        0.03,
        "open circles: independent runs\nfilled marker: mean ± 95% t interval",
        transform=axa.transAxes,
        color=COL["mid"],
        fontsize=6.3,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.2},
    )
    panel(axa, "a", "Replicated deployed speedup")

    for i, model in enumerate(models):
        vals = reps.loc[reps.model == model, "p99_state_entry_seconds"].to_numpy()
        axb.plot(
            np.arange(1, len(vals) + 1),
            vals,
            marker="o" if i == 0 else "s",
            ms=4,
            lw=1.5,
            color=[COL["blue"], COL["teal"]][i],
            label=short[i],
            zorder=3,
        )
    axb.axhspan(0, 2, color=COL["teal_soft"], alpha=0.18, zorder=-2)
    axb.axhline(2, color=COL["coral"], ls=(0, (4, 2)), lw=1.1)
    axb.text(5.05, 2.02, "2 s SLO", ha="right", va="bottom", color=COL["coral"])
    axb.set_xticks(range(1, 6))
    axb.set_xlabel("Independent run")
    axb.set_ylabel("State-entry P99 (s)")
    axb.set_ylim(1.15, 2.12)
    axb.legend(loc="upper center", ncol=2)
    panel(axb, "b", "Tail latency stays within the 2 s SLO")

    x = np.arange(2)
    w = 0.32
    rev = [r for r in energy_rows if r["mode"] == "RevTrace"]
    can = [r for r in energy_rows if r["mode"] == "All-canonical"]
    b1 = axc.bar(
        x - w / 2,
        [r["joules_per_audio_second"] for r in rev],
        w,
        yerr=[r["std"] for r in rev],
        capsize=2,
        color=COL["teal"],
        label="RevTrace",
        zorder=3,
    )
    b2 = axc.bar(
        x + w / 2,
        [r["joules_per_audio_second"] for r in can],
        w,
        yerr=[r["std"] for r in can],
        capsize=2,
        color=COL["light"],
        edgecolor=COL["mid"],
        linewidth=0.7,
        label="All-canonical",
        zorder=3,
    )
    for i in range(2):
        reduction = 100 * (
            1
            - rev[i]["joules_per_audio_second"] / can[i]["joules_per_audio_second"]
        )
        axc.text(i, can[i]["joules_per_audio_second"] + 1.1, f"−{reduction:.1f}%", ha="center")
    axc.set_xticks(x, short)
    axc.set_ylabel("Energy (J/audio-s)")
    axc.set_ylim(0, 36)
    axc.legend(loc="upper left", handlelength=1.1)
    panel(axc, "c", "Energy drops under matched two-GPU resources")

    vals = 100 * risk["upper_risk"].to_numpy()
    bars = axd.bar(
        [0, 1],
        vals,
        width=0.58,
        color=[COL["blue"], COL["teal"]],
        zorder=3,
    )
    axd.axhline(0.5, color=COL["coral"], ls=(0, (4, 2)), lw=1.1)
    axd.text(1.46, 0.505, "0.5% budget", ha="right", va="bottom", color=COL["coral"])
    for bar, value in zip(bars, vals):
        axd.text(
            bar.get_x() + bar.get_width() / 2,
            value - 0.035,
            f"{value:.3f}%",
            ha="center",
            color="white",
            fontsize=6.6,
            fontweight="semibold",
        )
    axd.set_xticks([0, 1], short)
    axd.set_ylabel("Anytime state-risk upper bound")
    axd.set_ylim(0, 0.56)
    panel(axd, "d", "Risk stays below the frozen budget")

    save_figure(fig, "figure3_deployed_efficiency_and_risk")


def figure4_adaptation() -> None:
    phase5 = load_json("results/phase5/summary.json")
    phase6 = load_json("results/phase6/summary.json")
    phase4 = load_json("results/phase4/summary.json")
    stages = phase5["phase5a"]["stages"]
    cells = phase5["phase5c"]["cells"]
    whisper = phase4["stages"]["phase4b_whisper_feedback"]

    stage_rows = []
    for stage in stages:
        stage_rows.append(
            {
                "stage": stage["label"],
                "concurrency": stage["concurrency"],
                "learned_threshold": stage["threshold"],
                "risk_upper_percent": 100 * stage["risk_upper_bound"],
                "p99_seconds": stage["state_entry_latency_seconds_p99"],
                "deadline_misses": stage["deadline_miss_events"],
                "goodput_events_per_second": stage["goodput_events_per_second"],
                "source": "results/phase5/summary.json",
            }
        )
    write_source("figure4_controller_trajectory.csv", stage_rows)
    write_source(
        "figure4_workload_frontier.csv",
        [
            {
                **{
                    k: c[k]
                    for k in [
                        "cell",
                        "model",
                        "concurrency",
                        "duration_seconds",
                        "arrival_mode",
                        "wall_speedup",
                        "gpu_normalized_speedup",
                        "p99_seconds",
                        "deadline_misses",
                        "state_violations",
                        "joules_per_audio_second",
                    ]
                },
                "source": "results/phase5/summary.json",
            }
            for c in cells
        ],
    )
    recert_rows = [
        {
            "method": "Flat relearning",
            "events": 1358,
            "source": "results/phase6/summary.json",
        },
        {
            "method": "Exact-contract renewal",
            "events": 64,
            "source": "results/phase6/summary.json",
        },
    ]
    write_source("figure4_recertification.csv", recert_rows)
    feedback_rows = [
        {
            "condition": "Feedback on",
            "propagating_pairs": whisper["feedback_on_propagating_pairs"],
            "total_pairs": whisper["distinct_pairs"],
            "source": "results/phase4/summary.json",
        },
        {
            "condition": "Feedback off",
            "propagating_pairs": whisper["feedback_off_propagating_pairs"],
            "total_pairs": whisper["distinct_pairs"],
            "source": "results/phase4/summary.json",
        },
    ]
    write_source("figure4_feedback_boundary.csv", feedback_rows)

    fig = plt.figure(figsize=(7.2, 5.15), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.25, 1.0, 0.9], hspace=0.26, wspace=0.35)
    axa = fig.add_subplot(gs[0, :2])
    axb = fig.add_subplot(gs[1, :2])
    axc = fig.add_subplot(gs[0, 2])
    axd = fig.add_subplot(gs[1, 2])

    x = np.arange(3)
    p99 = [r["p99_seconds"] for r in stage_rows]
    colors = [COL["teal"], COL["coral"], COL["teal"]]
    bars = axa.bar(x, p99, width=0.58, color=colors, alpha=0.9, zorder=3)
    axa.axhline(2, color=COL["coral"], ls=(0, (4, 2)), lw=1)
    axa.set_xticks(x, ["c16 initial", "c64 drift", "c16 return"])
    axa.set_ylabel("State-entry P99 (s)")
    axa.set_ylim(0, 3.25)
    for i, (bar, row) in enumerate(zip(bars, stage_rows)):
        axa.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.08,
            f"τ={row['learned_threshold']:.5f}\nUCB={row['risk_upper_percent']:.3f}%",
            ha="center",
            va="bottom",
            fontsize=6.2,
        )
    axa.text(2.45, 2.03, "2 s SLO", ha="right", va="bottom", color=COL["coral"])
    panel(axa, "a", "A contract switch invalidates and relearns evidence")

    for i, cell in enumerate(cells):
        safe = cell["state_violations"] == 0
        slo = cell["deadline_misses"] == 0
        marker = "o" if safe else "X"
        edge = COL["green"] if slo and safe else COL["coral"]
        face = COL["blue"] if "0.6B" in cell["model"] else COL["teal"]
        axb.scatter(
            cell["wall_speedup"],
            cell["p99_seconds"],
            s=32 + 2.0 * cell["concurrency"],
            marker=marker,
            facecolor=face if safe else COL["coral"],
            edgecolor=edge,
            linewidth=1.1,
            alpha=0.9,
            zorder=4,
        )
        axb.text(
            cell["wall_speedup"] + 0.05,
            cell["p99_seconds"] + 0.08,
            f"c{cell['concurrency']}/{cell['duration_seconds']}s",
            fontsize=5.6,
            color=COL["mid"],
        )
    axb.axhline(2, color=COL["coral"], ls=(0, (4, 2)), lw=1)
    axb.axhspan(0, 2, color=COL["teal_soft"], alpha=0.12)
    axb.set_xlabel("Wall-clock speedup")
    axb.set_ylabel("State-entry P99 (s)")
    axb.set_xlim(2.65, 7.2)
    axb.set_ylim(0.9, 6.1)
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["blue"], markeredgecolor=COL["green"], label="safe + SLO pass"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["teal"], markeredgecolor=COL["coral"], label="deadline boundary"),
        Line2D([0], [0], marker="X", color="none", markerfacecolor=COL["coral"], markeredgecolor=COL["coral"], label="state boundary"),
    ]
    axb.legend(handles=handles, loc="upper left", ncol=1)
    panel(axb, "b", "The workload frontier separates speed, safety and SLO")

    vals = [r["events"] for r in recert_rows]
    bars = axc.bar(
        [0, 1],
        vals,
        color=[COL["light"], COL["teal"]],
        edgecolor=[COL["mid"], COL["teal"]],
        width=0.6,
        zorder=3,
    )
    for bar, value in zip(bars, vals):
        axc.text(bar.get_x() + bar.get_width() / 2, value + 40, f"{value:,}", ha="center")
    axc.text(0.5, 760, "−95.29%", ha="center", color=COL["green"], fontweight="bold")
    axc.set_xticks([0, 1], ["Flat\nrelearn", "Exact\nrenewal"])
    axc.set_ylabel("Events to restore certificate")
    axc.set_ylim(0, 1540)
    panel(axc, "c", "Exact-contract renewal")

    vals = [r["propagating_pairs"] for r in feedback_rows]
    bars = axd.bar(
        [0, 1],
        vals,
        color=[COL["coral"], COL["teal_soft"]],
        edgecolor=[COL["coral"], COL["teal"]],
        width=0.6,
        zorder=3,
    )
    for bar, value in zip(bars, vals):
        axd.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.25,
            f"{value}/21",
            ha="center",
            fontweight="semibold",
        )
    axd.set_xticks([0, 1], ["Feedback\non", "Feedback\noff"])
    axd.set_ylabel("Propagating state pairs")
    axd.set_ylim(0, 9.5)
    panel(axd, "d", "Second-family causal boundary")

    save_figure(fig, "figure4_contract_adaptation_and_generality")


def figure5_long_horizon() -> None:
    final = load_json("results/checkpoint20_holdback_authority/final_summary_v2.json")
    ux = load_json(
        "results/checkpoint20_holdback_authority/provisional_experience_audit.json"
    )["audit"]
    seed_df = pd.read_csv(
        ROOT / "results/checkpoint20_holdback_authority/five_seed_metrics.csv"
    )
    quality = pd.read_csv(
        ROOT / "results/checkpoint20_holdback_authority/deployed_quality_summary.csv"
    )

    progression_rows = [
        {
            "mechanism": "Continuous",
            "p99_seconds": 2.393219992518425,
            "deadline_miss_rounds": 8,
            "source": "results/long_horizon/service_summary.csv",
        },
        {
            "mechanism": "Checkpoint/rebase",
            "p99_seconds": 1.937447289004922,
            "deadline_miss_rounds": 0,
            "source": "results/long_horizon/service_summary.csv",
        },
        {
            "mechanism": "Checkpoint-20 holdback",
            "p99_seconds": final["five_seed"]["maximum_p99_seconds"],
            "deadline_miss_rounds": 0,
            "source": "results/checkpoint20_holdback_authority/final_summary_v2.json",
        },
    ]
    write_source("figure5_mechanism_progression.csv", progression_rows)
    write_source(
        "figure5_five_seed_latency_energy.csv",
        seed_df.assign(
            source="results/checkpoint20_holdback_authority/five_seed_metrics.csv"
        ).to_dict("records"),
    )
    write_source(
        "figure5_quality.csv",
        quality.assign(
            source="results/checkpoint20_holdback_authority/deployed_quality_summary.csv"
        ).to_dict("records"),
    )
    transition_rows = []
    for episode_index, episode in enumerate(ux["episodes"]):
        for transition in episode["transitions"]:
            transition_rows.append(
                {
                    "episode": episode_index,
                    "language": episode["language"],
                    "kind": transition["kind"],
                    "overwrite_fraction": transition["overwrite_fraction"],
                    "burst_length": episode["burst_length"],
                    "resolution": episode["resolution"],
                    "source": "results/checkpoint20_holdback_authority/provisional_experience_audit.json",
                }
            )
    write_source("figure5_provisional_transitions.csv", transition_rows)

    fig = plt.figure(figsize=(7.2, 5.15), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 0.95], hspace=0.26, wspace=0.32)
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0])
    axd = fig.add_subplot(gs[1, 1])

    vals = [r["p99_seconds"] for r in progression_rows]
    colors = [COL["coral"], COL["gold"], COL["teal"]]
    bars = axa.bar(np.arange(3), vals, color=colors, width=0.62, zorder=3)
    axa.axhline(2.0, color=COL["coral"], ls=(0, (4, 2)), lw=1)
    axa.axhline(1.9, color=COL["mid"], ls=(0, (2, 2)), lw=0.9)
    for bar, row in zip(bars, progression_rows):
        axa.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{bar.get_height():.3f}s\n{row['deadline_miss_rounds']} miss rounds",
            ha="center",
            fontsize=6.2,
        )
    axa.set_xticks(
        np.arange(3),
        ["Continuous", "Checkpoint/\nrebase", "Checkpoint-20\nholdback"],
    )
    axa.set_ylabel("Long-session P99 (s)")
    axa.set_ylim(0, 2.72)
    panel(axa, "a", "Holdback removes synchronized verification stalls")

    seeds = np.arange(1, 6)
    axb.fill_between(seeds, 0, seed_df["p99_seconds"], color=COL["blue_soft"], alpha=0.35)
    axb.plot(seeds, seed_df["p99_seconds"], "-o", color=COL["navy"], lw=1.6, ms=4, label="P99")
    axb.plot(seeds, seed_df["p95_seconds"], "-s", color=COL["blue"], lw=1.25, ms=3.5, label="P95")
    axb.plot(seeds, seed_df["p50_seconds"], "-^", color=COL["teal"], lw=1.25, ms=3.5, label="P50")
    axb.axhline(1.9, color=COL["coral"], ls=(0, (4, 2)), lw=1)
    axb.set_xticks(seeds)
    axb.set_xlabel("Independent 120 s seed")
    axb.set_ylabel("State-entry latency (s)")
    axb.set_ylim(0.5, 2.02)
    axb.legend(loc="upper right", ncol=3, handlelength=1.3, columnspacing=0.8)
    axb.text(
        0.02,
        0.06,
        f"mean energy = {seed_df['joules_per_audio_second'].mean():.2f} J/audio-s\n"
        "0 deadline misses · 0 authority violations",
        transform=axb.transAxes,
        fontsize=6.2,
        color=COL["mid"],
    )
    panel(axb, "b", "The tail result repeats across five held-out seeds")

    labels = ["English: total", "Chinese: total", "English: holdback only", "Chinese: holdback only"]
    lookup = {row.language: row for row in quality.itertuples()}
    estimates = [
        100 * lookup["English"].total_delta,
        100 * lookup["Chinese"].total_delta,
        100 * lookup["English"].holdback_incremental_delta,
        100 * lookup["Chinese"].holdback_incremental_delta,
    ]
    lows = [
        100 * lookup["English"].total_ci_low,
        100 * lookup["Chinese"].total_ci_low,
        100 * lookup["English"].holdback_incremental_ci_low,
        100 * lookup["Chinese"].holdback_incremental_ci_low,
    ]
    highs = [
        100 * lookup["English"].total_ci_high,
        100 * lookup["Chinese"].total_ci_high,
        100 * lookup["English"].holdback_incremental_ci_high,
        100 * lookup["Chinese"].holdback_incremental_ci_high,
    ]
    ypos = np.arange(4)[::-1]
    colors = [COL["blue"], COL["teal"], COL["blue_soft"], COL["teal_soft"]]
    axc.axvline(0, color=COL["mid"], ls=(0, (3, 2)), lw=0.9)
    axc.axvspan(-2, 2, color=COL["teal_soft"], alpha=0.15, zorder=-2)
    for y, est, lo, hi, color in zip(ypos, estimates, lows, highs, colors):
        axc.plot([lo, hi], [y, y], color=color, lw=2)
        axc.plot(est, y, "o", color=color, ms=5)
    axc.set_yticks(ypos, labels)
    axc.set_xlabel("Paired WER/CER change (percentage points)")
    axc.set_xlim(-0.35, 2.7)
    axc.text(
        0.98,
        0.98,
        "pre-registered ±2 pp tolerance",
        transform=axc.transAxes,
        ha="right",
        va="top",
        color=COL["mid"],
        fontsize=6,
    )
    panel(axc, "c", "Holdback adds little incremental quality change")

    rng = np.random.default_rng(7)
    kinds = ["provisional_to_authority", "provisional_to_provisional"]
    labels = ["Provisional →\nauthority", "Provisional →\nprovisional"]
    for i, kind in enumerate(kinds):
        vals = np.array(
            [r["overwrite_fraction"] for r in transition_rows if r["kind"] == kind]
        )
        jitter = rng.uniform(-0.12, 0.12, size=len(vals))
        axd.scatter(
            np.full(len(vals), i) + jitter,
            100 * vals,
            s=13,
            facecolor=[COL["blue_soft"], COL["gold"]][i],
            edgecolor=[COL["blue"], COL["gold"]][i],
            linewidth=0.5,
            alpha=0.8,
            zorder=3,
        )
        q50, q95 = np.quantile(vals, [0.5, 0.95])
        mean = vals.mean()
        axd.plot([i - 0.18, i + 0.18], [100 * q50] * 2, color=COL["ink"], lw=1.3)
        axd.plot(i, 100 * mean, marker="D", ms=4, color=COL["coral"], zorder=5)
        axd.text(
            i,
            103,
            f"n={len(vals)}\nmean {100*mean:.1f}%",
            ha="center",
            va="top",
            fontsize=6.1,
        )
    axd.set_xticks([0, 1], labels)
    axd.set_ylabel("Already displayed text overwritten (%)")
    axd.set_ylim(-4, 108)
    axd.legend(
        handles=[
            Line2D([0], [0], marker="D", color="none", markerfacecolor=COL["coral"], label="mean"),
            Line2D([0], [0], color=COL["ink"], lw=1.3, label="median"),
        ],
        loc="center",
        bbox_to_anchor=(0.53, 0.84),
        ncol=2,
        handlelength=1,
        columnspacing=0.8,
    )
    panel(axd, "d", "Most provisional updates preserve displayed text")

    save_figure(fig, "figure5_long_horizon_holdback_closure")


def main() -> None:
    figure2_problem()
    figure3_system()
    figure4_adaptation()
    figure5_long_horizon()
    print(
        json.dumps(
            {
                "decision": "REVTRACE_NON_ARCHITECTURE_FIGURES_RENDERED",
                "figures": 4,
                "formats": ["svg", "pdf", "tiff", "png"],
                "source_tables": len(list(SOURCE.glob("figure*.csv"))),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
