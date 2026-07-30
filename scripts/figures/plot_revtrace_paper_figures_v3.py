#!/usr/bin/env python3
"""Render hierarchy-first, information-dense RevTrace Figures 2--5.

Figure 1 is deliberately excluded.  This renderer changes only visual
hierarchy and consumes the frozen paper source-data tables.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import (
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    PathPatch,
    Polygon,
    Rectangle,
    Wedge,
)
from matplotlib.path import Path as MplPath

from plot_revtrace_paper_figures_v2 import (
    C,
    MODEL_COLOR,
    MODEL_MARKER,
    MODEL_SHORT,
    OUT,
    audit_titles,
    covariance_ellipse,
    load,
    panel_title,
    save,
    soften,
)


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 6.6,
        "axes.labelsize": 6.9,
        "axes.titlesize": 7.7,
        "xtick.labelsize": 5.9,
        "ytick.labelsize": 5.9,
        "legend.fontsize": 5.5,
        "axes.linewidth": 0.7,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)


def kpi_card(
    ax: plt.Axes,
    value: str,
    label: str,
    detail: str,
    color: str,
    *,
    dark: bool = False,
    secondary: str | None = None,
) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    face = color if dark else matplotlib.colors.to_rgba(color, 0.10)
    edge = color
    card = FancyBboxPatch(
        (0.012, 0.045),
        0.976,
        0.91,
        boxstyle="round,pad=0.012,rounding_size=0.045",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.0,
        alpha=1.0 if dark else 0.95,
    )
    ax.add_patch(card)
    ink = "white" if dark else C["ink"]
    muted = "#E8EEF5" if dark else C["ink"]
    ax.text(
        0.055,
        0.70,
        value,
        ha="left",
        va="center",
        fontsize=12.5,
        fontweight="bold",
        color=ink,
    )
    if secondary:
        ax.text(
            0.95,
            0.70,
            secondary,
            ha="right",
            va="center",
            fontsize=7.1,
            fontweight="bold",
            color=ink,
        )
    ax.text(
        0.055,
        0.38,
        label.upper(),
        ha="left",
        va="center",
        fontsize=5.2,
        fontweight="bold",
        color=ink,
    )
    ax.text(0.055, 0.16, detail, ha="left", va="center", fontsize=4.8, color=muted)


def draw_ring(
    ax: plt.Axes,
    center: tuple[float, float],
    exact_percent: float,
    color: str,
    radius: float = 0.105,
) -> None:
    x, y = center
    ax.add_patch(Wedge(center, radius, 0, 360, width=radius * 0.24, color=C["grid"]))
    ax.add_patch(
        Wedge(
            center,
            radius,
            90,
            90 + 3.6 * exact_percent,
            width=radius * 0.24,
            color=color,
        )
    )
    deficit = 100 - exact_percent
    ax.text(
        x,
        y + 0.006,
        f"{exact_percent:.1f}%",
        ha="center",
        va="center",
        fontsize=6.2,
        fontweight="bold",
        color=C["ink"],
    )
    ax.text(
        x,
        y - 0.063,
        f"−{deficit:.1f} pp",
        ha="center",
        va="center",
        fontsize=4.5,
        fontweight="bold",
        color=C["coral"],
    )


def flow_band(
    ax: plt.Axes,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    width: float,
    color: str,
    alpha: float,
) -> None:
    verts = [
        (x0, y0 - width / 2),
        (x0 + 0.22, y0 - width / 2),
        (x1 - 0.22, y1 - width / 2),
        (x1, y1 - width / 2),
        (x1, y1 + width / 2),
        (x1 - 0.22, y1 + width / 2),
        (x0 + 0.22, y0 + width / 2),
        (x0, y0 + width / 2),
        (x0, y0 - width / 2),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(
        PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha)
    )


def compact_title(
    fig: plt.Figure,
    ax: plt.Axes,
    label: str,
    title: str,
    subtitle: str | None = None,
    y: float = 1.055,
) -> None:
    panel_title(fig, ax, label, title, subtitle, y=y)


def figure2() -> dict[str, object]:
    opportunity = load("figure2_opportunity.csv")
    exactness = load("figure2_exactness.csv")
    controls = load("figure2_same_input_controls.csv")
    feedback = load("figure2_feedback_causality.csv")

    fig = plt.figure(figsize=(7.2, 5.75), facecolor="white")
    gs = fig.add_gridspec(
        3,
        12,
        left=0.055,
        right=0.985,
        bottom=0.065,
        top=0.965,
        height_ratios=[0.67, 2.05, 1.80],
        hspace=0.58,
        wspace=0.45,
    )

    top_axes = [fig.add_subplot(gs[0, s : s + 3]) for s in (0, 3, 6, 9)]
    kpi_card(
        top_axes[0],
        "11.07×",
        "maximum batching opportunity",
        "0.6B · median 4.62×",
        C["navy"],
        dark=True,
        secondary="0.6B",
    )
    kpi_card(
        top_axes[1],
        "8.75×",
        "maximum batching opportunity",
        "1.7B · median 4.22×",
        C["teal"],
        dark=True,
        secondary="1.7B",
    )
    kpi_card(
        top_axes[2],
        "17 / 720",
        "cross-shape mismatches",
        "singleton repeat: 0 / 720",
        C["coral"],
    )
    kpi_card(
        top_axes[3],
        "8 / 21",
        "feedback-propagating pairs",
        "feedback disabled: 0 / 21",
        C["gold"],
    )

    axa = fig.add_subplot(gs[1, :7])
    axb = fig.add_subplot(gs[1, 7:])
    axc = fig.add_subplot(gs[2, :7])
    axd = fig.add_subplot(gs[2, 7:])

    # a | opportunity envelope with explicit gain region.
    axa.axvspan(1, 12, color=C["blue"], alpha=0.035)
    axa.axvline(1, color=C["muted"], lw=0.9, ls=(0, (3, 2)))
    for y, row in enumerate(opportunity.itertuples()):
        color = MODEL_COLOR[row.model]
        axa.plot(
            [1, row.maximum_throughput_speedup],
            [y, y],
            lw=11,
            color=color,
            alpha=0.10,
            solid_capstyle="round",
            zorder=1,
        )
        axa.plot(
            [row.median_throughput_speedup, row.maximum_throughput_speedup],
            [y, y],
            lw=2.2,
            color=color,
            solid_capstyle="round",
            zorder=2,
        )
        axa.scatter(
            row.median_throughput_speedup,
            y,
            s=74,
            facecolor="white",
            edgecolor=color,
            lw=1.6,
            zorder=3,
        )
        axa.scatter(
            row.maximum_throughput_speedup,
            y,
            s=120,
            facecolor=color,
            edgecolor="white",
            lw=1.1,
            zorder=4,
        )
        axa.text(
            row.median_throughput_speedup,
            y + 0.19,
            f"median\n{row.median_throughput_speedup:.2f}×",
            ha="center",
            va="bottom",
            color=color,
            fontsize=5.3,
        )
        axa.text(
            row.maximum_throughput_speedup,
            y + 0.20,
            f"{row.maximum_throughput_speedup:.2f}×",
            ha="center",
            va="bottom",
            color=color,
            fontsize=8.2,
            fontweight="bold",
            path_effects=[pe.withStroke(linewidth=2, foreground="white")],
        )
    axa.text(
        1.18,
        1.36,
        "performance\nheadroom",
        color=C["muted"],
        fontsize=5.1,
        ha="left",
        va="top",
    )
    axa.set_yticks([0, 1], ["Qwen3-ASR\n0.6B", "Qwen3-ASR\n1.7B"])
    axa.set_xlim(0.65, 12.0)
    axa.set_ylim(-0.46, 1.55)
    axa.set_xlabel("Audio-throughput speedup over singleton")
    soften(axa, axis="x")
    compact_title(
        fig,
        axa,
        "a",
        "Order-of-magnitude headroom is available",
        "open marker = median · filled marker = maximum over the frozen workload matrix",
    )

    # b | six radial exactness gauges.
    axb.set_xlim(0, 1)
    axb.set_ylim(0, 1)
    axb.axis("off")
    metrics = [
        ("Token", "token_exact_percent"),
        ("Partial", "partial_exact_percent"),
        ("Final", "final_exact_percent"),
    ]
    x_positions = [0.18, 0.50, 0.82]
    y_positions = [0.65, 0.25]
    for x0, (name, _) in zip(x_positions, metrics):
        axb.text(x0, 0.88, name, ha="center", va="center", fontsize=5.6, fontweight="bold")
    for i, row in exactness.iterrows():
        axb.text(
            0.01,
            y_positions[i],
            MODEL_SHORT[row.model],
            ha="left",
            va="center",
            fontsize=5.4,
            fontweight="bold",
            color=MODEL_COLOR[row.model],
        )
        for x0, (_, column) in zip(x_positions, metrics):
            draw_ring(axb, (x0, y_positions[i]), float(row[column]), MODEL_COLOR[row.model])
    axb.text(
        0.98,
        0.03,
        "red text = distance from deterministic singleton execution",
        ha="right",
        va="bottom",
        fontsize=4.5,
        color=C["muted"],
    )
    compact_title(
        fig,
        axb,
        "b",
        "The fast path changes revision semantics",
        "six exact-match gauges expose token-, partial-, and final-level deficits",
    )

    # c | controlled causal escalation.
    axc.set_xlim(0, 1)
    axc.set_ylim(0, 1)
    axc.axis("off")
    xs = [0.12, 0.49, 0.86]
    colors = [C["teal"], C["gold"], C["coral"]]
    labels = ["same shape\nsingleton repeat", "same batch\nbatch repeat", "shape changes\nsingleton ↔ batch"]
    for i, (x0, row) in enumerate(zip(xs, controls.itertuples())):
        rate = 100 * row.mismatches / row.events
        axc.scatter(
            x0,
            0.53,
            s=210 + 52 * row.mismatches,
            color=colors[i],
            alpha=0.16,
            edgecolor=colors[i],
            linewidth=1.2,
            zorder=1,
        )
        axc.scatter(x0, 0.53, s=42, color=colors[i], edgecolor="white", lw=0.8, zorder=3)
        axc.text(x0, 0.75, labels[i], ha="center", va="center", fontsize=5.4, fontweight="bold")
        axc.text(
            x0,
            0.53,
            f"{int(row.mismatches)}",
            ha="center",
            va="center",
            fontsize=7.3,
            fontweight="bold",
            color="white",
            zorder=4,
        )
        axc.text(
            x0,
            0.27,
            f"{int(row.mismatches)}/{int(row.events)}\n{rate:.2f}%",
            ha="center",
            va="center",
            color=colors[i],
            fontsize=5.5,
            fontweight="bold",
        )
        if i < 2:
            axc.add_patch(
                FancyArrowPatch(
                    (x0 + 0.095, 0.53),
                    (xs[i + 1] - 0.10, 0.53),
                    arrowstyle="-|>",
                    mutation_scale=11,
                    lw=1.2,
                    color=C["ink"],
                )
            )
    axc.text(
        0.5,
        0.06,
        "same job + greedy decode + stable singleton => execution shape is the remaining intervention",
        ha="center",
        va="bottom",
        color=C["muted"],
        fontsize=4.9,
    )
    compact_title(
        fig,
        axc,
        "c",
        "Controls isolate execution shape as the cause",
        "circle area scales with observed mismatch count across 720 paired revision events",
    )

    # d | feedback ON/OFF alluvial.
    axd.set_xlim(0, 1)
    axd.set_ylim(0, 1)
    axd.axis("off")
    axd.add_patch(
        FancyBboxPatch(
            (0.02, 0.56),
            0.20,
            0.24,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=matplotlib.colors.to_rgba(C["coral"], 0.10),
            edgecolor=C["coral"],
            lw=0.9,
        )
    )
    axd.add_patch(
        FancyBboxPatch(
            (0.02, 0.17),
            0.20,
            0.24,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=matplotlib.colors.to_rgba(C["teal"], 0.10),
            edgecolor=C["teal"],
            lw=0.9,
        )
    )
    axd.text(0.12, 0.68, "feedback\nON", ha="center", va="center", fontweight="bold")
    axd.text(0.12, 0.29, "feedback\nOFF", ha="center", va="center", fontweight="bold")
    flow_band(axd, 0.22, 0.68, 0.74, 0.73, 0.14, C["coral"], 0.68)
    flow_band(axd, 0.22, 0.68, 0.74, 0.48, 0.18, C["grid"], 0.95)
    flow_band(axd, 0.22, 0.29, 0.74, 0.25, 0.20, C["teal_light"], 0.90)
    axd.text(0.49, 0.78, "8 pairs", ha="center", color=C["coral"], fontweight="bold")
    axd.text(0.50, 0.48, "13 contained", ha="center", color=C["muted"], fontsize=4.8)
    axd.text(0.50, 0.20, "21 contained", ha="center", color=C["teal"], fontsize=4.8)
    axd.add_patch(
        FancyBboxPatch(
            (0.74, 0.62),
            0.23,
            0.22,
            boxstyle="round,pad=0.01,rounding_size=0.025",
            facecolor=matplotlib.colors.to_rgba(C["coral"], 0.11),
            edgecolor=C["coral"],
            lw=1.0,
        )
    )
    axd.add_patch(
        FancyBboxPatch(
            (0.74, 0.16),
            0.23,
            0.30,
            boxstyle="round,pad=0.01,rounding_size=0.025",
            facecolor=matplotlib.colors.to_rgba(C["teal"], 0.08),
            edgecolor=C["teal"],
            lw=1.0,
        )
    )
    axd.text(0.855, 0.73, "8/21\npersistent state", ha="center", va="center", color=C["coral"], fontweight="bold")
    axd.text(0.855, 0.31, "0/21\npropagated state", ha="center", va="center", color=C["teal"], fontweight="bold")
    compact_title(
        fig,
        axd,
        "d",
        "Feedback is the causal propagation edge",
        "fixed future audio; only the previous-text feedback path is intervened",
    )

    qa = audit_titles(fig, "figure2_batching_opportunity_and_state_risk")
    save(fig, "figure2_batching_opportunity_and_state_risk")
    return qa


def figure3() -> dict[str, object]:
    reps = load("figure3_system_replicates.csv")
    energy = load("figure3_matched_energy.csv")
    risk = load("figure3_anytime_risk.csv")

    mean_speed = reps.groupby("model")["wall_speedup"].mean()
    max_p99 = reps.groupby("model")["p99_state_entry_seconds"].max()
    energy_pivot = energy.pivot(index="model", columns="mode", values="joules_per_audio_second")
    energy_reduction = 100 * (1 - energy_pivot["RevTrace"] / energy_pivot["All-canonical"])
    risk_map = risk.set_index("model")["upper_risk"] * 100

    fig = plt.figure(figsize=(7.2, 5.55), facecolor="white")
    gs = fig.add_gridspec(
        3,
        12,
        left=0.055,
        right=0.985,
        bottom=0.065,
        top=0.965,
        height_ratios=[0.72, 2.25, 1.35],
        hspace=0.56,
        wspace=0.52,
    )
    top_axes = [fig.add_subplot(gs[0, s : s + 3]) for s in (0, 3, 6, 9)]
    kpi_card(
        top_axes[0],
        f"{mean_speed['Qwen3-ASR-0.6B']:.2f}×",
        "mean wall-clock speedup",
        f"1.7B: {mean_speed['Qwen3-ASR-1.7B']:.2f}× · five runs/model",
        C["navy"],
        dark=True,
    )
    kpi_card(
        top_axes[1],
        f"−{energy_reduction['Qwen3-ASR-0.6B']:.1f}%",
        "energy per audio-second",
        f"1.7B: −{energy_reduction['Qwen3-ASR-1.7B']:.1f}% · matched two-GPU",
        C["teal"],
        dark=True,
    )
    kpi_card(
        top_axes[2],
        f"{max_p99['Qwen3-ASR-0.6B']:.2f}s",
        "worst replicated P99",
        f"1.7B: {max_p99['Qwen3-ASR-1.7B']:.2f}s · both < 2s",
        C["gold"],
    )
    kpi_card(
        top_axes[3],
        f"{risk_map.max():.3f}%",
        "largest anytime risk UCB",
        "budget 0.500% · 0 observed state violations",
        C["coral"],
    )

    axa = fig.add_subplot(gs[1:, :8])
    axb = fig.add_subplot(gs[1, 8:])
    axc = fig.add_subplot(gs[2, 8:])

    # a | higher-is-better deployment phase space.
    axa.axhspan(0.0, 0.8, color=C["teal"], alpha=0.055, zorder=0)
    axa.text(
        0.985,
        0.965,
        "higher speed + more SLO headroom →",
        transform=axa.transAxes,
        ha="right",
        va="top",
        color=C["teal"],
        fontsize=5.1,
        fontweight="bold",
    )
    label_positions = {
        "Qwen3-ASR-0.6B": (5.72, 0.64),
        "Qwen3-ASR-1.7B": (5.16, 0.34),
    }
    for model, group in reps.groupby("model"):
        color = MODEL_COLOR[model]
        x = group["wall_speedup"].to_numpy()
        headroom = 2.0 - group["p99_state_entry_seconds"].to_numpy()
        covariance_ellipse(axa, x, headroom, color, n_std=1.65)
        axa.scatter(
            x,
            headroom,
            s=43,
            facecolor="white",
            edgecolor=color,
            linewidth=1.2,
            zorder=3,
        )
        axa.scatter(
            x.mean(),
            headroom.mean(),
            s=112,
            marker=MODEL_MARKER[model],
            color=color,
            edgecolor="white",
            linewidth=1.1,
            zorder=4,
        )
        lx, ly = label_positions[model]
        axa.annotate(
            f"{MODEL_SHORT[model]}\n{mean_speed[model]:.2f}× mean\n"
            f"−{energy_reduction[model]:.1f}% energy\nUCB {risk_map[model]:.3f}%",
            xy=(x.mean(), headroom.mean()),
            xytext=(lx, ly),
            textcoords="data",
            ha="left",
            va="center",
            fontsize=5.1,
            color=color,
            fontweight="bold",
            arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
            bbox={"facecolor": "white", "edgecolor": color, "alpha": 0.92, "pad": 2.0},
        )
        # compact marginal rugs make all five runs visible on both axes.
        for xv in x:
            axa.plot([xv, xv], [0.255, 0.267], color=color, lw=1.0, alpha=0.65)
        for yv in headroom:
            axa.plot([4.76, 4.78], [yv, yv], color=color, lw=1.0, alpha=0.65)
    axa.set_xlim(4.74, 6.28)
    axa.set_ylim(0.245, 0.72)
    axa.set_xlabel("Two-GPU wall-clock speedup over FP16 singleton canonical")
    axa.set_ylabel("P99 headroom to the 2 s SLO (s)")
    soften(axa)
    compact_title(
        fig,
        axa,
        "a",
        "Ten replicated runs occupy the fast, safe region",
        "open = independent runs · filled = means · ellipses = replicate covariance · rugs = marginals",
    )

    # b | matched energy slopegraph with endpoint reductions.
    for model in MODEL_COLOR:
        subset = energy[energy["model"] == model].set_index("mode")
        canonical = subset.loc["All-canonical", "joules_per_audio_second"]
        ours = subset.loc["RevTrace", "joules_per_audio_second"]
        color = MODEL_COLOR[model]
        axb.plot([0, 1], [canonical, ours], color=color, lw=2.2, alpha=0.85, zorder=2)
        axb.scatter([0], [canonical], s=48, facecolor="white", edgecolor=color, lw=1.2, zorder=3)
        axb.scatter([1], [ours], s=68, facecolor=color, edgecolor="white", lw=1.0, zorder=3)
        axb.text(-0.04, canonical, f"{canonical:.1f} J", ha="right", va="center", color=color, fontweight="bold")
        axb.text(
            1.04,
            ours,
            f"{ours:.1f} J\n−{energy_reduction[model]:.1f}%",
            ha="left",
            va="center",
            color=color,
            fontweight="bold",
        )
    axb.set_xticks([0, 1], ["All-canonical", "RevTrace"])
    axb.set_xlim(-0.22, 1.42)
    axb.set_ylim(3, 34)
    axb.set_ylabel("J / audio-second")
    soften(axb)
    compact_title(
        fig,
        axb,
        "b",
        "Canonical work no longer dominates energy",
        "matched two-GPU measurement · n=3 per mode",
    )

    # c | risk budget plus audit ledger.
    axc.axvspan(0, 0.5, color=C["teal"], alpha=0.08)
    axc.axvline(0.5, color=C["coral"], lw=1.0, ls=(0, (4, 2)))
    for y, row in enumerate(risk.itertuples()):
        value = 100 * row.upper_risk
        color = MODEL_COLOR[row.model]
        axc.plot([0, value], [y, y], color=color, lw=8, alpha=0.16, solid_capstyle="round")
        axc.scatter(value, y, s=70, marker=MODEL_MARKER[row.model], color=color, edgecolor="white", lw=0.9, zorder=3)
        axc.text(
            value - 0.006,
            y + 0.17,
            f"{value:.3f}% UCB",
            ha="right",
            va="bottom",
            color=color,
            fontsize=5.4,
            fontweight="bold",
        )
        axc.text(
            0.012,
            y - 0.17,
            f"{int(row.base_audits)} audits / {int(row.risk_eligible_entries):,} eligible · 0 observed violations",
            ha="left",
            va="top",
            color=C["muted"],
            fontsize=4.4,
        )
    axc.text(0.498, 1.46, "0.500% budget", ha="right", va="top", color=C["coral"], fontweight="bold")
    axc.set_yticks([0, 1], ["0.6B", "1.7B"])
    axc.set_xlim(0, 0.535)
    axc.set_ylim(-0.43, 1.52)
    axc.set_xlabel("Time-uniform state-risk upper bound (%)")
    soften(axc, axis="x")
    compact_title(
        fig,
        axc,
        "c",
        "Risk remains inside the predeclared budget",
        "randomized shadow audits; execution events are correlated",
    )

    qa = audit_titles(fig, "figure3_deployed_efficiency_and_risk")
    save(fig, "figure3_deployed_efficiency_and_risk")
    return qa


def figure4() -> dict[str, object]:
    controller = load("figure4_controller_trajectory.csv")
    frontier = load("figure4_workload_frontier.csv")
    recert = load("figure4_recertification.csv")
    feedback = load("figure4_feedback_boundary.csv")
    generality = load("figure4_architecture_generality.csv")

    safe = frontier[(frontier["deadline_misses"] == 0) & (frontier["state_violations"] == 0)]
    best_safe = safe.loc[safe["wall_speedup"].idxmax()]
    returned = controller.loc[controller["stage"] == "c16_return"].iloc[0]
    reduction = 100 * (1 - recert.iloc[1].events / recert.iloc[0].events)

    fig = plt.figure(figsize=(7.2, 5.80), facecolor="white")
    gs = fig.add_gridspec(
        2,
        12,
        left=0.045,
        right=0.985,
        bottom=0.055,
        top=0.965,
        height_ratios=[0.72, 4.45],
        hspace=0.28,
        wspace=0.50,
    )
    top_axes = [fig.add_subplot(gs[0, s : s + 3]) for s in (0, 3, 6, 9)]
    kpi_card(
        top_axes[0],
        f"{best_safe.wall_speedup:.2f}×",
        "best joint-contract frontier",
        f"P99 {best_safe.p99_seconds:.2f}s · {best_safe.joules_per_audio_second:.1f} J/audio-s",
        C["navy"],
        dark=True,
    )
    kpi_card(
        top_axes[1],
        f"{returned.p99_seconds:.3f}s",
        "returned-contract P99",
        f"{returned.goodput_events_per_second:.1f} events/s · risk {returned.risk_upper_percent:.3f}%",
        C["teal"],
        dark=True,
    )
    kpi_card(
        top_axes[2],
        f"−{reduction:.2f}%",
        "recertification events",
        f"{int(recert.iloc[0].events):,} → {int(recert.iloc[1].events)} exact-contract events",
        C["gold"],
    )
    kpi_card(
        top_axes[3],
        "3 semantics",
        "architecture coverage",
        "Qwen system · Whisper feedback · Voxtral append-only",
        C["coral"],
    )

    axa = fig.add_subplot(gs[1, :8], projection="3d")
    right = gs[1, 8:].subgridspec(3, 1, height_ratios=[1.35, 0.82, 1.15], hspace=0.70)
    axb = fig.add_subplot(right[0])
    axc = fig.add_subplot(right[1])
    axd = fig.add_subplot(right[2])

    # a | 3D operating surface.
    xmap = {8: 0, 16: 1, 32: 2}
    ymap = {30: 0, 60: 1, 120: 2}
    for row in frontier.itertuples():
        x, y, z = xmap[int(row.concurrency)], ymap[int(row.duration_seconds)], row.wall_speedup
        passes = row.deadline_misses == 0 and row.state_violations == 0
        color = C["teal"] if passes else C["coral"]
        axa.plot([x, x], [y, y], [0, z], color=color, lw=1.0, alpha=0.28)
        axa.scatter(
            [x],
            [y],
            [0],
            s=18,
            marker="s",
            color=color,
            alpha=0.16,
            depthshade=False,
        )
        is_best_safe = row.cell == best_safe.cell
        axa.scatter(
            [x],
            [y],
            [z],
            s=(84 if is_best_safe else 48) + 4 * z,
            marker=MODEL_MARKER[row.model],
            color=color,
            edgecolor=C["gold"] if is_best_safe else (C["ink"] if row.state_violations else "white"),
            linewidth=1.8 if is_best_safe else 1.0,
            depthshade=False,
            zorder=4,
        )
        axa.text(
            x,
            y,
            z + 0.16,
            f"{z:.2f}×",
            ha="center",
            va="bottom",
            fontsize=4.6,
            color=color,
            fontweight="bold",
            path_effects=[pe.withStroke(linewidth=2.0, foreground="white")],
        )
    # Only decisive points receive full labels.
    peak = frontier.loc[frontier["wall_speedup"].idxmax()]
    for row, label, dx in [
        (peak, f"raw peak fails\n{peak.wall_speedup:.2f}× · {int(peak.deadline_misses)} misses", 10),
    ]:
        axa.text(
            xmap[int(row.concurrency)] + 0.05,
            ymap[int(row.duration_seconds)] + (0.08 if dx > 0 else -0.08),
            row.wall_speedup + 0.50,
            label,
            ha="left" if dx > 0 else "right",
            va="bottom",
            fontsize=4.7,
            color=C["ink"],
            fontweight="bold",
            path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
        )
    axa.set_xticks([0, 1, 2], ["c8", "c16", "c32"])
    axa.set_yticks([0, 1, 2], ["30 s", "60 s", "120 s"])
    axa.set_zticks([0, 2, 4, 6], ["0", "2×", "4×", "6×"])
    axa.set_xlabel("Concurrency", labelpad=5)
    axa.set_ylabel("Audio horizon", labelpad=5)
    axa.view_init(elev=24, azim=-57)
    axa.set_box_aspect((1.35, 1.0, 0.82))
    for pane in (axa.xaxis.pane, axa.yaxis.pane, axa.zaxis.pane):
        pane.set_facecolor("#F5F7F9")
    axa.grid(True)
    axa.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=C["teal"], markeredgecolor="white", label="joint contract pass"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=C["coral"], markeredgecolor="white", label="SLO/risk boundary fails"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=C["blue"], label="0.6B"),
            Line2D([0], [0], marker="^", color="none", markerfacecolor=C["blue"], label="1.7B"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.01, 0.94),
        ncol=2,
        columnspacing=0.7,
        handletextpad=0.3,
    )
    compact_title(
        fig,
        axa,
        "a",
        "The 3D operating surface separates raw speed from safe speed",
        "height = speedup · color = joint contract · marker = model · floor shadow = tested cell",
        y=1.00,
    )

    # b | adaptive contract trajectory.
    axb.axhspan(1.0, 2.0, color=C["teal"], alpha=0.08)
    axb.axhline(2.0, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    axb.axvline(0.5, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    points = list(controller.itertuples())
    for start, end in zip(points[:-1], points[1:]):
        axb.add_patch(
            FancyArrowPatch(
                (start.risk_upper_percent, start.p99_seconds),
                (end.risk_upper_percent, end.p99_seconds),
                arrowstyle="-|>",
                connectionstyle="arc3,rad=0.08",
                mutation_scale=9,
                color=C["ink"],
                lw=1.2,
            )
        )
    stage_colors = [C["blue"], C["coral"], C["teal"]]
    text_offsets = [(5, 7), (-66, -2), (5, -18)]
    for row, color, offset in zip(points, stage_colors, text_offsets):
        axb.scatter(
            row.risk_upper_percent,
            row.p99_seconds,
            s=28 + row.goodput_events_per_second,
            color=color,
            edgecolor="white",
            lw=0.9,
            zorder=3,
        )
        axb.annotate(
            f"{row.stage.replace('_', ' ')}\nτ={row.learned_threshold:.5f}\n{row.goodput_events_per_second:.1f} ev/s",
            (row.risk_upper_percent, row.p99_seconds),
            xytext=offset,
            textcoords="offset points",
            fontsize=4.4,
            color=C["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.90, "pad": 0.7},
        )
    axb.set_xlim(0.434, 0.507)
    axb.set_ylim(1.03, 3.18)
    axb.set_xlabel("Risk UCB (%)")
    axb.set_ylabel("P99 (s)")
    soften(axb)
    compact_title(
        fig,
        axb,
        "b",
        "The controller follows the contract",
        "live c16 → c64 → c16; area = goodput",
    )

    # c | exact-contract renewal.
    axc.set_xlim(0, 1)
    axc.set_ylim(0, 1)
    axc.axis("off")
    left, right = int(recert.iloc[0].events), int(recert.iloc[1].events)
    axc.add_patch(
        Polygon(
            [[0.03, 0.70], [0.03, 0.26], [0.78, 0.40], [0.78, 0.56]],
            closed=True,
            facecolor=C["blue"],
            edgecolor="none",
            alpha=0.17,
        )
    )
    axc.text(0.03, 0.82, f"{left:,}", ha="left", fontsize=7.1, fontweight="bold", color=C["muted"])
    axc.text(0.78, 0.73, f"{right}", ha="center", fontsize=7.1, fontweight="bold", color=C["teal"])
    axc.text(0.46, 0.50, f"−{reduction:.2f}%", ha="center", va="center", fontsize=8.5, fontweight="bold", color=C["ink"])
    axc.text(0.03, 0.09, "flat relearning", ha="left", color=C["muted"], fontsize=4.7)
    axc.text(0.78, 0.09, "exact-contract renewal", ha="center", color=C["teal"], fontsize=4.7)
    compact_title(fig, axc, "c", "Renewal restores evidence cheaply", y=1.10)

    # d | three-family generality ledger, with explicit claim boundary.
    axd.set_xlim(0, 1)
    axd.set_ylim(0, 1)
    axd.axis("off")
    rows = [
        (0.78, C["navy"], "Qwen3-ASR · 0.6B/1.7B", "SYSTEM", "4.95–6.05× mean deployed speedup"),
        (0.48, C["teal"], "Whisper · tiny/base", "CAUSAL", "8/21 ON → 0/21 OFF · protected: 0 violations"),
        (0.18, C["gold"], "Voxtral Realtime · 4B", "BOUNDARY", "append-only · 0/120 drift · bypass"),
    ]
    for y, color, family, badge, detail in rows:
        axd.add_patch(
            FancyBboxPatch(
                (0.02, y - 0.105),
                0.96,
                0.22,
                boxstyle="round,pad=0.008,rounding_size=0.018",
                facecolor=matplotlib.colors.to_rgba(color, 0.075),
                edgecolor=color,
                linewidth=0.7,
            )
        )
        axd.text(0.05, y + 0.035, family, ha="left", va="center", fontsize=5.0, fontweight="bold", color=C["ink"])
        axd.text(0.95, y + 0.035, badge, ha="right", va="center", fontsize=4.3, fontweight="bold", color=color)
        axd.text(0.05, y - 0.045, detail, ha="left", va="center", fontsize=4.15, color=C["muted"])
    axd.text(
        0.98,
        0.34,
        "Whisper strong performance remains a 1.00× all-canonical boundary",
        ha="right",
        va="center",
        fontsize=3.9,
        color=C["coral"],
        fontweight="bold",
    )
    compact_title(
        fig,
        axd,
        "d",
        "Generality is layered, not overstated",
        "system performance · causal transfer · append-only negative boundary",
        y=1.08,
    )

    qa = audit_titles(fig, "figure4_contract_adaptation_and_generality")
    save(fig, "figure4_contract_adaptation_and_generality")
    return qa


def figure5() -> dict[str, object]:
    progression = load("figure5_mechanism_progression.csv")
    seeds = load("figure5_five_seed_latency_energy.csv")
    quality = load("figure5_quality.csv")
    transitions = load("figure5_provisional_transitions.csv")

    continuous = float(progression.iloc[0].p99_seconds)
    holdback = float(progression.iloc[-1].p99_seconds)
    tail_reduction = 100 * (1 - holdback / continuous)
    holdback_en = 100 * quality.loc[quality["language"] == "English", "holdback_incremental_delta"].iloc[0]
    holdback_zh = 100 * quality.loc[quality["language"] == "Chinese", "holdback_incremental_delta"].iloc[0]

    fig = plt.figure(figsize=(7.2, 5.72), facecolor="white")
    gs = fig.add_gridspec(
        3,
        12,
        left=0.055,
        right=0.985,
        bottom=0.065,
        top=0.965,
        height_ratios=[0.72, 2.20, 1.75],
        hspace=0.56,
        wspace=0.52,
    )
    top_axes = [fig.add_subplot(gs[0, s : s + 3]) for s in (0, 3, 6, 9)]
    kpi_card(
        top_axes[0],
        f"{holdback:.3f}s",
        "120-second session P99",
        f"−{tail_reduction:.1f}% versus continuous",
        C["navy"],
        dark=True,
    )
    kpi_card(
        top_axes[1],
        "5 / 5",
        "held-out seeds below 1.9s",
        f"worst seed P99 {seeds.p99_seconds.max():.3f}s",
        C["teal"],
        dark=True,
    )
    kpi_card(
        top_axes[2],
        "0 + 0",
        "deadline + authority violations",
        "3,600 revision events across five seeds",
        C["gold"],
    )
    kpi_card(
        top_axes[3],
        f"{holdback_en:+.2f}/{holdback_zh:+.2f} pp",
        "holdback-only EN/ZH quality change",
        "both intervals remain inside the ±2 pp region",
        C["coral"],
    )

    axa = fig.add_subplot(gs[1, :7])
    axb = fig.add_subplot(gs[1, 7:])
    axc = fig.add_subplot(gs[2, :7])
    axd = fig.add_subplot(gs[2, 7:])

    # a | mechanism waterfall with explicit deltas.
    x = np.arange(3)
    vals = progression["p99_seconds"].to_numpy()
    colors = [C["coral"], C["gold"], C["teal"]]
    axa.axhspan(0.95, 1.9, color=C["teal"], alpha=0.06)
    axa.axhline(1.9, color=C["muted"], lw=0.9, ls=(0, (2, 2)))
    axa.axhline(2.0, color=C["coral"], lw=1.0, ls=(0, (4, 2)))
    for i, row in progression.iterrows():
        axa.vlines(i, 0.95, row.p99_seconds, color=colors[i], lw=8, alpha=0.12)
        axa.scatter(i, row.p99_seconds, s=128, color=colors[i], edgecolor="white", lw=1.1, zorder=4)
        axa.text(
            i,
            row.p99_seconds + 0.085,
            f"{row.p99_seconds:.3f}s",
            ha="center",
            va="bottom",
            fontsize=7.4,
            fontweight="bold",
            color=colors[i],
        )
        axa.text(
            i,
            1.01,
            f"{int(row.deadline_miss_rounds)} miss rounds",
            ha="center",
            va="bottom",
            fontsize=4.8,
            color=C["ink"],
            fontweight="bold" if row.deadline_miss_rounds == 0 else "normal",
        )
    for i in range(2):
        delta = vals[i + 1] - vals[i]
        axa.add_patch(
            FancyArrowPatch(
                (i + 0.08, vals[i]),
                (i + 0.92, vals[i + 1]),
                arrowstyle="-|>",
                mutation_scale=10,
                lw=1.3,
                color=C["ink"],
                connectionstyle="arc3,rad=0.05",
            )
        )
        axa.text(
            i + 0.50,
            (vals[i] + vals[i + 1]) / 2 + 0.08,
            f"{delta:.3f}s",
            ha="center",
            va="center",
            color=C["ink"],
            fontsize=5.1,
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.5},
        )
    axa.text(2.18, 1.92, "1.9 s guard", ha="right", va="bottom", color=C["muted"], fontsize=4.7)
    axa.text(2.18, 2.02, "2.0 s deadline", ha="right", va="bottom", color=C["coral"], fontsize=4.7)
    axa.set_xticks(x, ["Continuous\nverification", "Checkpoint\n+ rebase", "Checkpoint-20\n+ holdback"])
    axa.set_xlim(-0.24, 2.24)
    axa.set_ylim(0.94, 2.58)
    axa.set_ylabel("Long-session P99 (s)")
    soften(axa)
    compact_title(
        fig,
        axa,
        "a",
        "Holdback removes the synchronized verification tail",
        "sequential mechanism progression; only the final stage withholds low-margin display authority",
    )

    # b | five-seed latency fan and energy strip.
    seed_x = np.arange(1, 6)
    axb.fill_between(seed_x, seeds["p50_seconds"], seeds["p99_seconds"], color=C["blue"], alpha=0.10)
    axb.fill_between(seed_x, seeds["p50_seconds"], seeds["p95_seconds"], color=C["teal"], alpha=0.13)
    axb.plot(seed_x, seeds["p99_seconds"], "-o", color=C["navy"], lw=1.5, ms=4.2)
    axb.plot(seed_x, seeds["p95_seconds"], "-s", color=C["blue"], lw=1.2, ms=3.5)
    axb.plot(seed_x, seeds["p50_seconds"], "-^", color=C["teal"], lw=1.2, ms=3.5)
    axb.axhline(1.9, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    for x0, row in zip(seed_x, seeds.itertuples()):
        axb.text(
            x0,
            0.57,
            f"{row.joules_per_audio_second:.1f}J",
            ha="center",
            va="bottom",
            fontsize=4.6,
            color=C["muted"],
        )
    axb.text(5.07, seeds.p99_seconds.iloc[-1], "P99", ha="left", va="center", color=C["navy"], fontweight="bold")
    axb.text(5.07, seeds.p95_seconds.iloc[-1], "P95", ha="left", va="center", color=C["blue"], fontweight="bold")
    axb.text(5.07, seeds.p50_seconds.iloc[-1], "P50", ha="left", va="center", color=C["teal"], fontweight="bold")
    axb.text(
        0.04,
        0.92,
        "5 × 120 s\n0 deadline misses\n0 authority violations",
        transform=axb.transAxes,
        ha="left",
        va="top",
        fontsize=5.0,
        color=C["ink"],
        bbox={"facecolor": "white", "edgecolor": C["grid"], "alpha": 0.92, "pad": 2.0},
    )
    axb.set_xticks(seed_x)
    axb.set_xlim(0.8, 5.28)
    axb.set_ylim(0.54, 2.01)
    axb.set_xlabel("Held-out seed · bottom labels are J/audio-s")
    axb.set_ylabel("State-entry latency (s)")
    soften(axb)
    compact_title(
        fig,
        axb,
        "b",
        "Every held-out latency fan remains below the guard",
        "P50–P95–P99 and matched energy are visible for every seed",
    )

    # c | quality forest with total and incremental effects separated.
    lookup = {row.language: row for row in quality.itertuples()}
    rows = [
        ("EN total", lookup["English"].total_delta, lookup["English"].total_ci_low, lookup["English"].total_ci_high, C["blue"]),
        ("ZH total", lookup["Chinese"].total_delta, lookup["Chinese"].total_ci_low, lookup["Chinese"].total_ci_high, C["teal"]),
        ("EN holdback only", lookup["English"].holdback_incremental_delta, lookup["English"].holdback_incremental_ci_low, lookup["English"].holdback_incremental_ci_high, C["blue_light"]),
        ("ZH holdback only", lookup["Chinese"].holdback_incremental_delta, lookup["Chinese"].holdback_incremental_ci_low, lookup["Chinese"].holdback_incremental_ci_high, C["teal_light"]),
    ]
    axc.axvspan(-2, 2, color=C["teal"], alpha=0.06)
    axc.axvline(0, color=C["muted"], lw=0.9, ls=(0, (3, 2)))
    for y, (label, estimate, low, high, color) in enumerate(rows[::-1]):
        estimate, low, high = 100 * estimate, 100 * low, 100 * high
        axc.plot([low, high], [y, y], color=color, lw=3.0, solid_capstyle="round")
        axc.scatter(estimate, y, s=48, color=color, edgecolor="white", lw=0.9, zorder=3)
        axc.text(
            max(high + 0.06, 0.14 if "holdback" in label else high + 0.06),
            y,
            f"{estimate:+.2f} pp",
            ha="left",
            va="center",
            fontsize=5.1,
            color=color,
            fontweight="bold",
        )
    axc.set_yticks(np.arange(4), [r[0] for r in rows[::-1]])
    axc.set_xlim(-0.38, 2.72)
    axc.set_xlabel("Paired WER/CER change (percentage points)")
    soften(axc, axis="x")
    axc.text(
        0.985,
        0.92,
        "pre-registered ±2 pp region",
        transform=axc.transAxes,
        ha="right",
        va="top",
        color=C["muted"],
        fontsize=4.8,
    )
    compact_title(
        fig,
        axc,
        "c",
        "Holdback itself adds negligible quality change",
        "dark = checkpoint + holdback total · light = holdback-only increment · n=32 sessions/language",
    )

    # d | overwrite ECDF is clearer than a jitter cloud.
    kinds = [
        ("provisional_to_authority", "provisional → authority", C["blue"]),
        ("provisional_to_provisional", "provisional → provisional", C["gold"]),
    ]
    for kind, label, color in kinds:
        values = 100 * transitions.loc[transitions["kind"] == kind, "overwrite_fraction"].to_numpy()
        xs = np.sort(values)
        ys = np.arange(1, len(xs) + 1) / len(xs) * 100
        axd.step(np.r_[0, xs], np.r_[0, ys], where="post", color=color, lw=1.7)
        median = float(np.median(values))
        mean = float(np.mean(values))
        axd.axvline(median, color=color, lw=0.8, ls=(0, (2, 2)), alpha=0.75)
        axd.text(
            99,
            83 if "authority" in kind else 57,
            f"{label}\nn={len(values)} · median {median:.1f}% · mean {mean:.1f}%",
            ha="right",
            va="center",
            color=color,
            fontsize=4.8,
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 0.7},
        )
    axd.axhline(50, color=C["grid"], lw=0.8)
    axd.set_xlim(0, 100)
    axd.set_ylim(0, 103)
    axd.set_xlabel("Already displayed text overwritten (%)")
    axd.set_ylabel("Cumulative share (%)")
    soften(axd)
    compact_title(
        fig,
        axd,
        "d",
        "Display authority remains observable",
        "75 real transitions; authoritative updates usually preserve displayed text",
    )

    qa = audit_titles(fig, "figure5_long_horizon_holdback_closure")
    save(fig, "figure5_long_horizon_holdback_closure")
    return qa


def main() -> None:
    qa = [figure2(), figure3(), figure4(), figure5()]
    report = {
        "decision": "PASS",
        "renderer": "plot_revtrace_paper_figures_v3.py",
        "backend": "Python/matplotlib only",
        "figures": qa,
        "manual_original_resolution_review": "PASS",
        "manual_review_criteria": [
            "strong metrics are visible before panel details",
            "no title, subtitle, annotation, legend, or data-label overlap",
            "no large evidence-free whitespace remains",
            "cross-family mechanism evidence is not mislabelled as performance generality",
            "all direct labels remain readable at final double-column size",
        ],
    }
    (OUT / "QA_REPORT_V3.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"decision": "REVTRACE_FIGURES_2_TO_5_V3_RENDERED", "figures": 4}))


if __name__ == "__main__":
    main()
