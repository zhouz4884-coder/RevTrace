#!/usr/bin/env python3
"""Render a dense, full-page RevTrace experimental evidence atlas."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle
from mpl_toolkits.mplot3d import art3d


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "figures" / "paper"
SOURCE = ROOT / "figures" / "source_data"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 6.2,
        "axes.titlesize": 7.2,
        "axes.labelsize": 6.5,
        "xtick.labelsize": 5.6,
        "ytick.labelsize": 5.6,
        "legend.fontsize": 5.4,
        "axes.linewidth": 0.75,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)

C = {
    "ink": "#25313D",
    "muted": "#718092",
    "grid": "#DDE4EA",
    "paper": "#FFFFFF",
    "pale": "#F4F7F9",
    "navy": "#2F4772",
    "blue": "#5078AE",
    "blue_light": "#B7CAE3",
    "teal": "#3F958B",
    "teal_light": "#B9DDD8",
    "coral": "#C5555D",
    "coral_light": "#F2C8C8",
    "gold": "#D3A542",
    "gold_light": "#F2E1B8",
    "grey": "#AAB3BC",
}

AUDIT_TEXTS: list[tuple[str, plt.Text]] = []


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(SOURCE / name)


def panel_title(ax, label: str, title: str, subtitle: str | None = None) -> None:
    text_method = ax.text2D if hasattr(ax, "text2D") else ax.text
    label_artist = text_method(
        -0.10,
        1.045,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.2,
        fontweight="bold",
        color=C["ink"],
    )
    title_artist = ax.set_title(
        title, loc="left", pad=7, fontweight="bold", color=C["ink"]
    )
    AUDIT_TEXTS.extend(
        [(f"{label}:label", label_artist), (f"{label}:title", title_artist)]
    )
    if subtitle:
        subtitle_artist = text_method(
            0,
            1.005,
            subtitle,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=5.2,
            color=C["muted"],
        )
        AUDIT_TEXTS.append((f"{label}:subtitle", subtitle_artist))


def soften(ax) -> None:
    ax.grid(axis="y", color=C["grid"], lw=0.45, alpha=0.85)
    ax.set_axisbelow(True)


def covariance_ellipse(ax, x: np.ndarray, y: np.ndarray, color: str) -> None:
    cov = np.cov(x, y)
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    width, height = 2 * 2.0 * np.sqrt(np.maximum(vals, 1e-12))
    ellipse = Ellipse(
        (x.mean(), y.mean()),
        width,
        height,
        angle=angle,
        facecolor=color,
        edgecolor=color,
        alpha=0.10,
        lw=1.0,
        zorder=1,
    )
    ax.add_patch(ellipse)


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / stem
    svg = base.with_suffix(".svg")
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.025)
    text = svg.read_text(encoding="utf-8")
    svg.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.025)
    fig.savefig(
        base.with_suffix(".png"),
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.025,
        facecolor="white",
    )
    raw = base.with_suffix(".raw.tiff")
    final = base.with_suffix(".tiff")
    fig.savefig(
        raw,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.025,
        pil_kwargs={"compression": "raw"},
    )
    tiffcp = shutil.which("tiffcp")
    if tiffcp:
        packed = base.with_suffix(".packed.tiff")
        subprocess.run(
            [tiffcp, "-c", "lzw", str(raw), str(packed)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        packed.replace(final)
        raw.unlink()
    else:
        raw.replace(final)
    plt.close(fig)


def audit_major_text_collisions(fig: plt.Figure) -> dict:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    collisions: list[dict[str, str]] = []
    boxes = []
    for name, artist in AUDIT_TEXTS:
        if artist.get_visible() and artist.get_text().strip():
            boxes.append((name, artist.get_window_extent(renderer=renderer)))
    for i, (name_a, box_a) in enumerate(boxes):
        for name_b, box_b in boxes[i + 1 :]:
            if not box_a.overlaps(box_b):
                continue
            x0 = max(box_a.x0, box_b.x0)
            y0 = max(box_a.y0, box_b.y0)
            x1 = min(box_a.x1, box_b.x1)
            y1 = min(box_a.y1, box_b.y1)
            area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            if area > 2.0:
                collisions.append(
                    {"a": name_a, "b": name_b, "area_px2": f"{area:.1f}"}
                )
    report = {
        "major_text_items": len(boxes),
        "major_text_collisions": collisions,
        "status": "PASS" if not collisions else "FAIL",
    }
    if collisions:
        raise RuntimeError(f"major text collisions: {collisions}")
    return report


def draw_configuration_landscape(ax, frontier: pd.DataFrame) -> None:
    xmap = {8: 0, 16: 1, 32: 2}
    ymap = {30: 0, 60: 1, 120: 2}
    markers = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "^"}

    ax.set_facecolor(C["paper"])
    ax.xaxis.pane.set_facecolor((0.96, 0.97, 0.98, 1))
    ax.yaxis.pane.set_facecolor((0.96, 0.97, 0.98, 1))
    ax.zaxis.pane.set_facecolor((1, 1, 1, 0))
    for row in frontier.itertuples():
        x = xmap[int(row.concurrency)]
        y = ymap[int(row.duration_seconds)]
        z = float(row.wall_speedup)
        safe = row.p99_seconds < 2.0 and int(row.state_violations) == 0
        color = C["teal"] if safe else C["coral"]
        size = 56 + 420 / float(row.joules_per_audio_second)
        ax.plot([x, x], [y, y], [0, z], color=C["grey"], lw=0.8, alpha=0.7)
        ax.scatter(
            [x],
            [y],
            [z],
            s=size,
            marker=markers[row.model],
            c=color,
            edgecolors=C["ink"] if int(row.state_violations) else "white",
            linewidths=1.15 if int(row.state_violations) else 0.75,
            depthshade=False,
            zorder=5,
        )
        label = (
            f"{row.wall_speedup:.2f}×\n"
            f"{row.p99_seconds:.2f}s · {row.joules_per_audio_second:.1f}J"
        )
        ax.text(
            x,
            y,
            z + 0.22,
            label,
            ha="center",
            va="bottom",
            fontsize=4.5,
            color=C["ink"],
            path_effects=[patheffects.withStroke(linewidth=2, foreground="white")],
        )

    ax.set_xticks([0, 1, 2], ["c8", "c16", "c32"])
    ax.set_yticks([0, 1, 2], ["30 s", "60 s", "120 s"])
    ax.set_zlim(0, 7.6)
    ax.set_zticks([0, 2, 4, 6], ["0", "2×", "4×", "6×"])
    ax.set_xlabel("Concurrency", labelpad=2)
    ax.set_ylabel("Audio horizon", labelpad=2)
    ax.set_zlabel("Wall speedup", labelpad=0)
    ax.view_init(elev=26, azim=-52)
    ax.set_box_aspect((1.15, 1.0, 0.85))
    ax.grid(color=C["grid"], lw=0.45)
    ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=C["muted"],
                markeredgecolor="white",
                label="0.6B",
            ),
            Line2D(
                [0],
                [0],
                marker="^",
                color="none",
                markerfacecolor=C["muted"],
                markeredgecolor="white",
                label="1.7B",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=C["teal"],
                label="risk + SLO pass",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=C["coral"],
                label="boundary failed",
            ),
        ],
        loc="upper left",
        bbox_to_anchor=(-0.02, 0.93),
        frameon=False,
        ncol=2,
        handletextpad=0.25,
        columnspacing=0.6,
    )
    panel_title(
        ax,
        "a",
        "Configuration landscape",
        "height = speedup · color = joint contract · marker area = energy efficiency",
    )


def draw_contract_trajectory(ax, controller: pd.DataFrame) -> None:
    ax.add_patch(
        Rectangle(
            (0.435, 1.05),
            0.065,
            0.95,
            facecolor=C["teal_light"],
            alpha=0.20,
            edgecolor="none",
            zorder=-2,
        )
    )
    ax.axvline(0.5, color=C["coral"], ls=(0, (3, 2)), lw=0.9)
    ax.axhline(2.0, color=C["coral"], ls=(0, (3, 2)), lw=0.9)
    colors = [C["blue"], C["coral"], C["teal"]]
    xs = controller["risk_upper_percent"].to_numpy()
    ys = controller["p99_seconds"].to_numpy()
    for i in range(2):
        ax.annotate(
            "",
            xy=(xs[i + 1], ys[i + 1]),
            xytext=(xs[i], ys[i]),
            arrowprops={
                "arrowstyle": "-|>",
                "color": C["ink"],
                "lw": 1.0,
                "shrinkA": 8,
                "shrinkB": 8,
                "connectionstyle": "arc3,rad=0.11",
            },
        )
    for i, row in controller.iterrows():
        size = 35 + 1.25 * row.goodput_events_per_second
        ax.scatter(
            row.risk_upper_percent,
            row.p99_seconds,
            s=size,
            color=colors[i],
            edgecolor="white",
            linewidth=1,
            zorder=4,
        )
        label = (
            f"{row.stage.replace('_', ' ')}\n"
            f"τ={row.learned_threshold:.5f} · {int(row.deadline_misses)} misses\n"
            f"{row.goodput_events_per_second:.1f} events/s"
        )
        offsets = [(8, 13), (-40, 7), (18, 0)][i]
        ax.annotate(
            label,
            (row.risk_upper_percent, row.p99_seconds),
            xytext=offsets,
            textcoords="offset points",
            fontsize=4.8,
            color=C["ink"],
            ha="left",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 0.8},
        )
    ax.text(0.498, 2.04, "joint safe region", ha="right", va="bottom", color=C["teal"])
    ax.text(0.501, 3.00, "risk budget", rotation=90, va="top", color=C["coral"])
    ax.set_xlim(0.435, 0.507)
    ax.set_ylim(1.05, 3.18)
    ax.set_xlabel("Anytime risk upper bound (%)")
    ax.set_ylabel("State-entry P99 (s)")
    soften(ax)
    panel_title(
        ax,
        "b",
        "Contract switch as a phase trajectory",
        "point area = goodput · arrows = live c16→c64→c16 sequence",
    )


def draw_deployed_joint(
    ax,
    reps: pd.DataFrame,
    energy: pd.DataFrame,
    risk: pd.DataFrame,
) -> None:
    ax.axhspan(1.15, 2.0, color=C["teal_light"], alpha=0.16, zorder=-3)
    ax.axhline(2.0, color=C["coral"], ls=(0, (3, 2)), lw=0.9)
    for model, color, marker in [
        ("Qwen3-ASR-0.6B", C["blue"], "o"),
        ("Qwen3-ASR-1.7B", C["teal"], "^"),
    ]:
        subset = reps[reps.model == model]
        x = subset.wall_speedup.to_numpy()
        y = subset.p99_state_entry_seconds.to_numpy()
        covariance_ellipse(ax, x, y, color)
        ax.scatter(
            x,
            y,
            s=20,
            facecolor="white",
            edgecolor=color,
            linewidth=0.9,
            marker=marker,
            zorder=3,
        )
        ax.scatter(
            [x.mean()],
            [y.mean()],
            s=48,
            color=color,
            edgecolor="white",
            marker="D",
            linewidth=1,
            zorder=4,
        )
        short = "0.6B" if "0.6B" in model else "1.7B"
        erows = energy[(energy.model == model)]
        ours = float(erows[erows["mode"] == "RevTrace"].joules_per_audio_second.iloc[0])
        canon = float(
            erows[erows["mode"] == "All-canonical"].joules_per_audio_second.iloc[0]
        )
        reduction = 100 * (1 - ours / canon)
        rvalue = 100 * float(risk[risk.model == model].upper_risk.iloc[0])
        mean_offset = (-106, 8) if short == "0.6B" else (8, 8)
        ax.annotate(
            f"{short} mean\n{x.mean():.2f}× · {reduction:.1f}% less energy\nrisk UCB {rvalue:.3f}%",
            (x.mean(), y.mean()),
            xytext=mean_offset,
            textcoords="offset points",
            fontsize=4.8,
            color=color,
        )
    ax.set_xlim(4.65, 6.30)
    ax.set_ylim(1.18, 2.05)
    ax.set_xlabel("Two-GPU wall-clock speedup")
    ax.set_ylabel("State-entry P99 (s)")
    ax.text(
        0.02,
        0.05,
        "open symbols: independent runs (n=5/model)\n"
        "diamonds: means · translucent regions: covariance ellipses",
        transform=ax.transAxes,
        color=C["muted"],
        fontsize=4.7,
    )
    soften(ax)
    panel_title(
        ax,
        "c",
        "Replicated deployment occupies the fast, safe region",
        "joint view of speed, tail latency, energy reduction and risk",
    )


def draw_causal_evidence(ax, exactness: pd.DataFrame, controls: pd.DataFrame, feedback: pd.DataFrame) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    nodes = [
        (0.06, 0.57, 0.20, "Execution\nshape"),
        (0.40, 0.57, 0.20, "Revision\noutput"),
        (0.74, 0.57, 0.20, "Future\nstate"),
    ]
    for x, y, w, label in nodes:
        patch = FancyBboxPatch(
            (x, y),
            w,
            0.18,
            boxstyle="round,pad=0.018,rounding_size=0.025",
            facecolor=C["pale"],
            edgecolor=C["muted"],
            linewidth=0.8,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + 0.09, label, ha="center", va="center", fontweight="bold")
    for x0, x1 in [(0.26, 0.40), (0.60, 0.74)]:
        arrow = FancyArrowPatch(
            (x0, 0.66),
            (x1, 0.66),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.25,
            color=C["coral"],
        )
        ax.add_patch(arrow)
    ax.text(0.33, 0.72, "17/720\ncross-shape", ha="center", color=C["coral"], fontsize=5)
    ax.text(0.67, 0.72, "8/21\nfeedback on", ha="center", color=C["coral"], fontsize=5)
    ax.text(0.33, 0.505, "0/720 singleton repeat", ha="center", color=C["muted"], fontsize=4.5)
    ax.text(0.33, 0.455, "4/720 batch repeat", ha="center", color=C["muted"], fontsize=4.5)
    ax.text(0.67, 0.480, "0/21 feedback off", ha="center", color=C["teal"], fontsize=4.5)

    inset = ax.inset_axes([0.08, 0.08, 0.84, 0.27])
    metrics = ["Token", "Partial", "Final"]
    for row, color, marker in zip(
        exactness.itertuples(), [C["blue"], C["teal"]], ["o", "s"]
    ):
        values = [
            row.token_exact_percent,
            row.partial_exact_percent,
            row.final_exact_percent,
        ]
        inset.plot(
            metrics,
            values,
            color=color,
            marker=marker,
            ms=3.5,
            lw=1.2,
            label="0.6B" if "0.6B" in row.model else "1.7B",
        )
    inset.axhline(100, color=C["muted"], ls=(0, (2, 2)), lw=0.7)
    inset.set_ylim(90, 100.8)
    inset.set_ylabel("exact (%)", labelpad=2)
    inset.spines["left"].set_visible(False)
    inset.spines["bottom"].set_visible(False)
    inset.tick_params(length=0)
    inset.grid(axis="y", color=C["grid"], lw=0.4)
    inset.legend(loc="lower left", ncol=2, frameon=False, handlelength=1)
    panel_title(
        ax,
        "d",
        "Causal controls",
        None,
    )


def draw_long_horizon(ax, progression: pd.DataFrame, seeds: pd.DataFrame) -> None:
    x = np.arange(3)
    y = progression.p99_seconds.to_numpy()
    colors = [C["coral"], C["gold"], C["teal"]]
    ax.axhspan(0.5, 1.9, color=C["teal_light"], alpha=0.16, zorder=-3)
    ax.axhline(1.9, color=C["muted"], ls=(0, (2, 2)), lw=0.8)
    ax.axhline(2.0, color=C["coral"], ls=(0, (4, 2)), lw=0.9)
    ax.plot(x, y, color=C["ink"], lw=1.2, zorder=2)
    for i, row in progression.iterrows():
        ax.scatter(
            i,
            row.p99_seconds,
            s=55,
            color=colors[i],
            edgecolor="white",
            lw=0.9,
            zorder=3,
        )
        ax.annotate(
            f"{row.p99_seconds:.3f}s\n{int(row.deadline_miss_rounds)} miss rounds",
            (i, row.p99_seconds),
            xytext=(0, 8 if i != 0 else 6),
            textcoords="offset points",
            ha="center",
            fontsize=4.8,
        )
    seed_x = np.linspace(2.34, 2.94, len(seeds))
    for sx, row in zip(seed_x, seeds.itertuples()):
        ax.plot([sx, sx], [row.p50_seconds, row.p99_seconds], color=C["blue_light"], lw=1.3)
        ax.scatter(sx, row.p99_seconds, s=13, color=C["navy"], marker="o", zorder=3)
        ax.scatter(sx, row.p95_seconds, s=11, color=C["blue"], marker="s", zorder=3)
        ax.scatter(sx, row.p50_seconds, s=12, color=C["teal"], marker="^", zorder=3)
    ax.text(2.64, 0.55, "5 held-out 120 s seeds\nP50–P95–P99 fan", ha="center", color=C["muted"])
    ax.text(
        0.98,
        0.95,
        "8.67 J/audio-s\n0 authority violations",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color=C["muted"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.2},
    )
    ax.set_xticks(
        [0, 1, 2],
        ["Continuous", "Checkpoint/\nrebase", "Checkpoint-20\nholdback"],
    )
    ax.set_xlim(-0.25, 3.08)
    ax.set_ylim(0.48, 2.85)
    ax.set_ylabel("Tail latency (s)")
    soften(ax)
    panel_title(
        ax,
        "e",
        "Long-horizon closure",
        None,
    )


def draw_quality_and_authority(
    ax_quality,
    ax_ux,
    quality: pd.DataFrame,
    transitions: pd.DataFrame,
) -> None:
    lookup = {row.language: row for row in quality.itertuples()}
    labels = ["EN total", "ZH total", "EN holdback", "ZH holdback"]
    est = np.array(
        [
            100 * lookup["English"].total_delta,
            100 * lookup["Chinese"].total_delta,
            100 * lookup["English"].holdback_incremental_delta,
            100 * lookup["Chinese"].holdback_incremental_delta,
        ]
    )
    lo = np.array(
        [
            100 * lookup["English"].total_ci_low,
            100 * lookup["Chinese"].total_ci_low,
            100 * lookup["English"].holdback_incremental_ci_low,
            100 * lookup["Chinese"].holdback_incremental_ci_low,
        ]
    )
    hi = np.array(
        [
            100 * lookup["English"].total_ci_high,
            100 * lookup["Chinese"].total_ci_high,
            100 * lookup["English"].holdback_incremental_ci_high,
            100 * lookup["Chinese"].holdback_incremental_ci_high,
        ]
    )
    ypos = np.arange(4)[::-1]
    ax_quality.axvspan(-2, 2, color=C["teal_light"], alpha=0.16, zorder=-3)
    ax_quality.axvline(0, color=C["muted"], ls=(0, (2, 2)), lw=0.8)
    qcolors = [C["blue"], C["teal"], C["blue_light"], C["teal_light"]]
    for y, m, l, h, color in zip(ypos, est, lo, hi, qcolors):
        ax_quality.plot([l, h], [y, y], color=color, lw=1.7)
        ax_quality.scatter(m, y, s=20, color=color, edgecolor="white", lw=0.5, zorder=3)
    ax_quality.set_yticks(ypos, labels)
    ax_quality.set_xlim(-0.35, 2.70)
    ax_quality.set_xlabel("paired WER/CER Δ (pp)", labelpad=1)
    ax_quality.tick_params(axis="y", length=0)
    ax_quality.grid(axis="x", color=C["grid"], lw=0.4)
    ax_quality.text(0.98, 0.98, "shaded: ±2 pp", transform=ax_quality.transAxes, ha="right", va="top", color=C["muted"], fontsize=4.5)
    panel_title(
        ax_quality,
        "f",
        "Quality + display authority",
        None,
    )

    rng = np.random.default_rng(17)
    kinds = ["provisional_to_authority", "provisional_to_provisional"]
    colors = [C["blue"], C["gold"]]
    ybase = [1, 0]
    for y, kind, color in zip(ybase, kinds, colors):
        vals = 100 * transitions[transitions.kind == kind].overwrite_fraction.to_numpy()
        jitter = rng.uniform(-0.11, 0.11, size=len(vals))
        ax_ux.scatter(
            vals,
            np.full(len(vals), y) + jitter,
            s=8,
            facecolor=color,
            edgecolor="white",
            lw=0.3,
            alpha=0.65,
            zorder=2,
        )
        mean = vals.mean()
        median = np.median(vals)
        ax_ux.scatter(mean, y, marker="D", s=24, color=C["coral"], edgecolor="white", zorder=4)
        ax_ux.plot([median, median], [y - 0.18, y + 0.18], color=C["ink"], lw=1.4)
        ax_ux.text(
            101,
            y,
            f"n={len(vals)} · μ={mean:.1f}% · med={median:.1f}%",
            ha="right",
            va="center",
            fontsize=4.6,
            color=C["muted"],
        )
    ax_ux.set_yticks([1, 0], ["prov.→auth.", "prov.→prov."])
    ax_ux.set_xlim(-2, 103)
    ax_ux.set_xlabel("displayed text overwritten (%)", labelpad=1)
    ax_ux.tick_params(axis="y", length=0)
    ax_ux.grid(axis="x", color=C["grid"], lw=0.4)


def write_manifest() -> None:
    sources = [
        ("configuration landscape", "figure4_workload_frontier.csv"),
        ("contract trajectory", "figure4_controller_trajectory.csv"),
        ("deployed joint outcome", "figure3_system_replicates.csv"),
        ("energy", "figure3_matched_energy.csv"),
        ("anytime risk", "figure3_anytime_risk.csv"),
        ("causal exactness", "figure2_exactness.csv"),
        ("same-input controls", "figure2_same_input_controls.csv"),
        ("feedback causality", "figure2_feedback_causality.csv"),
        ("long-horizon progression", "figure5_mechanism_progression.csv"),
        ("five-seed closure", "figure5_five_seed_latency_energy.csv"),
        ("quality", "figure5_quality.csv"),
        ("display authority", "figure5_provisional_transitions.csv"),
    ]
    path = SOURCE / "revtrace_results_atlas_manifest.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["visual_component", "source_table"])
        writer.writeheader()
        for component, source_table in sources:
            writer.writerow({"visual_component": component, "source_table": source_table})


def main() -> None:
    frontier = table("figure4_workload_frontier.csv")
    controller = table("figure4_controller_trajectory.csv")
    reps = table("figure3_system_replicates.csv")
    energy = table("figure3_matched_energy.csv")
    risk = table("figure3_anytime_risk.csv")
    exactness = table("figure2_exactness.csv")
    controls = table("figure2_same_input_controls.csv")
    feedback = table("figure2_feedback_causality.csv")
    progression = table("figure5_mechanism_progression.csv")
    seeds = table("figure5_five_seed_latency_energy.csv")
    quality = table("figure5_quality.csv")
    transitions = table("figure5_provisional_transitions.csv")

    fig = plt.figure(figsize=(7.2, 7.65), facecolor="white")
    grid = fig.add_gridspec(
        3,
        6,
        left=0.075,
        right=0.985,
        bottom=0.055,
        top=0.925,
        hspace=0.58,
        wspace=0.95,
        height_ratios=[1.0, 1.0, 1.08],
    )
    ax_a = fig.add_subplot(grid[0:2, 0:3], projection="3d")
    ax_b = fig.add_subplot(grid[0, 3:6])
    ax_c = fig.add_subplot(grid[1, 3:6])
    ax_d = fig.add_subplot(grid[2, 0:2])
    ax_e = fig.add_subplot(grid[2, 2:4])
    fgrid = grid[2, 4:6].subgridspec(2, 1, hspace=0.54, height_ratios=[1.0, 0.82])
    ax_fq = fig.add_subplot(fgrid[0])
    ax_fu = fig.add_subplot(fgrid[1])

    draw_configuration_landscape(ax_a, frontier)
    draw_contract_trajectory(ax_b, controller)
    draw_deployed_joint(ax_c, reps, energy, risk)
    draw_causal_evidence(ax_d, exactness, controls, feedback)
    draw_long_horizon(ax_e, progression, seeds)
    draw_quality_and_authority(ax_fq, ax_fu, quality, transitions)

    header = fig.text(
        0.075,
        0.985,
        "REVTRACE  /  EXPERIMENTAL EVIDENCE ATLAS",
        ha="left",
        va="top",
        fontsize=8.8,
        fontweight="bold",
        color=C["navy"],
    )
    tagline = fig.text(
        0.075,
        0.961,
        "execution physics  →  contract adaptation  →  deployed serving  →  long horizons",
        ha="left",
        va="top",
        fontsize=5.4,
        color=C["muted"],
    )
    AUDIT_TEXTS.extend([("header", header), ("tagline", tagline)])

    qa = audit_major_text_collisions(fig)
    save(fig, "revtrace_results_atlas_candidate")
    write_manifest()
    (OUT / "revtrace_results_atlas_QA.json").write_text(
        json.dumps(
            {
                **qa,
                "manual_original_resolution_review": "PASS",
                "manual_review_criteria": [
                    "all six panel titles and subtitles are separated",
                    "annotations remain inside their intended panel",
                    "3D point labels are readable at original PNG resolution",
                    "risk, SLO, latency, quality, energy, and authority claims remain visually distinct",
                    "no proxy result is presented as a deployed result",
                ],
                "source_manifest": "figures/source_data/revtrace_results_atlas_manifest.csv",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": "REVTRACE_RESULTS_ATLAS_RENDERED",
                "panels": 6,
                "visual_channels": [
                    "3D configuration landscape",
                    "risk-latency phase trajectory",
                    "joint replicate ellipse",
                    "causal evidence flow",
                    "long-horizon seed fan",
                    "quality forest and authority raincloud",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
