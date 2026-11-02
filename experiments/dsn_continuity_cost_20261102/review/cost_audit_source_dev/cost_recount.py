"""Independent CPU/NN cost recount. Prepared only; freeze before running.

Stdlib only: no primary summarize_spans, driver audit, model or CUDA imports.
Original task binding, CPU footprints and off/on system effects remain separate.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import traceback
from cost_forest import AuditError, need, forest, window_accounts, export_metadata_check, q

NN4F = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
OBSERVER = '3cf7cd10a3ba76958b4173aa20eb6116ac779a39'
DRIVER = 'b16481983674dec34e798342caf519e566a2b1cd'
OLD = 'bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
_OUT = None
_DONE = []


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def lines(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines() if line.strip()]


def put(path, obj):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def equal(a, b):
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-7)
    return a == b


def checked_fields(actual, declared, names, context):
    for name in names:
        need(name in actual and name in declared and equal(actual[name], declared[name]), context + ': ' + name)


def verify_source(manifest, expected):
    folder = Path(__file__).resolve().parent
    m = read(manifest)
    head = subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()
    need(head == expected == m.get('source_commit', m.get('code_commit')), 'independent source identity mismatch')
    need(not subprocess.check_output(['git', '-C', str(folder), 'status', '--porcelain', '--untracked-files=all'],
                                     text=True).strip(), 'independent source is dirty')
    tracked = set(subprocess.check_output(['git', '-C', str(folder), 'ls-files'], text=True).splitlines())
    entries = {r['path']: r for r in m['files']}
    need(tracked == set(entries), 'independent complete source manifest mismatch')
    for name, item in entries.items():
        p = folder/name
        need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(folder), 'source path escape')
        need(p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], 'source bytes mismatch: ' + name)
    return dict(source_commit=head, source_manifest_sha256=sha(manifest), source_files=len(entries))


def facts(path):
    """Independently parse RVN1, canonical JSON, checksum and prefix chain."""
    result, previous, sequence = [], '0'*64, 0
    with Path(path).open('rb') as f:
        while True:
            offset = f.tell()
            header = f.read(8)
            if not header:
                break
            need(len(header) == 8 and header[:4] == b'RVN1', 'torn/corrupt complete fact header')
            size = struct.unpack('>I', header[4:])[0]
            need(size <= 16*1024*1024, 'oversized fact')
            payload, checksum = f.read(size), f.read(32)
            need(len(payload) == size and len(checksum) == 32 and hashlib.sha256(payload).digest() == checksum,
                 'torn/corrupt fact payload')
            obj = json.loads(payload)
            need(canonical(obj) == payload, 'noncanonical fact encoding')
            need(obj['sequence'] == sequence+1 and obj['previous'] == previous, 'fact prefix ordering changed')
            sequence += 1
            previous = checksum.hex()
            result.append(dict(obj=obj, receipt=dict(sequence=sequence, record_sha256=previous,
                                                      offset=offset, end_offset=f.tell())))
    need(result and result[0]['obj']['kind'] == 'genesis', 'missing durable genesis')
    return result


def mapped_state(state):
    state = copy.deepcopy(state)
    marker = state['contract']['stage_execution']['source_commit']
    need(marker in (NN4F, OLD), 'unrecognized source marker in fixed reference')
    state['contract']['stage_execution']['source_commit'] = OLD
    return state


def edit_distance(a, b):
    prior = list(range(len(b)+1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1]+1, prior[j]+1, prior[j-1]+(left != right)))
        prior = current
    return prior[-1]


def task_audit(cfg, frames, consumer, reference):
    sources = {s['source_id']: s for s in cfg['settings']['sources']}
    roots = copy.deepcopy(frames[0]['obj']['body']['initials'])
    need(set(roots) == set(sources), 'genesis/source population differs')
    refs = {(r['source_id'], r['end']): r for r in reference}
    seen, semantic, unique = set(), [], set()
    canonical_count = 0
    for frame in frames[1:]:
        obj, receipt = frame['obj'], frame['receipt']
        need(obj['kind'] == 'canonical', 'unexpected noncanonical durable frame')
        b = obj['body']; sid, start, end, r, job = b['source_id'], b['parent_state'], b['next_state'], b['record'], b['job']
        need(b.get('kind') == 'original_full_canonical_transition', 'fact is not an original complete transition')
        need(sid in roots and roots[sid] == start, 'durable complete-parent chain mismatch')
        need(b['transition_id'] not in unique, 'duplicate selected fact identity')
        unique.add(b['transition_id'])
        need(job['source_id'] == sid and job['start'] == start and job['end'] == end['frontier']
             and job['dispatch_epoch'] == b['session_epoch'], 'durable original owned-call input changed')
        need(r['role'] == 'authority' and r['candidate_handoff'] is False
             and r['start_state'] == hashlib.sha256(canonical(start)).hexdigest()
             and r['end_state'] == hashlib.sha256(canonical(end)).hexdigest(), 'original C/U selected binding changed')
        need(end['frontier'] == min(sources[sid]['frames'], start['frontier']+8000), '500ms/partial-EOS cadence changed')
        key = sid, end['frontier']
        need(key in refs and key not in seen, 'missing/duplicate fixed-reference frontier')
        seen.add(key)
        ref = refs[key]
        need(mapped_state(start) == mapped_state(ref['original_full_start_cut'])
             and mapped_state(end) == mapped_state(ref['original_full_cut'])
             and r['token_ids'] == ref['original_full_result']['token_ids']
             and r['selected_correction'] == ref['original_full_result']['selected_correction'],
             'complete original task differs from fixed reference')
        roots[sid] = end
        canonical_count += 1
        semantic.append(dict(source_id=sid, parent=start, next=end, ids=r['token_ids'], correction=r['selected_correction']))
    expected = sum((s['frames']+7999)//8000 for s in sources.values())
    need(canonical_count == expected, 'selected original task does not cover all offered steps')
    quality = []
    for sid, source in sources.items():
        root = roots[sid]
        need(root['frontier'] == source['frames'], 'final selected EOS missing')
        eos = [row for row in consumer if row['source_id'] == sid and row['certified_frontier'] == source['frames']]
        need(eos and eos[-1]['canonical_sha'] == hashlib.sha256(canonical(root)).hexdigest(), 'actual Consumer final EOS binding differs')
        target, output = ''.join(c for c in source['reference'] if not c.isspace()), ''.join(c for c in root['transcript'] if not c.isspace())
        errors = edit_distance(target, output)
        quality.append(dict(source_id=sid, reference_characters=len(target), character_edits=errors,
                            CER=errors/len(target) if target else None, final_text=root['transcript']))
    return dict(checked_original_steps=canonical_count,
                semantic_fingerprint_sha256=hashlib.sha256(canonical(semantic)).hexdigest(), quality=quality)


def endpoint_recount(consumer, sources, origin):
    observed, ds, cs, credit = [], [], [], 0.0
    for source in sources:
        sid, n, previous = source['source_id'], source['frames'], 0
        timeline = [r for r in consumer if r['source_id'] == sid]
        need(timeline and all(a['observed'] <= b['observed'] for a, b in zip(timeline, timeline[1:])), 'Consumer observation order changed')
        for f in list(range(8000, n, 8000)) + [n]:
            ready, weight = origin + f/16000, (f-previous)/16000
            d = next((r['observed']-ready for r in timeline if r['observed'] >= ready and r['visible_frontier'] >= f), math.inf)
            c = next((r['observed']-ready for r in timeline if r['observed'] >= ready and r['certified_frontier'] >= f), math.inf)
            ds.append(d); cs.append(c)
            if d <= 2 and c <= 8:
                credit += weight
            observed.append(dict(source_id=sid, frontier=f, is_EOS=f == n,
                                 audio_seconds=weight, D=d if math.isfinite(d) else None,
                                 C=c if math.isfinite(c) else None, D2=d <= 2, C8=c <= 8))
            previous = f
    def endpoint_q(values):
        values = sorted(values)
        at = (len(values)-1)*.99; lo, hi = int(at), min(int(at)+1, len(values)-1)
        return math.inf if math.isinf(values[hi]) else values[lo]+(values[hi]-values[lo])*(at-lo)
    d99, c99 = endpoint_q(ds), endpoint_q(cs)
    return dict(offered_frontiers=len(observed), offered_audio_seconds=sum(r['audio_seconds'] for r in observed),
        primary_linear_all_offered_D99=d99 if math.isfinite(d99) else None,
        primary_linear_all_offered_C99=c99 if math.isfinite(c99) else None,
        original_quantile_test_pass=d99 <= 2 and c99 <= 8,
        complete_coverage_and_original_quantile_pass=all(math.isfinite(x) for x in ds+cs) and d99 <= 2 and c99 <= 8,
        dual_deadline_audio_credit_seconds=credit, D2_misses_all_offered=sum(not r['D2'] for r in observed),
        C8_misses_all_offered=sum(not r['C8'] for r in observed), EOS_D2_misses=sum(r['is_EOS'] and not r['D2'] for r in observed),
        missing_D_frontiers=sum(not math.isfinite(x) for x in ds), missing_C_frontiers=sum(not math.isfinite(x) for x in cs),
        frontiers=observed)


def energy_recount(power, start, end):
    need(math.isfinite(start) and math.isfinite(end) and end >= start, 'invalid energy endpoints')
    by = {}
    for gpu in ('0', '1'):
        points = sorted((row['time'], row['boards'][gpu]['watts']) for row in power)
        need(all(math.isfinite(t) and math.isfinite(w) and w >= 0 for t, w in points), 'invalid physical-board power sample')
        need(len(points) >= 2 and points[0][0] <= start <= end <= points[-1][0], 'power misses original endpoint boundary')
        need(all(a[0] < b[0] for a, b in zip(points, points[1:])), 'duplicate/regressing power sample clock')
        total = 0.0
        for (a, wa), (b, wb) in zip(points, points[1:]):
            left, right = max(a, start), min(b, end)
            if right <= left:
                continue
            low = wa+(wb-wa)*(left-a)/(b-a); high = wa+(wb-wa)*(right-a)/(b-a)
            total += .5*(low+high)*(right-left)
        by[gpu] = total
    return dict(begin_perf=start, end_perf=end, seconds=end-start, board_joules=by,
                total_joules=sum(by.values()), scope='both physical boards; not CPU/PSU energy')


def publication_counts(frames, publications, consumer):
    indexed = {f['receipt']['sequence']: f for f in frames}
    need(len(publications) == len(consumer), 'normal original publication/actual Consumer count differs')
    last = 0
    for pub, row in zip(publications, consumer):
        e = pub['event']; seq = e['publication_id']
        need(pub['bound_owner_epoch'] == row['owner_epoch'] == 0 and seq == last+1,
             'normal publication namespace/FIFO sequence changed')
        last = seq
        need(row['publication_id'] == seq and row['source_id'] == e['source_id'] and row['kind'] == e['kind'],
             'actual Consumer/publication identity differs')
        if e['kind'] == 'canonical':
            receipt = e['durable_receipt']; fact = indexed[receipt['sequence']]
            need(fact['obj']['kind'] == 'canonical' and all(receipt[k] == v for k, v in fact['receipt'].items()),
                 'Consumer publication durable receipt differs')
            need(e['state'] == fact['obj']['body']['next_state']
                 and row['transition_id'] == fact['obj']['body']['transition_id'], 'published selected fact changed')
    return dict(new_canonical_facts=sum(f['obj']['kind'] == 'canonical' for f in frames),
                genesis_frames=sum(f['obj']['kind'] == 'genesis' for f in frames),
                publications=len(publications), actual_Consumer_rows=len(consumer))


def reconcile_span_counts(enriched, counts, phase, enabled):
    labels = Counter(r['label'] for r in enriched)
    if enabled:
        need(labels['WAL.complete_fact_commit'] == counts['new_canonical_facts'], 'span/new durable fact count differs')
        need(labels['SUP.complete_consumer_apply'] == counts['publications'], 'span/whole Consumer publication count differs')
        need(labels['IO.actual_os_fsync'] > 0, 'no actual fsync timing evidence')
    else:
        need(not enriched, 'off control has timing spans')
    return dict(label_counts=dict(labels), **counts,
                genesis_not_counted_as_new_selected_transition=True,
                no_recovery_or_abnormal_path_performance_claim=(phase == 'nn'))


def matrix_check(plan):
    sources = tuple(plan['fixed_sources'])
    need(sources == ('BAC009S0908W0369', 'BAC009S0916W0463'), 'frozen two-source selection changed')
    cpu = {(c['source_id'], c['arm'], c['repeat']) for c in plan['cpu_cases']}
    nn = {(c['source_id'], c['arm'], c['repeat'], c['observation']) for c in plan['cells']}
    need(len(plan['cpu_cases']) == 12 and cpu == {(s, a, r) for s in sources
         for a in ('conservative', 'fullcall') for r in range(3)}, 'CPU12 matrix changed')
    need(len(plan['cells']) == 16 and nn == {(s, a, r, on) for s in sources
         for a in ('conservative', 'fullcall') for r in range(2) for on in (False, True)}, 'NN16 matrix changed')
    need(all(type(c['observation']) is bool for c in plan['cells']), 'off/on is not a Boolean mode')


def physical_drain_proof(power, declared):
    when, pids = declared['confirmed_perf'], {str(pid) for pid in declared['worker_pids']}
    need(len(pids) >= 2, 'physical drain has no two-worker ownership population')
    matching = [r for r in power if r['observation_end_perf'] == when]
    need(len(matching) == 1, 'physical drain boundary lacks unique external observation')
    row = matching[0]
    need(not row['compute_processes'] and pids.issubset(row['worker_process_states'])
         and all(row['worker_process_states'][pid] in ('absent', 'Z', 'X') for pid in pids),
         'claimed physical drain still has a live/CUDA owner')
    return dict(worker_pids=sorted(pids), confirmed_perf=when,
                scope='external observation upper boundary, not instantaneous hardware timestamp')


def pair_effects(cells):
    groups = defaultdict(dict)
    for cell in cells:
        key = cell['source_id'], cell['arm'], cell['repeat']
        need(cell['observation'] not in groups[key], 'duplicate off/on pair mode')
        groups[key][cell['observation']] = cell
    need(len(groups) == 8 and all(set(v) == {False, True} for v in groups.values()), 'incomplete frozen eight off/on pairs')
    result = []
    for key, values in sorted(groups.items()):
        off, on = values[False], values[True]
        need(off['task']['semantic_fingerprint_sha256'] == on['task']['semantic_fingerprint_sha256']
             and off['task']['quality'] == on['task']['quality'], 'off/on selected task or quality differs')
        effects = {}
        for metric in ('dual_deadline_audio_credit_seconds', 'primary_linear_all_offered_D99',
                       'primary_linear_all_offered_C99', 'EOS_D2_misses', 'D2_misses_all_offered', 'C8_misses_all_offered'):
            a, b = off['primary'][metric], on['primary'][metric]
            effects[metric] = None if a is None or b is None else b-a
        for window in ('origin_to_useful_certified_EOS', 'origin_to_confirmed_physical_model_drain'):
            effects[window + '_board_joules'] = on['energy'][window]['total_joules']-off['energy'][window]['total_joules']
            effects[window + '_seconds'] = on['energy'][window]['seconds']-off['energy'][window]['seconds']
        result.append(dict(source_id=key[0], arm=key[1], repeat=key[2], off=off['cell_id'], on=on['cell_id'],
            on_minus_off=effects, original_pass_off=off['primary']['complete_coverage_and_original_quantile_pass'],
            original_pass_on=on['primary']['complete_coverage_and_original_quantile_pass'],
            task_and_quality_equal=True, offered_seconds=off['primary']['offered_audio_seconds'],
            scope='instrumentation total system effect; not protocol-removal or pure safety tax'))
    return result


def main():
    global _OUT
    p = argparse.ArgumentParser()
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--cpu-campaign', type=Path)
    p.add_argument('--nn-campaign', type=Path)
    p.add_argument('--phase', choices=('cpu', 'nn', 'both'), default='both')
    p.add_argument('--source-commit', required=True)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--path-map', nargs=2)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    need(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'independent recount requires explicitly empty CUDA_VISIBLE_DEVICES')
    identity = verify_source(args.source_manifest, args.source_commit)
    plan = read(args.plan)
    need(plan['observer_source_commit'] == OBSERVER and plan['actual_nn_source_commit'] == NN4F,
         'wrong frozen cost execution roles')
    matrix_check(plan)
    def path(value):
        value = str(value)
        if args.path_map and value.startswith(args.path_map[0]):
            value = args.path_map[1]+value[len(args.path_map[0]):]
        return Path(value)
    need(not args.out.exists(), 'refusing to overwrite prior audit')
    args.out.mkdir(parents=True); _OUT = args.out
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    put(args.out/'CONFIG.json', config)
    put(args.out/'ENVIRONMENT.json', dict(python=sys.version, executable=sys.executable, platform=platform.platform()))
    put(args.out/'RUN_RECORD.json', dict(experiment_id='REVTRACE-INDEPENDENT-COST-RECOUNT-20261102', **identity,
        config_sha256=sha(args.out/'CONFIG.json'), environment_sha256=sha(args.out/'ENVIRONMENT.json'),
        plan_sha256=sha(args.plan), intended_summary=str(args.out/'SUMMARY.json'), intended_gate=str(args.out/'GATE.json'),
        raw_result_location=str(args.out), new_model_calls=0))
    phases = ('cpu', 'nn') if args.phase == 'both' else (args.phase,)
    all_cells = []
    for phase in phases:
        campaign_path = args.cpu_campaign if phase == 'cpu' else args.nn_campaign
        need(campaign_path is not None, 'selected phase lacks campaign path')
        campaign = Path(campaign_path)
        gate, summary, driver = read(campaign/'GATE.json'), read(campaign/'SUMMARY.json'), read(campaign/'DRIVER_CONFIG.json')
        need(gate['status'] == 'COMPLETE_FROZEN_COST_'+phase.upper()+'_CAMPAIGN', 'campaign not complete; never audit live matrix')
        need(driver['execution_roles']['driver']['source_commit'] == DRIVER
             and driver['execution_roles']['observer']['source_commit'] == OBSERVER
             and driver['execution_roles']['actual_NN']['source_commit'] == NN4F, 'campaign source roles changed')
        need(driver['plan_sha256'] == sha(args.plan), 'campaign/frozen plan hash differs')
        expected_cells = plan['cpu_cases'] if phase == 'cpu' else plan['cells']
        records = {r['cell_id']: r for r in summary['cells']}
        need(len(records) == len(expected_cells) and set(records) == {c['cell_id'] for c in expected_cells}, 'campaign cell set mismatch')
        for cell in expected_cells:
            raw = path(cell['output'] if phase == 'cpu' else cell['out'])
            primary_record = records[cell['cell_id']]
            members = list((raw/'cost_spans').glob('*.jsonl'))+list((raw/'cost_spans').glob('*_SUMMARY.json'))
            members += [raw/name for name in ('GATE.json', 'SUMMARY.json', 'facts.wal', 'consumer.jsonl')]
            if phase == 'cpu':
                original_raw = path(cell['input_raw'])
                cfg_path, pubs_path = original_raw/'CONFIG.json', original_raw/'publications.jsonl'
                cfg = read(cfg_path); declared = primary_record['summary']
                need(sha(raw/'facts.wal') == declared['original_and_replayed_facts_sha256'], 'CPU replayed full facts changed')
                for name, item in declared['input_files'].items():
                    member = original_raw/name
                    need(member.stat().st_size == item['bytes'] and sha(member) == item['sha256'], 'original CPU replay input changed')
                    members.append(member)
                consumers = lines(raw/'consumer.jsonl')
                windows, enabled = {'complete_CPU_object_replay': None}, True
            else:
                cfg_path, pubs_path = raw/'CONFIG.json', raw/'publications.jsonl'
                cfg = read(cfg_path); declared = primary_record
                planned_config = path(cell['config'])
                need(sha(planned_config) == cell['config_sha256'] and cfg == read(planned_config),
                     'actual/frozen NN config bytes or object binding differs')
                need(cfg['cost_observer']['enabled'] is cell['observation'] and cfg['arm'] == cell['arm'], 'actual mode/policy changed')
                enabled = cell['observation']; consumers = lines(raw/'consumer.jsonl')
                origin = read(raw/'ORIGIN.json')['origin_perf']; service_end = read(raw/'SERVICE_END.json')['service_end_perf']
                sources = cfg['settings']['sources']
                eos = max(min(r['observed'] for r in consumers if r['source_id'] == s['source_id']
                              and r['certified_frontier'] == s['frames']) for s in sources)
                drain = declared['common_external_energy']['physical_drain_observation']['confirmed_perf']
                windows = {'origin_to_service_end': (origin, service_end),
                    'origin_to_useful_certified_EOS': (origin, eos),
                    'origin_to_confirmed_physical_model_drain': (origin, drain)}
                members += [raw/name for name in ('ORIGIN.json', 'SERVICE_END.json', 'publications.jsonl', 'consumer_rejections.jsonl')]
                members.append(planned_config)
            need(cfg['settings']['source_commit'] == NN4F and cfg.get('fault', {}).get('kind') == 'none', 'not frozen normal NN4f objects')
            need([s['source_id'] for s in cfg['settings']['sources']] == [cell['source_id']], 'actual source/stratum changed')
            reference_path = path(cfg['reference_details'])
            need(sha(reference_path) == cfg['reference_details_sha256'], 'fixed reference details changed')
            members += [cfg_path, pubs_path, reference_path]
            before = {str(member): sha(member) for member in set(members)}
            frames, pubs = facts(raw/'facts.wal'), lines(pubs_path)
            counts = publication_counts(frames, pubs, consumers)
            task = task_audit(cfg, frames, consumers, read(reference_path))
            spans = [r for member in sorted((raw/'cost_spans').glob('*.jsonl')) for r in lines(member)]
            metadata = [read(member) for member in sorted((raw/'cost_spans').glob('*_SUMMARY.json'))]
            rebuilt = forest(spans)
            exports = export_metadata_check(rebuilt, metadata, phase, enabled, windows)
            count_check = reconcile_span_counts(rebuilt, counts, phase, enabled)
            result = dict(cell_id=cell['cell_id'], source_id=cell['source_id'], arm=cell['arm'], repeat=cell['repeat'],
                phase=phase, observation=enabled, task=task, counts=count_check, span_count=len(rebuilt),
                window_accounts=window_accounts(rebuilt, windows), export_scope=exports,
                brackets='threadCPU/processCPU start before wall; wall ends before CPU. Signed differences preserved, not blocking.',
                raw_result_location=str(raw), no_primary_summarizer_called=True)
            if phase == 'nn':
                primary = endpoint_recount(consumers, cfg['settings']['sources'], origin)
                checked_fields(primary, declared['primary'], [k for k in primary if k != 'frontiers'], 'original all-offered endpoints')
                power_path = campaign/'external'/(cell['cell_id']+'.jsonl')
                members.append(power_path); before[str(power_path)] = sha(power_path)
                power = lines(power_path)
                drain_check = physical_drain_proof(power, declared['common_external_energy']['physical_drain_observation'])
                energies = {}
                for name in ('origin_to_useful_certified_EOS', 'origin_to_confirmed_physical_model_drain'):
                    energies[name] = energy_recount(power, *windows[name])
                    checked_fields(energies[name], declared['common_external_energy'][name],
                                   ('begin_perf', 'end_perf', 'seconds', 'total_joules'), 'common energy window: '+name)
                    need(all(equal(energies[name]['board_joules'][gpu], declared['common_external_energy'][name]['board_joules'][gpu])
                             for gpu in ('0', '1')), 'individual board energy differs')
                result.update(primary=primary, energy=energies, physical_drain=drain_check,
                    actual_trace_c4_status='SEPARATE_ROOT_CHECK_REQUIRED_NOT_RUN_HERE')
            after = {str(member): sha(member) for member in set(members)}
            need(before == after, 'cost raw changed during independent audit')
            result['input_inventory_sha256'] = hashlib.sha256(canonical(before)).hexdigest()
            cell_out = args.out/cell['cell_id']; cell_out.mkdir()
            put(cell_out/'SUMMARY.json', result)
            put(cell_out/'INPUTS.json', before)
            all_cells.append(result); _DONE.append(result)
    nn = [c for c in all_cells if c['phase'] == 'nn']
    pairs = pair_effects(nn) if nn else []
    put(args.out/'SUMMARY.json', dict(status='PASS_INDEPENDENT_COST_OBJECT_FOREST_AND_ENDPOINT_RECOUNT',
        cells=all_cells, cpu_cells=sum(c['phase'] == 'cpu' for c in all_cells), NN_cells=len(nn), off_on_pairs=pairs,
        role_wall_totals_NOT_ADDED=True, timer_bracket_asymmetry_not_treated_as_negative_blocking=True,
        scope='current-object resource footprint and observation total effect, not protocol-removal tax', **identity))
    put(args.out/'GATE.json', dict(status='PASS_INDEPENDENT_COST_RECOUNT', completed_cells=len(all_cells),
        NN_off_on_pairs=len(pairs), current_trace_c4_is_separate=True, new_model_calls=0))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        if _OUT is not None:
            failure = dict(status='FAIL_INDEPENDENT_COST_RECOUNT_PRESERVED', completed=len(_DONE),
                           failure=traceback.format_exc(), new_model_calls=0)
            if not (_OUT/'SUMMARY.json').exists():
                put(_OUT/'SUMMARY.json', failure)
            put(_OUT/'FAILURE.json', failure)
            if not (_OUT/'GATE.json').exists():
                put(_OUT/'GATE.json', failure)
        raise
