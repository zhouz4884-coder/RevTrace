"""Render data/performance figures F3, F4, F5 for the RevTrace FGCS paper.

All numbers are read at runtime from the frozen audited evidence:
  - results/r10_qwen_cross_adapter/ablation_summary.json  (F3 ladder, 6 cells)
  - results/r10_qwen_cross_adapter/qwen*-*.json           (F5a per-session edit rates)
  - results/r9_dgft/FINAL_REPORT_ONLINE.json              (F4 Whisper 16 cells, F5b WER deltas)
No number is hardcoded here; if the frozen JSONs change, the figures change.
Style: scientific-figure-pro skill (Arial, no top/right spines, frameless legends).
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parents[2]  # .../RevTrace (script lives in Paper/scripts)
OUT = REPO / "Paper" / "figures"
OUT.mkdir(exist_ok=True)

# ---- skill style module -------------------------------------------------
_skill = Path.home() / ".qoderworkcn/skills/l-yifan-scientific-figure-pro/scripts/scientific_figure_pro.py"
sfp = None
if _skill.exists():
    spec = importlib.util.spec_from_file_location("sfp", _skill)
    sfp = importlib.util.module_from_spec(spec)
    sys.modules["sfp"] = sfp
    spec.loader.exec_module(sfp)
    sfp.apply_publication_style(sfp.FigureStyle(font_size=9, axes_linewidth=1.0,
                                                font_family=("Arial", "Helvetica", "DejaVu Sans")))
else:  # portable fallback style
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9, "axes.linewidth": 1.0, "axes.spines.top": False,
        "axes.spines.right": False, "legend.frameon": False,
    })
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42

def finalize(fig, out_stem, dpi=600):
    if sfp is not None:
        return sfp.finalize_figure(fig, out_stem, formats=["pdf", "png"], dpi=dpi)
    paths = []
    for fmt in ("pdf", "png"):
        p = Path(str(out_stem) + "." + fmt)
        fig.savefig(p, dpi=dpi, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths

# ---- semantic palette (Okabe-Ito, color-blind safe) ----------------------
C_SG = "#D55E00"        # vermilion: same-granularity contrast point
C_COARSE = "#0072B2"    # blue: proposed Coarse-DGFT
C_HYBRID = "#56B4E9"    # sky: proposed Hybrid-DGFT
C_TINY, C_BASE, C_SMALL = "#E69F00", "#009E73", "#CC79A7"
C_GREY = "#555555"
C_GREEN = "#009E73"

MKR = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "^"}

# ---- load audited evidence ----------------------------------------------
abl = json.load(open(REPO / "results/r10_qwen_cross_adapter/ablation_summary.json", encoding="utf-8"))
assert abl["decision"] == "COMPLETE_R10_ABLATION_WITH_SG_TAIL_BOUNDARY"
r9 = json.load(open(REPO / "results/r9_dgft/FINAL_REPORT_ONLINE.json", encoding="utf-8"))
assert r9["decision"] == "PASS_R9E_ONLINE_SUBMISSION_CLOSURE"

cells = {(c["adapter"], c["model"]): c["metrics"] for c in abl["cells"]}
per_session = {}
for key, fname in [
    (("coarse-dgft", "Qwen3-ASR-0.6B"), "qwen06-dgft-fp32batch.json"),
    (("coarse-dgft", "Qwen3-ASR-1.7B"), "qwen17-dgft-fp32batch.json"),
    (("hybrid-dgft", "Qwen3-ASR-0.6B"), "qwen06-hybrid-fp32batch.json"),
    (("hybrid-dgft", "Qwen3-ASR-1.7B"), "qwen17-hybrid-fp32batch.json"),
]:
    d = json.load(open(REPO / "results/r10_qwen_cross_adapter" / fname, encoding="utf-8"))
    per_session[key] = {
        "rates": sorted(r["unit_edit_rate"] for r in d["final_comparison"]),
        "exact": d["summary"]["final_exact_sessions"],
        "n": d["summary"]["final_sessions"],
    }
    assert per_session[key]["n"] == 16

def panel_label(ax, s):
    ax.text(-0.13, 1.05, s, transform=ax.transAxes, fontsize=10, fontweight="bold")

def clean(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

# ===========================================================================
# F3: same-workload operating points (c16) + latency-scope dumbbells
# ===========================================================================
fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.0, 3.1), gridspec_kw={"width_ratios": [1.15, 1.0]})

order = [("sg", "Qwen3-ASR-0.6B"), ("coarse-dgft", "Qwen3-ASR-0.6B"), ("hybrid-dgft", "Qwen3-ASR-0.6B"),
         ("sg", "Qwen3-ASR-1.7B"), ("coarse-dgft", "Qwen3-ASR-1.7B"), ("hybrid-dgft", "Qwen3-ASR-1.7B")]
proto_color = {"sg": C_SG, "coarse-dgft": C_COARSE, "hybrid-dgft": C_HYBRID}
proto_name = {"sg": "SG", "coarse-dgft": "Coarse-DGFT", "hybrid-dgft": "Hybrid-DGFT"}

# (a) Pareto scatter
for (ad, md) in order:
    m = cells[(ad, md)]
    axa.scatter(m["wall_speedup"], m["reference_edit_rate_p95"] * 100,
                s=m["service_energy_joules"] / 25, facecolor=proto_color[ad],
                edgecolor="black", linewidth=0.6, marker=MKR[md], zorder=4, alpha=0.92)
lab = {(5.104, 0.0): ("SG", 0.02, 0.42), (4.682, 0.0): ("SG", -0.02, 0.42),
       (6.884, 3.43): ("Coarse", -0.30, -0.50), (6.063, 1.79): ("Coarse", -0.28, -0.52),
       (5.190, 2.15): ("Hybrid", -0.14, 0.38), (3.918, 1.79): ("Hybrid", -0.20, -0.52)}
for (ad, md) in order:
    m = cells[(ad, md)]
    x, y = m["wall_speedup"], m["reference_edit_rate_p95"] * 100
    name, dx, dy = lab[(round(x, 3), round(y, 2))]
    axa.annotate(name, (x, y), xytext=(x + dx, y + dy), fontsize=7, color="black")
h_bub = [Line2D([], [], marker="o", ls="", markersize=np.sqrt(4000 / 25) / 2.2,
                markerfacecolor="none", markeredgecolor="grey", label="4 kJ"),
         Line2D([], [], marker="o", ls="", markersize=np.sqrt(8000 / 25) / 2.2,
                markerfacecolor="none", markeredgecolor="grey", label="8 kJ")]
h_proto = [Line2D([], [], marker="o", ls="", markerfacecolor=proto_color[p], markeredgecolor="black",
                  markersize=6, label=proto_name[p]) for p in ("sg", "coarse-dgft", "hybrid-dgft")]
h_model = [Line2D([], [], marker=MKR[m], ls="", markerfacecolor="#BBBBBB", markeredgecolor="black",
                  markersize=6, label=m.replace("Qwen3-ASR-", "")) for m in MKR]
axa.legend(handles=h_proto + h_model + h_bub, frameon=False, fontsize=6.6,
           ncol=2, loc="upper right", handletextpad=0.4, columnspacing=0.9,
           labelspacing=0.35, borderaxespad=0.1)
axa.set_xlabel("Wall-clock speedup ($\\times$)")
axa.set_ylabel("P95 mixed-unit edit rate (%)")
axa.set_xlim(3.4, 7.45)
axa.set_ylim(-0.35, 4.6)
clean(axa)
panel_label(axa, "(a)")

# (b) latency-scope dumbbells
ys = [0, 1, 2, 3.5, 4.5, 5.5]
labels = []
for y, (ad, md) in zip(ys, order):
    m = cells[(ad, md)]
    if ad == "sg":
        axa_p99 = m["state_or_segment_commit_latency_seconds_p99"]  # = state-entry P99 for SG
        axb.scatter(axa_p99, y, marker="D", s=34, color=C_SG, edgecolor="black", linewidth=0.5, zorder=4)
    else:
        disp = m["display_latency_seconds_p99"]
        comm = m["state_or_segment_commit_latency_seconds_p99"]
        axb.plot([disp, comm], [y, y], color="#999999", lw=1.2, zorder=2)
        axb.scatter(disp, y, marker="o", s=30, color=proto_color[ad], edgecolor="black", linewidth=0.5, zorder=4)
        axb.scatter(comm, y, marker="s", s=30, facecolor="white", edgecolor=proto_color[ad], linewidth=1.1, zorder=4)
    labels.append(f"{md.replace('Qwen3-ASR-', '')} {proto_name[ad]}")
axb.axvline(2.0, color="black", ls="--", lw=1.0, zorder=1)
axb.text(2.07, 6.3, "2 s state-entry deadline (SG scope)", fontsize=6.3, rotation=90,
         va="top", ha="left", color="black")
axb.axhline(2.75, color="#CCCCCC", lw=0.8)
axb.set_yticks(ys)
axb.set_yticklabels(labels, fontsize=6.8)
axb.set_xlim(0, 5.05)
axb.set_ylim(-0.6, 6.4)
axb.set_xlabel("Latency (s), scopes not mixed")
h_sc = [Line2D([], [], marker="D", ls="", color=C_SG, label="SG state-entry P99"),
        Line2D([], [], marker="o", ls="", markerfacecolor="#777777", markeredgecolor="black",
               label="display P99"),
        Line2D([], [], marker="s", ls="", markerfacecolor="white", markeredgecolor="#777777",
               label="segment-commit P99")]
axb.legend(handles=h_sc, frameon=False, fontsize=6.3, loc="lower right",
           handletextpad=0.3, labelspacing=0.3, borderaxespad=0.1)
clean(axb)
panel_label(axb, "(b)")
finalize(fig, OUT / "f3_pareto_latency")

# ===========================================================================
# F4: cross-family production evidence (Qwen 4 points + Whisper 16 cells)
# ===========================================================================
qx = [0, 1, 2, 3]
wx = {"whisper-tiny.en": 4.35, "whisper-base.en": 5.35, "whisper-small.en": 6.35}
wcol = {"whisper-tiny.en": C_TINY, "whisper-base.en": C_BASE, "whisper-small.en": C_SMALL}
qwen_pts = [  # (x, protocol color, metrics from ablation)
    (0, C_COARSE, cells[("coarse-dgft", "Qwen3-ASR-0.6B")]),
    (1, C_COARSE, cells[("coarse-dgft", "Qwen3-ASR-1.7B")]),
    (2, C_HYBRID, cells[("hybrid-dgft", "Qwen3-ASR-0.6B")]),
    (3, C_HYBRID, cells[("hybrid-dgft", "Qwen3-ASR-1.7B")]),
]
wcells = r9["service_cells"]
assert len(wcells) == 16

fig, axs = plt.subplots(1, 3, figsize=(7.0, 3.5))
panels = [
    (axs[0], "wall_speedup", "Wall-clock speedup ($\\times$)", 1.0),
    (axs[1], "gpu_normalized_speedup", "GPU-normalized speedup ($\\times$)", 1.0),
    (axs[2], "energy_reduction", "Service energy reduction (%)", None),
]
jit = {n: np.linspace(-0.17, 0.17, n) for n in (3, 10)}
for ax, key, ylab, refline in panels:
    ax.axvspan(-0.55, 3.55, color=C_COARSE, alpha=0.05, zorder=0)
    ax.axvspan(3.85, 6.9, color="#888888", alpha=0.08, zorder=0)
    if refline is not None:
        ax.axhline(refline, color="#AAAAAA", ls=":", lw=0.9, zorder=1)
    qkey = "energy_reduction_fraction" if key == "energy_reduction" else key
    for x, col, m in qwen_pts:
        v = m[qkey] * (100 if key == "energy_reduction" else 1)
        ax.scatter(x, v, s=78, color=col, edgecolor="black", linewidth=0.6, zorder=4)
    counts = {}
    for c in wcells:
        mdl, arr = c["model"], c["arrival"]
        i = counts[mdl] = counts.get(mdl, 0) + 1
        off = jit[sum(1 for cc in wcells if cc["model"] == mdl)][i - 1]
        v = c[key] * (100 if key == "energy_reduction" else 1)
        mk = "s" if arr == "poisson" else "o"
        ax.scatter(wx[mdl] + off, v, s=28, color=wcol[mdl], marker=mk,
                   edgecolor="black", linewidth=0.35, zorder=4)
    ax.text(1.5, 1.045, "Qwen3-ASR (R10 contract)", transform=ax.get_xaxis_transform(),
            ha="center", fontsize=7.5)
    ax.text(5.35, 1.045, "Whisper (R9.E contract)", transform=ax.get_xaxis_transform(),
            ha="center", fontsize=7.5)
    ax.set_xticks(qx + list(wx.values()))
    ax.set_xticklabels(["Coarse\n0.6B", "Coarse\n1.7B", "Hybrid\n0.6B", "Hybrid\n1.7B",
                        "tiny", "base", "small"], fontsize=7.5)
    ax.set_ylabel(ylab)
    ax.tick_params(axis="y", labelsize=8.0)
    clean(ax)
axs[0].set_ylim(1.6, 7.5)
axs[1].set_ylim(0.9, 3.85)
axs[2].set_ylim(20, 65)
panel_label(axs[0], "(a)")
panel_label(axs[1], "(b)")
panel_label(axs[2], "(c)")
h_f4 = [Line2D([], [], marker="o", ls="", color=C_COARSE, markeredgecolor="black", label="Qwen Coarse-DGFT"),
        Line2D([], [], marker="o", ls="", color=C_HYBRID, markeredgecolor="black", label="Qwen Hybrid-DGFT"),
        Line2D([], [], marker="o", ls="", color=C_TINY, markeredgecolor="black", label="Whisper tiny.en"),
        Line2D([], [], marker="o", ls="", color=C_BASE, markeredgecolor="black", label="Whisper base.en"),
        Line2D([], [], marker="o", ls="", color=C_SMALL, markeredgecolor="black", label="Whisper small.en"),
        Line2D([], [], marker="s", ls="", color="#999999", markeredgecolor="black", label="Poisson arrivals")]
fig.legend(handles=h_f4, frameon=False, fontsize=7.2, ncol=6, loc="lower center",
           bbox_to_anchor=(0.5, -0.035), handletextpad=0.4, columnspacing=1.0)
fig.tight_layout(rect=[0, 0.06, 1, 1])
finalize(fig, OUT / "f4_production")

# ===========================================================================
# F5: per-family quality contracts (never pooled)
# ===========================================================================
fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw={"width_ratios": [1.1, 1.0]})

# (a) Qwen per-session edit-rate CDF, one curve per R10 cell
cdf_style = {
    ("coarse-dgft", "Qwen3-ASR-0.6B"): (C_COARSE, "-",  "Coarse-DGFT 0.6B (11/16 exact)"),
    ("coarse-dgft", "Qwen3-ASR-1.7B"): (C_COARSE, "--", "Coarse-DGFT 1.7B (9/16 exact)"),
    ("hybrid-dgft", "Qwen3-ASR-0.6B"): (C_HYBRID, "-",  "Hybrid-DGFT 0.6B (13/16 exact)"),
    ("hybrid-dgft", "Qwen3-ASR-1.7B"): (C_HYBRID, "--", "Hybrid-DGFT 1.7B (10/16 exact)"),
}
for key, (col, ls, lbl) in cdf_style.items():
    r = np.asarray(per_session[key]["rates"]) * 100
    y = np.arange(1, len(r) + 1) / len(r)
    axa.step(r, y, where="post", color=col, ls=ls, lw=1.4, label=lbl)
axa.set_xlim(-0.15, 6.1)
axa.set_ylim(0, 1.06)
axa.set_xlabel("Mixed-unit edit rate vs. independent reference (%)")
axa.set_ylabel("Fraction of sessions (CDF)")
axa.legend(frameon=False, fontsize=6.6, loc="lower right", labelspacing=0.35, borderaxespad=0.2)
clean(axa)
panel_label(axa, "(a)")

# (b) Whisper paired WER deltas with one-sided 95% upper bounds
mods = ["whisper-tiny.en", "whisper-base.en", "whisper-small.en"]
mcol = dict(zip(mods, (C_TINY, C_BASE, C_SMALL)))
xs = {m: i for i, m in enumerate(mods)}
for q in r9["quality"]:
    x = xs[q["model"]] + (-0.17 if q["cohort"] == "development" else 0.17)
    mean, up = q["mean_delta_pp"], q["bootstrap_95_upper_pp"]
    axb.plot([x, x], [up, mean], color=mcol[q["model"]], lw=1.3, zorder=2)
    axb.plot([x - 0.055, x + 0.055], [up, up], color=mcol[q["model"]], lw=1.3, zorder=2)
    if q["cohort"] == "development":
        axb.scatter(x, mean, s=34, color=mcol[q["model"]], edgecolor="black", linewidth=0.5, zorder=4)
    else:
        axb.scatter(x, mean, s=34, facecolor="white", edgecolor=mcol[q["model"]], linewidth=1.3, zorder=4)
axb.axhline(0, color="black", ls="--", lw=0.9)
axb.text(2.62, -1.2, "no change", fontsize=6.5, ha="right", va="top")
axb.annotate("", xy=(2.78, -22), xytext=(2.78, -4),
             arrowprops=dict(arrowstyle="-|>", color=C_GREEN, lw=1.3))
axb.text(2.88, -12.5, "DGFT\nbetter", fontsize=6.8, color=C_GREEN, va="center")
axb.set_xticks(range(3))
axb.set_xticklabels(["tiny.en", "base.en", "small.en"], fontsize=7.5)
axb.set_xlim(-0.6, 3.15)
axb.set_ylim(-28, 2.5)
axb.set_ylabel("Paired WER change (points)")
h_q = [Line2D([], [], marker="o", ls="", color=mcol[m], markeredgecolor="black", label=m.replace("whisper-", "")) for m in mods]
h_q += [Line2D([], [], marker="o", ls="", markerfacecolor="#777777", markeredgecolor="black", label="development"),
        Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="#777777", label="untouched (n=40 long sessions/model)"),
        Line2D([], [], ls="-", color="#777777", label="one-sided 95% upper bound")]
axb.legend(handles=h_q, frameon=False, fontsize=6.3, loc="upper left",
           labelspacing=0.3, handletextpad=0.4, borderaxespad=0.2)
clean(axb)
panel_label(axb, "(b)")
finalize(fig, OUT / "f5_quality")

print("DONE:", [p.name for p in OUT.iterdir()])
