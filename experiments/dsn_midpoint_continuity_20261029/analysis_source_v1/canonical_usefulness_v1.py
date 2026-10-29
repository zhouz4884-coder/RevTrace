"""Recount actual provisional views against selected full Canonical snapshots.

Offline, retrospective future-Canonical agreement; neither ground truth nor a
verification available to the serving policy. No runtime/GPU imports.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import re
import statistics
import sys
import unicodedata


INPUTS = {}
NORMALIZATION = "NFKC; casefold; curly apostrophe to ASCII; Unicode letter/digit tokens with internal apostrophes; discard other punctuation; single spaces"
SAFE_AUDIT = 'PASS_INDEPENDENT_RETIREMENT_AND_INPUT_CONSUMER_AUDIT'


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def sha(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def read(path, jsonl=False):
    path = Path(path)
    payload = path.read_bytes()
    INPUTS[str(path.resolve())] = dict(bytes=len(payload), sha256=digest(payload))
    text = payload.decode('utf8')
    return [json.loads(row) for row in text.splitlines() if row] if jsonl else json.loads(text)


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold().replace('\u2019', "'")
    return ' '.join(re.findall(r"[^\W_]+(?:'[^\W_]+)*", text))


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def basename(path):
    return str(path).replace('\\', '/').rstrip('/').rsplit('/', 1)[-1]


def flag(argv, key, default=None):
    return argv[argv.index(key) + 1] if key in argv else default


def planned(plan):
    cohorts = {row['cohort']: row for row in plan.get('cohorts', [])}
    for item in plan['cells']:
        argv = item.get('argv', [])
        # v3 deliberately retains historical `out`; argv/output are current.
        out = flag(argv, '--out', item.get('output', item.get('out')))
        need(out, 'planned cell has no actual output path')
        cell = dict(item, out=out, cell_id=item.get('cell_id', basename(out)))
        for key, option, default in [('adapter', '--adapter', 'qwen'), ('arrival', '--arrival', 'sync'),
                                     ('policy', '--policy', 'row_complete'), ('method', '--method', 'standard_fair'),
                                     ('rho', '--rho', 1), ('repeat', '--repeat', 0), ('sessions', '--sessions', 16)]:
            cell[key] = cell.get(key, flag(argv, option, default))
        for key in ['rho', 'repeat', 'sessions']:
            cell[key] = int(cell[key])
        cell.setdefault('arm', cell['policy'])
        cell.setdefault('phase', 'retirement')
        cell.setdefault('cohort', 'OLD_DEVELOPMENT_16' if cell['sessions'] == 16 else 'UNSPECIFIED')
        cell.setdefault('expected_source_commit', plan.get('code_commit'))
        cell.setdefault('model', flag(argv, '--model'))
        cell['speaker_map'] = dict(zip(cohorts.get(cell['cohort'], {}).get('source_ids', []),
                                       cohorts.get(cell['cohort'], {}).get('speakers', [])))
        yield cell


def canonical_snapshots(events, workers, consumers):
    """Select complete text only through actual commit -> Authority -> publication.

    At no point truncate a later text to an earlier audio frontier. A coarse
    Canonical boundary cannot supply a fine-boundary comparison.
    """
    starts = [row['t0_perf'] for row in events if row['kind'] == 'run-start']
    need(len(starts) == 1, 'trace must have exactly one run-start')
    t0 = starts[0]
    selected = {}
    for row in events:
        if row['kind'] == 'commit':
            key = (row['session_id'], row['version'])
            need(key not in selected, 'duplicate selected Canonical version')
            selected[key] = row
    result_by_job = {row['job']['job_id']: row for row in workers}
    need(len(result_by_job) == len(workers), 'duplicate completed worker job')
    canonical = {}
    for row in events:
        if row['kind'] != 'canonical-display':
            continue
        commit = selected[(row['session_id'], row['version'])]
        need(commit['job_id'] == row['job_id'] and commit['audio_end_sample'] == row['audio_end_sample'],
             'Canonical publication does not name the selected same-F commit')
        worker = result_by_job[commit['job_id']]
        result = worker['result']
        need(worker['job']['role'] == 'authority', 'Canonical selected a non-Authority row')
        need(result['token_ids'] == commit['segment_tokens'] and result['state_tokens'] == commit['next_prompt_tokens'],
             'selected Canonical state differs from completed Authority row')
        need(result['text'] == row['text'], 'complete Canonical text differs from selected result')
        if row.get('text_sha256'):
            need(row['text_sha256'] == digest(row['text'].encode()), 'Canonical text byte hash differs')
        key = (row['session_id'], row['audio_end_sample'])
        value = dict(text=row['text'], version=row['version'], job_id=row['job_id'],
                     selected_perf=t0 + commit['installed'], published_perf=t0 + row.get('displayed', row['time']),
                     consumer_certified_perf=None)
        if key in canonical:
            need(canonical[key]['text'] == value['text'] and canonical[key]['version'] == value['version'],
                 'different selected Canonical versions at the same audio F')
        else:
            canonical[key] = value
    for row in consumers:
        key = (row['session_id'], row['certified_frontier'])
        if key not in canonical:
            continue
        target = canonical[key]
        need(row['canonical_version'] == target['version'] and row['certified_text'] == target['text'],
             'actual certified Consumer snapshot differs from selected Canonical')
        at = row['observed_perf']
        old = target['consumer_certified_perf']
        target['consumer_certified_perf'] = min(old, at) if old is not None else at
    return canonical


def compare_view(row, canonical):
    visible, certified = row['valid_visible_frontier'], row['certified_frontier']
    output = dict(visible_frontier=visible, certified_frontier=certified,
                  ahead=visible > certified, observed_perf=row['observed_perf'],
                  visible_text_sha256=digest(row['visible_text'].encode()),
                  same_F_status='NOT_AHEAD', raw_equal=None, normalized_equal=None,
                  selected_lead_seconds=None, consumer_certification_lead_seconds=None)
    if not output['ahead']:
        return output
    target = canonical.get((row['session_id'], visible))
    if target is None:
        output['same_F_status'] = 'UNMATCHED_NO_SELECTED_SAME_F'
        return output
    before, after = row['visible_text'], target['text']
    common = 0
    for a, b in zip(before, after):
        if a != b:
            break
        common += 1
    lead = target['selected_perf'] - row['observed_perf']
    applied = target['consumer_certified_perf']
    output.update(same_F_status='FUTURE_SELECTED_SAME_F' if lead > 0 else 'SELECTED_BEFORE_OR_AT_VIEW',
                  canonical_version=target['version'], canonical_job_id=target['job_id'],
                  canonical_text_sha256=digest(after.encode()), raw_equal=before == after,
                  normalized_equal=normalize(before) == normalize(after),
                  raw_erased_characters_to_same_F_canonical=len(before) - common,
                  raw_inserted_characters_to_same_F_canonical=len(after) - common,
                  selected_lead_seconds=lead,
                  consumer_certification_lead_seconds=applied - row['observed_perf'] if applied is not None else None)
    return output


def recount(consumers, frontiers, canonical, end_perf):
    """All view exposures plus an audio partition using first actual coverage."""
    by_session = defaultdict(list)
    for index, row in enumerate(consumers):
        need(finite(row['observed_perf']) and row['observed_perf'] <= end_perf + 1e-6, 'invalid actual Consumer time')
        by_session[row['session_id']].append((index, row))
    views = []
    lookup = {}
    for sid, rows in by_session.items():
        need(all(a[1]['observed_perf'] <= b[1]['observed_perf'] for a, b in zip(rows, rows[1:])), 'Consumer clock regressed')
        for position, (index, row) in enumerate(rows):
            value = dict(session_id=sid, consumer_row_index=index, **compare_view(row, canonical))
            next_at = rows[position + 1][1]['observed_perf'] if position + 1 < len(rows) else end_perf
            value['wall_exposure_seconds'] = next_at - row['observed_perf']
            lookup[index] = value
            if value['ahead']:
                views.append(value)
    offered = []
    seen = set()
    for row in frontiers:
        key = (row['session_id'], row['frontier'])
        need(key not in seen, 'duplicate offered frontier')
        seen.add(key)
        first = next(((index, view) for index, view in by_session[row['session_id']]
                      if view['valid_visible_frontier'] >= row['frontier']), None)
        value = dict(session_id=row['session_id'], frontier=row['frontier'], audio_seconds=row['audio_seconds'],
                     display_timely=finite(row['display_latency']) and row['display_latency'] <= 2.,
                     dual_timely=bool(row['dual_credit']), display_latency=row['display_latency'],
                     commit_view_latency=row['commit_view_latency'], ahead=False, same_F_status='NOT_OBSERVED',
                     raw_equal=None, normalized_equal=None)
        if first is not None:
            index, actual = first
            need(abs(actual['observed_perf'] - row['first_actual_visible_perf']) < 1e-6,
                 'independent first actual coverage differs from audited frontier')
            value.update({key: item for key, item in lookup[index].items() if key != 'wall_exposure_seconds'})
        else:
            need(row['first_actual_visible_perf'] is None, 'audit saw a frontier absent from actual Consumer trace')
        offered.append(value)
    return views, offered


def summarize(frontiers, views):
    """Every offered audio interval appears once, including unmatched/missing."""
    output = dict(offered_frontiers=len(frontiers), offered_audio_seconds=sum(row['audio_seconds'] for row in frontiers),
                  ahead_consumer_views=len(views),
                  ahead_session_wall_exposure_seconds=sum(row['wall_exposure_seconds'] for row in views))
    for status in ['UNMATCHED_NO_SELECTED_SAME_F', 'FUTURE_SELECTED_SAME_F', 'SELECTED_BEFORE_OR_AT_VIEW']:
        output['ahead_view_' + status.lower() + '_count'] = sum(row['same_F_status'] == status for row in views)
    for equality in ['raw', 'normalized']:
        for state, expected in [('equal', True), ('different', False)]:
            chosen = [row for row in views if row[equality + '_equal'] is expected]
            output['ahead_view_' + equality + '_' + state + '_count'] = len(chosen)
            output['ahead_view_' + equality + '_' + state + '_session_wall_seconds'] = sum(row['wall_exposure_seconds'] for row in chosen)
    categories = {
        'not_observed': lambda r: r['same_F_status'] == 'NOT_OBSERVED',
        'first_certified': lambda r: r['same_F_status'] == 'NOT_AHEAD',
        'first_ahead': lambda r: r['ahead'],
        'first_ahead_unmatched': lambda r: r['same_F_status'] == 'UNMATCHED_NO_SELECTED_SAME_F',
        'first_ahead_future_selected': lambda r: r['same_F_status'] == 'FUTURE_SELECTED_SAME_F',
        'first_ahead_already_selected': lambda r: r['same_F_status'] == 'SELECTED_BEFORE_OR_AT_VIEW',
    }
    for name, choose in list(categories.items()):
        if name in ['first_ahead', 'first_ahead_future_selected']:
            for equality in ['raw', 'normalized']:
                categories[name + '_' + equality + '_equal'] = lambda r, choose=choose, equality=equality: choose(r) and r[equality + '_equal'] is True
                categories[name + '_' + equality + '_different'] = lambda r, choose=choose, equality=equality: choose(r) and r[equality + '_equal'] is False
    for name, choose in categories.items():
        chosen = [row for row in frontiers if choose(row)]
        output[name + '_frontiers'] = len(chosen)
        for deadline, condition in [('', lambda r: True), ('_display_timely', lambda r: r['display_timely']),
                                    ('_dual_timely', lambda r: r['dual_timely'])]:
            output[name + deadline + '_audio_seconds'] = sum(row['audio_seconds'] for row in chosen if condition(row))
    for kind in ['selected', 'consumer_certification']:
        key = kind + '_lead_seconds'
        chosen = [row for row in frontiers if row['ahead'] and finite(row.get(key))]
        weight = sum(row['audio_seconds'] for row in chosen)
        output[kind + '_lead_audio_weight_seconds'] = weight
        output[kind + '_lead_audio_weighted_mean_seconds'] = sum(row['audio_seconds'] * row[key] for row in chosen) / weight if weight else None
        output[kind + '_lead_frontier_median_seconds'] = statistics.median(row[key] for row in chosen) if chosen else None
    return output


def load_cell(cell, roots, allow_bounded):
    directory = next((root / basename(cell['out']) for root in roots if (root / basename(cell['out'])).exists()), Path(cell['out']))
    coverage = {key: cell[key] for key in ['cell_id', 'arm', 'phase', 'cohort', 'adapter', 'rho', 'arrival', 'repeat']}
    coverage.update(path=str(directory), expected_source_commit=cell['expected_source_commit'], status='MISSING', formal_accepted=False)
    required = ['attempt0/consumer.jsonl', 'attempt0/events.jsonl', 'attempt0/worker_records.jsonl',
                'attempt0/sessions.json', 'attempt0/config.json', 'audit/FRONTIERS.json', 'audit/SUMMARY.json']
    missing = [name for name in required if not (directory / name).exists()]
    if missing:
        coverage.update(status='MISSING_REQUIRED_TRACE_OR_AUDIT', missing=missing)
        return coverage, None
    audit = read(directory / 'audit/SUMMARY.json')
    need(audit['status'] == SAFE_AUDIT, 'original independent audit was not accepted')
    service = audit['service']
    need(all(service[key] == 0 for key in ['unauthorized_admissions', 'stale_publications', 'root_incompatible_actual_views', 'certified_only_violations']), 'protected service invariant failed')
    metadata = ['SUMMARY.json', 'FREEZE.json', 'RUN_RECORD.json', 'GATE.json', 'ENVIRONMENT.json']
    missing_metadata = [name for name in metadata if not (directory / name).exists()]
    if missing_metadata and not allow_bounded:
        coverage.update(status='SOURCE_FREEZE_METADATA_NOT_AVAILABLE', missing=missing_metadata)
        return coverage, None
    if not missing_metadata:
        summary, frozen, run, gate = [read(directory / name) for name in metadata[:4]]
        read(directory / 'ENVIRONMENT.json')
        need(summary['status'] == 'COMPLETE_SINGLE_CELL_AND_INDEPENDENT_AUDIT' and not (directory / 'STOP.json').exists(), 'cell incomplete or stopped')
        need(gate['gate'] == 'PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT', 'original cell gate not accepted')
        need(summary['independent_summary'] == audit, 'audit replacement cannot relabel an original failed cell')
        need(summary['source_commit'] == frozen['code_commit'] == run['code_commit'] == cell['expected_source_commit'], 'execution source relabelled')
        need(summary['config'] == frozen['frozen_config'], 'summary config differs from frozen config')
        for key in ['adapter', 'rho', 'arrival', 'repeat', 'method', 'sessions', 'policy']:
            need(frozen['frozen_config'][key] == cell[key], 'cell differs from frozen plan: ' + key)
        need(INPUTS[str((directory / 'FREEZE.json').resolve())]['sha256'] == run['frozen_config_sha256'], 'freeze changed')
        need(INPUTS[str((directory / 'ENVIRONMENT.json').resolve())]['sha256'] == frozen['frozen_config']['environment_sha256'], 'environment changed')
        coverage.update(formal_accepted=True, source_commit=summary['source_commit'])
    else:
        coverage['missing_source_identity_metadata'] = missing_metadata
    consumers, events, workers = [read(directory / 'attempt0' / name, True) for name in ['consumer.jsonl', 'events.jsonl', 'worker_records.jsonl']]
    sessions = read(directory / 'attempt0/sessions.json')
    cfg = read(directory / 'attempt0/config.json')
    frontiers = read(directory / 'audit/FRONTIERS.json')
    canonical = canonical_snapshots(events, workers, consumers)
    end = cfg['episode_origin_perf'] + service['original_episode_wall_seconds']
    views, offered = recount(consumers, frontiers, canonical, end)
    need(abs(sum(row['audio_seconds'] for row in offered) - sum(row['duration'] for row in sessions)) < 1e-6, 'offered audio denominator differs from sessions')
    need(len(offered) == service['whole_offered_frontiers'], 'offered frontier denominator differs from audit')
    session_map = {row['session_id']: row for row in sessions}
    if cell['speaker_map']:
        need([row['source_id'] for row in sorted(sessions, key=lambda r: r['session_id'])] == list(cell['speaker_map']), 'frozen cohort source/order differs')
    for row in views + offered:
        row.update(cell_id=cell['cell_id'], source_id=session_map[row['session_id']]['source_id'])
    sources = []
    for sid, spec in session_map.items():
        sources.append(dict(session_id=sid, source_id=spec['source_id'], speaker=cell['speaker_map'].get(spec['source_id']),
                            **summarize([row for row in offered if row['session_id'] == sid], [row for row in views if row['session_id'] == sid])))
    contract = dict(sessions=sessions, source_commit=cell['expected_source_commit'], phase=cell['phase'], cohort=cell['cohort'],
                    adapter=cell['adapter'], model=cell['model'], rho=cell['rho'], arrival=cell['arrival'],
                    repeat=cell['repeat'], fixture_sha256=cfg.get('retirement_fault_fixture_sha256'),
                    authority_runtime=cfg['authority_runtime'], proposal_runtime=cfg['proposal_runtime'],
                    microbatch=cfg['microbatch'], arrival_schedule_sha256=cfg.get('arrival_schedule_sha256'))
    coverage['status'] = 'ACCEPTED_AUDITED_TRACE_RECOUNT' if coverage['formal_accepted'] else 'BOUNDED_AUDITED_TRACE_RECOUNT_SOURCE_IDENTITY_NOT_REVALIDATED'
    return coverage, dict(plan=cell, metrics=summarize(offered, views), views=views, frontiers=offered, sources=sources,
                          pair_contract_sha256=sha(contract), final_WER_percent_separate=service['all_offered_WER_percent'])


def write_table(out, name, rows):
    (out / (name + '.json')).write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n', encoding='utf8')
    if rows:
        with (out / (name + '.csv')).open('w', newline='', encoding='utf8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
            writer.writeheader()
            writer.writerows({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--additional-plan', type=Path, action='append', default=[])
    parser.add_argument('--results-root', type=Path, action='append', default=[])
    parser.add_argument('--allow-bounded-traces', action='store_true', help='allow trace-only recount; never marks source identity/formal run accepted')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(not args.output.exists(), 'output directory must be new')
    cells = [cell for path in [args.plan] + args.additional_plan for cell in planned(read(path))]
    need(len({cell['cell_id'] for cell in cells}) == len(cells), 'duplicate planned cell ID')
    coverage, values = [], []
    for cell in cells:
        try:
            state, value = load_cell(cell, args.results_root, args.allow_bounded_traces)
        except (ValueError, KeyError, OSError) as error:
            state, value = dict(cell_id=cell['cell_id'], status='RECOUNT_REJECTED', formal_accepted=False, reason=str(error)), None
        coverage.append(state)
        if value:
            values.append(value)
    runs, sources, views, frontiers, pairs, source_pairs, factorials, source_factorials = [], [], [], [], [], [], [], []
    for value in values:
        labels = {key: value['plan'][key] for key in ['cell_id', 'arm', 'phase', 'cohort', 'adapter', 'rho', 'arrival', 'repeat']}
        runs.append(dict(**labels, **value['metrics'], final_WER_percent_separate=value['final_WER_percent_separate']))
        sources += [dict(**labels, **row) for row in value['sources']]
        views += value['views']
        frontiers += value['frontiers']
    for left, right in combinations(values, 2):
        if left['pair_contract_sha256'] != right['pair_contract_sha256'] or left['plan']['arm'] == right['plan']['arm']:
            continue
        labels = dict(reference_cell=left['plan']['cell_id'], candidate_cell=right['plan']['cell_id'],
                      reference_arm=left['plan']['arm'], candidate_arm=right['plan']['arm'])
        delta = lambda a, b: {key: b[key] - a[key] for key in a.keys() & b.keys() if finite(a[key]) and finite(b[key])}
        pairs.append(dict(**labels, delta_candidate_minus_reference=delta(left['metrics'], right['metrics'])))
        by_source = {row['source_id']: row for row in right['sources']}
        for row in left['sources']:
            source_pairs.append(dict(**labels, source_id=row['source_id'], speaker=row['speaker'],
                                     delta_candidate_minus_reference=delta(row, by_source[row['source_id']])) )
    by_contract = defaultdict(dict)
    for value in values:
        arms = by_contract[value['pair_contract_sha256']]
        need(value['plan']['arm'] not in arms, 'duplicate same-arm cells in a matched contract')
        arms[value['plan']['arm']] = value
    for contract, arms in by_contract.items():
        factors = ['R0_S0', 'R0_S1', 'R1_S0', 'R1_S1']
        if not all(arm in arms for arm in factors):
            continue
        def interaction(rows):
            return {key: rows[3][key] - rows[2][key] - rows[1][key] + rows[0][key]
                    for key in rows[0] if all(finite(row.get(key)) for row in rows)}
        labels = dict(pair_contract_sha256=contract, cells={arm: arms[arm]['plan']['cell_id'] for arm in factors})
        factorials.append(dict(**labels, interaction_Y11_minus_Y10_minus_Y01_plus_Y00=interaction([arms[arm]['metrics'] for arm in factors])))
        maps = [{row['source_id']: row for row in arms[arm]['sources']} for arm in factors]
        for source in maps[0]:
            source_factorials.append(dict(**labels, source_id=source, speaker=maps[0][source]['speaker'],
                                          interaction_Y11_minus_Y10_minus_Y01_plus_Y00=interaction([row[source] for row in maps])))
    cohorts = []
    for key in sorted({tuple(row[k] for k in ['phase', 'cohort', 'adapter', 'rho', 'arrival', 'arm']) for row in runs}):
        members = [row for row in runs if tuple(row[k] for k in ['phase', 'cohort', 'adapter', 'rho', 'arrival', 'arm']) == key]
        source_rows = [row for row in sources if row['cell_id'] in {item['cell_id'] for item in members}]
        cohorts.append(dict(zip(['phase', 'cohort', 'adapter', 'rho', 'arrival', 'arm'], key),
                            cells=[row['cell_id'] for row in members], unique_sources=len({row['source_id'] for row in source_rows}),
                            unique_known_speakers=len({row['speaker'] for row in source_rows if row['speaker'] is not None}),
                            source_observations_with_unknown_speaker=sum(row['speaker'] is None for row in source_rows),
                            per_repeat_metrics=[dict(repeat=row['repeat'], cell_id=row['cell_id'],
                                                     offered_audio_seconds=row['offered_audio_seconds'],
                                                     first_ahead_raw_equal_dual_timely_audio_seconds=row['first_ahead_raw_equal_dual_timely_audio_seconds'],
                                                     first_ahead_raw_different_dual_timely_audio_seconds=row['first_ahead_raw_different_dual_timely_audio_seconds'],
                                                     first_ahead_unmatched_dual_timely_audio_seconds=row['first_ahead_unmatched_dual_timely_audio_seconds']) for row in members],
                            repeated_exposure_audio_seconds=sum(row['offered_audio_seconds'] for row in members)))
    summary = dict(status='OFFLINE_RETROSPECTIVE_RECOUNT_COMPLETE' if len(values) == len(cells) else 'PARTIAL_OFFLINE_RETROSPECTIVE_RECOUNT',
                   planned_cells=len(cells), recounted_cells=len(values), formally_source_revalidated_cells=sum(row['formal_accepted'] for row in coverage),
                   coverage_status_counts=dict(Counter(row['status'] for row in coverage)), normalization=NORMALIZATION,
                   interpretation='Future selected full Canonical agreement at exactly the observed visible F; not groundtruth, semantic correctness, final WER, or deployed verification.',
                   audio_partition='Each offered frontier audio weight is assigned exactly once to its first actual covering Consumer view. Comparison is at that complete visible snapshot F, which may exceed the offered frontier. Unmatched same-F boundaries remain in the offered denominator.',
                   view_exposure='All actual ahead views and session-wall exposure are descriptive; they are not additional independent audio samples.',
                   lead_definition='Selected lead is actual Canonical installed_perf minus actual Consumer observed_perf; negative/zero means already selected. Consumer-certification lead is reported separately.',
                   new_GPU_calls=0)
    args.output.mkdir(parents=True)
    for name, rows in [('COVERAGE', coverage), ('RUNS', runs), ('SOURCE_METRICS', sources), ('AHEAD_VIEWS', views),
                       ('OFFERED_FRONTIERS', frontiers), ('PAIRED_EFFECTS', pairs), ('SOURCE_PAIRED_EFFECTS', source_pairs), ('COHORTS', cohorts)]:
        write_table(args.output, name, rows)
    write_table(args.output, 'FACTORIAL_EFFECTS', factorials)
    write_table(args.output, 'SOURCE_FACTORIAL_EFFECTS', source_factorials)
    (args.output / 'SUMMARY.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf8')
    record = dict(experiment_id='REVTRACE-CANONICAL-USEFULNESS-' + args.output.name,
                  evidence_type='offline recorded-trace recount; no new serving experiment',
                  analysis_script_sha256=digest(Path(__file__).read_bytes()), inputs=INPUTS,
                  expected_execution_source_commits=sorted({cell['expected_source_commit'] for cell in cells}),
                  environment=dict(python=sys.version, platform=platform.platform()),
                  raw_result_paths=[row.get('path') for row in coverage if row.get('path')],
                  aggregate_summary_path=str((args.output / 'SUMMARY.json').resolve()),
                  gate_decision=summary['status'], new_GPU_calls=0)
    (args.output / 'ANALYSIS_RECORD.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
