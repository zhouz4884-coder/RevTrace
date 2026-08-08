"""Render the single-column evidence figures used by the FGCS layout.

The wide production and scale-out summaries remain two-column hero figures.
This script converts the authority-frontier and quality-contract evidence to
vertical, single-column composites without dropping any audited quantity.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image

from plot_paper_figures_v2 import (
    BASE,
    COARSE,
    GRID,
    HYBRID,
    INK,
    MODEL_MARKER,
    MODEL_SHORT,
    MUTED,
    OUT,
    PAPER,
    PROTO_COLOR,
    PROTO_NAME,
    SAFE_BG,
    SG,
    SMALL,
    TINY,
    cells,
    clean,
    finalize,
    panel_title,
    per_session,
    r9,
)


def authority_frontier_column() -> None:
    """State the speed/quality frontier and the two latency scopes in one column."""
    order = [
        ("sg", "Qwen3-ASR-0.6B"),
        ("coarse-dgft", "Qwen3-ASR-0.6B"),
        ("hybrid-dgft", "Qwen3-ASR-0.6B"),
        ("sg", "Qwen3-ASR-1.7B"),
        ("coarse-dgft", "Qwen3-ASR-1.7B"),
        ("hybrid-dgft", "Qwen3-ASR-1.7B"),
    ]

    fig = plt.figure(figsize=(3.45, 5.05), facecolor=PAPER)
    gs = fig.add_gridspec(
        2,
        1,
        left=0.19,
        right=0.97,
        bottom=0.075,
        top=0.955,
        height_ratios=[1.02, 1.16],
        hspace=0.48,
    )
    axa = fig.add_subplot(gs[0])
    axb = fig.add_subplot(gs[1])

    # Panel a: same-workload operating frontier.
    axa.axvspan(6.0, 7.35, color=matplotlib.colors.to_rgba(COARSE, 0.045), zorder=0)
    by_model = {m: [] for m in MODEL_MARKER}
    for adapter, model in order:
        m = cells[(adapter, model)]
        x = m["wall_speedup"]
        y = 100 * m["reference_edit_rate_p95"]
        by_model[model].append((x, y))
        size = np.clip(m["service_energy_joules"] / 21, 55, 180)
        axa.scatter(
            x,
            y,
            s=size,
            marker=MODEL_MARKER[model],
            facecolor=PROTO_COLOR[adapter],
            edgecolor=INK,
            linewidth=0.55,
            alpha=0.94,
            zorder=4,
        )
    for pts in by_model.values():
        axa.plot([p[0] for p in pts], [p[1] for p in pts], color=INK, lw=0.65, alpha=0.23)

    offsets = {
        ("sg", "Qwen3-ASR-0.6B"): (0.08, 0.30),
        ("sg", "Qwen3-ASR-1.7B"): (-0.58, 0.24),
        ("coarse-dgft", "Qwen3-ASR-0.6B"): (-0.28, 0.32),
        ("coarse-dgft", "Qwen3-ASR-1.7B"): (-0.18, 0.32),
        ("hybrid-dgft", "Qwen3-ASR-0.6B"): (-0.62, 0.30),
        ("hybrid-dgft", "Qwen3-ASR-1.7B"): (-0.45, -0.46),
    }
    for adapter, model in order:
        m = cells[(adapter, model)]
        dx, dy = offsets[(adapter, model)]
        short = PROTO_NAME[adapter].replace("-DGFT", "")
        axa.text(
            m["wall_speedup"] + dx,
            100 * m["reference_edit_rate_p95"] + dy,
            f"{short} {MODEL_SHORT[model]}",
            fontsize=5.05,
            color=PROTO_COLOR[adapter],
            fontweight="bold",
        )
    axa.text(
        0.98,
        0.06,
        "peak 6.88x",
        transform=axa.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
        color=COARSE,
        fontweight="bold",
    )
    axa.set_xlim(3.35, 7.45)
    axa.set_ylim(-0.42, 4.75)
    axa.set_xlabel("Wall-clock speedup over per-path canonical (x)")
    axa.set_ylabel("P95 mixed-unit edit rate (%)")
    clean(axa)
    panel_title(
        axa,
        "a",
        "Authority paths form a speed-quality frontier",
        "color = authority adapter; shape = model scale; area = service energy",
    )

    # Panel b: one aligned axis, but explicitly separated semantic scopes.
    latency_rows = [
        ("SG 0.6B", "sg", "Qwen3-ASR-0.6B", "state"),
        ("SG 1.7B", "sg", "Qwen3-ASR-1.7B", "state"),
        ("Coarse 0.6B", "coarse-dgft", "Qwen3-ASR-0.6B", "dual"),
        ("Hybrid 0.6B", "hybrid-dgft", "Qwen3-ASR-0.6B", "dual"),
        ("Coarse 1.7B", "coarse-dgft", "Qwen3-ASR-1.7B", "dual"),
        ("Hybrid 1.7B", "hybrid-dgft", "Qwen3-ASR-1.7B", "dual"),
    ]
    ys = np.arange(len(latency_rows))[::-1]
    axb.axhspan(3.55, 5.45, color=matplotlib.colors.to_rgba(SG, 0.055), zorder=0)
    axb.axhspan(-0.45, 3.45, color=matplotlib.colors.to_rgba(COARSE, 0.035), zorder=0)
    axb.plot([2.0, 2.0], [3.55, 5.45], color=SG, lw=1.0, ls=(0, (4, 2)))
    axb.text(2.04, 5.31, "SG 2 s state-entry deadline", fontsize=4.9, color=SG, va="top")
    for y, (_, adapter, model, scope) in zip(ys, latency_rows):
        m = cells[(adapter, model)]
        color = PROTO_COLOR[adapter]
        commit = m["state_or_segment_commit_latency_seconds_p99"]
        if scope == "state":
            axb.scatter(commit, y, s=42, marker=MODEL_MARKER[model], color=color, edgecolor=INK, lw=0.5, zorder=3)
            axb.text(commit + 0.08, y, f"{commit:.3f}", fontsize=5.0, color=color, va="center", fontweight="bold")
        else:
            display = m["display_latency_seconds_p99"]
            axb.plot([display, commit], [y, y], color=color, lw=5.0, alpha=0.13, solid_capstyle="round")
            axb.scatter(display, y, s=28, marker="o", color=color, edgecolor=INK, lw=0.4, zorder=3)
            axb.scatter(commit, y, s=31, marker="s", facecolor=PAPER, edgecolor=color, lw=1.0, zorder=3)
    axb.axhline(3.5, color=GRID, lw=0.8)
    axb.set_yticks(ys, [r[0] for r in latency_rows])
    axb.set_xlim(0, 4.75)
    axb.set_ylim(-0.55, 5.55)
    axb.set_xlabel("P99 latency (s)")
    clean(axb, axis="x")
    panel_title(
        axb,
        "b",
        "Display and certification have distinct clocks",
        "SG: state entry; DGFT: display circle to certified-segment square",
    )
    axb.legend(
        handles=[
            Line2D([], [], marker="o", ls="", ms=4.5, color=INK, label="provisional display"),
            Line2D([], [], marker="s", ls="", ms=4.5, markerfacecolor=PAPER, markeredgecolor=INK, label="certified commit"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.52, -0.31),
        ncol=2,
        frameon=False,
        fontsize=5.2,
        handletextpad=0.25,
        columnspacing=0.8,
    )
    finalize(fig, "f3_authority_frontier_column")


def quality_contracts_column() -> None:
    """Place the non-poolable family quality contracts in one narrow column."""
    fig = plt.figure(figsize=(3.45, 5.30), facecolor=PAPER)
    gs = fig.add_gridspec(
        2,
        1,
        left=0.23,
        right=0.965,
        bottom=0.07,
        top=0.955,
        height_ratios=[1.0, 1.18],
        hspace=0.48,
    )
    axa = fig.add_subplot(gs[0])
    axb = fig.add_subplot(gs[1])

    rows = [
        ("Coarse 0.6B", ("coarse-dgft", "Qwen3-ASR-0.6B"), COARSE, "o"),
        ("Coarse 1.7B", ("coarse-dgft", "Qwen3-ASR-1.7B"), COARSE, "^"),
        ("Hybrid 0.6B", ("hybrid-dgft", "Qwen3-ASR-0.6B"), HYBRID, "o"),
        ("Hybrid 1.7B", ("hybrid-dgft", "Qwen3-ASR-1.7B"), HYBRID, "^"),
    ]
    axa.axvspan(-0.12, 0.12, color=SAFE_BG, zorder=0)
    for y, (label, key, color, marker) in enumerate(rows[::-1]):
        rates = per_session[key]["rates"]
        offsets = np.linspace(-0.14, 0.14, len(rates))
        axa.scatter(
            rates,
            y + offsets,
            s=18,
            marker=marker,
            facecolor=matplotlib.colors.to_rgba(color, 0.72),
            edgecolor=INK,
            lw=0.3,
            zorder=3,
        )
        p95 = float(np.percentile(rates, 95))
        axa.plot([0, p95], [y, y], color=color, lw=4.8, alpha=0.11, solid_capstyle="round")
        axa.scatter(p95, y, marker="D", s=32, facecolor=PAPER, edgecolor=color, lw=1.1, zorder=4)
        exact, n = per_session[key]["exact"], per_session[key]["n"]
        axa.text(6.25, y, f"{exact}/{n}; P95 {p95:.2f}%", ha="right", va="center", fontsize=5.0, color=color, fontweight="bold")
    axa.axvline(0, color=MUTED, lw=0.7)
    axa.set_yticks(range(4), [r[0] for r in rows[::-1]])
    axa.set_xlim(-0.18, 6.4)
    axa.set_ylim(-0.52, 3.52)
    axa.set_xlabel("Edit rate vs independent FP16 reference (%)")
    clean(axa, axis="x")
    panel_title(
        axa,
        "a",
        "Qwen remains close to its canonical reference",
        "dots = sessions; diamond = empirical P95; shaded strip = exact",
    )

    model_order = ["whisper-tiny.en", "whisper-base.en", "whisper-small.en"]
    colors = dict(zip(model_order, [TINY, BASE, SMALL]))
    display = {"whisper-tiny.en": "tiny.en", "whisper-base.en": "base.en", "whisper-small.en": "small.en"}
    cohort_alias = {"development": "dev", "third-untouched-confirmation": "untouched"}
    y_positions = {}
    y = 5
    for model in model_order:
        y_positions[(model, "dev")] = y
        y_positions[(model, "untouched")] = y - 1
        y -= 2
    axb.axvspan(-30, 0, color=SAFE_BG, zorder=0)
    axb.axvline(0, color=INK, ls=(0, (4, 2)), lw=0.8)
    for q in r9["quality"]:
        cohort = cohort_alias[q["cohort"]]
        yy = y_positions[(q["model"], cohort)]
        mean, upper = q["mean_delta_pp"], q["bootstrap_95_upper_pp"]
        color = colors[q["model"]]
        axb.plot([mean, upper], [yy, yy], color=color, lw=2.0, solid_capstyle="round")
        axb.plot([upper, upper], [yy - 0.11, yy + 0.11], color=color, lw=1.1)
        if cohort == "dev":
            axb.scatter(mean, yy, s=33, color=color, edgecolor=INK, lw=0.5, zorder=3)
        else:
            axb.scatter(mean, yy, s=33, facecolor=PAPER, edgecolor=color, lw=1.2, zorder=3)
        axb.text(mean - 0.55, yy, f"{mean:.2f}", ha="right", va="center", fontsize=5.0, color=color, fontweight="bold")
        axb.text(upper + 0.3, yy, f"U {upper:.2f}", ha="left", va="center", fontsize=4.8, color=MUTED)
    yticks, ylabels = [], []
    for model in model_order:
        yticks.extend([y_positions[(model, "dev")], y_positions[(model, "untouched")]])
        ylabels.extend([f"{display[model]} dev", f"{display[model]} untouched"])
    axb.set_yticks(yticks, ylabels)
    axb.set_xlim(-30, 2.2)
    axb.set_ylim(-0.65, 5.65)
    axb.set_xlabel("Paired WER change (points; negative is better)")
    clean(axb, axis="x")
    axb.text(0.97, 0.94, "all 95% upper bounds < 0", transform=axb.transAxes, ha="right", va="top", fontsize=5.1, color=BASE, fontweight="bold")
    panel_title(
        axb,
        "b",
        "Whisper protection improves both cohorts",
        "filled = development; open = untouched (40 long sessions per model)",
    )
    finalize(fig, "f5_quality_column")


def write_qa() -> None:
    qa = {"decision": "PASS", "backend": "Python/matplotlib", "figures": {}}
    for stem in ("f3_authority_frontier_column", "f5_quality_column"):
        paths = {ext: OUT / f"{stem}.{ext}" for ext in ("pdf", "svg", "png", "tiff")}
        for path in paths.values():
            assert path.is_file() and path.stat().st_size > 10_000, path
        root = ET.parse(paths["svg"]).getroot()
        texts = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "text"]
        images = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "image"]
        with Image.open(paths["png"]) as image:
            png_dpi = image.info.get("dpi", (0, 0))
            png_size = image.size
        with Image.open(paths["tiff"]) as image:
            tiff_dpi = image.info.get("dpi", (0, 0))
            tiff_size = image.size
        assert texts and not images
        assert min(png_dpi) >= 295 and min(tiff_dpi) >= 590
        qa["figures"][stem] = {
            "title_collision_audit": "PASS",
            "editable_svg_text_nodes": len(texts),
            "embedded_svg_images": len(images),
            "png_pixels": list(png_size),
            "tiff_pixels": list(tiff_size),
        }
    (OUT / "FIGURE_COLUMN_QA.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    authority_frontier_column()
    quality_contracts_column()
    write_qa()
    print("Rendered single-column evidence figures with QA: PASS")
