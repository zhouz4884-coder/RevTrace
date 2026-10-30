"""Traceable tables and compact figures; no model calls and no semantic fill-in."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import re

CONDITIONS = ('none', 'duplicate_late', 'worker_after_asr', 'worker_partial_frame',
              'owner_before_durable', 'owner_after_durable')
ARMS = ('conservative', 'fullcall')
LIVE_FIELDS = ('live_jobs', 'completed_full', 'branch_steps', 'canonical_witnesses',
               'nodes', 'projections', 'issued_proofs', 'issued_id_memory_entries',
               'pending_job_refs')
REQUIRED_COHORTS = {'short_main': 24, 'short_regression': 4, 'sustained': 8}


def read(path):
    return json.loads(Path(path).read_bytes())


def lines(path):
    return [json.loads(x) for x in Path(path).read_bytes().splitlines() if x.strip()]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def put(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf8')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def minmax(values):
    return [min(values), max(values)] if values and all(finite(v) for v in values) else None


def verify_config_binding(runtime_config, collection, plan_cell, frozen_config_path):
    """The operator's frozen file and runtime echo have distinct byte encodings."""
    if sha(frozen_config_path) != plan_cell['config_sha256']:
        raise ValueError('original frozen config bytes differ from exact formal plan')
    if runtime_config != read(frozen_config_path):
        raise ValueError('complete runtime config object differs from original frozen input')
    echo = collection['raw_config_sha256']
    if not re.fullmatch('[0-9a-f]{64}', echo):
        raise ValueError('actual runtime echo digest missing')
    return dict(frozen_input_sha256=plan_cell['config_sha256'],
                runtime_config_echo_sha256=echo,
                frozen_config_path=str(frozen_config_path),
                complete_JSON_value_equality=True,
                byte_encoding_scope='Frozen original input and runtime echo have separately bound SHA256; no byte-equality claim.')


def load_index(path):
    index = read(path)
    root = Path(path).resolve().parent
    planned = {}
    if len(index.get('plans', [])) != 2:
        raise ValueError('both exact frozen formal plans and their SHA256 inputs required')
    plan_kinds = set()
    for descriptor in index['plans']:
        plan_path = (root/descriptor['path']).resolve()
        if sha(plan_path) != descriptor['sha256']:
            raise ValueError('frozen formal plan bytes differ')
        plan = read(plan_path)
        configs_dir = (root/descriptor['frozen_configs_dir']).resolve()
        if not configs_dir.is_dir():
            raise ValueError('original frozen per-cell config directory required')
        kind = plan['campaign_kind']
        plan_kinds.add(kind)
        if len(plan['cells']) != plan['expected_cells']:
            raise ValueError('frozen formal plan cell count differs')
        for cell in plan['cells']:
            if cell['cell_id'] in planned:
                raise ValueError('duplicate frozen formal plan cell')
            frozen_config = configs_dir/(cell['cell_id']+'.json')
            planned[cell['cell_id']] = (kind, cell, plan['source_commit'], frozen_config)
    if plan_kinds != {'formal_short28', 'formal_sustained8'} or len(planned) != 36:
        raise ValueError('exact formal short28 plus sustained8 required')
    trials, ids = [], set()
    for item in index['trials']:
        folder = (root / item['bounded_dir']).resolve()
        collection = read(folder / 'COLLECTION_METADATA.json')
        if collection['schema'] != 'revtrace-bounded-service-evidence-v1':
            raise ValueError('unexpected bounded evidence schema')
        for name, digest in collection['outputs'].items():
            if sha(folder / name) != digest:
                raise ValueError('bounded input bytes differ: ' + name)
        config = read(folder / 'CONFIG.json')
        metrics = read(folder / 'METRICS_SUMMARY.json')
        cell = config['cell_id']
        if cell not in planned:
            raise ValueError('actual cell absent from exact frozen formal plans')
        plan_kind, plan_cell, plan_commit, frozen_config = planned[cell]
        binding = verify_config_binding(config, collection, plan_cell, frozen_config)
        if config['source_commit'] != plan_commit:
            raise ValueError('actual source differs from exact frozen plan')
        if collection['raw_config_sha256'] != metrics['primary']['raw_inputs']['config_sha256']:
            raise ValueError('actual runtime echo digest differs between export and metrics')
        if item['cohort'] == 'sustained' and plan_kind != 'formal_sustained8':
            raise ValueError('short trial cannot be relabelled sustained')
        if item['cohort'] != 'sustained' and plan_kind != 'formal_short28':
            raise ValueError('sustained trial cannot be relabelled short')
        if cell in ids:
            raise ValueError('duplicate actual cell in index')
        ids.add(cell)
        if item['cohort'] not in REQUIRED_COHORTS:
            raise ValueError('explicit analysis cohort required')
        if config['arm'] not in ARMS:
            raise ValueError('unknown runtime arm')
        if item['condition'] != config.get('fault', {'kind': 'none'})['kind']:
            raise ValueError('analysis condition differs from frozen runtime config')
        if collection['source_commit'] != config['source_commit'] or metrics['source_commit'] != config['source_commit']:
            raise ValueError('actual source identity differs between inputs')
        semantic = item.get('semantic_audit', {})
        for field in ('illegal_installs', 'legal_progress_wrong_rejections'):
            if semantic.get(field) is not None:
                if not all(semantic.get(k) for k in ('checker_source_commit', 'checker_summary_sha256', 'scope')):
                    raise ValueError('independent semantic number lacks checker provenance')
                if not re.fullmatch('[0-9a-f]{40}', semantic['checker_source_commit']):
                    raise ValueError('checker source commit is not complete')
                if not re.fullmatch('[0-9a-f]{64}', semantic['checker_summary_sha256']):
                    raise ValueError('checker summary digest is not complete')
                if type(semantic[field]) is not int or semantic[field] < 0:
                    raise ValueError('semantic counts must be explicit nonnegative integers')
        trials.append(dict(item=item, folder=folder, config=config, metrics=metrics,
                           collection=collection, semantic=semantic, config_binding=binding))
    counts = {c: sum(t['item']['cohort'] == c for t in trials) for c in REQUIRED_COHORTS}
    if counts != REQUIRED_COHORTS:
        raise ValueError('complete formal36 scope required: ' + str(counts))
    if ids != set(planned):
        raise ValueError('missing exact frozen formal cells')
    if len({t['config']['source_commit'] for t in trials}) != 1:
        raise ValueError('formal36 source commits differ')
    for condition in CONDITIONS:
        for arm in ARMS:
            selected = [t for t in trials if t['item']['cohort'] == 'short_main'
                        and t['item']['condition'] == condition and t['config']['arm'] == arm]
            if len(selected) != 2 or {t['config']['repeat'] for t in selected} != {0, 1}:
                raise ValueError('six-condition two-fresh arm scope differs')
    sustained = [t for t in trials if t['item']['cohort'] == 'sustained']
    source_sets = {tuple(s['source_id'] for s in t['config']['settings']['sources']) for t in sustained}
    if len(source_sets) != 2 or any(len(s) != 1 for s in source_sets):
        raise ValueError('exactly two individual sustained source streams required')
    for source in source_sets:
        selected = [t for t in sustained if tuple(s['source_id'] for s in t['config']['settings']['sources']) == source]
        if {(t['config']['arm'], t['config']['repeat']) for t in selected} != {(a, r) for a in ARMS for r in (0, 1)}:
            raise ValueError('sustained two-arm two-fresh scope differs')
    return trials


def trial_row(t):
    config, metrics = t['config'], t['metrics']
    primary, integrity = metrics['primary'], metrics['integrity']
    clocks = metrics['recovery']['events']
    expected_clock = t['item']['condition'] not in ('none', 'duplicate_late')
    if expected_clock and len(clocks) != 1:
        raise ValueError('exactly one actual fault required for a recovery cell')
    rec = clocks[0] if expected_clock else {}
    task = (integrity['all_original_obligations_eventually_processed']
            and integrity['consumer_binding']['durable_facts_not_yet_consumed'] == 0
            and integrity['unexpected_owner_error_records'] == 0
            and integrity['original_reference']['status'] == 'PASS_COMPLETE_ORIGINAL_REFERENCE')
    row = dict(cell_id=config['cell_id'], cohort=t['item']['cohort'],
        condition=t['item']['condition'], arm=config['arm'], repeat=config['repeat'],
        source_commit=config['source_commit'], source_ids=[s['source_id'] for s in config['settings']['sources']],
        config_binding=t['config_binding'],
        illegal_installs=t['semantic'].get('illegal_installs'),
        legal_progress_wrong_rejections=t['semantic'].get('legal_progress_wrong_rejections'),
        semantic_audit=t['semantic'] or None,
        complete_original_task=bool(task), local_reject_records=integrity['local_reject_records'],
        local_reject_canonical_mutations=integrity['local_reject_canonical_mutations'],
        final_quality=metrics['quality'], original_reference=integrity['original_reference'],
        original_D2_C8_pass=primary['complete_coverage_and_original_quantile_pass'],
        original_D99=primary['primary_linear_all_offered_D99'],
        original_C99=primary['primary_linear_all_offered_C99'],
        EOS_D2_misses=primary['EOS_D2_misses'],
        D2_misses_all_offered=primary['D2_misses_all_offered'],
        C8_misses_all_offered=primary['C8_misses_all_offered'],
        missing_D_frontiers=primary['missing_D_frontiers'], missing_C_frontiers=primary['missing_C_frontiers'],
        offered_frontiers=primary['offered_frontiers'],
        offered_audio_seconds=primary['offered_audio_seconds'],
        dual_deadline_audio_credit_seconds=primary['dual_deadline_audio_credit_seconds'],
        energy_joules=metrics['energy'].get('service', {}).get('total_joules'),
        energy_status=metrics['energy']['status'], recovery_clock_applicable=expected_clock,
        recovery=rec if expected_clock else None,
        new_model_completed_after_fault_and_certified_consume_seconds=rec.get('fault_to_new_certified_result'),
        old_durable_replay_seconds=rec.get('fault_to_old_fact_replay'),
        new_durable_fact_seconds=rec.get('fault_to_new_durable_fact'),
        pending_accepted_uncertified_samples=integrity['pending_accepted_uncertified_samples'],
        unprocessed_all_offered_samples=integrity['unprocessed_all_offered_samples'],
        observed_acknowledged_input_loss_samples=integrity['observed_acknowledged_input_loss_samples'],
        posterior_whole_text_support=metrics['posterior_whole_text_support'],
        runtime_gate=metrics['gate'], bounded_input=str(t['folder']))
    return row


def aggregate(rows):
    output = []
    for condition in CONDITIONS:
        for arm in ARMS:
            cells = [r for r in rows if r['cohort'] == 'short_main' and r['condition'] == condition and r['arm'] == arm]
            known_illegal = [c['illegal_installs'] for c in cells]
            output.append(dict(condition=condition, arm=arm, fresh_trials=len(cells),
                illegal_installs=sum(known_illegal) if all(v is not None for v in known_illegal) else None,
                complete_original_task=sum(c['complete_original_task'] for c in cells),
                local_reject_records=sum(c['local_reject_records'] for c in cells),
                local_reject_canonical_mutations=sum(c['local_reject_canonical_mutations'] for c in cells),
                new_certified_result_seconds=minmax([c['new_model_completed_after_fault_and_certified_consume_seconds'] for c in cells])
                    if cells[0]['recovery_clock_applicable'] else 'NA',
                old_durable_replay_seconds=minmax([c['old_durable_replay_seconds'] for c in cells])
                    if cells[0]['recovery_clock_applicable'] else 'NA',
                original_D2_C8_pass=sum(c['original_D2_C8_pass'] for c in cells),
                EOS_D2_misses=sum(c['EOS_D2_misses'] for c in cells),
                energy_joules=minmax([c['energy_joules'] for c in cells])))
    return output


def display_range(value, digits=2):
    if value == 'NA':
        return '--'
    if value is None:
        return '?'
    a, b = value
    return f'{a:.{digits}f}' if a == b else f'{a:.{digits}f}--{b:.{digits}f}'


def write_tables(trials, out):
    rows = [trial_row(t) for t in trials]
    groups = aggregate(rows)
    put(out / 'ALL36_MACHINE_TABLE.json', rows)
    put(out / 'SHORT24_AGGREGATES.json', groups)
    flat = []
    for row in rows:
        flat.append({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    with (out / 'ALL36_MACHINE_TABLE.csv').open('w', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    labels = dict(none='No fault', duplicate_late='Duplicate / late', worker_after_asr='Worker after ASR',
        worker_partial_frame='Worker partial frame', owner_before_durable='Owner before durable',
        owner_after_durable='Owner after durable')
    tex = [r'\begin{tabular}{lrrrrrr}', r'\toprule',
           r'Condition & Illegal / done & Reject / mutation & New result (s) & D2/C8 pass & EOS miss & Energy (J) \\',
           r'\midrule']
    for condition in CONDITIONS:
        pair = [next(g for g in groups if g['condition'] == condition and g['arm'] == arm) for arm in ARMS]
        def two(fn): return r'\shortstack{' + fn(pair[0]) + r'\\' + fn(pair[1]) + '}'
        vals = [labels[condition],
            two(lambda g: ('?' if g['illegal_installs'] is None else str(g['illegal_installs'])) + f" / {g['complete_original_task']}/2"),
            two(lambda g: f"{g['local_reject_records']} / {g['local_reject_canonical_mutations']}"),
            two(lambda g: display_range(g['new_certified_result_seconds'])),
            two(lambda g: f"{g['original_D2_C8_pass']}/2"),
            two(lambda g: str(g['EOS_D2_misses'])),
            two(lambda g: display_range(g['energy_joules'], 0))]
        tex.append(' & '.join(vals) + r' \\')
    tex.extend([r'\bottomrule', r'\end{tabular}',
        '% Fixed vertical order within each cell: Conservative / Full-call. Ranges are two fresh trials, not confidence intervals.',
        '% New result copies frozen 4f fault_to_new_certified_result (runtime model_end>=fault filter). Any strict > statement is a separately audited observed property.',
        '% A qualifying call may already be in flight on a surviving worker. This clock is neither replacement-neural readiness nor old durable replay.',
        '% Illegal installs require independent trace-checker evidence. ? means unknown. -- means not applicable, not zero.',
        '% Main table: development S0908 24 cells only. Regression4 and sustained8 remain separately listed in ALL36_MACHINE_TABLE.'])
    (out / 'reliability_table.tex').write_text('\n'.join(tex) + '\n', encoding='utf8')
    return rows


def bins(points, xkey, yfn, width=1.0):
    values = defaultdict(list)
    for row in points:
        x, y = row.get(xkey), yfn(row)
        if finite(x) and finite(y):
            values[math.floor(x / width)].append(y)
    keys = sorted(values)
    return ([width * (k + .5) for k in keys], [min(values[k]) for k in keys],
            [max(values[k]) for k in keys])


def plot(trials, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.text import Text
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 8.5,
        'mathtext.fontset': 'stix', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'svg.fonttype': 'none', 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .6, 'legend.frameon': False, 'savefig.facecolor': 'white',
        'axes.labelsize': 8.5, 'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5})
    sustained = sorted([t for t in trials if t['item']['cohort'] == 'sustained'], key=lambda t: t['config']['cell_id'])
    bysource = defaultdict(list)
    by_source_arm = defaultdict(list)
    all_history, all_edges = [], []
    memory = []
    for t in sustained:
        sid = t['config']['settings']['sources'][0]['source_id']
        series = {name: lines(t['folder'] / (name + '.jsonl')) for name in
                  ('native_boundaries', 'canonical_edges', 'frontiers', 'history', 'gpu_memory')}
        if not all(series[name] for name in ('native_boundaries', 'canonical_edges', 'frontiers', 'history')):
            raise ValueError('all sustained serving series required')
        bysource[sid].append((t, series))
        by_source_arm[(sid, t['config']['arm'])].append((t, series))
        all_history.extend(series['history'])
        all_edges.append((t['config']['cell_id'], series['canonical_edges']))
        history = series['history']
        gpu = series['gpu_memory']
        memory.append(dict(cell_id=t['config']['cell_id'], source_id=sid,
            history_samples=len(history),
            individual_entry_peaks={k: max(r['history'][k] for r in history) for k in LIVE_FIELDS},
            unpinned_terminal_peak=max(r['history']['inbox']['terminal']-r['history']['inbox']['pinned_terminals'] for r in history),
            total_terminal_peak=max(r['history']['inbox']['terminal'] for r in history),
            pinned_terminal_peak=max(r['history']['inbox']['pinned_terminals'] for r in history),
            audit_retained_peaks={k: max(r['history']['audit_retained'][k] for r in history) for k in history[0]['history']['audit_retained']},
            consumer_pins_peak=max(r['consumer_pins'] for r in history),
            pending_publications_peak=max(r['pending_publications'] for r in history),
            application_and_process_bytes={k: minmax([r[k] for r in history if finite(r.get(k))]) for k in
                ('current_cut_bytes', 'current_text_bytes', 'immutable_audio_bytes', 'owner_RSS_bytes')},
            NVML_gpu_memory_MiB={str(device): minmax([r['gpu_memory_MiB'][str(device)] for r in gpu if r.get('gpu_memory_MiB') and str(device) in r['gpu_memory_MiB']]) for device in (0, 1)},
            worker_torch_allocated_reserved='UNKNOWN_NOT_RECORDED',
            no_sum_of_separate_maxima=True))
    put(out / 'SUSTAINED8_MEMORY_DETAILS.json', memory)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 3.0))
    fig.subplots_adjust(left=.075, right=.92, bottom=.17, top=.87, wspace=.43, hspace=.72)
    a, b, c, d = axes.flat
    at = a.twinx(); at.spines['right'].set_visible(True)
    dt = d.twinx(); dt.spines['right'].set_visible(True)
    colors = ['#0F4D92', '#6B9BCB', '#A53338', '#CF8A8D']
    labels = []
    def band(ax, points, xkey, fn, color, ls='-', width=1., alpha=.16, label=None):
        x, lo, hi = bins(points, xkey, fn, width)
        ax.fill_between(x, lo, hi, color=color, alpha=alpha, lw=0)
        ax.plot(x, hi, color=color, ls=ls, lw=.85, label=label)
    frontier_details = []
    for i, ((sid, arm), cells) in enumerate(sorted(by_source_arm.items())):
        color = colors[i]
        short = re.search(r'S\d+', sid)
        label = (short[0] if short else sid) + (' C' if arm == 'conservative' else ' F')
        labels.append((label, color))
        boundaries = [r for _, series in cells for r in series['native_boundaries']]
        inserts = [dict(r, audio_s=r['end_frontier']/16000) for r in boundaries if r['boundary'] == 'audio_insert']
        trims = [dict(r, audio_s=r['end_frontier']/16000) for r in boundaries if r['boundary'] == 'context_trim']
        band(a, inserts, 'audio_s', lambda r: r['after']['audio_buffer_samples']/16000, color, width=.5)
        band(at, trims, 'audio_s', lambda r: r['after']['total_decoder_input_tokens'], color, ':', width=.5)
        frontiers = [dict(r, audio_s=r['frontier']/16000) for _, series in cells for r in series['frontiers']]
        band(b, frontiers, 'audio_s', lambda r: r['D'], color, '-', width=.5)
        band(b, frontiers, 'audio_s', lambda r: r['C'], color, ':', width=.5)
        for t, series in cells:
            frontier_details.append(dict(cell_id=t['config']['cell_id'], source_id=sid,
                offered_frontiers=len(series['frontiers']), missing_D=sum(r['D'] is None for r in series['frontiers']),
                missing_C=sum(r['C'] is None for r in series['frontiers']),
                changed_selected_edges=sum(r['own_prediction_changed'] is True for r in series['canonical_edges']),
                unknown_selected_edges=sum(r['own_prediction_changed'] is None for r in series['canonical_edges'])))
        histories = [r for _, series in cells for r in series['history']]
        band(d, histories, 't_since_origin', lambda r: r['current_cut_bytes']/1024, color, '-')
        band(d, histories, 't_since_origin', lambda r: r['current_text_bytes']/1024, color, ':')
        band(dt, histories, 't_since_origin', lambda r: r['owner_RSS_bytes']/2**20 if finite(r.get('owner_RSS_bytes')) else None, color, '--', alpha=.07)
    # Every selected edge is eligible for the rug; unknown evidence is distinct.
    for i, (cell, edges) in enumerate(all_edges):
        y = .025 + .014*i
        changed = [r['frontier']/16000 for r in edges if r['own_prediction_changed'] is True]
        unknown = [r['frontier']/16000 for r in edges if r['own_prediction_changed'] is None]
        a.plot(changed, [y]*len(changed), '|', color='#525B68', ms=2.5, mew=.5, transform=a.get_xaxis_transform())
        a.plot(unknown, [y]*len(unknown), 'x', color='#AD6225', ms=2.5, mew=.5, transform=a.get_xaxis_transform())
    missing_d = sum(row['missing_D'] for row in frontier_details)
    missing_c = sum(row['missing_C'] for row in frontier_details)
    if missing_d or missing_c:
        b.text(.99, .99, f'Missing D/C: {missing_d}/{missing_c}', transform=b.transAxes,
               ha='right', va='top', fontsize=8.5, color='#AD6225')
    history_series = [
        ('Unpinned receipts', '#0F4D92', '-', lambda r: r['history']['inbox']['terminal']-r['history']['inbox']['pinned_terminals']),
        ('Max retained audit class', '#A53338', ':', lambda r: max(r['history']['audit_retained'].values(), default=0)),
        ('Max live category', '#28734F', '-', lambda r: max(r['history'][k] for k in LIVE_FIELDS)),
        ('Consumer pins', '#AD6225', '--', lambda r: r['consumer_pins']),
        ('Pending publications', '#79528E', '-.', lambda r: r['pending_publications'])]
    for name, color, style, fn in history_series:
        for run_index, t in enumerate(sustained):
            points = lines(t['folder']/'history.jsonl')
            x, lo, hi = bins(points, 't_since_origin', fn)
            c.plot(x, hi, color=color, ls=style, lw=.55, alpha=.65,
                   label=name if run_index == 0 else None)
    c.axhline(64, c='#777777', ls='--', lw=.6)
    c.set_ylim(bottom=0)
    a.set(xlabel='Audio frontier (s)', ylabel='Audio buffer (s)')
    at.set_ylabel('Derived T+C', fontsize=8.5)
    b.set(xlabel='Offered audio frontier (s)', ylabel='Actual delay (s)')
    for threshold in (2, 8):
        b.axhline(threshold, c='#777777', ls='--', lw=.55)
    b.set_ylim(bottom=0)
    c.set(xlabel='Service time (s)', ylabel='Entries (bin maximum)')
    d.set(xlabel='Service time (s)', ylabel='Current state / text (KiB)')
    dt.set_ylabel('Owner RSS (MiB)', fontsize=8.5)
    input_ends = sorted({t['config']['settings']['sources'][0]['frames']/16000 for t in sustained})
    for ax in (c, d):
        for end in input_ends:
            ax.axvline(end, c='#BBBBBB', ls=':', lw=.55, zorder=0)
    for ax, title in zip((a, b, c, d), ('a  Native window / context', 'b  Original D2 / C8 endpoints',
                                       'c  Live dependencies / retained history', 'd  Current data / process memory')):
        ax.set_title(title, loc='left', fontsize=8.5, pad=4)
        ax.grid(axis='y', color='#DDDDDD', lw=.35)
    handles = [Line2D([], [], c=color, lw=1, label=label) for label, color in labels]
    fig.legend(handles=handles, fontsize=8.5, loc='upper center',
               bbox_to_anchor=(.5, 1.0), handlelength=1.0,
               ncol=4, columnspacing=.8, borderaxespad=.1)
    b.legend(handles=[Line2D([], [], c='#333333', lw=1, ls='-', label='D'),
                      Line2D([], [], c='#333333', lw=1, ls=':', label='C')], fontsize=8.5,
             loc='upper left', ncol=2, handlelength=1.2, columnspacing=.6)
    fig.legend(*c.get_legend_handles_labels(), fontsize=8.5, loc='lower center',
               bbox_to_anchor=(.5, .0), ncol=5, handlelength=1.1,
               columnspacing=.6, borderaxespad=.2)
    d.legend(handles=[Line2D([], [], c='#333333', lw=1, ls='-', label='Cut'),
                      Line2D([], [], c='#333333', lw=1, ls=':', label='Text'),
                      Line2D([], [], c='#333333', lw=1, ls='--', label='RSS')], fontsize=8.5,
             loc='upper left', ncol=3, handlelength=1.2, columnspacing=.5)
    fig.canvas.draw()
    text_artists = [obj for obj in fig.findobj(Text) if obj.get_visible() and obj.get_text()]
    minimum_size = min(obj.get_fontsize() for obj in text_artists)
    if minimum_size < 8:
        raise ValueError('figure text smaller than 8pt')
    for ext in ('pdf', 'svg', 'png'):
        fig.savefig(out / ('sustained_state_history.' + ext), dpi=300)
    plt.close(fig)
    put(out / 'SUSTAINED8_FRONTIER_AND_CLUSTER_DETAILS.json', frontier_details)
    return dict(figure_size_inches=[7.2, 3.0], minimum_text_points=minimum_size,
        serving_trials=len(sustained), sources=len(bysource),
        per_source_trials=4, envelope_fresh_trials=2, new_model_calls=0,
        transformation='Native/endpoints: min-max across every actual observation in each 0.5s audio-frontier bin within each fixed (source,arm), two fresh trials. History: maximum over every observed row in each 1s service-time bin separately for each of all eight trials; no cross-run sum. Current data/RSS: min-max every row in each 1s bin within fixed (source,arm), two fresh trials. Not confidence intervals.',
        x_axes='Native/endpoints use original audio frontier. History/current state/RSS use actual wall time since original ORIGIN including post-input drain/backlog; no audio-duration truncation.',
        original_input_end_seconds=input_ends,
        selected_edge_rug='Panel a, all eight rows: gray own-prediction-changed edges; orange x unknown. It is not human-error rate.',
        rug_row_order_bottom_to_top=[cell for cell, edges in all_edges],
        missing_D_frontiers=missing_d, missing_C_frontiers=missing_c,
        native_boundary_scope='All actual worker observations including recomputation. Audio-insert and post-trim are distinct boundary events.',
        decoder_limit_scope='Derived post-trim T+C is the exact exported observer field: current token-group sum plus reencoded context tokens, excluding a nonempty-context prefix. It is not full L or an observed forward tensor; no positional-overflow claim.',
        pending_visual_review=True,
        memory_scope='No sum of category maxima; no constant total RSS claim. NVML separate; worker torch allocator unknown.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    trials = load_index(args.index)
    args.out.mkdir(parents=True, exist_ok=False)
    rows = write_tables(trials, args.out)
    audit = plot(trials, args.out)
    audit.update(index_path=str(args.index.resolve()), index_sha256=sha(args.index),
        script_sha256=sha(Path(__file__)), contract_sha256=sha(Path(__file__).with_name('EVIDENCE_CONTRACT.zh.md')),
        semantic_audit_known_cells=sum(r['illegal_installs'] is not None for r in rows),
        outputs={p.name: sha(p) for p in sorted(args.out.iterdir()) if p.is_file()},
        analysis_gate='PENDING_INDEPENDENT_INPUT_AND_VISUAL_QA')
    put(args.out / 'FIGURE_TABLE_AUDIT.json', audit)
    print(json.dumps(dict(cells=len(rows), sustained_cells=8,
                         analysis_gate=audit['analysis_gate'], out=str(args.out))))


if __name__ == '__main__':
    main()
