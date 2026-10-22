"""Read-only metadata plan, not a performance or outcome-selection analysis."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import sys

B = Path(sys.argv[1])
O = B / 'results/revtrace/online_admission_20261022'
D = O / 'formal_v1'
plan, opportunities = [], []
for load in ['sync16', 'cohort8']:
    for method, traffic in [(m, t) for m in ['score', 'strict'] for t in ['clean', 'F2']] + [('unprotected', 'F2')]:
        name = f'{method}-{load}-{traffic}-r0'
        c = D / name
        if not (c / 'result.json').exists():
            opportunities.append({'cell': name, 'status': 'not_complete_yet'})
            continue
        rows = [json.loads(line) for line in (c / 'worker_records.jsonl').read_text().splitlines()]
        records = {r['job']['job_id']: r for r in rows}
        groups = defaultdict(list)
        for r in rows:
            if r['job']['role'] == 'authority':
                groups[r['result']['started_perf'], r['result']['completed_perf']].append(r)
        selected = {}
        sessions = json.loads((c / 'sessions.json').read_text())
        for s in sessions:
            sid = s['session_id']
            options = [r for r in rows if r['job']['role'] == 'authority' and r['job']['session_id'] == sid
                       and r['job']['chunk_id'] >= 2 and r['job']['end_window'] >= 5]
            if method == 'unprotected':
                options = [r for r in options if 'fault_actual_prompt_tokens' in
                           records[r['job']['candidate_origin_job_id']]['job']]
            options.sort(key=lambda r: (r['job']['enqueue_perf'], r['job']['job_id']))
            choice = options[0] if options else None
            opportunities.append({'cell': name, 'session_id': sid, 'source_id': s['source_id'],
                                  'status': 'selected_by_input_time' if choice else 'missing_opportunity',
                                  'target_job_id': choice['job']['job_id'] if choice else None})
            if choice:
                selected[choice['job']['job_id']] = True
        for i, rs in enumerate(groups.values()):
            targets = [r['job']['job_id'] for r in rs if r['job']['job_id'] in selected]
            if targets:
                plan.append({'cell': name, 'batch_index': i, 'target_job_ids': targets,
                             'whole_peer_job_ids': [r['job']['job_id'] for r in rs],
                             'batch_rows': len(rs), 'method': method, 'load': load, 'traffic': traffic})
out = {'status': 'INPUT_TIME_SELECTED_NO_FORMAL_OUTCOME_METRICS',
       'protocol_sha256': hashlib.sha256((B / 'projects/revtrace_online_admission_20261022/FORMAL_ORACLE_EXTENSION_FREEZE.md').read_bytes()).hexdigest(),
       'opportunities': opportunities, 'batches': plan,
       'bounds': {'maximum_selected_target_rows': 160, 'future_source_opportunities': 32},
       'no_formal_quality_latency_energy_tables_inspected': True}
target = O / 'FORMAL_ORACLE_INPUT_PLAN.json'
assert not target.exists(), 'Do not overwrite an existing frozen selection'
target.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'selected_rows': sum(x['status'] == 'selected_by_input_time' for x in opportunities),
                  'missing': sum(x['status'] == 'missing_opportunity' for x in opportunities),
                  'incomplete_cells': sum(x['status'] == 'not_complete_yet' for x in opportunities),
                  'physical_batches': len(plan), 'performance_claim': False}))
