"""Independent supplemental input-presence and actual-Consumer linkage audit.

Unlike equality of two optional dictionaries, this requires nonempty actual
processed tensor and executed-prompt evidence before marking an input match.
Owner publication and actual Consumer application are recorded separately.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import platform
import subprocess
import sys

INPUTS = {}
CONTEXT_KEYS = {'declared_prompt_digest', 'executed_prompt_digest', 'executed_prompt_tokens',
                'actual_audio_sha256', 'conditioning_prefix_sha256', 'fault_override'}
MODEL_KEYS = {'waveform_sha256', 'declared_prompt_tokens', 'input_ids', 'attention_mask',
              'unpadded_input_ids', 'batch_tensors', 'row_features', 'batch_rows', 'dtype'}


def read(path, lines=False):
    path = Path(path)
    raw = path.read_bytes()
    INPUTS[str(path)] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if lines:
        return [json.loads(line) for line in raw.decode('utf8').splitlines() if line]
    return json.loads(raw)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


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
        assert path.stat().st_size == row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
    return manifest['code_commit']


def present(job, result):
    context = result.get('execution_context_audit')
    model = result.get('model_input_audit')
    if not isinstance(context, dict) or not isinstance(model, dict):
        return False, 'missing_audit_dictionary'
    if not CONTEXT_KEYS <= set(context) or not MODEL_KEYS <= set(model):
        return False, 'missing_required_actual_input_fields'
    if not model['batch_tensors']:
        return False, 'empty_actual_tensor_evidence'
    for tensor in list(model['batch_tensors'].values()) + list(model['row_features'].values()):
        if not {'shape', 'dtype', 'sha256'} <= set(tensor) or len(tensor['sha256']) != 64:
            return False, 'malformed_actual_tensor_identity'
    assert isinstance(model['input_ids'], list) and model['input_ids']
    assert isinstance(model['attention_mask'], list) and len(model['attention_mask']) == len(model['input_ids'])
    assert model['waveform_sha256'] == context['actual_audio_sha256'] == job['prefix_audio_sha256']
    assert model['declared_prompt_tokens'] == job['prompt_tokens']
    expected = job.get('fault_actual_prompt_tokens', job['prompt_tokens'])
    assert context['executed_prompt_tokens'] == expected
    digest = hashlib.sha256(','.join(map(str, expected)).encode()).hexdigest()
    assert context['executed_prompt_digest'] == digest
    assert context['fault_override'] == ('fault_actual_prompt_tokens' in job)
    return True, 'actual_tensor_prompt_audio_evidence_present'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    args = parser.parse_args()
    commit = verify_source(args.source_manifest)
    plan = read(args.plan)
    assert read(args.analysis / 'GATE.json')['gate'] == 'PASS_OFFLINE_RECOUNT'
    runs = read(args.analysis / 'RUNS.json')
    matched = read(args.analysis / 'MATCHED_ROWS.json')
    byrun = {r['cell_id']: r for r in runs}
    cells = {}
    presence_rows, consumer_links, legal_links, exit_links = [], [], [], []
    for cell in plan['cells']:
        base = Path(cell['output'])
        assert read(base / 'GATE.json')['gate'] == 'PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT'
        records = read(base / 'attempt0/worker_records.jsonl', True)
        events = read(base / 'attempt0/events.jsonl', True)
        start = next(e['t0_perf'] for e in events if e['kind'] == 'run-start')
        consumers = read(base / 'attempt0/consumer.jsonl', True)
        cfg = read(base / 'attempt0/config.json')
        index = {r['job']['job_id']: r for r in records}
        displays = defaultdict(list)
        for event in events:
            if event['kind'] == 'display':
                displays[event['job_id']].append(event)
        applications = defaultdict(list)
        for consumer in consumers:
            applications[consumer['session_id'], consumer['source_kind'], consumer['server_time']].append(consumer)
        present_by_job = {}
        links_by_job = {}
        for record in records:
            job, result = record['job'], record['result']
            jid = job['job_id']
            ok, reason = present(job, result)
            present_by_job[jid] = ok
            assert ok, (cell['cell_id'], jid, reason)
            links = []
            for display in displays[jid]:
                candidates = applications[job['session_id'], 'display', display['displayed']]
                assert len(candidates) <= 1, 'ambiguous Consumer application for one immutable Owner event'
                applied = candidates[0] if candidates else None
                actual = bool(applied and applied['valid_visible_frontier'] == job['audio_end_sample']
                              and applied['visible_text'] == display['text'])
                first = next((c for c in consumers if c['session_id'] == job['session_id']
                              and c['valid_visible_frontier'] >= job['audio_end_sample']), None)
                certified = next((c for c in consumers if c['session_id'] == job['session_id']
                                  and c['certified_frontier'] >= job['audio_end_sample']), None)
                link = dict(cell_id=cell['cell_id'], job_id=jid, source_id=job['source_id'],
                            session_id=job['session_id'], target_F=job['audio_end_sample'],
                            owner_display_perf=start + display['displayed'],
                            exact_consumer_application=actual,
                            consumer_observed_perf=None if applied is None else applied['observed_perf'],
                            consumer_display_latency=None if applied is None else applied['observed_perf'] - job['audio_ready_perf'],
                            actual_consumer_text_equals_complete_owner_text=actual,
                            first_covering_consumer_perf=None if first is None else first['observed_perf'],
                            first_covering_consumer_kind=None if first is None else first['source_kind'],
                            first_certified_consumer_perf=None if certified is None else certified['observed_perf'],
                            actual_row_met_D2=bool(actual and applied['observed_perf'] - job['audio_ready_perf'] <= 2.),
                            first_coverage_met_D2=bool(first and first['observed_perf'] - job['audio_ready_perf'] <= 2.),
                            actual_certified_coverage_met_C8=bool(certified and certified['observed_perf'] - job['audio_ready_perf'] <= 8.))
                links.append(link)
                consumer_links.append(link)
            links_by_job[jid] = links
        presence_rows.append(dict(cell_id=cell['cell_id'], records=len(records), proposal_records=sum(
            r['job']['role'] == 'proposal' for r in records), all_records_with_actual_input_evidence=sum(present_by_job.values()),
            required_context_keys=sorted(CONTEXT_KEYS), required_model_keys=sorted(MODEL_KEYS),
            observer_scope='Observed processed tensors and execution prompt; not trusted execution attestation'))
        for pressure in byrun[cell['cell_id']]['legal_pressure']:
            if pressure['compatible'] is not True:
                continue
            row = index[pressure['job_id']]
            job = row['job']
            assert 'fault_actual_prompt_tokens' not in job
            assert row['result']['execution_context_audit']['executed_prompt_tokens'] == job['prompt_tokens']
            legal_links.append(dict(cell_id=cell['cell_id'], arm=cell['arm'], arrival=cell['arrival'], repeat=cell['repeat'],
                                   pressure=pressure, original_parent=job['parent'],
                                   actual_complete_input_sha256=sha(row['result']['model_input_audit']),
                                   consumer_display_applications=links_by_job[job['job_id']]))
        for chain in byrun[cell['cell_id']]['exit_chains']:
            following = []
            for jid in chain['following_job_ids']:
                following.append(dict(job_id=jid, has_complete_result=jid in index,
                                      actual_consumer_applications=links_by_job.get(jid, [])))
            exit_links.append(dict(cell_id=cell['cell_id'], arm=cell['arm'], arrival=cell['arrival'], repeat=cell['repeat'],
                                   chain=chain, following_actual_consumer_links=following))
        cells[cell['cell_id']] = dict(records=index, present=present_by_job)
    match_presence = []
    for group in matched:
        pairs = []
        for pair in group['rows']:
            a = cells[group['a']]['records'][pair['a_job']]
            b = cells[group['b']]['records'][pair['b_job']]
            both = cells[group['a']]['present'][pair['a_job']] and cells[group['b']]['present'][pair['b_job']]
            full = both and a['result']['model_input_audit'] == b['result']['model_input_audit']
            context = both and a['result']['execution_context_audit'] == b['result']['execution_context_audit']
            assert full == pair['full_model_input_audit_equal']
            assert context == pair['actual_execution_context_equal']
            pairs.append(dict(input_sha256=pair['input_sha256'], a_job=pair['a_job'], b_job=pair['b_job'],
                              both_actual_audits_present=both, actual_full_input_equal=full,
                              actual_context_equal=context, peers_equal=pair['peers_equal'],
                              complete_outputs_equal=pair['output_equal']))
        match_presence.append(dict(a=group['a'], b=group['b'], matched_unique_inputs=len(pairs),
                                   both_actual_audits_present=sum(p['both_actual_audits_present'] for p in pairs),
                                   same_complete_input_context_and_peers=sum(p['actual_full_input_equal'] and p['actual_context_equal']
                                                                           and p['peers_equal'] for p in pairs), rows=pairs))
    args.out.mkdir(parents=True, exist_ok=False)
    outputs = dict(INPUT_AUDIT_PRESENCE=presence_rows, MATCHED_AUDIT_PRESENCE=match_presence,
                   OWNER_TO_ACTUAL_CONSUMER=consumer_links, LEGAL_PRESSURE_CONSUMER=legal_links,
                   EXIT_FOLLOWING_CONSUMER=exit_links)
    summary = dict(status='PASS_ACTUAL_INPUT_PRESENCE_AND_CONSUMER_LINKAGE', cells=len(cells),
                   actual_complete_records=sum(r['records'] for r in presence_rows),
                   with_required_actual_input_evidence=sum(r['all_records_with_actual_input_evidence'] for r in presence_rows),
                   owner_display_events=len(consumer_links),
                   exact_actual_consumer_applications=sum(r['exact_consumer_application'] for r in consumer_links),
                   compatible_unmodified_actual_model_crossings=len(legal_links),
                   exit_chains=len(exit_links), new_model_calls=0)
    outputs.update(SUMMARY=summary, GATE=dict(gate='PASS_SUPPLEMENTAL_OFFLINE_AUDIT'),
                   RUN_RECORD=dict(experiment_id=plan['experiment_id']+'-ACTUAL-INPUT-CONSUMER-AUDIT',
                                   code_commit=commit, frozen_plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                                   inputs=INPUTS, python=sys.version, platform=platform.platform(),
                                   raw_result_location=[c['output'] for c in plan['cells']],
                                   aggregate_summary_location=str(args.out/'SUMMARY.json'), gate_decision_location=str(args.out/'GATE.json')))
    assert verify_source(args.source_manifest) == commit
    for name, value in outputs.items():
        (args.out/(name+'.json')).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
