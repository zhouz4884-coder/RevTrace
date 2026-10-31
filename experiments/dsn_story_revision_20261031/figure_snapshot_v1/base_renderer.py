"""Writing-closure figures: bounded original data, no neural/model calls.

Run only from this independently frozen figure-source checkout. Experimental
execution commits are provenance, never this renderer's runtime identity.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.ticker import PercentFormatter, MaxNLocator
import numpy as np
import fitz
from PIL import Image

HERE = Path(__file__).resolve().parent
BLUE = '#0F4D92'
TEAL = '#287F86'
RED = '#B64342'
GRAY = '#626262'
INK = '#272727'
LIGHT = '#E6E6E6'
WIDTH = 7.125
MIN_FONT = 8.5
ARMS = ('R0_S0', 'R0_S1', 'R1_S0', 'R1_S1')
POINTS = ('c8-sync', 'c8-staggered', 'c12-staggered', 'c16-staggered')
COLORS = dict(zip(ARMS, (GRAY, TEAL, '#5C80A5', BLUE)))
MARKERS = dict(zip(ARMS, ('o', 's', '^', 'D')))
LABELS = dict(zip(ARMS, ('Recompute + snapshot', 'View only (S)', 'Compute only (R)', 'RevTrace (R+S)')))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                     allow_nan=False) + '\n', encoding='utf8')


def git(*args):
    return subprocess.check_output(['git', '-C', str(HERE), *args], text=True).strip()


def source_gate():
    assert Path(git('rev-parse', '--show-toplevel')).resolve() == HERE
    assert not git('status', '--porcelain', '--untracked-files=all')
    manifest_path = HERE.parent/'FIGURE_SOURCE_dev_v1.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    commit = git('rev-parse', 'HEAD')
    assert commit == manifest['code_commit']
    assert git('rev-parse', manifest['code_commit']+'^{commit}') == commit
    assert set(git('ls-files').splitlines()) == {r['path'] for r in manifest['files']}
    for row in manifest['files']:
        p = HERE/row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    return commit


def style():
    plt.rcParams.update({
        'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
        'font.size': 8.5, 'axes.titlesize': 9, 'axes.labelsize': 8.5,
        'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
        'legend.fontsize': 8.5, 'axes.linewidth': .65,
        'axes.spines.top': False, 'axes.spines.right': False,
        'xtick.major.width': .6, 'ytick.major.width': .6,
        'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'savefig.facecolor': 'white', 'mathtext.fontset': 'dejavusans',
        'figure.dpi': 160,
    })


def export(fig, out, name, caption, scope, details=None):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w, h = fig.get_size_inches() * fig.dpi
    texts = [t for t in fig.findobj(matplotlib.text.Text)
             if t.get_visible() and t.get_text()]
    outside = []
    for t in texts:
        b = t.get_window_extent(renderer)
        if b.x0 < -1 or b.y0 < -1 or b.x1 > w + 1 or b.y1 > h + 1:
            outside.append(t.get_text())
    assert not outside, outside
    minimum = min(t.get_fontsize() for t in texts)
    assert minimum >= MIN_FONT and fig.get_figwidth() <= 7.2 and fig.get_figheight() <= 3.6
    for suffix in ('pdf', 'svg', 'png'):
        fig.savefig(out / (name + '.' + suffix), dpi=400)
    doc = fitz.open(out / (name + '.pdf'))
    fonts = doc[0].get_fonts(full=True)
    assert fonts and not any('Type3' in f for f in fonts)
    embedded = []
    for f in fonts:
        data = doc.extract_font(f[0])[-1]
        assert data, f
        embedded.append(dict(font=f[3], type=f[2], embedded_bytes=len(data)))
    pix = doc[0].get_pixmap(dpi=200)
    pix.save(out / (name + '_PDF_PAGE.png'))
    doc.close()
    with Image.open(out / (name + '_PDF_PAGE.png')) as im:
        im.convert('L').save(out / (name + '_GRAYSCALE_QA.png'))
    svg = ET.parse(out / (name + '.svg'))
    svg_texts = svg.findall('.//{http://www.w3.org/2000/svg}text')
    assert svg_texts, 'SVG must retain editable text'
    qa = dict(figure=name, scope=scope, width_inches=fig.get_figwidth(),
              height_inches=fig.get_figheight(), minimum_font_pt=minimum,
              exact_paper_width_inches=WIDTH, out_of_canvas_text=outside,
              PDF_fonts=embedded, Type3_fonts=0, SVG_editable_text_nodes=len(svg_texts),
              grayscale_cues='line style, hatching, marker shape, text and border style',
              details=details or {})
    put(out / (name + '.QA.json'), qa)
    (out / (name + '.caption.txt')).write_text(caption + '\n', encoding='utf8')
    plt.close(fig)
    return qa


def plot_case(out, summary, trace, snapshots):
    D, L, C = (summary[k] for k in ('D', 'loss_start', 'C'))
    assert summary['offered_interval_audio_seconds'] == 2.0
    assert summary['first_text_delta']['introduced_raw_code_points'] == 37
    assert summary['first_and_recovered_complete_text_equal']
    assert summary['compatible'] and summary['actual_input_prompt_equals_selected_root_P']
    assert L < 2 < C and C - L == summary['loss_duration']
    assert [r['relative_to_offered_F_seconds'] for r in snapshots[1:]] == [D, L, C]
    assert (D, L, C) == (1.4439057689160109, 1.543663284741342, 3.7196051217615604)
    fig, ax = plt.subplots(figsize=(WIDTH, 2.65))
    fig.subplots_adjust(left=.095, right=.985, bottom=.21, top=.79)
    x = [r['t'] for r in trace]
    ax.step(x, [r['visible_F'] for r in trace], where='post', color=TEAL,
            lw=1.75, label='Actual whole-view frontier', zorder=3)
    ax.step(x, [r['certified_F'] for r in trace], where='post', color=BLUE,
            lw=1.35, ls=(0, (4, 2)), label='Actual certified frontier', zorder=4)
    ax.add_patch(Rectangle((L, 12), C-L, 2, facecolor='#FAEDEC',
                           edgecolor=RED, hatch='////', lw=.45, zorder=0))
    ax.axvline(2, color=INK, ls=(0, (2, 2)), lw=.85, zorder=2)
    ax.plot(D, 14, 'o', color=TEAL, ms=3.4, zorder=5)
    ax.plot(L, 12, 'x', color=RED, ms=4, mew=1.2, zorder=5)
    ax.plot(C, 14, 'D', color=BLUE, ms=3.4, zorder=5)
    props = dict(arrowstyle='->', color=GRAY, lw=.7, shrinkA=1, shrinkB=3)
    ax.annotate('Displayed: 1.444 s\n+37 raw characters', (D, 14), (.20, 14.58),
                fontsize=8.5, arrowprops=props, va='bottom')
    ax.annotate('Compatible update: 1.544 s\nwhole view withdrawn', (L, 12), (.12, 11.20),
                fontsize=8.5, arrowprops=props, va='top')
    ax.annotate('Identical text returns\ncertified: 3.720 s', (C, 14), (3.04, 14.58),
                fontsize=8.5, arrowprops=props, va='bottom')
    ax.text(2.64, 13.0, '2.176 s\nvisibility gap', color=RED, ha='center', va='center',
            bbox=dict(facecolor='white', edgecolor='none', alpha=.93, pad=1.6))
    ax.text(2.05, 10.7, 'Original D2 read\ninterval missing', color=INK, va='bottom')
    ax.set(xlim=(0, 4.35), ylim=(9.6, 15.35), xticks=[0, 1, 2, 3, 4], yticks=[10, 12, 14],
           xlabel='Wall seconds from original offered F = 14 s', ylabel='Audio frontier (s)')
    ax.grid(axis='y', alpha=.15, lw=.4)
    fig.legend(*ax.get_legend_handles_labels(), loc='upper center', ncol=2,
               bbox_to_anchor=(.54, 1.01), frameon=False, columnspacing=2)
    caption = (
        'Timely first delivery can still leave a gap in delivered progress. '
        'In an actual computation-only c16-staggered run, a complete non-EOS two-second '
        'interval ending at F=14 s is first displayed at 1.444 s, withdrawn by a compatible '
        'selected-root update at 1.544 s, and restored with identical whole text in the '
        'certified view at 3.720 s. The update returns the frontier to F=12 s; shading marks '
        'the 2.176 s visibility gap, and the vertical line is the original two-second D2 '
        'read point. The view introduces 37 raw Unicode code points (31 non-whitespace), '
        'replacing one punctuation mark; these are not character/audio alignments. '
        'Compatibility uses the actual complete consumed input and selected parent state, '
        'not text equality alone. First-delivery D2/C8 credit is unchanged. This post-hoc '
        'c16 overload case illustrates a failure mode, not its incidence or a whole-run SLO win.')
    return export(fig, out, 'timely_full_interval_case', caption, 'actual bounded single-arm trace',
                  dict(D=D, withdrawal=L, certified_return=C, gap=C-L, raw_code_points=37,
                       offered_interval_audio_seconds=2, original_D2=2, paired_counterfactual=False))


def txt(ax, x, y, s, **kw):
    return ax.text(x, y, s, fontsize=kw.pop('fontsize',8.5), color=kw.pop('color', INK),
                   ha=kw.pop('ha', 'center'), va=kw.pop('va', 'center'), **kw)


def box(ax, x, y, w, h, label, color=GRAY, fill='white', ls='solid', weight='normal'):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=color,
                           linewidth=.9, linestyle=ls, zorder=2))
    return txt(ax, x+w/2, y+h/2, label, color=color, fontweight=weight, zorder=3)


def arrow(ax, a, b, color=GRAY, ls='solid', lw=.85):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=7,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1.2, shrinkB=1.2, zorder=1))


def plot_mechanism(out):
    fig = plt.figure(figsize=(WIDTH, 3.0))
    ax = fig.add_axes([.005, .01, .99, .98])
    ax.set(xlim=(0, WIDTH), ylim=(0, 3.0))
    ax.axis('off')
    txt(ax, .08, 2.88, '(a) Confirmed input preserves the original full result across producer exit',
        ha='left', fontweight='bold')
    txt(ax, .08, 2.51, 'Parent', ha='left', fontweight='bold')
    txt(ax, .08, 1.96, 'Child j', ha='left', fontweight='bold')
    # The parent original C/U remains authoritative; the child's early forecast is not.
    box(ax, .80, 2.33, 1.03, .35, 'ASR', BLUE)
    box(ax, 2.05, 2.33, 2.33, .35, 'Original correction / update', BLUE)
    box(ax, 4.72, 2.33, 1.15, .35, r'Selected $P_2$', BLUE, '#EAF1F8')
    arrow(ax, (1.83, 2.505), (2.05, 2.505), BLUE)
    arrow(ax, (4.38, 2.505), (4.72, 2.505), BLUE)
    # A complete original call, not a typed ASR projection, reaches the buffer.
    box(ax, .80, 1.62, 2.10, .61,
        'Complete call: frozen ' + r'$\hat P_2$' + '\nASR ' + r'$\hat P_3$' + ' → original C/U ' + r'$P_3$' + '\n' + r'$\hat P_3 \ne P_3$' + ' is allowed', TEAL, '#F0F8F7')
    box(ax, 3.12, 1.73, .89, .39, 'Accepted B', TEAL, '#F0F8F7', ls=(0, (3, 1.5)))
    arrow(ax, (2.90, 1.925), (3.12, 1.925), TEAL)
    ax.plot([4.26, 4.26], [1.66, 2.16], color=GRAY, ls=(0, (2, 2)), lw=1)
    txt(ax, 4.26, 1.51, 'Producer exit', color=GRAY)
    txt(ax, 4.26, 1.33, 'new messages fenced', color=GRAY)
    arrow(ax, (4.01, 1.925), (4.66, 1.925), TEAL)
    box(ax, 4.66, 1.71, 1.27, .43, r'$\hat P_2=P_2$' + '\ninput confirmed', BLUE, '#EAF1F8')
    arrow(ax, (5.295, 2.33), (5.295, 2.14), BLUE, ls=(0, (2, 1.5)))
    box(ax, 6.12, 1.71, .90, .43, 'Sync D\ninstall → use', BLUE, '#EAF1F8')
    arrow(ax, (5.93, 1.925), (6.12, 1.925), BLUE)
    txt(ax, 1.85, 1.37, 'Original UID / birth / incarnation retained', color=GRAY)
    ax.plot([.08, 7.02], [1.16, 1.16], color='#B8B8B8', lw=.6)
    txt(ax, .08, 1.00, '(b) A lost view does not refute an unknown future call input',
        ha='left', fontweight='bold')
    box(ax, .13, .31, 1.03, .43, 'Trusted\nupdate C', BLUE, '#EAF1F8')
    box(ax, 1.49, .31, 1.22, .43, 'Whole-view\nguard S(C,h)', GRAY)
    arrow(ax, (1.16, .525), (1.49, .525), BLUE)
    box(ax, 3.10, .61, 1.19, .29, 'true: retain h', TEAL, '#F0F8F7')
    box(ax, 3.10, .14, 1.19, .29, 'false: withdraw h', RED, '#FAEDEC', ls=(0, (2.5, 1.5)))
    arrow(ax, (2.71, .63), (3.10, .755), TEAL)
    arrow(ax, (2.71, .42), (3.10, .285), RED, ls=(0, (2, 1.5)))
    box(ax, 4.71, .17, 2.30, .70,
        'Future complete input: UNKNOWN\nno same-frontier refuting witness\nkeep call / buffer; no commit', GRAY, '#F5F5F5', ls=(0, (3, 2)))
    txt(ax, 4.50, .525, '≠', color=INK)
    caption = (
        'Eligibility, original selection, and whole-view support are separate decisions. '
        '(a) Child j runs the complete original call on frozen P-hat_2. Its prediction '
        'P-hat_3 may be wrong while original C/U legitimately returns P_3. Strictly accepted '
        'complete buffer B survives producer exit with its original UID/birth/incarnation; '
        'future messages are fenced. Matching actual selected P_2 later confirms the input; '
        'ordered selection requires durable sync before install and Consumer use. '
        '(b) A failed whole-view guard withdraws h without refuting an unresolved future '
        'call input. UNKNOWN authorizes neither commit nor a cancellation proof. '
        'Assumptions are complete feedback-sensitive state and frozen audio/target/EOS/'
        'model/decoding contract, faithful owned original C/U, single-Owner selection, '
        'exact input/identity checks, durable sync, and Consumer order/parent checks. '
        'Sealed-channel tail receipts are validated before fencing. Retained views are '
        'whole, without suffix splicing. This causal schematic has no measured time axis.')
    return export(fig, out, 'coordination_protocol', caption, 'native full-call mechanism schematic',
                  dict(time_axis=False, performance_numbers=False, complete_original_C_U=True,
                       equality='complete frozen input, not equal text only',
                       prediction_may_differ=True, accepted_buffer_survives_producer_exit=True,
                       unknown_is_not_refuted=True, no_suffix_splice=True))


def plot_workloads(out, rows):
    assert len(rows) == 48 and len({r['cell_id'] for r in rows}) == 48
    assert all(sum(r['point'] == p and r['arm'] == a for r in rows) == 3
               for p in POINTS for a in ARMS)
    assert all(r['display_P99'] > 2 for r in rows
               if r['point'] == 'c12-staggered' and r['arm'] == 'R1_S1')
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.65))
    fig.subplots_adjust(left=.071, right=.990, bottom=.23, top=.77, wspace=.49)
    metrics = [('display_P99', 1., 'a  First visibility', 'Display P99 (s)'),
               ('dual_audio_fraction', 100., 'b  Timely delivery', 'D2/C8 credit (%)'),
               ('compatible_timely_deficit_area', 1., 'c  Later visibility loss',
                'Compatible deficit\n(audio s × wall s)')]
    plotted = {}
    for ax, (key, scale, title, ylabel) in zip(axes, metrics):
        ax.set_title(title, loc='left', fontweight='bold', pad=6)
        ax.set_ylabel(ylabel, labelpad=3)
        ax.set_xlabel('Sessions / arrival', labelpad=4)
        ax.set_xticks(range(4), ('8/sync', '8/stg', '12/stg', '16/stg'))
        ax.set_xlim(-.5, 3.5)
        ax.grid(axis='y', color='#DADADA', lw=.4, zorder=0)
        plotted[key] = []
        for pi, point in enumerate(POINTS):
            for ai, arm in enumerate(ARMS):
                group = sorted((r for r in rows if r['point'] == point and r['arm'] == arm),
                               key=lambda r: r['repeat'])
                values = [r[key]*scale for r in group]
                center = pi+(ai-1.5)*.18
                for r, value in zip(group, values):
                    ax.scatter(center+(r['repeat']-1)*.038, value, s=15,
                               marker=MARKERS[arm], facecolors='white' if arm == 'R1_S0' else COLORS[arm],
                               edgecolors=COLORS[arm], linewidths=.7, zorder=4)
                    plotted[key].append(dict(cell_id=r['cell_id'], raw=r[key],
                                             display_value=value, scale=scale))
                ax.vlines(center, min(values), max(values), color=COLORS[arm], lw=.65, zorder=2)
                ax.hlines(np.median(values), center-.066, center+.066,
                          color=COLORS[arm], lw=1.2, zorder=3)
        if key == 'display_P99':
            ax.axhline(2, color=INK, ls=(0, (3, 2)), lw=.8)
            ax.text(.99, 2.04, 'D2', transform=ax.get_yaxis_transform(), ha='right', va='bottom')
            ax.set_ylim(0, max(r[key] for r in rows)*1.14)
            ax.set_yticks([0, 1, 2, 3, 4, 5])
        elif key == 'dual_audio_fraction':
            ax.set_ylim(55, 102)
            ax.set_yticks([60, 80, 100])
            ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
        else:
            top = max(r[key] for r in rows)
            ax.set_ylim(-.025*max(1, top), 1.14*max(1, top))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    handles = [Line2D([], [], color=COLORS[a], marker=MARKERS[a], ls='None',
                      markerfacecolor='white' if a == 'R1_S0' else COLORS[a],
                      markersize=4, label=LABELS[a]) for a in ARMS]
    fig.legend(handles=handles, ncol=4, loc='upper center', bbox_to_anchor=(.52, 1.005),
               frameon=False, columnspacing=1.4, handletextpad=.35)
    caption = (
        'First visibility, timely credit, and subsequent visibility loss are different endpoints. '
        'All 48 fresh-process runs are shown: four explicit development workloads × four '
        'arms × three repeats. R retains eligible computation; S retains supported whole '
        'views. Shapes and colors identify arms; horizontal ticks are medians and vertical '
        'lines span the three observed values, not confidence intervals. Panel (a) uses '
        'actual Consumer first-visibility P99, with the original D2 threshold; (b) uses '
        'all offered audio intervals and the original 2 s display / 8 s certified-view '
        'deadlines. Panel (c) is the secondary deficit area from later loss of previously '
        'dual-timely intervals whose complete prior view remains compatible with the new '
        'selected root. Single-root windows are right-censored at the next Canonical root '
        'if no covering view returns sooner; necessary incompatible revisions remain '
        'separate and original first credit is unchanged. The exploratory c12 midpoint '
        'and its negative deadline result are retained. Original36 plus midpoint12 reuse '
        'development audio; c16 expands the metadata-nested source mix. Sync arrivals are '
        'simultaneous and staggered arrivals are 0.25 s apart. Workloads are not a pure '
        'capacity sweep; no lines interpolate between them.')
    put(out / 'PLOTTED_NUMERIC_VALUES.json', plotted)
    assert all(len(v) == 48 for v in plotted.values())
    return export(fig, out, 'service_region', caption, 'original 48 fresh-process runs',
                  dict(actual_cells=48, plotted_points_each_panel=48,
                       metrics=[k for k, *_ in metrics], c12_joint_all_D2_fail=True,
                       median_and_observed_range=True, confidence_intervals=False,
                       no_workload_interpolation=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    commit = source_gate()
    config = json.loads((HERE/'CONFIG.json').read_text(encoding='utf8'))
    source_map = json.loads((HERE/'SOURCE_MAP.json').read_text(encoding='utf8'))
    inputs = {}
    for row in source_map['bounded_inputs']:
        path = HERE/row['copy']
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        original = Path(row['original'])
        if original.exists():
            assert sha(original) == row['sha256']
        inputs[row['key']] = json.loads(path.read_text(encoding='utf8'))
    protected = []
    for row in source_map['read_only_originals']:
        path = Path(row['path'])
        assert path.exists() and sha(path) == row['sha256']
        protected.append(row)
    out = args.out.resolve()
    out.mkdir(exist_ok=False, parents=True)
    put(out/'CONFIG.json', config)
    env = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
               matplotlib=matplotlib.__version__, numpy=np.__version__,
               pymupdf=fitz.VersionBind, new_model_calls=0)
    put(out/'ENVIRONMENT.json', env)
    put(out/'RUN_RECORD.json', dict(
        experiment_id=config['experiment_id'], type='CPU-only figure rendering',
        actual_figure_execution_source_commit=commit,
        figure_source_manifest_sha256=sha(HERE.parent/'FIGURE_SOURCE_dev_v1.json'),
        frozen_config=str(HERE/'CONFIG.json'), frozen_config_sha256=sha(HERE/'CONFIG.json'),
        environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location='bounded source copies in figure_source_dev/inputs; originals in SOURCE_MAP.json',
        aggregate_summary_location=str(out/'SUMMARY.json'), gate_decision_location=str(out/'GATE.json'),
        experimental_execution_commits_are_provenance_only=True,
        new_model_calls=0, new_neural_experiments=0))
    style()
    qa = [plot_case(out, inputs['case_summary'], inputs['case_trace'], inputs['case_snapshots']),
          plot_mechanism(out), plot_workloads(out, inputs['run_endpoints_48'])]
    for row in protected:
        assert sha(row['path']) == row['sha256']
    assert source_gate() == commit
    put(out/'INPUT_SOURCE_SHA.json', source_map)
    put(out/'SUMMARY.json', dict(figures=3, formats=['pdf', 'svg', 'png'],
                                actual_figure_execution_source_commit=commit,
                                bounded_input_checks='PASS', original_files_unchanged=True,
                                all_48_rows_retained=True, numeric_values_unchanged=True,
                                exact_paper_width_inches=WIDTH, minimum_font_pt=8.5,
                                figure_QA=qa, new_model_calls=0))
    put(out/'GATE.json', dict(gate='PASS_BOUNDED_FIGURE_SOURCE_NUMERIC_AND_VECTOR_QA',
                             original_files_unchanged=True, new_model_calls=0,
                             visual_review='required separately; automatic checks do not claim visual approval'))
    put(out/'OUTPUT_SHA256.json', [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p))
                                  for p in sorted(out.iterdir()) if p.is_file()])
    print(json.dumps(dict(out=str(out), actual_figure_execution_source_commit=commit,
                          figures=3, actual_cells=48, new_model_calls=0)))


if __name__ == '__main__':
    main()
