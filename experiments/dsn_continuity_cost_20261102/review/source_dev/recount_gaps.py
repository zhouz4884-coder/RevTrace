"""Independent original-clock gap audit; write-only preparation, not serving.

Does not import history_analysis or its selector/merge/integration functions.
Uses only the byte-pinned original Consumer and original core apply predicate.
The entire source and config must be independently frozen before execution.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import subprocess
import sys


class AuditError(RuntimeError):
    pass


def must(value, message):
    if not value:
        raise AuditError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    data = Path(path).read_bytes()
    output, tail = [], 0
    lines = data.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            output.append(json.loads(line))
        except (ValueError, UnicodeDecodeError):
            must(i == len(lines) - 1 and not line.endswith(b'\n'),
                 'corrupt complete raw JSONL row: ' + str(path))
            tail = len(line)
    return output, tail


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def verify_tree(root, manifest_path, expected_commit):
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    manifest = read(manifest_path)
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    must(head == expected_commit == manifest.get('code_commit', manifest.get('source_commit')),
         'source HEAD / requested commit / manifest mismatch')
    must(not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain',
                                    '--untracked-files=all'], text=True).strip(), 'dirty source checkout')
    expected = {item['path']: item for item in manifest['files']}
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True).splitlines()
    must(set(expected) == set(tracked), 'incomplete tracked source manifest')
    for name, item in expected.items():
        path = root / name
        must(path.is_file() and not path.is_symlink(), 'missing/symlink source: ' + name)
        must(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
             'source byte mismatch: ' + name)
    return dict(commit=head, manifest_sha256=digest(manifest_path), files=len(expected))


def load_reference(folder):
    modules = []
    for filename, name in [('reference_view.py', 'gap_original_view'),
                           ('reference_kernel.py', 'gap_original_kernel')]:
        spec = importlib.util.spec_from_file_location(name, Path(folder) / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return tuple(modules)


def union_length(intervals):
    cursor, total = None, 0.0
    for lo, hi in sorted(intervals):
        must(hi >= lo, 'reversed interval')
        if cursor is None or lo > cursor:
            total += hi - lo
        elif hi > cursor:
            total += hi - cursor
        cursor = hi if cursor is None else max(cursor, hi)
    return total


def classification(job, ever_shown_jobs, ever_audio_frontier, selected_frontier):
    if job in ever_shown_jobs:
        return 'restore_originally_visible_same_node'
    if ever_audio_frontier >= selected_frontier:
        return 'new_legal_node_for_previously_visible_audio'
    return 'registered_old_publication_newly_visible_audio'


def close_number(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=2e-8)


def rank(node):
    return node['audio_end_sample'], node.get('display_revision', 0), node['job_id']


def original_core_accepts(core, consumer_row, state, node, jobs, owner, contract):
    """Run original apply guard on a restricted real-root/real-result snapshot.

    This checks the per-cut predicate, not a replay of all original dispatch,
    durable receipt ownership, publication ticket or physical transitions.
    """
    sid, version = consumer_row['session_id'], consumer_row['canonical_version']
    fact = dict(v=version, F=consumer_row['certified_frontier'], P=state['Psha'],
                Z=consumer_row.get('certified_Z_sha256'), textsha=consumer_row.get('certified_text_sha256'),
                txn=consumer_row.get('certified_transaction'))
    kernel = core.State(contract, consumer_row['canonical_epoch'], owner)
    kernel.C = {sid: fact}
    kernel.D = {sid: {version: fact} if version else {}}
    kernel.J = jobs
    kernel.V = {sid: dict(v=0, F=0, visible=0, revision=0)}
    key = (sid, 'independent-query')
    kernel.publications = {key: dict(_sid=sid, canonical=True, fact=fact)}
    query = dict(v=version, F=fact['F'], P=fact['P'], visible=node['audio_end_sample'],
                 private=node['job_id'], text=node['text'], revision=1)
    try:
        pending, effects = core.step(kernel, 'apply-request', dict(
            sid=sid, view=query, key=key, operation='independent-gap-query'))
        must(effects == ['apply-view'], 'unexpected original core apply effect')
        core.step(pending, 'view-applied', dict(operation='independent-gap-query'))
        return True, None
    except core.Denied as exc:
        return False, str(exc)


def permission(node, state, contract, mode, floor, revoked, generation_floor):
    return (mode not in ('CERTIFIED-ONLY', 'RECOVERY')
            and node['audio_end_sample'] > state['F']
            and node.get('contract_epoch') == state.get('epoch')
            and node.get('contract_digest') == contract
            and node.get('display_revision', 0) > floor
            and node['job_id'] not in revoked
            and node.get('branch_generation', 0) >= generation_floor)


def validate_publication(node, raw, view_module, receive_cut):
    job, result = raw['job'], raw['result']
    must(float(result['received_perf']) <= receive_cut, 'publication precedes actual host receipt')
    for key in ('job_id', 'session_id', 'chunk_id', 'end_window', 'audio_end_sample',
                'branch_generation', 'contract_epoch', 'contract_digest'):
        must(node.get(key) == job.get(key), 'publication/job identity changed: ' + key)
    must(node['input_projection_sha256'] == view_module.digest_tokens(job['prompt_tokens']),
         'full frozen input digest mismatch')
    must(node['output_projection_sha256'] == view_module.digest_tokens(result['state_tokens']),
         'complete result state digest mismatch')
    must(node['text'] == result['text'] and node['text_sha256'] == view_module.text_sha(result['text']),
         'complete result text mismatch')
    # Preserve and fingerprint actual complete Z; no new token-to-text rendering.
    must(isinstance(result['token_ids'], list) and bool(result['token_ids']), 'missing complete original Z')
    if 'display_tokens' in node:
        must(node['display_tokens'] == result['token_ids'], 'published Z differs from original complete Z')
    return dict(job_id=job['job_id'], full_Z_sha256=view_module.digest_tokens(result['token_ids']),
                input_P_sha256=node['input_projection_sha256'], output_P_sha256=node['output_projection_sha256'],
                text_sha256=node['text_sha256'], received_perf=result['received_perf'])


def prove_selected_state(view, original, state, workers, now, floor, revoked, generations, owner, core, vm):
    generation_floor = max([0] + [gen for when, gen in generations if when <= now])
    proof_jobs = {}
    for jid, raw in workers.items():
        job, result = raw['job'], raw.get('result', {})
        if (job.get('role') != 'proposal' or job['session_id'] != original['session_id']
                or 'received_perf' not in result or float(result['received_perf']) > now):
            continue
        proof_jobs[jid] = dict(id=jid, sid=job['session_id'], role='proposal',
                              rootF=job['chunk_id'] * view.fine, end=job['audio_end_sample'],
                              inputP=vm.digest_tokens(job['prompt_tokens']),
                              result=dict(P=vm.digest_tokens(result['state_tokens']),
                                          Z=vm.digest_tokens(result['token_ids']), textsha=vm.text_sha(result['text'])))
    accepted, rejected = [], Counter()
    for node in state['nodes'].values():
        if not permission(node, state, view.contract, view.modes.get(original['session_id'], 'NORMAL'),
                          floor, revoked, generation_floor):
            continue
        if not view._compatible(state, node, state['Psha']):
            rejected['original_native_path'] += 1
            continue
        ok, reason = original_core_accepts(core, original, state, node, proof_jobs, owner, view.contract)
        if ok:
            accepted.append(node)
        else:
            rejected[reason] += 1
    selected = max(accepted, key=rank, default=None)
    actual_legal = original['valid_visible_frontier'] == state['F']
    tip = state.get('tentative')
    if not actual_legal and tip:
        actual_legal = any(tip['job_id'] == candidate['job_id'] for candidate in accepted)
    return selected, actual_legal, dict(rejected)


def reproduce_atoms(entry, paths, vm, core):
    events, etail = rows(paths['events.jsonl'])
    consumer_name = 'consumer.jsonl' if 'consumer.jsonl' in paths else 'consumer-live.jsonl'
    actual, ctail = rows(paths[consumer_name])
    raw_workers, wtail = rows(paths['worker_records.jsonl'])
    cfg = read(paths['config.json'])
    must(actual, 'no original Consumer observations')
    rate, fine = int(cfg.get('sample_rate', 16000)), round(cfg.get('fine_seconds', 2) * cfg.get('sample_rate', 16000))
    starts = [event for event in events if event['kind'] == 'run-start']
    must(len(starts) == 1, 'not a single original Owner stream')
    owner, end_global = float(starts[0]['t0_perf']), float(actual[-1]['observed_perf'])
    must(all(actual[i]['observed_perf'] <= actual[i+1]['observed_perf'] for i in range(len(actual)-1)),
         'original Consumer clock regressed')
    workers = {raw['job']['job_id']: raw for raw in raw_workers}
    must(len(workers) == len(raw_workers), 'duplicate physical worker-result UID')
    lookup, next_rows, last = defaultdict(deque), {}, {}
    for i, row in enumerate(actual):
        lookup[(row['source_kind'], row['session_id'], row['server_time'])].append((i, row))
    for i in range(len(actual)-1, -1, -1):
        sid = actual[i]['session_id']
        next_rows[i], last[sid] = last.get(sid), i
    retire = defaultdict(list)
    for event in events:
        if event['kind'] == 'private-generation-retired':
            retire[event['session_id']].append((owner + event['time'], event['generation']))
    view = vm.EnvelopeView(policy=entry.get('reference_policy') or 'two_lane',
                           strict_bound=True, fine_samples=fine)
    floors, revoked, shown, ever = defaultdict(int), defaultdict(set), defaultdict(set), defaultdict(int)
    atoms, cut_winners, proofs, baseline_missing = [], [], {}, Counter()
    checked = 0
    for event in events:
        if checked == len(actual):
            break
        key = (event['kind'], event.get('session_id'), event.get('displayed', event.get('time')))
        queue = lookup.get(key)
        replayed = view.consume(event, float(queue[0][1]['observed_perf']) if queue else None)
        if replayed is None:
            continue
        must(queue, 'reference produced an unrecorded original application')
        index, original = queue.popleft()
        must(index == checked, 'original FIFO event order mismatch')
        checked += 1
        for field in ('canonical_version', 'certified_frontier', 'valid_visible_frontier', 'visible_text',
                      'contract_digest', 'owner_incarnation', 'canonical_epoch', 'certified_P_sha256',
                      'certified_Z_sha256', 'certified_text_sha256', 'certified_transaction', 'envelope_mode'):
            if field in original:
                must(replayed.get(field) == original[field], 'baseline identity/view mismatch: ' + field)
            else:
                baseline_missing[field] += 1
        sid = original['session_id']
        state = dict(view.states[sid])  # query state; NEVER mutate the reference.
        if state['version'] == 0:
            state['Psha'] = vm.digest_tokens(())
        if event['kind'] == 'view-mode':
            revoked[sid].update(event.get('revoked_job_ids', ()))
            if event['mode'] in ('CERTIFIED-ONLY', 'RECOVERY'):
                floors[sid] = max(floors[sid], event['display_revision'])
        if state.get('tentative') and original['valid_visible_frontier'] > state['F']:
            shown[sid].add(state['tentative']['job_id'])
        ever[sid] = max(ever[sid], original['valid_visible_frontier'])
        for jid, node in state['nodes'].items():
            must(jid in workers, 'Consumer-registered result missing its full original worker row')
            proofs[jid] = validate_publication(node, workers[jid], vm, float(original['consumer_received_perf']))
        start = float(original['observed_perf'])
        next_index = next_rows[index]
        end = float(actual[next_index]['observed_perf']) if next_index is not None else end_global
        # Independent sorted endpoint sweep; not the primary analyzer's merger.
        boundaries = {start, end}
        boundaries.update(t for t, _ in retire[sid] if start < t < end)
        boundaries.update(float(raw['result']['received_perf']) for raw in raw_workers
                          if raw['job'].get('role') == 'proposal' and raw['job']['session_id'] == sid
                          and 'received_perf' in raw.get('result', {})
                          and start < float(raw['result']['received_perf']) < end)
        selected, actual_legal, _ = prove_selected_state(view, original, state, workers, start,
            floors[sid], revoked[sid], retire[sid], owner, core, vm)
        cut_winners.append(dict(session_id=sid, time=start, actual=original['valid_visible_frontier'],
            selected=selected['audio_end_sample'] if selected else state['F'],
            certified=state['F'], legal=actual_legal,
            selected_text=selected['text'] if selected else state['text'], actual_text=original['visible_text']))
        points = sorted(boundaries)
        for a, b in zip(points, points[1:]):
            if b <= a:
                continue
            selected, actual_legal, rejects = prove_selected_state(view, original, state, workers, a,
                floors[sid], revoked[sid], retire[sid], owner, core, vm)
            if not actual_legal or selected is None or selected['audio_end_sample'] <= original['valid_visible_frontier']:
                continue
            jid, f0, f1 = selected['job_id'], original['valid_visible_frontier'], selected['audio_end_sample']
            atoms.append(dict(session_id=sid, source_id=workers[jid]['job']['source_id'],
                start_perf=a, end_perf=b, selected_job=jid, actual_frontier=f0, selected_frontier=f1,
                canonical_version=state['version'], canonical_frontier=state['F'],
                category=classification(jid, shown[sid], ever[sid], f1),
                area_audio_seconds_x_wall_seconds=(f1-f0)/rate*(b-a), duration_seconds=b-a,
                right_censored=(next_index is None and b == end_global),
                global_prefix_extension_after_session_last_apply=next_index is None,
                original_consumer_row=index, original_trigger=event['kind'], original_apply_perf=start,
                selected_complete_result=proofs[jid], core_rejected_candidate_reasons=rejects))
    must(checked == len(actual) and not any(lookup.values()), 'unreplayed original Consumer row')
    return dict(atoms=atoms, cuts=cut_winners, sample_rate=rate,
                original_rows=len(actual), baseline_missing=dict(baseline_missing),
                tails=dict(events=etail, consumer=ctail, worker=wtail)), actual


def same_coverage(ours, reported):
    """Verify complete positive support by interval partition, not only a sum."""
    sids = {row['session_id'] for row in ours + reported}
    for sid in sids:
        left = [row for row in ours if row['session_id'] == sid]
        right = [row for row in reported if row['session_id'] == sid]
        endpoints = sorted({value for row in left + right for value in (row['start_perf'], row['end_perf'])})
        for a, b in zip(endpoints, endpoints[1:]):
            if b <= a:
                continue
            midpoint = a + (b-a)/2
            arows = [row for row in left if row['start_perf'] <= midpoint < row['end_perf']]
            brows = [row for row in right if row['start_perf'] <= midpoint < row['end_perf']]
            must(len(arows) <= 1 and len(brows) <= 1, 'overlapping positive intervals double count time')
            must(bool(arows) == bool(brows), 'positive time support differs')
            if arows:
                for field in ('selected_job', 'actual_frontier', 'selected_frontier', 'category', 'canonical_version'):
                    must(arows[0][field] == brows[0][field], 'interval identity/classification differs: ' + field)
        for interval in right:
            is_censored = any(atom.get('right_censored', False)
                              and close_number(atom['end_perf'], interval['end_perf'])
                              and atom['start_perf'] < interval['end_perf']
                              and interval['start_perf'] < atom['end_perf'] for atom in left)
            must(bool(interval.get('right_censored', False)) == is_censored,
                 'reported interval right-censoring differs')


def totals(atoms, rate):
    values, audio, times = Counter(), defaultdict(list), defaultdict(list)
    for atom in atoms:
        a, b = atom['start_perf'], atom['end_perf']
        values['joint_gap_area_audio_seconds_x_wall_seconds'] += (atom['selected_frontier']-atom['actual_frontier'])/rate*(b-a)
        values['joint_gap_session_wall_seconds'] += b-a
        suffix = ('global_prefix_extension' if atom['global_prefix_extension_after_session_last_apply']
                  else 'within_session_observation')
        values['joint_gap_area_' + suffix] += atom['area_audio_seconds_x_wall_seconds']
        values['joint_gap_wall_' + suffix] += b-a
        audio[atom['session_id']].append((atom['actual_frontier'], atom['selected_frontier']))
        times[atom['session_id']].append((a, b))
    values['distinct_deficient_audio_seconds'] = sum(union_length(v)/rate for v in audio.values())
    values['union_deficit_session_wall_seconds'] = sum(union_length(v) for v in times.values())
    return dict(values)


def deadline_totals(cfg, sessions, owner, observed, rate, fine):
    if isinstance(sessions, dict):
        sessions = sessions.get('sessions', list(sessions.values()))
    origin = float(cfg.get('episode_origin_perf', owner))
    result, by_sid = Counter(), defaultdict(list)
    for cut in observed:
        by_sid[cut['session_id']].append(cut)
    for session in sessions:
        total = round(session['duration'] * rate)
        for start in range(0, total, fine):
            end = min(total, start + fine)
            ready, weight = origin + session['offset'] + end/rate, (end-start)/rate
            timeline = by_sid[session['session_id']]
            display = min([cut['time'] for cut in timeline if cut['actual'] >= end], default=math.inf)
            certified = min([cut['time'] for cut in timeline if cut['certified'] >= end], default=math.inf)
            selected = min([cut['time'] for cut in timeline if cut['legal'] and cut['selected'] >= end], default=math.inf)
            result['offered_audio_seconds'] += weight
            result['offered_intervals'] += 1
            result['partial_EOS_intervals'] += end-start < fine
            if display <= ready+2 and certified <= ready+8:
                result['actual_joint_D2_C8_audio_seconds'] += weight
            if selected <= ready+2 and certified <= ready+8:
                result['registered_zero_apply_delay_joint_D2_C8_audio_seconds'] += weight
            if display > ready+2 >= selected and certified <= ready+8:
                result['new_first_D2_C8_audio_seconds'] += weight
                result['new_first_D2_C8_partial_EOS_audio_seconds'] += weight if end-start < fine else 0
    return dict(result)


def first_deadlines(paths, observed, rate, fine):
    cfg, sessions = read(paths['config.json']), read(paths['sessions.json'])
    owner = next(event['t0_perf'] for event in rows(paths['events.jsonl'])[0] if event['kind'] == 'run-start')
    return deadline_totals(cfg, sessions, owner, observed, rate, fine)


def raw_inputs(entry, remap):
    found, evidence = {}, []
    for item in entry['trace_identity']:
        name, original = Path(item['path']).name, item['path']
        if remap:
            must(original.startswith(remap[0]), 'raw remap misses frozen member')
            original = remap[1] + original[len(remap[0]):]
        path = Path(original)
        must(name not in found and path.is_file(), 'missing/ambiguous frozen member: ' + name)
        must(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'raw hash/size mismatch')
        found[name] = path
        evidence.append(dict(path=str(path), bytes=path.stat().st_size, sha256=item['sha256']))
    return found, evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--h-output', type=Path, required=True)
    parser.add_argument('--bank-manifest', type=Path, required=True)
    parser.add_argument('--reference-source', type=Path, required=True)
    parser.add_argument('--reference-manifest', type=Path, required=True)
    parser.add_argument('--reference-commit', required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--selection', choices=('positive3', 'reported-gaps'), default='positive3')
    parser.add_argument('--raw-remap', nargs=2)
    args = parser.parse_args()
    identity = verify_tree(Path(__file__).resolve().parent, args.source_manifest, args.source_commit)
    reference = verify_tree(args.reference_source, args.reference_manifest, args.reference_commit)
    must(not args.out.exists(), 'refusing to overwrite an earlier audit result')
    args.out.mkdir(parents=True)
    record = dict(experiment_id='REVTRACE-INDEPENDENT-H-GAP-RECOUNT-20261102', **identity,
                  reference=reference, h_output=str(args.h_output), selection=args.selection,
                  bank_manifest_sha256=digest(args.bank_manifest), new_model_calls=0,
                  scope='fixed original-clock offline opportunity audit; no online service claim')
    write(args.out/'RUN_RECORD.json', record)
    write(args.out/'ENVIRONMENT.json', dict(python=sys.version, executable=sys.executable, platform=platform.platform()))
    vm, core = load_reference(args.reference_source)
    primary, bank = read(args.h_output/'SUMMARY.json'), read(args.bank_manifest)
    must(primary['source_commit'] == args.reference_commit, 'H results/reference source identity differs')
    entries = {entry['attempt']: entry for entry in bank['attempts']}
    reports = [run for run in primary['runs'] if run['status'] == 'PASS_ORIGINAL_CONSUMER_CLOCK_OFFLINE_OPPORTUNITY']
    if args.selection == 'positive3':
        reports = [run for run in reports if entries[run['attempt']]['original_point_opportunities'] > 0]
        must(len(reports) == 3, 'frozen historical positive3 membership changed')
    else:
        reports = [run for run in reports if run.get('gap_segments', 0) > 0]
    audited = []
    for report in reports:
        entry = entries[report['attempt']]
        tag = f'{entry["bank"]}-{entry["ordinal"]:03d}'
        primary_path = args.h_output/tag
        reported_gaps = read(primary_path/'GAPS.json')
        output = args.out/tag
        output.mkdir()
        paths, before = raw_inputs(entry, args.raw_remap)
        rebuilt, actual = reproduce_atoms(entry, paths, vm, core)
        same_coverage(rebuilt['atoms'], reported_gaps)
        recounted = totals(rebuilt['atoms'], rebuilt['sample_rate'])
        for name in ('joint_gap_area_audio_seconds_x_wall_seconds', 'joint_gap_session_wall_seconds',
                     'joint_gap_area_within_session_observation', 'joint_gap_wall_within_session_observation',
                     'joint_gap_area_global_prefix_extension', 'joint_gap_wall_global_prefix_extension'):
            must(close_number(recounted.get(name, 0), report['metrics'].get(name, 0)), 'metric differs: ' + name)
        must(close_number(recounted.get('distinct_deficient_audio_seconds', 0),
                          report.get('distinct_deficient_audio_seconds', 0)), 'audio interval union differs')
        deadline = first_deadlines(paths, rebuilt['cuts'], rebuilt['sample_rate'],
                                   round(read(paths['config.json']).get('fine_seconds', 2)*rebuilt['sample_rate']))
        for name in set(deadline) | set(report['first_deadline_analysis']):
            must(close_number(deadline.get(name, 0), report['first_deadline_analysis'].get(name, 0)),
                 'first-delivery/EOS metric differs: ' + name)
        _, after = raw_inputs(entry, args.raw_remap)
        must(before == after, 'original raw changed during independent audit')
        counts = Counter(atom['category'] for atom in rebuilt['atoms'])
        summary = dict(status='PASS_INDEPENDENT_GAP_INTERVAL_UID_RIGHTS_AND_UNION_RECOUNT',
            attempt=report['attempt'], primary_gap_segments=len(reported_gaps), atomic_pieces=len(rebuilt['atoms']),
            independent_metrics=recounted, original_deadlines=deadline, atomic_categories=dict(counts),
            baseline_rows=rebuilt['original_rows'], baseline_missing=rebuilt['baseline_missing'], tails=rebuilt['tails'],
            input_before_after_equal=True, original_inputs=before,
            original_clock_scope='Consumer observed_perf; global-prefix extensions separately flagged',
            selected_full_Z_retained_without_rerender=True,
            no_original_owner_or_GPU_refinement_claim=True, new_model_calls=0)
        write(output/'SUMMARY.json', summary)
        write(output/'INDEPENDENT_ATOMS.json', rebuilt['atoms'])
        audited.append(summary)
    write(args.out/'SUMMARY.json', dict(status='PASS', attempted=len(reports), audited=len(audited),
                                      runs=audited, **record))
    write(args.out/'GATE.json', dict(status='PASS_INDEPENDENT_H_GAP_RECOUNT', attempts=len(audited), new_model_calls=0))


if __name__ == '__main__':
    main()
