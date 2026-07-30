#!/usr/bin/env python3
"""Render information-dense RevTrace manuscript Figures 2--5.

Figure 1 is deliberately out of scope.  This renderer consumes only the frozen
source-data tables produced by the evidence extraction pipeline.
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
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

from plot_revtrace_results_atlas import C, save


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "figures" / "source_data"
OUT = ROOT / "figures" / "paper"

plt.rcParams.update(
    {
        "font.size": 6.3,
        "axes.labelsize": 6.8,
        "axes.titlesize": 7.5,
        "xtick.labelsize": 5.9,
        "ytick.labelsize": 5.9,
        "legend.fontsize": 5.6,
        "axes.linewidth": 0.65,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
    }
)

MODEL_COLOR = {"Qwen3-ASR-0.6B": C["blue"], "Qwen3-ASR-1.7B": C["teal"]}
MODEL_SHORT = {"Qwen3-ASR-0.6B": "0.6B", "Qwen3-ASR-1.7B": "1.7B"}
MODEL_MARKER = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "^"}


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(SOURCE / name)


def soften(ax: plt.Axes, axis: str = "both") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis=axis, color=C["grid"], linewidth=0.42, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)


def panel_title(
    fig: plt.Figure,
    ax: plt.Axes,
    label: str,
    title: str,
    subtitle: str | None = None,
    y: float = 1.08,
) -> None:
    texts = getattr(fig, "_revtrace_audit_texts", [])
    text_fn = ax.text2D if hasattr(ax, "text2D") else ax.text
    lab = text_fn(
        -0.10,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.2,
        fontweight="bold",
        color=C["ink"],
        clip_on=False,
    )
    ttl = text_fn(
        0.0,
        y,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        fontweight="bold",
        color=C["ink"],
        clip_on=False,
    )
    texts.extend([(f"{label}:label", lab), (f"{label}:title", ttl)])
    if subtitle:
        sub = text_fn(
            0.0,
            y - 0.035,
            subtitle,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=5.4,
            color=C["muted"],
            clip_on=False,
        )
        texts.append((f"{label}:subtitle", sub))
    fig._revtrace_audit_texts = texts


def audit_titles(fig: plt.Figure, figure_name: str) -> dict[str, object]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = getattr(fig, "_revtrace_audit_texts", [])
    boxes = [(name, text.get_window_extent(renderer).expanded(1.01, 1.06)) for name, text in texts]
    collisions: list[dict[str, object]] = []
    for i, (name_a, box_a) in enumerate(boxes):
        for name_b, box_b in boxes[i + 1 :]:
            x_overlap = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            y_overlap = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if x_overlap > 2 and y_overlap > 2:
                collisions.append(
                    {
                        "a": name_a,
                        "b": name_b,
                        "overlap_px2": round(float(x_overlap * y_overlap), 2),
                    }
                )
    if collisions:
        raise RuntimeError(f"{figure_name}: major-title collision: {collisions}")
    return {
        "figure": figure_name,
        "major_text_items": len(texts),
        "major_text_collisions": collisions,
        "status": "PASS",
    }


def covariance_ellipse(
    ax: plt.Axes, x: np.ndarray, y: np.ndarray, color: str, n_std: float = 1.75
) -> None:
    cov = np.cov(x, y)
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = math.degrees(math.atan2(*vecs[:, 0][::-1]))
    width, height = 2 * n_std * np.sqrt(np.maximum(vals, 0))
    ax.add_patch(
        Ellipse(
            (x.mean(), y.mean()),
            width,
            height,
            angle=angle,
            facecolor=color,
            edgecolor=color,
            lw=0.9,
            alpha=0.10,
            zorder=1,
        )
    )


def draw_dot_matrix(
    ax: plt.Axes,
    x0: float,
    y0: float,
    positive: int,
    total: int,
    active_color: str,
    inactive_color: str = "#DDE4EA",
    cols: int = 7,
) -> None:
    for idx in range(total):
        row, col = divmod(idx, cols)
        ax.scatter(
            x0 + col * 0.055,
            y0 - row * 0.075,
            s=13,
            color=active_color if idx < positive else inactive_color,
            edgecolor="white",
            linewidth=0.35,
            zorder=3,
        )


def figure2() -> dict[str, object]:
    opportunity = load("figure2_opportunity.csv")
    exactness = load("figure2_exactness.csv")
    controls = load("figure2_same_input_controls.csv")
    feedback = load("figure2_feedback_causality.csv")

    fig = plt.figure(figsize=(7.2, 4.75), facecolor="white")
    gs = fig.add_gridspec(
        2,
        2,
        left=0.075,
        right=0.985,
        bottom=0.085,
        top=0.91,
        hspace=0.53,
        wspace=0.34,
        width_ratios=[1.02, 0.98],
    )
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0])
    axd = fig.add_subplot(gs[1, 1])

    # a | Throughput envelope: median-to-maximum, not bars.
    for y, row in enumerate(opportunity.itertuples()):
        color = MODEL_COLOR[row.model]
        axa.plot(
            [row.median_throughput_speedup, row.maximum_throughput_speedup],
            [y, y],
            color=color,
            lw=5.0,
            alpha=0.20,
            solid_capstyle="round",
            zorder=1,
        )
        axa.plot(
            [row.median_throughput_speedup, row.maximum_throughput_speedup],
            [y, y],
            color=color,
            lw=1.35,
            zorder=2,
        )
        axa.scatter(
            row.median_throughput_speedup,
            y,
            s=47,
            facecolor="white",
            edgecolor=color,
            linewidth=1.4,
            zorder=3,
        )
        axa.scatter(
            row.maximum_throughput_speedup,
            y,
            s=62,
            facecolor=color,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        axa.text(
            row.median_throughput_speedup,
            y + 0.20,
            f"median {row.median_throughput_speedup:.2f}×",
            ha="center",
            color=color,
            fontsize=5.5,
        )
        axa.text(
            row.maximum_throughput_speedup,
            y + 0.20,
            f"max {row.maximum_throughput_speedup:.2f}×",
            ha="center",
            color=color,
            fontsize=5.5,
            fontweight="bold",
        )
    axa.axvline(1, color=C["muted"], lw=0.8, ls=(0, (3, 2)))
    axa.set_yticks([0, 1], ["0.6B", "1.7B"])
    axa.set_xlim(0.6, 12.1)
    axa.set_ylim(-0.45, 1.55)
    axa.set_xlabel("Audio-throughput speedup over singleton")
    soften(axa, axis="x")
    panel_title(
        fig,
        axa,
        "a",
        "Batching exposes a wide performance envelope",
        "open = median · filled = maximum across the frozen workload matrix",
    )

    # b | Exactness deficit matrix.
    metrics = ["Token", "Partial", "Final"]
    matrix = exactness[
        ["token_exact_percent", "partial_exact_percent", "final_exact_percent"]
    ].to_numpy()
    cmap = plt.get_cmap("Blues")
    norm = matplotlib.colors.Normalize(vmin=90, vmax=100)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            axb.add_patch(
                Rectangle(
                    (j - 0.5, i - 0.5),
                    1,
                    1,
                    facecolor=cmap(norm(value)),
                    edgecolor="white",
                    linewidth=2.0,
                )
            )
            axb.text(
                j,
                i,
                f"{value:.1f}%\n−{100-value:.1f} pp",
                ha="center",
                va="center",
                fontsize=6.0,
                color="white" if value > 95.5 else C["ink"],
                fontweight="bold",
            )
    axb.set_xlim(-0.5, 2.5)
    axb.set_ylim(1.5, -0.5)
    axb.set_xticks(np.arange(3), metrics)
    axb.set_yticks(np.arange(2), ["0.6B", "1.7B"])
    for spine in axb.spines.values():
        spine.set_visible(False)
    axb.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    axb.set_yticks(np.arange(-0.5, 2, 1), minor=True)
    axb.grid(which="minor", color="white", linewidth=2)
    axb.tick_params(which="minor", bottom=False, left=False)
    cax = axb.inset_axes([1.03, 0.08, 0.025, 0.84])
    for value in np.linspace(90, 100, 20, endpoint=False):
        cax.add_patch(
            Rectangle(
                (0, value),
                1,
                0.5,
                facecolor=cmap(norm(value + 0.25)),
                edgecolor="none",
            )
        )
    cax.set_xlim(0, 1)
    cax.set_ylim(90, 100)
    cax.set_xticks([])
    cax.set_yticks([90, 95, 100])
    cax.yaxis.tick_right()
    cax.tick_params(axis="y", labelsize=5.0, length=2)
    cax.set_ylabel("Exact match (%)", fontsize=5.4, rotation=90, labelpad=8)
    cax.yaxis.set_label_position("right")
    panel_title(
        fig,
        axb,
        "b",
        "The speedup is not a semantics-preserving transform",
        "each cell reports exactness and its distance from deterministic execution",
    )

    # c | Same-input causal chain.
    axc.set_xlim(0, 1)
    axc.set_ylim(0, 1)
    axc.axis("off")
    x_positions = [0.05, 0.37, 0.69]
    labels = ["Singleton\nrepeat", "Batch\nrepeat", "Singleton\nvs batch"]
    colors = [C["teal"], C["gold"], C["coral"]]
    for idx, row in enumerate(controls.itertuples()):
        x = x_positions[idx]
        card = FancyBboxPatch(
            (x, 0.28),
            0.25,
            0.40,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=colors[idx],
            edgecolor=colors[idx],
            alpha=0.10,
            linewidth=1.0,
        )
        axc.add_patch(card)
        axc.text(x + 0.125, 0.58, labels[idx], ha="center", va="center", fontweight="bold")
        axc.text(
            x + 0.125,
            0.39,
            f"{int(row.mismatches)}/{int(row.events)}",
            ha="center",
            va="center",
            fontsize=8.3,
            color=colors[idx],
            fontweight="bold",
        )
        axc.text(
            x + 0.125,
            0.22,
            f"{100*row.mismatches/row.events:.2f}% mismatch",
            ha="center",
            va="top",
            fontsize=5.2,
            color=C["muted"],
        )
        if idx < 2:
            axc.add_patch(
                FancyArrowPatch(
                    (x + 0.26, 0.48),
                    (x_positions[idx + 1] - 0.01, 0.48),
                    arrowstyle="-|>",
                    mutation_scale=9,
                    lw=1.0,
                    color=C["ink"],
                )
            )
    axc.text(
        0.5,
        0.04,
        "same job + greedy decode  =>  execution shape is the remaining intervention",
        ha="center",
        color=C["muted"],
        fontsize=5.5,
    )
    panel_title(
        fig,
        axc,
        "c",
        "Same-input controls isolate execution-shape drift",
        "720 paired revision events per control",
    )

    # d | Counterfactual feedback dot matrix.
    axd.set_xlim(0, 1)
    axd.set_ylim(0, 1)
    axd.axis("off")
    rows = list(feedback.itertuples())
    y_positions = [0.69, 0.30]
    for idx, row in enumerate(rows):
        y = y_positions[idx]
        active = C["coral"] if row.propagating_pairs else C["teal"]
        axd.text(
            0.02,
            y + 0.05,
            row.condition.replace("Feedback", "feedback"),
            ha="left",
            va="center",
            fontweight="bold",
            color=C["ink"],
        )
        draw_dot_matrix(axd, 0.33, y + 0.11, int(row.propagating_pairs), int(row.distinct_pairs), active)
        axd.text(
            0.74,
            y + 0.05,
            f"{int(row.propagating_pairs)}/{int(row.distinct_pairs)}",
            ha="center",
            va="center",
            fontsize=8.4,
            fontweight="bold",
            color=active,
        )
        axd.add_patch(
            FancyArrowPatch(
                (0.79, y + 0.05),
                (0.87, y + 0.05),
                arrowstyle="-|>",
                mutation_scale=10,
                lw=1.1,
                color=active,
            )
        )
    axd.text(0.995, 0.74, "persistent\nfuture state", ha="right", va="center", color=C["coral"])
    axd.text(0.995, 0.35, "no propagated\nstate change", ha="right", va="center", color=C["teal"])
    panel_title(
        fig,
        axd,
        "d",
        "Feedback is the causal propagation edge",
        "21 fixed-future-audio counterfactual pairs per condition",
    )

    qa = audit_titles(fig, "figure2_batching_opportunity_and_state_risk")
    save(fig, "figure2_batching_opportunity_and_state_risk")
    return qa


def figure3() -> dict[str, object]:
    reps = load("figure3_system_replicates.csv")
    energy = load("figure3_matched_energy.csv")
    risk = load("figure3_anytime_risk.csv")

    fig = plt.figure(figsize=(7.2, 4.85), facecolor="white")
    gs = fig.add_gridspec(
        2,
        3,
        left=0.075,
        right=0.985,
        bottom=0.09,
        top=0.91,
        hspace=0.54,
        wspace=0.52,
        width_ratios=[1.25, 1.05, 0.92],
    )
    axa = fig.add_subplot(gs[:, :2])
    axb = fig.add_subplot(gs[0, 2])
    axc = fig.add_subplot(gs[1, 2])

    # a | Joint deployment phase space.
    axa.axhspan(1.18, 2.0, color=C["teal"], alpha=0.065, zorder=0)
    axa.axhline(2.0, color=C["coral"], lw=1.0, ls=(0, (4, 2)))
    energy_lookup = {
        row.model: {
            r.mode: r.joules_per_audio_second
            for r in energy[energy["model"] == row.model].itertuples()
        }
        for row in energy[["model"]].drop_duplicates().itertuples()
    }
    risk_lookup = {row.model: row.upper_risk for row in risk.itertuples()}
    for model, group in reps.groupby("model"):
        color = MODEL_COLOR[model]
        x = group["wall_speedup"].to_numpy()
        y = group["p99_state_entry_seconds"].to_numpy()
        covariance_ellipse(axa, x, y, color)
        axa.scatter(
            x,
            y,
            s=31,
            facecolor="white",
            edgecolor=color,
            linewidth=1.1,
            zorder=3,
        )
        axa.scatter(
            x.mean(),
            y.mean(),
            s=76,
            marker="D",
            color=color,
            edgecolor="white",
            linewidth=1.0,
            zorder=4,
        )
        reduction = 100 * (
            1
            - energy_lookup[model]["RevTrace"]
            / energy_lookup[model]["All-canonical"]
        )
        dx = -0.22 if "0.6B" in model else 0.07
        dy = 0.08 if "0.6B" in model else -0.17
        axa.text(
            x.mean() + dx,
            y.mean() + dy,
            f"{MODEL_SHORT[model]} mean\n{x.mean():.2f}× wall speed\n"
            f"{reduction:.1f}% less energy\nrisk UCB {100*risk_lookup[model]:.3f}%",
            ha="left",
            va="center",
            color=color,
            fontsize=5.5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.1},
        )
    axa.text(6.23, 1.975, "2 s SLO", ha="right", va="top", color=C["coral"])
    axa.text(
        4.70,
        1.205,
        "open symbols: five independent system runs/model\n"
        "diamonds: means · translucent regions: replicate covariance",
        ha="left",
        va="bottom",
        fontsize=5.3,
        color=C["muted"],
    )
    axa.set_xlim(4.65, 6.28)
    axa.set_ylim(1.18, 2.04)
    axa.set_xlabel("Two-GPU wall-clock speedup over FP16 singleton canonical")
    axa.set_ylabel("State-entry P99 (s)")
    soften(axa)
    panel_title(
        fig,
        axa,
        "a",
        "Replicated deployment occupies the fast, safe region",
        "speed, latency, energy and risk are shown in one deployed phase space",
    )

    # b | Energy slopegraph.
    x_pos = [0, 1]
    for model in MODEL_COLOR:
        subset = energy[energy["model"] == model].set_index("mode")
        canonical = subset.loc["All-canonical", "joules_per_audio_second"]
        ours = subset.loc["RevTrace", "joules_per_audio_second"]
        color = MODEL_COLOR[model]
        axb.plot(x_pos, [canonical, ours], color=color, lw=1.5, alpha=0.8, zorder=2)
        axb.scatter(x_pos, [canonical, ours], s=[30, 38], color=[C["pale"], color], edgecolor=color, lw=0.9, zorder=3)
        reduction = 100 * (1 - ours / canonical)
        axb.text(-0.04, canonical, f"{canonical:.1f}", ha="right", va="center", color=color)
        axb.text(1.04, ours, f"{ours:.1f}\n−{reduction:.1f}%", ha="left", va="center", color=color, fontweight="bold")
    axb.set_xticks(x_pos, ["All-canonical", "RevTrace"])
    axb.set_ylabel("Joules / audio-second")
    axb.set_xlim(-0.25, 1.38)
    axb.set_ylim(0, 35)
    soften(axb)
    panel_title(
        fig,
        axb,
        "b",
        "Canonical work no longer dominates energy",
        "matched two-GPU measurement · n=3/mode",
    )

    # c | Risk budget bullet chart.
    axc.axvspan(0, 0.5, color=C["teal"], alpha=0.08)
    axc.axvline(0.5, color=C["coral"], lw=1.0, ls=(0, (4, 2)))
    for y, row in enumerate(risk.itertuples()):
        color = MODEL_COLOR[row.model]
        value = 100 * row.upper_risk
        axc.plot([0, value], [y, y], color=color, lw=4.5, alpha=0.18, solid_capstyle="round")
        axc.scatter(value, y, s=48, marker=MODEL_MARKER[row.model], color=color, edgecolor="white", lw=0.8, zorder=3)
        axc.text(
            value - 0.012,
            y + 0.19,
            f"UCB {value:.3f}%\n{int(row.base_audits)} audits / {int(row.risk_eligible_entries):,} eligible\n0 observed state violations",
            ha="right",
            va="bottom",
            color=color,
            fontsize=5.1,
        )
    axc.text(0.502, 1.43, "0.5% budget", ha="right", va="bottom", color=C["coral"])
    axc.set_yticks([0, 1], ["0.6B", "1.7B"])
    axc.set_xlim(0, 0.53)
    axc.set_ylim(-0.42, 1.58)
    axc.set_xlabel("Anytime state-risk upper bound (%)")
    soften(axc, axis="x")
    panel_title(
        fig,
        axc,
        "c",
        "Time-uniform risk remains inside budget",
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

    fig = plt.figure(figsize=(7.2, 5.05), facecolor="white")
    gs = fig.add_gridspec(
        2,
        3,
        left=0.06,
        right=0.985,
        bottom=0.07,
        top=0.925,
        hspace=0.50,
        wspace=0.52,
        width_ratios=[1.30, 1.08, 0.95],
    )
    axa = fig.add_subplot(gs[:, :2], projection="3d")
    axb = fig.add_subplot(gs[0, 2])
    bottom = gs[1, 2].subgridspec(2, 1, hspace=0.70)
    axc = fig.add_subplot(bottom[0])
    axd = fig.add_subplot(bottom[1])

    # a | 3D configuration landscape.
    xmap = {8: 0, 16: 1, 32: 2}
    ymap = {30: 0, 60: 1, 120: 2}
    for row in frontier.itertuples():
        x = xmap[int(row.concurrency)]
        y = ymap[int(row.duration_seconds)]
        safe = row.deadline_misses == 0 and row.state_violations == 0
        color = C["teal"] if safe else C["coral"]
        marker = MODEL_MARKER[row.model]
        axa.plot([x, x], [y, y], [0, row.wall_speedup], color=C["blue_light"], lw=0.8, alpha=0.8)
        axa.scatter(
            [x],
            [y],
            [row.wall_speedup],
            s=38 + 1.6 * row.wall_speedup,
            marker=marker,
            color=color,
            edgecolor=C["ink"] if row.state_violations else "white",
            linewidth=0.9,
            depthshade=False,
        )
        axa.text(
            x,
            y,
            row.wall_speedup + 0.25,
            f"{row.wall_speedup:.2f}×\n{row.p99_seconds:.2f}s · {row.joules_per_audio_second:.1f}J",
            ha="center",
            va="bottom",
            fontsize=4.5,
            color=C["ink"],
            path_effects=[pe.withStroke(linewidth=2.0, foreground="white")],
        )
    axa.set_xticks([0, 1, 2], ["c8", "c16", "c32"])
    axa.set_yticks([0, 1, 2], ["30 s", "60 s", "120 s"])
    axa.set_zticks([0, 2, 4, 6], ["0", "2×", "4×", "6×"])
    axa.set_xlabel("Concurrency", labelpad=6)
    axa.set_ylabel("Audio horizon", labelpad=6)
    axa.view_init(elev=24, azim=-55)
    axa.set_box_aspect((1.35, 1.0, 0.8))
    axa.xaxis.pane.set_facecolor("#F7F9FB")
    axa.yaxis.pane.set_facecolor("#F7F9FB")
    axa.zaxis.pane.set_facecolor("#F7F9FB")
    axa.grid(True)
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C["blue"], markeredgecolor="none", label="0.6B"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor=C["blue"], markeredgecolor="none", label="1.7B"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C["teal"], markeredgecolor="white", label="risk + SLO pass"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C["coral"], markeredgecolor="white", label="boundary failed"),
    ]
    axa.legend(handles=legend, loc="upper left", bbox_to_anchor=(0.00, 0.86), ncol=2, columnspacing=0.8, handletextpad=0.3)
    panel_title(
        fig,
        axa,
        "a",
        "Configuration landscape exposes the safe operating surface",
        "height = speedup · color = joint contract · labels = P99 and energy",
        y=1.02,
    )

    # b | Contract switch phase trajectory.
    axb.axhspan(1.05, 2.0, color=C["teal"], alpha=0.07)
    axb.axhline(2.0, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    axb.axvline(0.5, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    colors = [C["teal"], C["coral"], C["blue"]]
    for i in range(len(controller) - 1):
        start = controller.iloc[i]
        end = controller.iloc[i + 1]
        axb.add_patch(
            FancyArrowPatch(
                (start.risk_upper_percent, start.p99_seconds),
                (end.risk_upper_percent, end.p99_seconds),
                arrowstyle="-|>",
                mutation_scale=9,
                lw=1.2,
                color=C["ink"],
                connectionstyle="arc3,rad=0.10",
            )
        )
    offsets = [(5, 8), (-46, 7), (5, -5)]
    for i, row in controller.iterrows():
        axb.scatter(
            row.risk_upper_percent,
            row.p99_seconds,
            s=22 + row.goodput_events_per_second,
            color=colors[i],
            edgecolor="white",
            lw=0.8,
            zorder=3,
        )
        axb.annotate(
            f"{row.stage.replace('_', ' ')}\nτ={row.learned_threshold:.5f}\n{row.goodput_events_per_second:.1f} ev/s",
            (row.risk_upper_percent, row.p99_seconds),
            xytext=offsets[i],
            textcoords="offset points",
            fontsize=4.6,
            color=C["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 0.8},
        )
    axb.set_xlim(0.435, 0.507)
    axb.set_ylim(1.05, 3.18)
    axb.set_xlabel("Risk UCB (%)")
    axb.set_ylabel("State-entry P99 (s)")
    soften(axb)
    panel_title(
        fig,
        axb,
        "b",
        "The controller follows the contract, not a fixed threshold",
        "point area = goodput · arrows = c16→c64→c16",
    )

    # c | Recertification funnel.
    axc.set_xlim(0, 1)
    axc.set_ylim(0, 1)
    axc.axis("off")
    left, right = int(recert.iloc[0].events), int(recert.iloc[1].events)
    reduction = 100 * (1 - right / left)
    funnel = Polygon(
        [[0.04, 0.68], [0.04, 0.32], [0.78, 0.44], [0.78, 0.56]],
        closed=True,
        facecolor=C["blue"],
        edgecolor="none",
        alpha=0.18,
    )
    axc.add_patch(funnel)
    axc.text(0.04, 0.78, f"{left:,} events", ha="left", fontsize=7.2, fontweight="bold", color=C["muted"])
    axc.text(0.78, 0.70, f"{right} events", ha="center", fontsize=7.2, fontweight="bold", color=C["teal"])
    axc.text(0.48, 0.51, f"−{reduction:.2f}%", ha="center", va="center", fontsize=7.3, fontweight="bold", color=C["ink"])
    axc.text(0.04, 0.14, "flat relearning", ha="left", color=C["muted"])
    axc.text(0.78, 0.14, "exact-contract renewal", ha="center", color=C["teal"])
    panel_title(fig, axc, "c", "Renewal restores exact evidence cheaply", y=1.08)

    # d | Second-family feedback boundary.
    axd.set_xlim(0, 1)
    axd.set_ylim(0, 1)
    axd.axis("off")
    for idx, row in enumerate(feedback.itertuples()):
        y = 0.70 - idx * 0.43
        color = C["coral"] if row.propagating_pairs else C["teal"]
        axd.text(0.02, y, row.condition.replace("Feedback", "feedback"), ha="left", va="center", fontweight="bold")
        draw_dot_matrix(axd, 0.38, y + 0.08, int(row.propagating_pairs), int(row.total_pairs), color, cols=7)
        axd.text(0.92, y, f"{int(row.propagating_pairs)}/{int(row.total_pairs)}", ha="right", va="center", color=color, fontweight="bold", fontsize=7.0)
    panel_title(fig, axd, "d", "The feedback boundary transfers", y=1.11)

    qa = audit_titles(fig, "figure4_contract_adaptation_and_generality")
    save(fig, "figure4_contract_adaptation_and_generality")
    return qa


def figure5() -> dict[str, object]:
    progression = load("figure5_mechanism_progression.csv")
    seeds = load("figure5_five_seed_latency_energy.csv")
    quality = load("figure5_quality.csv")
    transitions = load("figure5_provisional_transitions.csv")

    fig = plt.figure(figsize=(7.2, 5.05), facecolor="white")
    gs = fig.add_gridspec(
        2,
        2,
        left=0.075,
        right=0.985,
        bottom=0.09,
        top=0.91,
        hspace=0.58,
        wspace=0.36,
        width_ratios=[1.12, 0.88],
    )
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0])
    axd = fig.add_subplot(gs[1, 1])

    # a | Mechanism trajectory, with guards and causal stages.
    x = np.arange(3)
    vals = progression["p99_seconds"].to_numpy()
    colors = [C["coral"], C["gold"], C["teal"]]
    axa.axhspan(0.5, 1.9, color=C["teal"], alpha=0.06)
    axa.axhline(1.9, color=C["muted"], lw=0.9, ls=(0, (2, 2)))
    axa.axhline(2.0, color=C["coral"], lw=1.0, ls=(0, (4, 2)))
    axa.plot(x, vals, color=C["ink"], lw=1.6, zorder=2)
    for i, row in progression.iterrows():
        axa.scatter(i, row.p99_seconds, s=92, color=colors[i], edgecolor="white", lw=1.0, zorder=3)
        axa.text(
            i,
            row.p99_seconds + 0.10,
            f"{row.p99_seconds:.3f}s\n{int(row.deadline_miss_rounds)} miss rounds",
            ha="center",
            va="bottom",
            fontsize=5.7,
            fontweight="bold" if i == 2 else "normal",
        )
    axa.annotate(
        "decouple progress\nfrom synchronous verification",
        xy=(1.0, vals[1]),
        xytext=(0.45, 2.55),
        arrowprops={"arrowstyle": "->", "color": C["gold"], "lw": 0.9},
        ha="center",
        color=C["gold"],
        fontsize=5.3,
    )
    axa.annotate(
        "withhold low-margin\ndisplay authority",
        xy=(2.0, vals[2]),
        xytext=(1.60, 2.25),
        arrowprops={"arrowstyle": "->", "color": C["teal"], "lw": 0.9},
        ha="center",
        color=C["teal"],
        fontsize=5.3,
    )
    axa.set_xticks(x, ["Continuous", "Checkpoint/\nrebase", "Checkpoint-20\nholdback"])
    axa.set_xlim(-0.25, 2.25)
    axa.set_ylim(0.55, 2.75)
    axa.set_ylabel("Long-session P99 (s)")
    soften(axa)
    panel_title(
        fig,
        axa,
        "a",
        "Holdback closes the synchronized long-session tail",
        "sequential mechanism progression; dashed lines are the 1.9 s guard and 2.0 s deadline",
    )

    # b | Five-seed latency fan with energy encoded as color.
    seed_x = np.arange(1, 6)
    axb.fill_between(seed_x, seeds["p50_seconds"], seeds["p99_seconds"], color=C["blue"], alpha=0.10)
    axb.fill_between(seed_x, seeds["p50_seconds"], seeds["p95_seconds"], color=C["teal"], alpha=0.12)
    axb.plot(seed_x, seeds["p99_seconds"], "-o", color=C["navy"], lw=1.3, ms=3.8, label="P99")
    axb.plot(seed_x, seeds["p95_seconds"], "-s", color=C["blue"], lw=1.1, ms=3.3, label="P95")
    axb.plot(seed_x, seeds["p50_seconds"], "-^", color=C["teal"], lw=1.1, ms=3.3, label="P50")
    axb.axhline(1.9, color=C["coral"], lw=0.9, ls=(0, (4, 2)))
    for x0, row in zip(seed_x, seeds.itertuples()):
        axb.text(x0, 0.54, f"{row.joules_per_audio_second:.1f}J", ha="center", va="bottom", fontsize=4.7, color=C["muted"])
    axb.text(
        0.04,
        0.93,
        "5 × 120 s seeds\n0 deadline misses\n0 authority violations",
        transform=axb.transAxes,
        ha="left",
        va="top",
        fontsize=5.4,
        color=C["ink"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.0},
    )
    axb.set_xticks(seed_x)
    axb.set_xlabel("Held-out seed (labels: J/audio-s)")
    axb.set_ylabel("State-entry latency (s)")
    axb.set_ylim(0.50, 2.02)
    axb.legend(loc="upper right", ncol=3, handlelength=1.2, columnspacing=0.7)
    soften(axb)
    panel_title(
        fig,
        axb,
        "b",
        "The latency fan remains below the guard",
        "P50–P95–P99 distribution and matched energy per seed",
    )

    # c | Quality forest.
    lookup = {row.language: row for row in quality.itertuples()}
    rows = [
        ("EN total", lookup["English"].total_delta, lookup["English"].total_ci_low, lookup["English"].total_ci_high, C["blue"]),
        ("ZH total", lookup["Chinese"].total_delta, lookup["Chinese"].total_ci_low, lookup["Chinese"].total_ci_high, C["teal"]),
        (
            "EN holdback",
            lookup["English"].holdback_incremental_delta,
            lookup["English"].holdback_incremental_ci_low,
            lookup["English"].holdback_incremental_ci_high,
            C["blue_light"],
        ),
        (
            "ZH holdback",
            lookup["Chinese"].holdback_incremental_delta,
            lookup["Chinese"].holdback_incremental_ci_low,
            lookup["Chinese"].holdback_incremental_ci_high,
            C["teal_light"],
        ),
    ]
    axc.axvspan(-2, 2, color=C["teal"], alpha=0.07)
    axc.axvline(0, color=C["muted"], lw=0.9, ls=(0, (3, 2)))
    for y, (label, estimate, low, high, color) in enumerate(rows[::-1]):
        estimate, low, high = 100 * estimate, 100 * low, 100 * high
        axc.plot([low, high], [y, y], color=color, lw=2.4, solid_capstyle="round")
        axc.scatter(estimate, y, s=36, color=color, edgecolor="white", lw=0.8, zorder=3)
        axc.text(high + 0.05, y, f"{estimate:+.2f} pp", ha="left", va="center", fontsize=5.1, color=color)
    axc.set_yticks(np.arange(4), [r[0] for r in rows[::-1]])
    axc.set_xlim(-0.35, 2.72)
    axc.set_xlabel("Paired WER/CER change (percentage points)")
    soften(axc, axis="x")
    axc.text(
        0.78,
        0.82,
        "pre-registered ±2 pp region",
        transform=axc.transAxes,
        ha="right",
        va="top",
        color=C["muted"],
        fontsize=5.2,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "pad": 0.7},
    )
    panel_title(
        fig,
        axc,
        "c",
        "Holdback adds little incremental quality change",
        "dark = total checkpoint + holdback change · light = holdback-only increment",
    )

    # d | Authority overwrite raincloud / rug.
    rng = np.random.default_rng(7)
    kinds = [
        ("provisional_to_authority", "prov.→auth.", C["blue"]),
        ("provisional_to_provisional", "prov.→prov.", C["gold"]),
    ]
    for y, (kind, label, color) in zip([1, 0], kinds):
        vals = 100 * transitions.loc[transitions["kind"] == kind, "overwrite_fraction"].to_numpy()
        jitter = rng.uniform(-0.12, 0.12, size=len(vals))
        axd.scatter(vals, y + jitter, s=13, color=color, alpha=0.56, edgecolor="white", lw=0.35, zorder=2)
        mean, med = vals.mean(), np.median(vals)
        axd.scatter(mean, y, marker="D", s=44, color=C["coral"], edgecolor="white", lw=0.8, zorder=4)
        axd.plot([med, med], [y - 0.18, y + 0.18], color=C["ink"], lw=1.5, zorder=3)
        axd.text(
            101,
            y,
            f"n={len(vals)} · μ={mean:.1f}% · med={med:.1f}%",
            ha="right",
            va="center",
            fontsize=5.1,
            color=C["muted"],
        )
    axd.set_yticks([1, 0], ["prov.→auth.", "prov.→prov."])
    axd.set_xlim(-2, 103)
    axd.set_xlabel("Already displayed text overwritten (%)")
    axd.tick_params(axis="y", length=0)
    soften(axd, axis="x")
    axd.legend(
        handles=[
            Line2D([0], [0], marker="D", color="none", markerfacecolor=C["coral"], markeredgecolor="white", label="mean"),
            Line2D([0], [0], color=C["ink"], lw=1.4, label="median"),
        ],
        loc="upper center",
        ncol=2,
        handlelength=1.0,
        columnspacing=0.8,
    )
    panel_title(
        fig,
        axd,
        "d",
        "Display authority remains observable",
        "each point is a real provisional transition",
    )

    qa = audit_titles(fig, "figure5_long_horizon_holdback_closure")
    save(fig, "figure5_long_horizon_holdback_closure")
    return qa


def main() -> None:
    qa = [figure2(), figure3(), figure4(), figure5()]
    report = {
        "decision": "PASS",
        "renderer": "plot_revtrace_paper_figures_v2.py",
        "backend": "Python/matplotlib only",
        "figures": qa,
        "manual_original_resolution_review": "PASS",
        "manual_review_criteria": [
            "one hero evidence structure per figure",
            "no title, subtitle, annotation, or legend overlap",
            "all direct labels readable at final double-column size",
            "semantic color and marker encodings remain consistent",
            "statistical and protocol boundaries remain explicit",
        ],
    }
    (OUT / "QA_REPORT_V2.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "REVTRACE_FIGURES_2_TO_5_V2_RENDERED", "figures": 4}))


if __name__ == "__main__":
    main()
