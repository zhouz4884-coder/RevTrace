"""Fig. 1 only: bounded editorial rendering of immutable real two-run observations.

No model invocation, service-log reading, resimulation, or event alignment occurs.
The separate clean source checkout and complete manifest must be frozen before use.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import fitz


HERE = Path(__file__).resolve().parent
P = dict(ink="#26344B", selected="#285B91", view="#1C817B",
         compute="#6653A0", unknown="#A8761C", withdraw="#AD554F",
         withdraw_bg="#FCEAE6", neutral="#607083")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                     allow_nan=False) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", str(HERE), *args], text=True).strip()


def check_source(manifest):
    assert git("rev-parse", "--show-toplevel").replace("\\", "/").lower() == HERE.as_posix().lower()
    assert not git("status", "--porcelain", "--untracked-files=all")
    assert git("rev-parse", "HEAD") == manifest["code_commit"]
    assert set(git("ls-files").splitlines()) == {r["path"] for r in manifest["files"]}
    for row in manifest["files"]:
        path = HERE / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8,
        "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "pdf.fonttype": 42, "ps.fonttype": 42,
        "svg.fonttype": "none", "axes.spines.top": False,
        "axes.spines.right": False, "axes.linewidth": .65,
        "hatch.linewidth": .5, "savefig.facecolor": "white",
        "text.color": P["ink"], "axes.labelcolor": P["ink"],
    })


def application(arm, row, selected_s, visible_s):
    event = next(p for p in arm["complete_trace"] if p["input_row"] == row)
    action = next(p for p in arm["canonical_ahead_applications"] if p["row"] == row)
    assert event["kind"] == "canonical-display"
    assert event["t"] == action["relative_time"]
    assert event["certified_F"] == selected_s and event["visible_F"] == visible_s
    assert action["selected_F"] / 16000 == selected_s
    assert action["after_visible_F"] / 16000 == visible_s
    return event, action


def render(out, j, config):
    assert j["status"] == "PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS"
    assert j["same_input_interval"] and not j["same_execution_interleaving"]
    assert not j["paired_counterfactual"]
    top_event, top_action = application(j["arms"]["R1_S0"], 13, 12, 12)
    bottom_event, bottom_action = application(j["arms"]["R1_S1"], 15, 14, 16)
    assert top_event["t"] == 1.543663284741342
    assert bottom_event["t"] == 3.7943886145949364
    assert top_action["before_visible_F"] / 16000 == 14
    assert not top_action["whole_view_unchanged"] and bottom_action["whole_view_unchanged"]

    # A small height increase leaves 8-pt action labels clear of real stairs.
    fig = plt.figure(figsize=tuple(config["figure_inches"]))
    axes = [fig.add_axes([.087, .570, .895, .257]),
            fig.add_axes([.087, .170, .895, .257])]
    for i, (ax, arm_name) in enumerate(zip(axes, ["R1_S0", "R1_S1"])):
        arm = j["arms"][arm_name]
        trace = arm["complete_trace"]
        x = [p["t"] for p in trace]
        ax.step(x, [p["visible_F"] for p in trace], where="post",
                color=P["view"], lw=1.45, zorder=4)
        ax.step(x, [p["certified_F"] for p in trace], where="post",
                color=P["selected"], lw=1.1, ls=(0, (4, 2)), zorder=4)
        for gap in arm["observed_target_loss_windows"]:
            ax.add_patch(Rectangle((gap["start"], 12), gap["end"]-gap["start"], 2,
                                   facecolor=P["withdraw_bg"], edgecolor=P["withdraw"],
                                   hatch="///", lw=.4, zorder=1))
        ax.axvline(2, color=P["unknown"], ls=(0, (1, 2)), lw=.85, zorder=2)
        ax.axhline(14, color="#ABB4BF", ls=(0, (2, 3)), lw=.5, zorder=0)
        ax.set(xlim=(0, 4.35), ylim=(9.6, 17.6), yticks=[10, 12, 14, 16],
               xticks=[0, 1, 2, 3, 4])
        ax.grid(axis="y", color="#E2E6EB", lw=.4)
        ax.tick_params(axis="x", labelbottom=i == 1)
        first, certified = arm["first_visible"], arm["first_certified"]
        ax.annotate(f"first {first:.3f} s", xy=(first, 14),
                    xytext=(first-.55, 16.75), ha="center", va="center", fontsize=8,
                    color=P["view"], arrowprops=dict(arrowstyle="-", color=P["view"], lw=.65),
                    bbox=dict(facecolor="white", edgecolor="none", pad=.5))
        ax.annotate(f"certified {certified:.3f} s", xy=(certified, 14),
                    xytext=(3.65, 10.6), ha="center", va="center", fontsize=8,
                    color=P["selected"], arrowprops=dict(arrowstyle="-", color=P["selected"], lw=.65),
                    bbox=dict(facecolor="white", edgecolor="none", pad=.5))
        title_y = .918 if i == 0 else .518
        fig.text(.087, title_y, ["(a) Computation only", "(b) RevTrace: joint retention"][i],
                 fontsize=9, fontweight="bold", ha="left",
                 color=P["compute"] if i == 0 else P["selected"])
        summary = ["First delivery: D2 met   |   Compatible-update gap: 2.176 s",
                   "First delivery: D2 +27.4 ms   |   Compatible-update gap: none in shown interval"][i]
        fig.text(.087, title_y-.046, summary, fontsize=8, color=P["ink"])

    # The withdrawal callout ends at the actual selected-12-s application,
    # not at the earlier first delivery and not at a synthetic aligned event.
    axes[0].annotate(config["actions"][0]["text"],
                     xy=(top_event["t"], top_event["visible_F"]),
                     xytext=tuple(config["actions"][0]["text_xy"]), fontsize=8, ha="center", va="center",
                     color=P["ink"], linespacing=1.15,
                     arrowprops=dict(arrowstyle="-", color=P["neutral"], lw=.65,
                                     shrinkA=3, shrinkB=2),
                     bbox=dict(facecolor="white", edgecolor="none", pad=.6), zorder=5)
    # The retained view is the real 16-s object at the exact selected-14-s
    # application time. It is distinct from the earlier 16-s view arrival.
    axes[1].annotate(config["actions"][1]["text"],
                     xy=(bottom_event["t"], bottom_event["visible_F"]),
                     xytext=tuple(config["actions"][1]["text_xy"]), fontsize=8, ha="center", va="center",
                     color=P["ink"], linespacing=1.15,
                     arrowprops=dict(arrowstyle="-", color=P["neutral"], lw=.65,
                                     shrinkA=3, shrinkB=2),
                     bbox=dict(facecolor="white", edgecolor="none", pad=.6), zorder=5)
    gap = next(g for g in j["arms"]["R1_S0"]["observed_target_loss_windows"]
               if g["classification"] == "compatible")
    axes[0].text((gap["start"]+gap["end"])/2, 13,
                 f"{gap['gap_seconds']:.3f} s", ha="center", va="center",
                 fontsize=9, fontweight="bold", color=P["withdraw"],
                 bbox=dict(facecolor="white", edgecolor="none", alpha=.9, pad=.7), zorder=6)
    axes[-1].set_xlabel("Wall time since the 12–14-s input interval became ready in each run (s)", labelpad=3)
    fig.text(.018, .492, "Audio frontier (s)", rotation=90, va="center", fontsize=8)
    handles = [Line2D([], [], color=P["view"], lw=1.45, label="Whole view"),
               Line2D([], [], color=P["selected"], lw=1.1, ls=(0, (4, 2)), label="Selected coverage"),
               Line2D([], [], color=P["unknown"], lw=.85, ls=(0, (1, 2)), label="D2 = 2 s")]
    fig.legend(handles=handles, ncol=3, loc="upper right", bbox_to_anchor=(.99, 1.005),
               columnspacing=1.6, handlelength=2, frameon=False)

    name = "timely_full_interval_case"
    files = []
    for ext in ["pdf", "svg", "png"]:
        path = out/(name+"."+ext)
        fig.savefig(path, dpi=300)
        files.append(dict(path=path.name, bytes=path.stat().st_size, sha256=sha(path)))
    doc = fitz.open(out/(name+".pdf"))
    page = doc[0]
    spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
             for line in b["lines"] for s in line["spans"] if s["text"].strip()]
    page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY,
                    alpha=False).save(out/(name+"_gray.png"))
    result = dict(name=name, width_inches=fig.get_figwidth(), height_inches=fig.get_figheight(),
                  minimum_pdf_span_pt=min(s["size"] for s in spans), files=files,
                  details=dict(input_same=True, interleavings_different=True,
                               not_event_matched_counterfactual=True,
                               first_delivery_s=[j["arms"][k]["first_visible"] for k in ["R1_S0", "R1_S1"]],
                               compatible_gap_s=gap["gap_seconds"],
                               D2_excess_joint_ms=(j["arms"]["R1_S1"]["first_visible"]-2)*1000,
                               leaders_anchor_real_events=True,
                               action_annotations=[
                                   dict(arm="R1_S0", input_row=13, time=top_event["t"],
                                        selected_F_s=12, visible_F_before_s=14, visible_F_after_s=12,
                                        leader_y_s=12),
                                   dict(arm="R1_S1", input_row=15, time=bottom_event["t"],
                                        selected_F_s=14, visible_F_before_s=16, visible_F_after_s=16,
                                        leader_y_s=16)],
                               other_figures_rendered=0))
    assert abs(fig.get_figwidth()-7.125) < 1e-12
    assert result["minimum_pdf_span_pt"] >= 7.999
    put(out/(name+".QA.json"), result)
    plt.close(fig)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        help="Optional internal complete frozen-source manifest; standalone use verifies immutable input hashes")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes()) if args.manifest else None
    if manifest:
        check_source(manifest)
    input_map = json.loads((HERE/"INPUT_MAP.json").read_bytes())
    for row in input_map["sources"]:
        assert sha(HERE/row["path"]) == row["sha256"]
    args.out.mkdir(parents=True, exist_ok=False)
    style()
    config = json.loads((HERE/"config.json").read_bytes())
    result = render(args.out, json.loads((HERE/"inputs/case.json").read_bytes()), config)
    if manifest:
        check_source(manifest)
    environment = dict(python=sys.version, executable=sys.executable,
                       platform=platform.platform(), matplotlib=matplotlib.__version__,
                       pymupdf=fitz.VersionBind)
    put(args.out/"SUMMARY.json", dict(status="PASS_NUMERIC_EXPORTS_PENDING_VISUAL_INSPECTION",
                                     source_commit=manifest["code_commit"] if manifest else None,
                                     source_manifest_sha256=sha(args.manifest) if manifest else None,
                                     standalone_reproduction=not bool(manifest),
                                     config_sha256=sha(HERE/"config.json"),
                                     figure=result, environment=environment,
                                     new_model_calls=0, raw_service_readers=0))
    put(args.out/"GATE.json", dict(status="PASS_FROZEN_NUMERIC_VECTOR_EXPORTS",
                                  visual_QA="PENDING", new_model_calls=0,
                                  raw_service_readers=0))
    print(json.dumps(dict(source_commit=manifest["code_commit"] if manifest else None, figures=1,
                          out=str(args.out), new_model_calls=0)))


if __name__ == "__main__":
    main()
