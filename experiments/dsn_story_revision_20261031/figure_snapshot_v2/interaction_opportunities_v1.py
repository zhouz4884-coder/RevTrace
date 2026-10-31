"""Offline recount of witnessed opportunities at actual Canonical installations.

Only complete, actually published Private work is eligible. No runtime imports,
counterfactual jobs, new model calls, or changes to a frozen experiment.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import sys


INPUTS = {}
COUNTS = ('canonical_updates', 'matched_consumer_updates', 'ahead_updates',
          'compatible_opportunities', 'incompatible_ahead_updates',
          'unresolved_ahead_updates', 'compatible_retained', 'compatible_cleared',
          'compatible_changed', 'compatible_unmatched', 'incompatible_cleared',
          'incompatible_still_visible', 'ahead_to_consumer_boundary_changed',
          'ahead_observation_missing', 'install_inflight_ahead_jobs',
          'install_complete_unpublished_ahead_jobs')
DIMENSIONS = ('phase', 'adapter', 'rho', 'arrival', 'cohort', 'repeat', 'arm')
RATE_DIMENSIONS = (*DIMENSIONS, 'clock_scope')


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def read(path, jsonl=False):
    path = Path(path)
    data = path.read_bytes()
    INPUTS[str(path.resolve())] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    text = data.decode('utf8')
    return [json.loads(line) for line in text.splitlines() if line] if jsonl else json.loads(text)


def basename(path):
    return str(path).replace('\\', '/').rstrip('/').rsplit('/', 1)[-1]


def need(value, reason):
    if not value:
        raise ValueError(reason)


def complete_chain(jid, F, P, records, published, fine):
    """Replay exact Private predecessor links; never trust a retention boolean.

    A unique earlier same-session/generation complete published result must
    supply every consumed prompt, until the newly selected (F,P) is reached.
    Return unknown for missing/ambiguous evidence, false for an exact mismatch.
    """
    route = []
    seen = set()
    target = records.get(jid)
    if target is None:
        return None, 'visible_job_has_no_complete_result', route
    identity = tuple(target['job'].get(k) for k in
                     ('session_id', 'source_id', 'contract_epoch', 'contract_digest', 'branch_generation'))
    while jid not in seen:
        seen.add(jid)
        if jid not in records or jid not in published:
            return None, 'missing_complete_published_ancestor', route
        row = records[jid]
        job, result = row['job'], row['result']
        route.append(jid)
        if job['role'] != 'proposal':
            return False, 'non_private_ancestor', route
        if tuple(job.get(k) for k in ('session_id', 'source_id', 'contract_epoch',
                                      'contract_digest', 'branch_generation')) != identity:
            return False, 'ancestor_identity_changed', route
        if not all(k in result for k in ('state_tokens', 'token_ids', 'text')):
            return None, 'partial_result_is_not_a_complete_ancestor', route
        actual_prompt = result.get('execution_context_audit', {}).get('executed_prompt_tokens',
                                    job.get('fault_actual_prompt_tokens', job['prompt_tokens']))
        if actual_prompt != job['prompt_tokens']:
            return False, 'actual_conditioning_differs_from_declared_prompt', route
        # audio_start_sample binds the old Canonical interval and may precede
        # this job's actual feedback boundary. chunk_id is the relevant boundary.
        if job['chunk_id'] == round(F / fine):
            return (True, 'exact_selected_root', route) if job['prompt_tokens'] == list(P) else \
                (False, 'selected_root_prompt_mismatch', route)
        if job['audio_end_sample'] == F:
            return (True, 'complete_ancestor_matches_selected_root', route) if result['state_tokens'] == list(P) else \
                (False, 'selected_boundary_state_mismatch', route)
        if job['chunk_id'] < round(F / fine):
            return False, 'private_feedback_boundary_precedes_selected_root', route
        options = []
        for key in published:
            if key not in records:
                continue
            prior = records[key]
            pred = prior['job']
            if (pred['role'] == 'proposal' and
                tuple(pred.get(k) for k in ('session_id', 'source_id', 'contract_epoch',
                                           'contract_digest', 'branch_generation')) == identity and
                pred['end_window'] == job['chunk_id'] and
                F <= pred['audio_end_sample'] < job['audio_end_sample'] and
                prior['result'].get('state_tokens') == job['prompt_tokens']):
                # The supplying result must really have been available when the
                # child was issued; future coincident token strings are not ancestry.
                received = prior['result'].get('received_perf')
                if received is not None and received > job['enqueue_perf']:
                    continue
                options.append(key)
        if len(options) != 1:
            return None, ('missing_complete_ancestor' if not options else 'ambiguous_complete_ancestry'), route
        jid = options[0]
    return False, 'ancestry_cycle', route


def rates(row):
    for name, numerator, denominator in [
        ('ahead_rate_all_updates', 'ahead_updates', 'canonical_updates'),
        ('compatible_rate_all_updates', 'compatible_opportunities', 'canonical_updates'),
        ('compatible_rate_ahead_updates', 'compatible_opportunities', 'ahead_updates'),
        ('retained_rate_compatible', 'compatible_retained', 'compatible_opportunities'),
        ('cleared_rate_compatible', 'compatible_cleared', 'compatible_opportunities'),
        ('unresolved_rate_ahead', 'unresolved_ahead_updates', 'ahead_updates')]:
        row[name] = row[numerator] / row[denominator] if row[denominator] else None
    return row


def total(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return sum(values) if values else None


def recount(directory, metadata=None):
    directory = Path(directory)
    root = directory / 'attempt0'
    cfg = read(root / 'config.json')
    events = read(root / 'events.jsonl', True)
    workers = read(root / 'worker_records.jsonl', True)
    consumers = read(root / 'consumer.jsonl', True)
    sessions = read(root / 'sessions.json')
    starts = [e['t0_perf'] for e in events if e['kind'] == 'run-start']
    need(len(starts) == 1, 'one run-start required')
    start = starts[0]
    fine = cfg['fine_seconds'] * cfg['sample_rate']
    meta = dict(phase='bounded_development', adapter=cfg.get('proposal_runtime', {}).get('model_adapter', 'unspecified'),
                rho=cfg['rho'], arrival=cfg['arrival'], cohort='OLD_DEVELOPMENT', repeat=None,
                arm=basename(directory), cell_id=basename(directory), paired_block=None,
                actual_authority_runtime_sha256=sha(cfg.get('authority_runtime', {})),
                actual_proposal_runtime_sha256=sha(cfg.get('proposal_runtime', {})))
    meta.update(metadata or {})
    records = {r['job']['job_id']: r for r in workers}
    need(len(records) == len(workers), 'duplicate complete result')
    lookup = defaultdict(list)
    for event in events:
        if event['kind'] in ('display', 'canonical-display', 'view-mode'):
            lookup[event['session_id'], event['kind'], event['displayed']].append(event)
    by_session = defaultdict(list)
    for index, row in enumerate(consumers):
        by_session[row['session_id']].append(dict(row, input_row=index))
    provenance = {}
    for sid, rows in by_session.items():
        rows.sort(key=lambda r: (r['observed_perf'], r['input_row']))
        previous = None
        visible_job = None
        for row in rows:
            matches = lookup[sid, row['source_kind'], row['server_time']]
            event = matches[0] if len(matches) == 1 else None
            if (row['source_kind'] == 'display' and event and
                    event.get('text') == row['visible_text'] and
                    event.get('audio_end_sample') == row['valid_visible_frontier']):
                visible_job = event['job_id']
            elif previous is None or (previous['valid_visible_frontier'], previous['visible_text']) != \
                    (row['valid_visible_frontier'], row['visible_text']):
                visible_job = None
            provenance[row['input_row']] = visible_job
            previous = row
    consumer_lookup = defaultdict(list)
    for rows in by_session.values():
        for row in rows:
            consumer_lookup[row['session_id'], row['source_kind'], row['server_time']].append(row)
    commits = [e for e in events if e['kind'] == 'commit']
    history = defaultdict(list)
    selected_valid = {}
    for e in commits:
        selected = records.get(e['job_id'])
        valid = bool(selected and selected['job']['role'] == 'authority' and
            selected['job']['session_id'] == e['session_id'] and
            selected['job']['audio_end_sample'] == e['audio_end_sample'] and
            selected['result'].get('token_ids') == e['segment_tokens'] and
            selected['result'].get('state_tokens') == e['next_prompt_tokens'] and 'text' in selected['result'])
        selected_valid[e['session_id'], e['version']] = valid
        history[e['session_id']].append(dict(version=e['version'], start=e['audio_start_sample'],
            F=e['audio_end_sample'], Z=e['segment_tokens'], P=e['next_prompt_tokens'],
            text=selected['result']['text'] if valid else None))
    publications = defaultdict(list)
    for e in events:
        if e['kind'] == 'canonical-display':
            publications[e['session_id'], e['version']].append(e)
    displays = [e for e in events if e['kind'] == 'display']
    enqueues = [e for e in events if e['kind'] == 'enqueue' and e['role'] == 'proposal']
    cancelled_path = root / 'worker_cancelled_records.jsonl'
    cancelled = {r['job']['job_id']:r for r in read(cancelled_path, True)} if cancelled_path.exists() else {}
    updates = []
    for e in commits:
        sid = e['session_id']
        F = e['audio_end_sample']
        installed = start + e['installed']
        selected = records.get(e['job_id'])
        root_valid = selected_valid[sid, e['version']]
        rows = by_session.get(sid, [])
        before_index = bisect_right([r['observed_perf'] for r in rows], installed) - 1
        before = rows[before_index] if before_index >= 0 else None
        output = dict(meta, clock_scope='owner_install', session_id=sid, version=e['version'], F=F, installed_perf=installed,
                      selected_P_sha256=sha(e['next_prompt_tokens']), selected_job_id=e['job_id'],
                      complete_selected_root_matched=root_valid,
                      previous_consumer_row=before.get('input_row') if before else None,
                      before_visible_F=before['valid_visible_frontier'] if before else None,
                      visible_job_id=provenance.get(before['input_row']) if before else None,
                      ahead=False, compatible=None, compatibility_reason='no_ahead_view', chain=[],
                      consumer_outcome='unmatched', consumer_match_reason=None,
                      boundary_view_changed=False, retention_flag=None,
                      ahead_observation_missing=before is None,
                      install_inflight_ahead_job_ids=[], install_complete_unpublished_ahead_job_ids=[])
        published = {d['job_id'] for d in displays if d['session_id'] == sid and
                     start + d['displayed'] <= installed}
        for job in enqueues:
            if job['session_id'] != sid or job['audio_end_sample'] <= F or job['enqueue_perf'] > installed:
                continue
            jid = job['job_id']
            result = records.get(jid, {}).get('result', {})
            terminal = result.get('_row_receipt', {}).get('terminal_perf', result.get('row_terminal_perf', result.get('completed_perf')))
            if jid in cancelled:
                terminal = cancelled[jid]['cancellation']['message']['acknowledged_perf']
            if terminal is None or terminal > installed:
                output['install_inflight_ahead_job_ids'].append(jid)
            elif jid in records and jid not in published:
                output['install_complete_unpublished_ahead_job_ids'].append(jid)
        if before is None:
            output['compatibility_reason'] = 'no_consumer_view_observed_before_install'
        elif before['valid_visible_frontier'] > F:
            output['ahead'] = True
            jid = output['visible_job_id']
            if not root_valid:
                output['compatibility_reason'] = 'selected_root_missing_or_mismatched_complete_authority_result'
            elif jid is None:
                output['compatibility_reason'] = 'ahead_view_has_no_exact_private_publication_provenance'
            else:
                output['compatible'], output['compatibility_reason'], output['chain'] = \
                    complete_chain(jid, F, e['next_prompt_tokens'], records, published, fine)
                if jid in records and any(records[jid]['job'].get(k) != selected['job'].get(k)
                                           for k in ('session_id','source_id','contract_epoch','contract_digest')):
                    output.update(compatible=False, compatibility_reason='private_and_selected_root_identity_differ')
        pubs = publications[sid, e['version']]
        after = None
        if len(pubs) == 1:
            pub = pubs[0]
            matches = consumer_lookup[sid, 'canonical-display', pub['displayed']]
            if len(matches) == 1:
                after = matches[0]
                if (after['canonical_version'] != e['version'] or after['certified_frontier'] != F or
                    pub['job_id'] != e['job_id'] or (root_valid and (
                    after.get('certified_text', selected['result']['text']) != selected['result']['text'] or
                    pub.get('text', selected['result']['text']) != selected['result']['text']))):
                    after = None
                    output['consumer_match_reason'] = 'consumer_selected_version_or_frontier_mismatch'
            else:
                output['consumer_match_reason'] = 'missing_or_duplicate_exact_consumer_update'
        else:
            output['consumer_match_reason'] = 'missing_or_duplicate_canonical_publication'
        output['consumer_matched'] = after is not None
        if after:
            output['after_visible_F'] = after['valid_visible_frontier']
            output['retention_flag'] = after.get('compatible_provisional_retained')
            output['observed_perf'] = after['observed_perf']
            if before and after['valid_visible_frontier'] == before['valid_visible_frontier'] and after['visible_text'] == before['visible_text']:
                output['consumer_outcome'] = 'retained_same_view' if output['ahead'] else 'no_ahead_view'
            elif after['valid_visible_frontier'] <= F:
                output['consumer_outcome'] = 'cleared_to_canonical'
            else:
                output['consumer_outcome'] = 'changed_ahead_view'
            after_index = next(i for i,r in enumerate(rows) if r['input_row'] == after['input_row'])
            boundary_before = rows[after_index - 1] if after_index else None
            output['boundary_view_changed'] = bool(before and boundary_before and
                (boundary_before['valid_visible_frontier'], boundary_before['visible_text']) !=
                (before['valid_visible_frontier'], before['visible_text']))
        updates.append(output)
        # A frame already published before owner installation can reach the
        # Consumer afterwards but before its FIFO Canonical frame. This is a
        # real display retention opportunity even when installation-time is zero.
        applied = dict(output, clock_scope='consumer_apply', ahead=False, compatible=None,
                       compatibility_reason='missing_exact_consumer_update', chain=[],
                       previous_consumer_row=None, before_visible_F=None, visible_job_id=None,
                       ahead_observation_missing=True, install_inflight_ahead_job_ids=[],
                       install_complete_unpublished_ahead_job_ids=[])
        if after:
            applied.update(previous_consumer_row=boundary_before['input_row'] if boundary_before else None,
                before_visible_F=boundary_before['valid_visible_frontier'] if boundary_before else None,
                visible_job_id=provenance.get(boundary_before['input_row']) if boundary_before else None,
                ahead_observation_missing=boundary_before is None,
                compatibility_reason='no_ahead_view' if boundary_before else 'no_prior_consumer_view')
            if boundary_before and boundary_before['valid_visible_frontier'] > F:
                applied['ahead'] = True
                available = {d['job_id'] for d in displays if d['session_id'] == sid and d['displayed'] <= pub['displayed']}
                jid = applied['visible_job_id']
                if not root_valid:
                    applied['compatibility_reason'] = 'selected_root_missing_or_mismatched_complete_authority_result'
                elif jid is None:
                    applied['compatibility_reason'] = 'ahead_view_has_no_exact_private_publication_provenance'
                else:
                    applied['compatible'], applied['compatibility_reason'], applied['chain'] = \
                        complete_chain(jid, F, e['next_prompt_tokens'], records, available, fine)
                    if jid in records and any(records[jid]['job'].get(k) != selected['job'].get(k)
                                               for k in ('session_id','source_id','contract_epoch','contract_digest')):
                        applied.update(compatible=False, compatibility_reason='private_and_selected_root_identity_differ')
            if boundary_before and (after['valid_visible_frontier'], after['visible_text']) == \
                    (boundary_before['valid_visible_frontier'], boundary_before['visible_text']):
                applied['consumer_outcome'] = 'retained_same_view' if applied['ahead'] else 'no_ahead_view'
            elif after['valid_visible_frontier'] <= F:
                applied['consumer_outcome'] = 'cleared_to_canonical'
            else:
                applied['consumer_outcome'] = 'changed_ahead_view'
        updates.append(applied)
    source_rows = []
    for session, clock_scope in ((s, scope) for s in sessions for scope in ('owner_install', 'consumer_apply')):
        sid = session['session_id']
        rows = [r for r in updates if r['session_id'] == sid and r['clock_scope'] == clock_scope]
        counts = Counter()
        reasons = Counter(r['compatibility_reason'] for r in rows)
        for row in rows:
            counts['canonical_updates'] += 1
            counts['matched_consumer_updates'] += row['consumer_matched']
            counts['ahead_updates'] += row['ahead']
            counts['ahead_to_consumer_boundary_changed'] += row['ahead'] and row['boundary_view_changed']
            counts['ahead_observation_missing'] += row['ahead_observation_missing']
            counts['install_inflight_ahead_jobs'] += len(row['install_inflight_ahead_job_ids'])
            counts['install_complete_unpublished_ahead_jobs'] += len(row['install_complete_unpublished_ahead_job_ids'])
            if not row['ahead']:
                continue
            compatible = row['compatible']
            counts['compatible_opportunities' if compatible is True else
                   'incompatible_ahead_updates' if compatible is False else 'unresolved_ahead_updates'] += 1
            outcome = row['consumer_outcome']
            if compatible is True:
                key = {'retained_same_view': 'compatible_retained', 'cleared_to_canonical': 'compatible_cleared',
                       'changed_ahead_view': 'compatible_changed', 'unmatched': 'compatible_unmatched'}[outcome]
                counts[key] += 1
            elif compatible is False:
                counts['incompatible_cleared'] += outcome == 'cleared_to_canonical'
                counts['incompatible_still_visible'] += outcome == 'retained_same_view'
        count_values = {k:counts[k] for k in COUNTS}
        if clock_scope != 'owner_install':
            for key in ('install_inflight_ahead_jobs', 'install_complete_unpublished_ahead_jobs'):
                count_values[key] = None
        source_rows.append(rates(dict(meta, clock_scope=clock_scope, session_id=sid, source_id=session['source_id'],
            canonical_history_sha256=sha(sorted(history[sid], key=lambda r:r['version'])) if
                history[sid] and all(selected_valid[sid,r['version']] for r in history[sid]) else None,
            **count_values, compatibility_reasons=dict(reasons))))
    return updates, source_rows


def table(path, rows):
    path.with_suffix('.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n', encoding='utf8')
    if rows:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with path.with_suffix('.csv').open('w', newline='', encoding='utf8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k:json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k,v in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--results-root', type=Path)
    parser.add_argument('--cell-root', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cells = [(p, None) for p in args.cell_root]
    if args.plan:
        plan = read(args.plan)
        for raw in plan['cells']:
            argv = raw.get('argv', [])
            target = argv[argv.index('--out') + 1] if '--out' in argv else raw.get('output', raw.get('out'))
            cells.append((args.results_root / basename(target) if args.results_root else Path(target),
                          {k:raw.get(k) for k in (*DIMENSIONS, 'cell_id', 'paired_block')}))
    need(cells, 'provide --plan or at least one --cell-root')
    updates, sources, coverage = [], [], []
    for directory, meta in cells:
        item = dict(meta or {}, cell_root=str(directory.resolve()))
        try:
            u, s = recount(directory, meta)
            updates += u
            sources += s
            item.update(status='RECOUNTED_OFFLINE', canonical_updates=len(u)//2, source_clock_rows=len(s))
        except (OSError, ValueError, KeyError, TypeError) as error:
            item.update(status='UNMATCHED_INPUTS', reason=f'{type(error).__name__}: {error}')
        coverage.append(item)
    grouped = defaultdict(list)
    for row in sources:
        grouped[tuple(row.get(k) for k in RATE_DIMENSIONS)].append(row)
    groups = [rates(dict(zip(RATE_DIMENSIONS, key), source_rows=len(rows),
                   **{k:total(rows, k) for k in COUNTS})) for key,rows in grouped.items()]
    # Membership only, not an effect estimate. Source, run and full selected
    # history must match; arms with no actual work gain no invented opportunity.
    histories = defaultdict(list)
    for row in sources:
        if row.get('paired_block') and row['clock_scope'] == 'owner_install' and row['canonical_history_sha256']:
            histories[row['paired_block'], row['source_id'], row['canonical_history_sha256'],
                      row['actual_authority_runtime_sha256']].append(row['cell_id'])
    history_groups = [dict(paired_block=k[0], source_id=k[1], canonical_history_sha256=k[2],
                           actual_authority_runtime_sha256=k[3],
                           cell_ids=sorted(values), n_cells=len(values)) for k,values in histories.items()]
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in [('UPDATES', updates), ('SOURCE_OPPORTUNITIES', sources), ('STRATIFIED_RATES', groups),
                       ('COVERAGE', coverage), ('SAME_CANONICAL_HISTORY_GROUPS', history_groups)]:
        table(args.output / name, rows)
    record = dict(analysis_id='REVTRACE-WITNESSED-INTERACTION-OPPORTUNITIES-v1',
        evidence_tier='offline recount of actual recorded views and complete result ancestry; not a new serving experiment',
        analysis_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        command=sys.argv, environment=dict(python=platform.python_version(), platform=platform.platform()),
        inputs=INPUTS, cells_requested=len(cells), cells_recounted=sum(r['status']=='RECOUNTED_OFFLINE' for r in coverage),
        by_clock={scope:{k:total([r for r in sources if r['clock_scope']==scope], k) for k in COUNTS}
                  for scope in ('owner_install', 'consumer_apply')},
        gate='OFFLINE_RECOUNT_COMPLETE' if all(r['status']=='RECOUNTED_OFFLINE' for r in coverage) else 'OFFLINE_RECOUNT_INCOMPLETE_INPUTS',
        limits=['No causal effect is inferred from pooled counts or differing Canonical histories.',
                'Unresolved ancestry and unmatched Consumer observations remain explicit.',
                'Compatibility is exact selected-state agreement, not task correctness or a deterministic guarantee.',
                'Owner-install and Consumer-apply observations have separate denominators and counts.',
                'In-flight/complete-unpublished job counts are incidence counts at installs, not certified computational retention opportunities.',
                'Existing independent safety, provenance, deadline, quality and cost gates remain separate.'])
    (args.output / 'ANALYSIS_RECORD.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('inputs', 'limits', 'command', 'environment')}, allow_nan=False))


if __name__ == '__main__':
    main()
