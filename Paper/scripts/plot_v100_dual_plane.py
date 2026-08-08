"""Render the repeated V100 dual-plane scaling figure for RevTrace."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.lines import Line2D


REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Paper" / "figures"
SOURCE = OUT / "source_data"
OUT.mkdir(exist_ok=True)
SOURCE.mkdir(exist_ok=True)

V14 = REPO / "results" / "v100_v1_v4" / "results" / "v1_v4" / "178168.manager" / "v1_v4_summary.json"
V5 = REPO / "results" / "v100_v5_headline" / "178169.manager" / "v5_headline_summary.json"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7.2,
    "axes.labelsize": 7.4,
    "axes.titlesize": 8.0,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 5.8,
    "axes.linewidth": 0.75,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})

INK = "#172333"
MUTED = "#65758A"
GRID = "#D9E1EA"
PAPER = "#FFFFFF"
SG = "#D55E00"
COARSE = "#0072B2"
HYBRID = "#56B4E9"
M06 = "#0072B2"
M17 = "#CC79A7"
SAFE_BG = "#EAF6F2"
WARN_BG = "#FCF3E8"

MODEL_COLOR = {"Qwen3-ASR-0.6B": M06, "Qwen3-ASR-1.7B": M17}
MODEL_MARKER = {"Qwen3-ASR-0.6B": "o", "Qwen3-ASR-1.7B": "^"}
MODEL_SHORT = {"Qwen3-ASR-0.6B": "0.6B", "Qwen3-ASR-1.7B": "1.7B"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(ax, axis="both"):
    ax.grid(axis=axis, color=GRID, lw=0.45, alpha=0.75, zorder=0)
    ax.set_axisbelow(True)


def panel_title(ax, label, heading, subtitle=None):
    artists = getattr(ax.figure, "_paper_title_artists", [])
    artists.append((
        f"{label}:label",
        ax.text(-0.13, 1.055, label, transform=ax.transAxes, ha="left",
                va="bottom", fontsize=9.2, fontweight="bold", color=INK,
                clip_on=False),
    ))
    artists.append((
        f"{label}:heading",
        ax.text(0.0, 1.055, heading, transform=ax.transAxes, ha="left",
                va="bottom", fontsize=7.8, fontweight="bold", color=INK,
                clip_on=False),
    ))
    if subtitle:
        artists.append((
            f"{label}:subtitle",
            ax.text(0.0, 1.017, subtitle, transform=ax.transAxes, ha="left",
                    va="top", fontsize=5.2, color=MUTED, clip_on=False),
        ))
    ax.figure._paper_title_artists = artists


def range_error(block):
    med = float(block["median"])
    return med, np.array([[med - float(block["min"])], [float(block["max"]) - med]])


def finalize(fig, stem):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [
        (name, artist.get_window_extent(renderer).expanded(1.01, 1.03))
        for name, artist in getattr(fig, "_paper_title_artists", [])
    ]
    collisions = []
    for index, (name_a, box_a) in enumerate(boxes):
        for name_b, box_b in boxes[index + 1:]:
            x = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            y = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if x > 2 and y > 2:
                collisions.append((name_a, name_b, x * y))
    if collisions:
        raise RuntimeError(f"title collision in {stem}: {collisions}")
    for suffix, dpi in (("pdf", None), ("svg", None), ("png", 300), ("tiff", 600)):
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.025, "facecolor": PAPER}
        if dpi:
            kwargs["dpi"] = dpi
        fig.savefig(OUT / f"{stem}.{suffix}", **kwargs)
    plt.close(fig)


def main():
    v14 = load(V14)
    v5 = load(V5)
    assert v5["decision"] == "V5_REPEAT_MATRIX_COMPLETE"
    assert v5["completed_cells"] == 30 and v5["failed_cells"] == 0

    cells14 = {cell["cell_id"]: cell for cell in v14["cells"]}
    agg = {
        (row["model"], row["allocation"], int(row["concurrency"])): row
        for row in v5["aggregates"]
    }
    models = ("Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B")

    source_rows = []
    fig = plt.figure(figsize=(7.2, 4.55), facecolor=PAPER)
    gs = fig.add_gridspec(
        2, 2, left=0.085, right=0.985, bottom=0.12, top=0.92,
        hspace=0.55, wspace=0.34,
    )
    axa, axb = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    axc, axd = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    # a: independent c16 method ladder.
    modes = (
        ("revtrace-sg", "SG", SG),
        ("hybrid-dgft", "Hybrid", HYBRID),
        ("coarse-dgft", "Coarse", COARSE),
    )
    x = np.arange(len(modes))
    reference_wall = {
        model: cells14[f"v2-{model}-all-singleton-c16"]["wall_seconds"]
        for model in models
    }
    for model, dx in zip(models, (-0.12, 0.12)):
        values = []
        for mode, _, _ in modes:
            cell = cells14[f"v2-{model}-{mode}-c16"]
            value = reference_wall[model] / float(cell["wall_seconds"])
            values.append(value)
            source_rows.append({
                "panel": "a", "model": model, "configuration": mode,
                "concurrency": 16, "metric": "wall_speedup",
                "median": value, "min": value, "max": value, "unit": "x",
            })
        axa.plot(x + dx, values, color=MODEL_COLOR[model], lw=1.0, alpha=0.4)
        for pos, value, (_, _, color) in zip(x + dx, values, modes):
            axa.scatter(pos, value, s=48, marker=MODEL_MARKER[model],
                        facecolor=color, edgecolor=INK, lw=0.55, zorder=3)
            axa.text(pos, value + 0.18, f"{value:.2f}x", ha="center",
                     va="bottom", fontsize=4.9, color=color, fontweight="bold")
    axa.set_xticks(x, [name for _, name, _ in modes])
    axa.set_ylim(2.7, 6.55)
    axa.set_ylabel("Wall-clock speedup over all-singleton")
    clean(axa, "y")
    panel_title(axa, "a", "The method benefit survives an independent V100 contract",
                "c16, 30 s bilingual sessions; circles 0.6B, triangles 1.7B")

    # b: repeated p4a4 throughput scaling.
    concurrencies = (16, 32, 64, 128)
    for model in models:
        medians, lows, highs = [], [], []
        for concurrency in concurrencies:
            if concurrency == 16:
                cell = cells14[f"v3-{model}-p4a4-c16"]
                med = low = high = float(cell["audio_throughput_x_realtime"])
            else:
                block = agg[(model, "p4a4", concurrency)]["audio_throughput_x_realtime"]
                med, low, high = map(float, (block["median"], block["min"], block["max"]))
            medians.append(med); lows.append(low); highs.append(high)
            source_rows.append({
                "panel": "b", "model": model, "configuration": "p4a4",
                "concurrency": concurrency, "metric": "audio_throughput_x_realtime",
                "median": med, "min": low, "max": high, "unit": "xRT",
            })
        medians = np.asarray(medians)
        yerr = np.vstack([medians - np.asarray(lows), np.asarray(highs) - medians])
        axb.errorbar(concurrencies, medians, yerr=yerr, color=MODEL_COLOR[model],
                     marker=MODEL_MARKER[model], ms=5.5, lw=1.6, capsize=2.5,
                     markeredgecolor=INK, markeredgewidth=0.45,
                     label=MODEL_SHORT[model])
        c64 = medians[2]
        c64_offset = 6.0 if model == "Qwen3-ASR-0.6B" else -7.0
        axb.text(66, c64 + c64_offset, f"{c64:.1f}x", ha="left", va="center",
                 fontsize=5.2, color=MODEL_COLOR[model], fontweight="bold",
                 bbox={"facecolor": PAPER, "edgecolor": "none", "alpha": 0.78,
                       "pad": 0.45})
    axb.axvspan(56, 72, color=SAFE_BG, zorder=0)
    axb.axvline(64, color="#2E9E44", lw=0.8, ls=(0, (3, 2)), alpha=0.8)
    axb.set_xscale("log", base=2)
    axb.set_xticks(concurrencies, ["c16", "c32", "c64", "c128"])
    axb.set_xlim(13.5, 150)
    axb.set_ylim(20, 178)
    axb.set_ylabel("Audio throughput (x real time)")
    axb.legend(loc="lower right", ncol=2)
    clean(axb, "y")
    panel_title(axb, "b", "Balanced 4+4 replication scales the display plane to c64",
                "three-run median and min--max; c16 is an independently frozen baseline")

    # c: dual-plane latency. The 2 s line is explicitly display-only.
    latency_concurrency = (32, 64, 128)
    for model in models:
        color = MODEL_COLOR[model]
        for metric, marker, linestyle, suffix in (
            ("display_latency_p99_seconds", MODEL_MARKER[model], "-", "display"),
            ("commit_latency_p99_seconds", "s", "--", "commit"),
        ):
            medians, lows, highs = [], [], []
            for concurrency in latency_concurrency:
                block = agg[(model, "p4a4", concurrency)][metric]
                med, low, high = map(float, (block["median"], block["min"], block["max"]))
                medians.append(med); lows.append(low); highs.append(high)
                source_rows.append({
                    "panel": "c", "model": model, "configuration": f"p4a4-{suffix}",
                    "concurrency": concurrency, "metric": metric,
                    "median": med, "min": low, "max": high, "unit": "s",
                })
            medians = np.asarray(medians)
            yerr = np.vstack([medians - np.asarray(lows), np.asarray(highs) - medians])
            axc.errorbar(latency_concurrency, medians, yerr=yerr, color=color,
                         marker=marker, mfc=(color if suffix == "display" else PAPER),
                         mec=color, ms=5.0, lw=1.25, ls=linestyle, capsize=2.2)
            c64_value = medians[1]
            label_offset = {
                ("Qwen3-ASR-0.6B", "display"): (4, -8),
                ("Qwen3-ASR-1.7B", "display"): (4, 7),
                ("Qwen3-ASR-0.6B", "commit"): (4, -8),
                ("Qwen3-ASR-1.7B", "commit"): (4, 7),
            }[(model, suffix)]
            axc.annotate(f"{c64_value:.2f}s", (64, c64_value),
                         xytext=label_offset, textcoords="offset points",
                         ha="left", va="center", fontsize=4.5,
                         color=color, fontweight="bold",
                         bbox={"facecolor": PAPER, "edgecolor": "none",
                               "alpha": 0.72, "pad": 0.35})
    axc.axhspan(0.7, 2.0, color=SAFE_BG, zorder=0)
    axc.axhline(2.0, color=SG, lw=0.9, ls=(0, (4, 2)))
    axc.text(126, 1.88, "2 s display SLO", ha="right", va="top",
             fontsize=4.7, color=SG, fontweight="bold")
    axc.set_xscale("log", base=2)
    axc.set_yscale("log", base=2)
    axc.set_xticks(latency_concurrency, ["c32", "c64", "c128"])
    axc.set_yticks([1, 2, 4, 8, 16], ["1", "2", "4", "8", "16"])
    axc.set_xlim(27, 150)
    axc.set_ylim(0.68, 13.5)
    axc.set_ylabel("P99 latency (s, log2 scale)")
    clean(axc, "y")
    latency_legend = [
        Line2D([], [], color=INK, marker="o", lw=1.2, label="display P99"),
        Line2D([], [], color=INK, marker="s", mfc=PAPER, lw=1.2, ls="--", label="commit P99"),
        Line2D([], [], color=M06, marker="o", lw=0, label="0.6B"),
        Line2D([], [], color=M17, marker="^", lw=0, label="1.7B"),
    ]
    axc.legend(handles=latency_legend, loc="upper left", ncol=2,
               columnspacing=0.8, handletextpad=0.35)
    panel_title(axc, "c", "Display and certified commit have distinct capacity boundaries",
                "the display SLO is not transferred to six-second segment commit")

    # d: c64 allocation sensitivity as a service-balance plane.
    allocations = ("p1a1", "p4a4", "p3a5")
    allocation_marker = {"p1a1": "X", "p4a4": "D", "p3a5": "P"}
    allocation_label = {
        "p1a1": "Minimal 1+1",
        "p4a4": "Balanced 4+4",
        "p3a5": "Authority-heavy 3+5",
    }
    label_offsets = {
        ("Qwen3-ASR-0.6B", "p1a1"): (-5, 10, "right"),
        ("Qwen3-ASR-0.6B", "p4a4"): (8, 2, "left"),
        ("Qwen3-ASR-0.6B", "p3a5"): (7, 9, "left"),
        ("Qwen3-ASR-1.7B", "p1a1"): (-8, 10, "right"),
        ("Qwen3-ASR-1.7B", "p4a4"): (8, -8, "left"),
        ("Qwen3-ASR-1.7B", "p3a5"): (7, -11, "left"),
    }
    axd.axvspan(0.0, 1.0, color=SAFE_BG, zorder=0)
    axd.axvspan(1.0, 1.45, color=WARN_BG, zorder=0)
    axd.axvline(1.0, color=MUTED, lw=0.9, ls=(0, (4, 2)))
    for model in models:
        for allocation in allocations:
            row = agg[(model, allocation, 64)]
            xr = row["authority_to_proposer_ratio"]
            yr = row["audio_throughput_x_realtime"]
            xmed, xerr = range_error(xr)
            ymed, yerr = range_error(yr)
            axd.errorbar(xmed, ymed, xerr=xerr, yerr=yerr, fmt=allocation_marker[allocation],
                         ms=6.2, color=MODEL_COLOR[model], mfc=MODEL_COLOR[model],
                         mec=INK, mew=0.45, capsize=2.0, lw=0.9, zorder=3)
            commit = float(row["commit_latency_p99_seconds"]["median"])
            dx, dy, ha = label_offsets[(model, allocation)]
            axd.annotate(f"{allocation_label[allocation]} - {commit:.2f}s", (xmed, ymed),
                         xytext=(dx, dy), textcoords="offset points", ha=ha,
                         va="center", fontsize=4.4, color=MODEL_COLOR[model],
                         bbox={"facecolor": PAPER, "edgecolor": "none",
                               "alpha": 0.76, "pad": 0.45})
            source_rows.extend([
                {"panel": "d", "model": model, "configuration": allocation,
                 "concurrency": 64, "metric": "authority_to_proposer_ratio",
                 "median": xmed, "min": xr["min"], "max": xr["max"], "unit": "ratio"},
                {"panel": "d", "model": model, "configuration": allocation,
                 "concurrency": 64, "metric": "audio_throughput_x_realtime",
                 "median": ymed, "min": yr["min"], "max": yr["max"], "unit": "xRT"},
            ])
    axd.text(0.97, 171, "authority service <= proposer", ha="right", va="top",
             fontsize=4.6, color="#2E9E44", fontweight="bold")
    axd.set_xlim(0.35, 1.42)
    axd.set_ylim(20, 178)
    axd.set_xlabel("Authority / proposer service ratio")
    axd.set_ylabel("c64 audio throughput (x real time)")
    clean(axd, "both")
    panel_title(axd, "d", "Balanced resources dominate replica count alone",
                "c64 three-run medians; point labels are allocation · certified-commit P99")

    source_path = SOURCE / "f7_v100_dual_plane.csv"
    with source_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "panel", "model", "configuration", "concurrency", "metric",
            "median", "min", "max", "unit",
        ])
        writer.writeheader()
        writer.writerows(source_rows)

    stem = "f7_v100_dual_plane"
    finalize(fig, stem)

    paths = {ext: OUT / f"{stem}.{ext}" for ext in ("pdf", "svg", "png", "tiff")}
    for path in paths.values():
        assert path.is_file() and path.stat().st_size > 10_000, path
    root = ET.parse(paths["svg"]).getroot()
    text_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"]
    image_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "image"]
    assert text_nodes and not image_nodes
    with Image.open(paths["png"]) as image:
        png_pixels = list(image.size)
        png_dpi = [round(float(value), 2) for value in image.info.get("dpi", (0, 0))]
    with Image.open(paths["tiff"]) as image:
        tiff_pixels = list(image.size)
        tiff_dpi = [round(float(value), 2) for value in image.info.get("dpi", (0, 0))]
    assert min(png_dpi) >= 295 and min(tiff_dpi) >= 590
    qa = {
        "decision": "PASS",
        "renderer": Path(__file__).name,
        "source_data": str(source_path.relative_to(REPO)),
        "repeats": 3,
        "interval": "min--max",
        "title_collision_audit": "PASS",
        "editable_svg_text_nodes": len(text_nodes),
        "embedded_svg_images": len(image_nodes),
        "png_pixels": png_pixels,
        "png_dpi": png_dpi,
        "tiff_pixels": tiff_pixels,
        "tiff_dpi": tiff_dpi,
    }
    (OUT / "F7_FIGURE_QA.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
