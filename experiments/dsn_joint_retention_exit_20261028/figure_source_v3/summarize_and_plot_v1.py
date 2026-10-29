"""CPU-only, all-cell R x K summary and IEEE-width publication figures."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, PercentFormatter

ARMS = ('R0K0', 'R0K1', 'R1K0', 'R1K1')
POINTS = ('sync', 'staggered')
COLORS = {'R0K0': '#767676', 'R0K1': '#42949E', 'R1K0': '#B64342', 'R1K1': '#0F4D92'}
MARKERS = {'R0K0': 'o', 'R0K1': 's', 'R1K0': '^', 'R1K1': 'D'}
LABELS = {'R0K0': 'R0K0', 'R0K1': 'R0K1', 'R1K0': 'R1K0', 'R1K1': 'R1K1'}
INPUTS = {}


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    INPUTS[str(path.resolve())] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return json.loads(raw)


def verify_source(manifest_path):
    manifest = read(manifest_path)
    root = Path(__file__).resolve().parent
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    assert Path(git('rev-parse', '--show-toplevel')).resolve() == root
    assert git('rev-parse', 'HEAD') == manifest['code_commit']
    assert not git('status', '--porcelain', '--untracked-files=all')
    assert set(git('ls-files').splitlines()) == {r['path'] for r in manifest['files']}
    for row in manifest['files']:
        path = root / row['path']
        assert path.stat().st_size == row['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
    return manifest['code_commit']


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('x', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def style():
    plt.rcParams.update({
        'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'], 'font.size': 8.5,
        'axes.titlesize': 9., 'axes.labelsize': 8.5, 'xtick.labelsize': 8.,
        'ytick.labelsize': 8., 'legend.fontsize': 8., 'axes.linewidth': .7,
        'axes.spines.top': False, 'axes.spines.right': False,
        'xtick.major.width': .6, 'ytick.major.width': .6,
        'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'savefig.facecolor': 'white', 'figure.dpi': 150})


def x_for(point, arm, repeat):
    return POINTS.index(point) + (ARMS.index(arm) - 1.5) * .18 + (repeat - 1) * .038


def panel(ax, rows, metric, title, ylabel, percent=False, threshold=None):
    ax.set_title(title, loc='left', fontweight='bold', pad=6)
    ax.set_ylabel(ylabel, labelpad=3)
    ax.set_xticks((0, 1), ('16 / sync', '16 / stag.'))
    ax.set_xlabel('Sessions / arrival phase', labelpad=3)
    ax.set_xlim(-.5, 1.5)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.grid(axis='y', alpha=.16, linewidth=.4, zorder=0)
    ax.set_axisbelow(True)
    all_values = []
    for point in POINTS:
        for arm in ARMS:
            selected = sorted((r for r in rows if r['arrival'] == point and r['arm'] == arm), key=lambda r: r['repeat'])
            assert len(selected) == 3
            values = []
            for row in selected:
                value = row[metric] * (100. if percent else 1.)
                assert math.isfinite(value)
                values.append(value)
                ax.scatter(x_for(point, arm, row['repeat']), value, s=15, marker=MARKERS[arm],
                           facecolors=COLORS[arm], edgecolors=COLORS[arm], linewidths=.6, zorder=4)
            center = POINTS.index(point) + (ARMS.index(arm) - 1.5) * .18
            ax.vlines(center, min(values), max(values), color=COLORS[arm], lw=.65, zorder=2)
            ax.hlines(statistics.median(values), center-.065, center+.065, color=COLORS[arm], lw=1.2, zorder=3)
            all_values.extend(values)
    if threshold is not None:
        ax.axhline(threshold, color='#272727', lw=.8, ls=(0, (3, 2)), zorder=1)
        ax.text(.99, threshold, 'D2 ', transform=ax.get_yaxis_transform(), ha='right', va='bottom', fontsize=8.)
        all_values.append(threshold)
    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
        ax.set_ylim(max(0., math.floor(min(all_values)/5)*5-5), 101.5)
    else:
        ax.set_ylim(-.02 * max(1., max(all_values)), max(1., max(all_values)) * 1.15)


def export(fig, output, name, caption):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width, height = fig.get_size_inches() * fig.dpi
    visible = [text for text in fig.findobj(matplotlib.text.Text) if text.get_visible() and text.get_text()]
    outside = []
    for text in visible:
        box = text.get_window_extent(renderer)
        if box.x0 < -1 or box.y0 < -1 or box.x1 > width+1 or box.y1 > height+1:
            outside.append(text.get_text())
    assert not outside, outside
    qa = dict(width_inches=fig.get_figwidth(), height_inches=fig.get_figheight(),
              minimum_font_pt=min(t.get_fontsize() for t in visible), out_of_canvas_text=outside)
    assert qa['minimum_font_pt'] >= 8
    for suffix in ('pdf', 'svg', 'png'):
        fig.savefig(output / (name + '.' + suffix), dpi=350)
    import fitz
    document = fitz.open(output / (name + '.pdf'))
    fonts = document[0].get_fonts(full=True)
    qa.update(PDF_fonts=[list(v) for v in fonts], Type3_fonts=[list(v) for v in fonts if 'Type3' in v])
    assert not qa['Type3_fonts']
    document[0].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False).save(output / (name + '_PDF_PAGE.png'))
    document.close()
    (output / (name + '.caption.txt')).write_text(caption + '\n', encoding='utf8')
    (output / (name + '.QA.json')).write_text(json.dumps(qa, indent=2) + '\n', encoding='utf8')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    args = parser.parse_args()
    commit = verify_source(args.source_manifest)
    analysis = args.results / 'analysis'
    assert read(analysis / 'GATE.json')['gate'] == 'PASS_OFFLINE_RECOUNT'
    assert read(args.results / 'controller/GATE.json')['gate'] == 'PASS_ALL_FROZEN_EXECUTION_CELLS'
    runs = read(analysis / 'RUNS.json')
    factors = read(analysis / 'FACTORIAL_EFFECTS.json')
    matches = read(analysis / 'MATCHED_ROWS.json')
    record = read(analysis / 'ANALYSIS_RECORD.json')
    assert len(runs) == 24 and len(factors) == 6 and len(matches) == 12
    assert record['analysis_code_commit'] == '6eb02d6ecceacb1810e247cdbe2ba72013eddcea'
    assert record['neural_execution_commit'] == 'f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
    rows = []
    for run in runs:
        assert run['accepted_unfulfilled_samples'] == 0
        assert abs(run['offered_audio_seconds'] - 250.18) < 1e-8
        positives = [p for p in run['legal_pressure'] if p['compatible'] is True]
        displayed = [p for p in positives if 'display' in p['owner_outcomes']]
        row = dict(cell_id=run['cell_id'], arm=run['arm'], arrival=run['arrival'], repeat=run['repeat'],
                   **run['metrics'], offered_audio_seconds=run['offered_audio_seconds'],
                   dual_audio_fraction=run['metrics']['dual_credited_audio_seconds']/run['offered_audio_seconds'],
                   GPU_joules_per_offered_audio_second=run['metrics']['GPU_joules']/run['offered_audio_seconds'],
                   compatible_crossing_events=len(positives),
                   compatible_crossing_unique_jobs=len({p['job_id'] for p in positives}),
                   compatible_crossing_displayed_unique_jobs=len({p['job_id'] for p in displayed}),
                   incompatible_crossing_events=sum(p['compatible'] is False for p in run['legal_pressure']),
                   unknown_crossing_events=sum(p['compatible'] is None for p in run['legal_pressure']),
                   compatible_max_model_seconds=max([0.] + [p['model_to_terminal_seconds'] for p in positives]),
                   cancelled_rows=run['cancelled_rows'],
                   canonical_sha256=run['canonical_sha256'])
        for chain in run['exit_chains']:
            assert chain['request_to_ack_seconds'] >= 0 and chain['ack_to_drain_seconds'] >= 0
            if chain['next_actual_dispatch_perf'] is not None:
                assert chain['next_actual_dispatch_perf'] >= chain['actual_batch_drain_perf']
        rows.append(row)
    rows.sort(key=lambda r: (POINTS.index(r['arrival']), r['repeat'], ARMS.index(r['arm'])))
    paired = []
    for point in POINTS:
        for repeat in range(3):
            arms = {r['arm']: r for r in rows if r['arrival'] == point and r['repeat'] == repeat}
            assert set(arms) == set(ARMS)
            for label, a, b in [('K_at_R0', 'R0K0', 'R0K1'), ('K_at_R1', 'R1K0', 'R1K1'),
                                ('R_at_K0', 'R0K0', 'R1K0'), ('R_at_K1', 'R0K1', 'R1K1'),
                                ('joint_minus_neither', 'R0K0', 'R1K1')]:
                paired.append(dict(arrival=point, repeat=repeat, contrast=label, a=a, b=b,
                                   **{k: arms[b][k]-arms[a][k] for k in runs[0]['metrics']}))
    summaries = []
    for point in POINTS:
        for arm in ARMS:
            selected = [r for r in rows if r['arrival'] == point and r['arm'] == arm]
            values = {}
            for metric in ['dual_credited_audio_seconds', 'display_P99', 'commit_view_P99', 'GPU_joules',
                           'physical_model_seconds', 'physical_lease_seconds', 'audio_rollback_events',
                           'compatible_crossing_unique_jobs', 'compatible_crossing_displayed_unique_jobs',
                           'compatible_max_model_seconds', 'cancelled_rows']:
                array = [r[metric] for r in selected]
                values[metric] = dict(values=array, minimum=min(array), maximum=max(array), median=statistics.median(array))
            summaries.append(dict(arrival=point, arm=arm, metrics=values))
    output = args.out
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in [('RUN_ENDPOINTS', rows), ('PAIRED_EFFECTS', paired), ('POINT_SUMMARY', summaries),
                          ('FACTORIAL_EFFECTS', factors), ('MATCHING_COVERAGE', [
                              {k:v for k,v in m.items() if k != 'rows'} for m in matches])]:
        (output / (name + '.json')).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf8')
        if name in ('RUN_ENDPOINTS', 'PAIRED_EFFECTS', 'MATCHING_COVERAGE'):
            write_csv(output / (name + '.csv'), payload)
    style()
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.4))
    fig.subplots_adjust(left=.065, right=.992, bottom=.22, top=.79, wspace=.43)
    panel(axes[0], rows, 'display_P99', 'a. First actual visibility', 'Display P99 (s)', threshold=2.)
    panel(axes[1], rows, 'dual_audio_fraction', 'b. Offered-input service', 'D2/C8 credit (%)', percent=True)
    panel(axes[2], rows, 'physical_lease_seconds', 'c. Actual occupied leases', 'Physical lease time (s)')
    handles = [Line2D([], [], color=COLORS[a], marker=MARKERS[a], ls='None', markersize=3.7, label=LABELS[a]) for a in ARMS]
    fig.legend(handles=handles, ncol=4, loc='upper center', bbox_to_anchor=(.5, 1.005), frameon=False,
               handletextpad=.4, columnspacing=1.8)
    caption = ('S is enabled in all arms. The frozen compute-retention R x coverage-exit K study uses the same legal two-lane Consumer, '
               'shared physical executor, original D2/C8 deadlines and every offered audio interval. '
               'Every arm has all three fresh-process repeats at each of two preselected 16-session arrival phases. '
               'Points show individual runs; horizontal ticks and vertical ranges show observed medians and ranges, not confidence intervals. '
               'The fixed F2 actual-prompt fixture creates controlled useless tails; compatible long-work witnesses are counted separately '
               'only from unmodified actual prompts. Physical lease time includes both workers until actual batch drain, not merely cancellation requests. '
               'This reused development corpus does not measure natural fault prevalence or independent-source replication.')
    export(fig, output, 'retention_coverage_exit', caption)
    manifest = dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-SUMMARY-FIGURE', code_commit=commit,
                    inputs=INPUTS, new_model_calls=0, actual_execution_cells=24, python=sys.version,
                    platform=platform.platform(), matplotlib=matplotlib.__version__,
                    complete_history_equal_blocks=sum(r['canonical_histories_equal'] for r in factors),
                    complete_history_compared_blocks=len(factors),
                    result_scope='Controlled F2 service, two phases, temporal repeats on reused development sources',
                    output_files=[dict(path=p.name, bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                  for p in sorted(output.iterdir())])
    (output / 'RUN_RECORD.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    assert verify_source(args.source_manifest) == commit
    print(json.dumps(dict(output=str(output), actual_cells=24, new_model_calls=0)))


if __name__ == '__main__':
    main()
