"""Render refined, evidence-dense RevTrace paper Figures 3--5.

Every plotted quantity is read from the frozen R9/R10 evidence.  The visual
redesign separates non-comparable latency scopes, foregrounds the strongest
system results, and retains the paper's established Okabe--Ito color language.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle


REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Paper" / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7.2,
        "axes.labelsize": 7.4,
        "axes.titlesize": 8.0,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.2,
        "axes.linewidth": 0.75,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)

# Established color-blind-safe palette.
INK = "#172333"
MUTED = "#65758A"
GRID = "#D9E1EA"
PAPER = "#FFFFFF"
SG = "#D55E00"
COARSE = "#0072B2"
HYBRID = "#56B4E9"
TINY, BASE, SMALL = "#E69F00", "#009E73", "#CC79A7"
FAMILY_BG = "#F3F7FB"
WHISPER_BG = "#F8F6F8"
SAFE_BG = "#EAF6F2"

MODEL_MARKER = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "^"}
MODEL_SHORT = {"Qwen3-ASR-0.6B": "0.6B", "Qwen3-ASR-1.7B": "1.7B"}
PROTO_COLOR = {"sg": SG, "coarse-dgft": COARSE, "hybrid-dgft": HYBRID}
PROTO_NAME = {"sg": "SG", "coarse-dgft": "Coarse-DGFT", "hybrid-dgft": "Hybrid-DGFT"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


abl = load_json(REPO / "results/r10_qwen_cross_adapter/ablation_summary.json")
assert abl["decision"] == "COMPLETE_R10_ABLATION_WITH_SG_TAIL_BOUNDARY"
r9 = load_json(REPO / "results/r9_dgft/FINAL_REPORT_ONLINE.json")
assert r9["decision"] == "PASS_R9E_ONLINE_SUBMISSION_CLOSURE"

cells = {(c["adapter"], c["model"]): c["metrics"] for c in abl["cells"]}
per_session = {}
for key, fname in [
    (("coarse-dgft", "Qwen3-ASR-0.6B"), "qwen06-dgft-fp32batch.json"),
    (("coarse-dgft", "Qwen3-ASR-1.7B"), "qwen17-dgft-fp32batch.json"),
    (("hybrid-dgft", "Qwen3-ASR-0.6B"), "qwen06-hybrid-fp32batch.json"),
    (("hybrid-dgft", "Qwen3-ASR-1.7B"), "qwen17-hybrid-fp32batch.json"),
]:
    d = load_json(REPO / "results/r10_qwen_cross_adapter" / fname)
    per_session[key] = {
        "rates": np.sort([row["unit_edit_rate"] * 100 for row in d["final_comparison"]]),
        "exact": d["summary"]["final_exact_sessions"],
        "n": d["summary"]["final_sessions"],
    }
    assert per_session[key]["n"] == 16


def clean(ax, axis="both"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis=axis, color=GRID, lw=0.45, alpha=0.75, zorder=0)
    ax.set_axisbelow(True)


def panel_title(ax, label, heading, subtitle=None):
    lab = ax.text(-0.12, 1.055, label, transform=ax.transAxes, ha="left", va="bottom", fontsize=9.2, fontweight="bold", color=INK, clip_on=False)
    head = ax.text(0.0, 1.055, heading, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.0, fontweight="bold", color=INK, clip_on=False)
    artists = getattr(ax.figure, "_paper_title_artists", [])
    artists.extend([(f"{label}:label", lab), (f"{label}:heading", head)])
    if subtitle:
        sub = ax.text(0.0, 1.018, subtitle, transform=ax.transAxes, ha="left", va="top", fontsize=5.6, color=MUTED, clip_on=False)
        artists.append((f"{label}:subtitle", sub))
    ax.figure._paper_title_artists = artists


def badge(ax, xy, value, detail, color, width=0.42):
    x, y = xy
    ax.add_patch(
        FancyBboxPatch(
            (x, y), width, 0.12,
            transform=ax.transAxes,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=matplotlib.colors.to_rgba(color, 0.085),
            edgecolor=matplotlib.colors.to_rgba(color, 0.55),
            linewidth=0.65,
            clip_on=False,
        )
    )
    ax.text(x + 0.025, y + 0.077, value, transform=ax.transAxes, ha="left", va="center", fontsize=8.1, fontweight="bold", color=color, clip_on=False)
    ax.text(x + 0.025, y + 0.028, detail, transform=ax.transAxes, ha="left", va="center", fontsize=4.7, color=MUTED, clip_on=False)


def finalize(fig, stem):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    title_boxes = []
    for name, artist in getattr(fig, "_paper_title_artists", []):
        title_boxes.append((name, artist.get_window_extent(renderer).expanded(1.01, 1.03)))
    collisions = []
    for i, (name_a, box_a) in enumerate(title_boxes):
        for name_b, box_b in title_boxes[i + 1 :]:
            x_overlap = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            y_overlap = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if x_overlap > 2 and y_overlap > 2:
                collisions.append({"a": name_a, "b": name_b, "area_px2": round(float(x_overlap * y_overlap), 1)})
    if collisions:
        raise RuntimeError(f"title collision in {stem}: {collisions}")
    fig.patch.set_facecolor(PAPER)
    for suffix, dpi in (("pdf", None), ("svg", None), ("png", 300), ("tiff", 600)):
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.025, "facecolor": PAPER}
        if dpi:
            kwargs["dpi"] = dpi
        fig.savefig(OUT / f"{stem}.{suffix}", **kwargs)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: authority-granularity ladder and semantically separated latency.
# ---------------------------------------------------------------------------
def figure3():
    order = [
        ("sg", "Qwen3-ASR-0.6B"),
        ("coarse-dgft", "Qwen3-ASR-0.6B"),
        ("hybrid-dgft", "Qwen3-ASR-0.6B"),
        ("sg", "Qwen3-ASR-1.7B"),
        ("coarse-dgft", "Qwen3-ASR-1.7B"),
        ("hybrid-dgft", "Qwen3-ASR-1.7B"),
    ]

    fig = plt.figure(figsize=(7.2, 3.75), facecolor=PAPER)
    gs = fig.add_gridspec(2, 12, left=0.075, right=0.985, bottom=0.15, top=0.90, width_ratios=[1] * 12, height_ratios=[1.0, 1.14], hspace=0.56, wspace=0.75)
    axa = fig.add_subplot(gs[:, :7])
    axb = fig.add_subplot(gs[0, 7:])
    axc = fig.add_subplot(gs[1, 7:])

    # (a) Pareto map with paired model paths and compact legends.
    axa.axvspan(6.0, 7.35, color=matplotlib.colors.to_rgba(COARSE, 0.045), zorder=0)
    axa.text(7.30, 4.48, "HIGH-SPEED REGION", ha="right", va="top", fontsize=4.9, fontweight="bold", color=COARSE)
    by_model = {m: [] for m in MODEL_MARKER}
    for adapter, model in order:
        m = cells[(adapter, model)]
        x = m["wall_speedup"]
        y = 100 * m["reference_edit_rate_p95"]
        by_model[model].append((x, y, adapter))
        energy_size = np.clip(m["service_energy_joules"] / 18, 70, 270)
        axa.scatter(x, y, s=energy_size, marker=MODEL_MARKER[model], facecolor=PROTO_COLOR[adapter], edgecolor=INK, linewidth=0.65, alpha=0.93, zorder=4)
    for model, pts in by_model.items():
        # Thin path makes the per-model tradeoff trace legible without implying time.
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        axa.plot(xs, ys, color=INK, lw=0.7, alpha=0.24, zorder=2)
    labels = {
        ("sg", "Qwen3-ASR-0.6B"): (0.03, 0.42),
        ("sg", "Qwen3-ASR-1.7B"): (-0.34, 0.42),
        ("coarse-dgft", "Qwen3-ASR-0.6B"): (-0.18, 0.36),
        ("coarse-dgft", "Qwen3-ASR-1.7B"): (-0.05, 0.38),
        ("hybrid-dgft", "Qwen3-ASR-0.6B"): (0.04, 0.42),
        ("hybrid-dgft", "Qwen3-ASR-1.7B"): (-0.05, -0.58),
    }
    for adapter, model in order:
        m = cells[(adapter, model)]
        x, y = m["wall_speedup"], 100 * m["reference_edit_rate_p95"]
        dx, dy = labels[(adapter, model)]
        axa.text(x + dx, y + dy, f"{PROTO_NAME[adapter].replace('-DGFT','')} · {MODEL_SHORT[model]}", ha="left", va="center", fontsize=5.15, color=PROTO_COLOR[adapter], fontweight="bold")
    coarse06 = cells[("coarse-dgft", "Qwen3-ASR-0.6B")]
    coarse17 = cells[("coarse-dgft", "Qwen3-ASR-1.7B")]
    badge(axa, (0.53, 0.02), f"{coarse06['wall_speedup']:.2f}× / {coarse17['wall_speedup']:.2f}×", "Coarse-DGFT wall-clock · 0.6B / 1.7B", COARSE, width=0.44)
    axa.set_xlim(3.35, 7.45)
    axa.set_ylim(-0.42, 4.68)
    axa.set_xlabel("Wall-clock speedup over per-path canonical (×)")
    axa.set_ylabel("P95 mixed-unit edit rate (%) · lower is better")
    clean(axa)
    panel_title(axa, "a", "Authority granularity exposes a speed–quality–energy frontier", "color = authority adapter · shape = model scale · area = measured service energy")
    handles = [
        Line2D([], [], marker="o", ls="", ms=6, markerfacecolor=SG, markeredgecolor=INK, label="SG"),
        Line2D([], [], marker="o", ls="", ms=6, markerfacecolor=COARSE, markeredgecolor=INK, label="Coarse-DGFT"),
        Line2D([], [], marker="o", ls="", ms=6, markerfacecolor=HYBRID, markeredgecolor=INK, label="Hybrid-DGFT"),
        Line2D([], [], marker="o", ls="", ms=6, markerfacecolor="#C8D0D8", markeredgecolor=INK, label="0.6B"),
        Line2D([], [], marker="^", ls="", ms=6, markerfacecolor="#C8D0D8", markeredgecolor=INK, label="1.7B"),
    ]
    axa.legend(handles=handles, ncol=5, loc="lower left", bbox_to_anchor=(-0.01, -0.31), frameon=False, handletextpad=0.28, columnspacing=0.75, fontsize=5.5)

    # (b) SG-only state-entry latency. Deadline is scoped to this panel only.
    sg_rows = [("Qwen3-ASR-0.6B", 1), ("Qwen3-ASR-1.7B", 0)]
    axb.axvspan(0, 2.0, color=SAFE_BG, zorder=0)
    axb.axvline(2.0, color=SG, ls=(0, (4, 2)), lw=1.0)
    for model, y in sg_rows:
        val = cells[("sg", model)]["state_or_segment_commit_latency_seconds_p99"]
        axb.plot([0, val], [y, y], color=SG, lw=5.5, alpha=0.13, solid_capstyle="round")
        axb.scatter(val, y, marker=MODEL_MARKER[model], s=55, color=SG, edgecolor=INK, lw=0.6, zorder=3)
        axb.text(val + 0.07, y, f"{val:.3f}s", ha="left", va="center", color=SG, fontsize=5.4, fontweight="bold")
    axb.text(1.96, 1.39, "2s deadline", ha="right", va="top", fontsize=4.7, color=SG, fontweight="bold")
    axb.set_yticks([0, 1], ["1.7B", "0.6B"])
    axb.set_xlim(0, 3.25)
    axb.set_ylim(-0.42, 1.48)
    axb.set_xlabel("SG state-entry P99 (s)")
    clean(axb, axis="x")
    panel_title(axb, "b", "SG misses its own state-entry deadline", "same-granularity certification scope")

    # (c) DGFT display and segment-commit latency on their own axis.
    dgft_order = [
        ("hybrid-dgft", "Qwen3-ASR-1.7B"),
        ("coarse-dgft", "Qwen3-ASR-1.7B"),
        ("hybrid-dgft", "Qwen3-ASR-0.6B"),
        ("coarse-dgft", "Qwen3-ASR-0.6B"),
    ]
    for y, (adapter, model) in enumerate(dgft_order):
        m = cells[(adapter, model)]
        disp = m["display_latency_seconds_p99"]
        commit = m["state_or_segment_commit_latency_seconds_p99"]
        color = PROTO_COLOR[adapter]
        axc.plot([disp, commit], [y, y], color=color, lw=5.5, alpha=0.13, solid_capstyle="round")
        axc.scatter(disp, y, marker="o", s=38, color=color, edgecolor=INK, lw=0.5, zorder=3)
        axc.scatter(commit, y, marker="s", s=38, facecolor=PAPER, edgecolor=color, lw=1.2, zorder=3)
    short_adapter = {"coarse-dgft": "Coarse", "hybrid-dgft": "Hybrid"}
    axc.set_yticks(range(4), [f"{MODEL_SHORT[m]} · {short_adapter[a]}" for a, m in dgft_order])
    axc.set_xlim(0, 4.75)
    axc.set_ylim(-0.55, 3.55)
    axc.set_xlabel("DGFT latency (s) · display ●     certified segment commit □")
    clean(axc, axis="x")
    panel_title(axc, "c", "DGFT displays early while certification completes", "separate display and segment-commit scope; no SG deadline transfer")

    finalize(fig, "f3_pareto_latency")


# ---------------------------------------------------------------------------
# Figure 4: cross-family, per-contract production matrix.
# ---------------------------------------------------------------------------
def figure4():
    wcells = r9["service_cells"]
    assert len(wcells) == 16
    qwen_pts = [
        ("Coarse\n0.6B", COARSE, cells[("coarse-dgft", "Qwen3-ASR-0.6B")]),
        ("Coarse\n1.7B", COARSE, cells[("coarse-dgft", "Qwen3-ASR-1.7B")]),
        ("Hybrid\n0.6B", HYBRID, cells[("hybrid-dgft", "Qwen3-ASR-0.6B")]),
        ("Hybrid\n1.7B", HYBRID, cells[("hybrid-dgft", "Qwen3-ASR-1.7B")]),
    ]
    wmodels = ["whisper-tiny.en", "whisper-base.en", "whisper-small.en"]
    wlabels = ["tiny.en", "base.en", "small.en"]
    wcolors = dict(zip(wmodels, [TINY, BASE, SMALL]))
    metrics = [
        ("wall_speedup", "wall_speedup", "Wall-clock speedup (×)", (1.0, 7.35), "a"),
        ("gpu_normalized_speedup", "gpu_normalized_speedup", "GPU-normalized speedup (×)", (0.9, 3.72), "b"),
        ("energy_reduction_fraction", "energy_reduction", "Service-energy reduction (%)", (20, 63), "c"),
    ]

    q_peak = max(p[2]["wall_speedup"] for p in qwen_pts)
    w_wall = np.asarray([c["wall_speedup"] for c in wcells])
    w_energy = np.asarray([100 * c["energy_reduction"] for c in wcells])

    fig = plt.figure(figsize=(7.2, 4.9), facecolor=PAPER)
    gs = fig.add_gridspec(4, 2, left=0.10, right=0.985, bottom=0.105, top=0.95, height_ratios=[0.55, 1, 1, 1], width_ratios=[1.04, 1.0], hspace=0.42, wspace=0.20)

    # Family headers act as evidence cards and make contract scopes explicit.
    headers = [
        (fig.add_subplot(gs[0, 0]), COARSE, "QWEN3-ASR · R10 CANONICAL CONTRACT", f"peak {q_peak:.2f}×  ·  two scales  ·  Coarse + Hybrid"),
        (fig.add_subplot(gs[0, 1]), BASE, "WHISPER · R9.E PROTECTED-FEEDBACK CONTRACT", f"16/16 cells pass  ·  median {np.median(w_wall):.2f}×  ·  median energy −{np.median(w_energy):.1f}%"),
    ]
    for ax, color, heading, detail in headers:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.0, 0.10), 1.0, 0.80, boxstyle="round,pad=.012,rounding_size=.025", facecolor=matplotlib.colors.to_rgba(color, .075), edgecolor=matplotlib.colors.to_rgba(color, .5), linewidth=.7))
        ax.add_patch(Rectangle((0, .10), .018, .80, facecolor=color, edgecolor="none"))
        ax.text(.055, .63, heading, ha="left", va="center", fontsize=6.2, fontweight="bold", color=INK)
        ax.text(.055, .31, detail, ha="left", va="center", fontsize=5.1, color=color, fontweight="bold")

    for row, (qkey, wkey, ylabel, ylim, label) in enumerate(metrics, start=1):
        aq = fig.add_subplot(gs[row, 0])
        aw = fig.add_subplot(gs[row, 1], sharey=aq)
        aq.set_facecolor(FAMILY_BG)
        aw.set_facecolor(WHISPER_BG)
        if row < 3:
            aq.axhline(1.0, color=MUTED, lw=.75, ls=(0, (2, 2)), alpha=.75)
            aw.axhline(1.0, color=MUTED, lw=.75, ls=(0, (2, 2)), alpha=.75)

        # Qwen: lollipops emphasize exact values and adapter/model structure.
        for x, (name, color, m) in enumerate(qwen_pts):
            value = m[qkey] * (100 if qkey == "energy_reduction_fraction" else 1)
            base = ylim[0]
            aq.vlines(x, base, value, color=color, lw=5.2, alpha=.13)
            marker = "o" if "0.6B" in name else "^"
            aq.scatter(x, value, s=48, marker=marker, color=color, edgecolor=INK, lw=.55, zorder=3)
            aq.text(x, value + (ylim[1] - ylim[0]) * .035, f"{value:.2f}{'%' if row == 3 else '×'}", ha="center", va="bottom", fontsize=4.75, color=color, fontweight="bold")
        aq.set_xticks(range(4), [p[0] for p in qwen_pts] if row == 3 else ["", "", "", ""])
        aq.set_ylim(*ylim)
        aq.set_ylabel(ylabel)
        clean(aq, axis="y")
        aq.text(-.24, .50, label, transform=aq.transAxes, ha="center", va="center", fontsize=9.0, fontweight="bold", color=INK, clip_on=False)

        # Whisper: compact distribution + all 16 audited production cells.
        for x, model in enumerate(wmodels):
            subset = [c for c in wcells if c["model"] == model]
            vals = np.asarray([c[wkey] * (100 if wkey == "energy_reduction" else 1) for c in subset])
            rng = np.random.default_rng(20260804 + row * 10 + x)
            jitter = rng.uniform(-.13, .13, size=len(vals))
            for xv, v, c in zip(x + jitter, vals, subset):
                marker = "s" if c["arrival"] == "poisson" else "o"
                aw.scatter(xv, v, s=22, marker=marker, color=wcolors[model], edgecolor=INK, lw=.35, alpha=.88, zorder=3)
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            aw.vlines(x, q1, q3, color=INK, lw=3.2, alpha=.22, zorder=2)
            aw.scatter(x, med, marker="D", s=34, color=PAPER, edgecolor=wcolors[model], lw=1.2, zorder=4)
            aw.text(x, min(ylim[1] - .04 * (ylim[1]-ylim[0]), vals.max() + .04 * (ylim[1]-ylim[0])), f"med {med:.2f}{'%' if row == 3 else '×'}", ha="center", va="bottom", fontsize=4.5, color=wcolors[model], fontweight="bold")
        aw.set_xticks(range(3), wlabels if row == 3 else ["", "", ""])
        aw.tick_params(axis="y", left=False, labelleft=False)
        clean(aw, axis="y")
        aw.spines["left"].set_visible(False)

    legend = [
        Line2D([], [], marker="o", ls="", ms=5.5, markerfacecolor=COARSE, markeredgecolor=INK, label="Qwen Coarse-DGFT"),
        Line2D([], [], marker="o", ls="", ms=5.5, markerfacecolor=HYBRID, markeredgecolor=INK, label="Qwen Hybrid-DGFT"),
        Line2D([], [], marker="D", ls="", ms=5, markerfacecolor=PAPER, markeredgecolor=MUTED, label="Whisper median"),
        Line2D([], [], marker="o", ls="", ms=5, markerfacecolor=MUTED, markeredgecolor=INK, label="synchronous"),
        Line2D([], [], marker="s", ls="", ms=5, markerfacecolor=MUTED, markeredgecolor=INK, label="Poisson"),
    ]
    fig.legend(handles=legend, ncol=5, loc="lower center", bbox_to_anchor=(.54, .018), frameon=False, fontsize=5.7, handletextpad=.3, columnspacing=.8)
    finalize(fig, "f4_production")


# ---------------------------------------------------------------------------
# Figure 5: per-family quality contracts, never pooled.
# ---------------------------------------------------------------------------
def figure5():
    fig = plt.figure(figsize=(7.2, 3.85), facecolor=PAPER)
    gs = fig.add_gridspec(1, 2, left=.09, right=.985, bottom=.16, top=.89, width_ratios=[1.04, 1.0], wspace=.36)
    axa, axb = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])

    # (a) Qwen per-session strip distribution with exact-session mass and P95.
    rows = [
        ("Coarse · 0.6B", ("coarse-dgft", "Qwen3-ASR-0.6B"), COARSE, "o"),
        ("Coarse · 1.7B", ("coarse-dgft", "Qwen3-ASR-1.7B"), COARSE, "^"),
        ("Hybrid · 0.6B", ("hybrid-dgft", "Qwen3-ASR-0.6B"), HYBRID, "o"),
        ("Hybrid · 1.7B", ("hybrid-dgft", "Qwen3-ASR-1.7B"), HYBRID, "^"),
    ]
    axa.axvspan(-.12, .12, color=SAFE_BG, zorder=0)
    for y, (label, key, color, marker) in enumerate(rows[::-1]):
        rates = per_session[key]["rates"]
        # Deterministic vertical jitter resolves stacked exact sessions without inventing density.
        offsets = np.linspace(-.16, .16, len(rates))
        axa.scatter(rates, y + offsets, s=22, marker=marker, facecolor=matplotlib.colors.to_rgba(color, .72), edgecolor=INK, lw=.35, zorder=3)
        p95 = float(np.percentile(rates, 95))
        axa.plot([0, p95], [y, y], color=color, lw=5.5, alpha=.11, solid_capstyle="round", zorder=1)
        axa.scatter(p95, y, marker="D", s=42, facecolor=PAPER, edgecolor=color, lw=1.25, zorder=4)
        exact, n = per_session[key]["exact"], per_session[key]["n"]
        axa.text(6.28, y, f"{exact}/{n} exact   ·   P95 {p95:.2f}%", ha="right", va="center", fontsize=4.9, color=color, fontweight="bold")
    axa.axvline(0, color=MUTED, lw=.8)
    axa.set_yticks(range(4), [r[0] for r in rows[::-1]])
    axa.set_xlim(-.18, 6.42)
    axa.set_ylim(-.55, 3.55)
    axa.set_xlabel("Mixed-unit edit rate vs. independent FP16 singleton reference (%)")
    clean(axa, axis="x")
    panel_title(axa, "a", "Qwen: bounded distance to canonical", "each dot = one bilingual session · diamond = empirical P95 · shaded strip = exact")

    # (b) Whisper forest: two cohorts per model, one-sided upper bound toward zero.
    model_order = ["whisper-tiny.en", "whisper-base.en", "whisper-small.en"]
    colors = dict(zip(model_order, [TINY, BASE, SMALL]))
    display = {"whisper-tiny.en": "tiny.en", "whisper-base.en": "base.en", "whisper-small.en": "small.en"}
    cohort_alias = {
        "development": "development",
        "third-untouched-confirmation": "untouched",
    }
    observed_cohorts = {q["cohort"] for q in r9["quality"]}
    assert observed_cohorts == set(cohort_alias), observed_cohorts
    y_positions = {}
    y = 5
    for model in model_order:
        y_positions[(model, "development")] = y
        y_positions[(model, "untouched")] = y - 1
        y -= 2
    axb.axvspan(-30, 0, color=SAFE_BG, zorder=0)
    axb.axvline(0, color=INK, ls=(0, (4, 2)), lw=.9)
    for q in r9["quality"]:
        cohort = cohort_alias[q["cohort"]]
        yy = y_positions[(q["model"], cohort)]
        mean, upper = q["mean_delta_pp"], q["bootstrap_95_upper_pp"]
        color = colors[q["model"]]
        axb.plot([mean, upper], [yy, yy], color=color, lw=2.2, solid_capstyle="round")
        axb.plot([upper, upper], [yy-.12, yy+.12], color=color, lw=1.2)
        if cohort == "development":
            axb.scatter(mean, yy, s=42, color=color, edgecolor=INK, lw=.55, zorder=3)
        else:
            axb.scatter(mean, yy, s=42, facecolor=PAPER, edgecolor=color, lw=1.35, zorder=3)
        axb.text(mean - .55, yy, f"{mean:.2f}", ha="right", va="center", fontsize=4.85, color=color, fontweight="bold")
        axb.text(upper + .35, yy, f"U {upper:.2f}", ha="left", va="center", fontsize=4.35, color=MUTED)
    yticks, ylabels = [], []
    for model in model_order:
        yticks.extend([y_positions[(model, "development")], y_positions[(model, "untouched")]])
        ylabels.extend([f"{display[model]} · dev", f"{display[model]} · untouched"])
    axb.set_yticks(yticks, ylabels)
    axb.set_xlim(-30, 2.2)
    axb.set_ylim(-.65, 5.65)
    axb.set_xlabel("Paired WER change (points) · more negative is better")
    clean(axb, axis="x")
    axb.text(.97, .94, "ALL UPPER BOUNDS < 0", transform=axb.transAxes, ha="right", va="top", fontsize=5.0, color=BASE, fontweight="bold")
    panel_title(axb, "b", "Whisper: protection improves both cohorts", "filled = development · open = untouched n=214 · whisker end = one-sided 95% upper bound")

    finalize(fig, "f5_quality")


if __name__ == "__main__":
    figure3()
    figure4()
    figure5()
    stems = ["f3_pareto_latency", "f4_production", "f5_quality"]
    whisper_cells = r9["service_cells"]
    qwen_peak = max(
        metrics["wall_speedup"]
        for (adapter, _), metrics in cells.items()
        if adapter in {"coarse-dgft", "hybrid-dgft"}
    )
    qwen_gpu_peak = max(
        metrics["gpu_normalized_speedup"]
        for (adapter, _), metrics in cells.items()
        if adapter in {"coarse-dgft", "hybrid-dgft"}
    )
    qwen_energy_peak = 100 * max(
        metrics["energy_reduction_fraction"]
        for (adapter, _), metrics in cells.items()
        if adapter in {"coarse-dgft", "hybrid-dgft"}
    )
    qwen_worst_p95 = max(
        100 * metrics["reference_edit_rate_p95"]
        for (adapter, _), metrics in cells.items()
        if adapter in {"coarse-dgft", "hybrid-dgft"}
    )
    whisper_upper_max = max(q["bootstrap_95_upper_pp"] for q in r9["quality"])
    assert len(whisper_cells) == 16 and all(c["strict_gate_pass"] for c in whisper_cells)
    assert whisper_upper_max < 0
    qa = {
        "decision": "PASS",
        "renderer": Path(__file__).name,
        "evidence_sentinels": {
            "qwen_peak_wall_speedup": qwen_peak,
            "qwen_peak_gpu_normalized_speedup": qwen_gpu_peak,
            "qwen_peak_energy_reduction_percent": qwen_energy_peak,
            "qwen_worst_plotted_p95_edit_percent": qwen_worst_p95,
            "whisper_strict_gate_cells_passed": len(whisper_cells),
            "whisper_median_wall_speedup": float(np.median([c["wall_speedup"] for c in whisper_cells])),
            "whisper_median_energy_reduction_percent": float(100 * np.median([c["energy_reduction"] for c in whisper_cells])),
            "whisper_largest_one_sided_upper_pp": whisper_upper_max,
        },
        "figures": {},
    }
    for stem in stems:
        paths = {ext: OUT / f"{stem}.{ext}" for ext in ("pdf", "svg", "png", "tiff")}
        for ext, path in paths.items():
            assert path.is_file() and path.stat().st_size > 10_000, (ext, path)
        root = ET.parse(paths["svg"]).getroot()
        text_nodes = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "text"]
        image_nodes = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "image"]
        with Image.open(paths["png"]) as im:
            png_size, png_dpi = im.size, im.info.get("dpi", (0, 0))
        with Image.open(paths["tiff"]) as im:
            tif_size, tif_dpi = im.size, im.info.get("dpi", (0, 0))
        assert text_nodes and not image_nodes
        assert min(png_dpi) >= 295 and min(tif_dpi) >= 590
        qa["figures"][stem] = {
            "title_collision_audit": "PASS",
            "editable_svg_text_nodes": len(text_nodes),
            "embedded_svg_images": len(image_nodes),
            "png_pixels": list(png_size),
            "png_dpi": [round(float(v), 2) for v in png_dpi],
            "tiff_pixels": list(tif_size),
            "tiff_dpi": [round(float(v), 2) for v in tif_dpi],
        }
    (OUT / "FIGURE_QA_V2.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))
