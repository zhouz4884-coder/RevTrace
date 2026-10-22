"""Read-only actual clocks; no GPU or CPU model generation, no metrics retuning."""
from pathlib import Path
import csv
import hashlib
import json
import sys
from candidate_wait_core import availability_bounds


def main():
    B = Path(sys.argv[1]); O = B / 'results/revtrace/online_admission_20261022'
    assert json.loads((O / 'POSTPROCESS_SUMMARY.json').read_text())['status'] == 'COMPLETE_FORMAL_ORACLE_AND_CPU_AUDITS'
    D = O / 'CANDIDATE_WAIT_BOUNDS_v1'; D.mkdir(exist_ok=False); rows = []
    def read_lines(p): return [json.loads(x) for x in p.read_text().splitlines()]
    try:
        for c in sorted((O / 'formal_v1').iterdir()):
            if not c.is_dir() or not (c / 'result.json').exists(): continue
            cfg = json.loads((c / 'config.json').read_text()); method = cfg['online_study']['method']
            if method not in ['unprotected', 'score', 'strict']: continue
            es = read_lines(c / 'events.jsonl'); records = read_lines(c / 'worker_records.jsonl')
            by_job = {r['job']['job_id']: r for r in records}; t0 = next(e['t0_perf'] for e in es if e['kind'] == 'run-start')
            installs = {(e['session_id'], e['version']): t0 + e['installed'] for e in es if e['kind'] == 'commit'}
            rendered = {e['job_id']: t0 + e['time'] for e in es if e['kind'] == 'render-checked'}
            published = {e['job_id']: t0 + e['displayed'] for e in es if e['kind'] == 'display'}
            for r in records:
                j = r['job']
                if j['role'] != 'authority': continue
                origin = by_job[j['candidate_origin_job_id']]; oid = origin['job']['job_id']
                parent_ready = installs[j['session_id'], j['parent']] if j['parent'] else t0
                b = availability_bounds(audio_ready=j['audio_ready_perf'], parent_ready=parent_ready,
                    candidate_gpu_done=origin['result']['completed_perf'], candidate_owner_received=origin['result']['received_perf'],
                    render_checked=rendered[oid], provisional_published=published[oid], target_enqueued=j['enqueue_perf'])
                rows.append({'cell': c.name, 'method': method, 'traffic': cfg['online_study']['traffic'],
                    'source_id': j['source_id'], 'job_id': j['job_id'], 'candidate_job_id': oid,
                    'parent': j['parent'], **b, 'enqueue_to_worker_start_s': r['result']['started_perf'] - j['enqueue_perf'],
                    'not_a_pure_candidate_causal_fraction': True})
        with (D / 'TARGET_WAIT_BOUNDS.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        out = {'status': 'COMPLETE_CANDIDATE_READINESS_BOUND_AUDIT', 'target_rows': len(rows),
               'source_count': len({r['source_id'] for r in rows}),
               'scope': 'per-target row seconds; candidate availability bounded by actual owner events; overlaps other blockers; not additive GPU busy or causal attribution',
               'does_not_change_frozen_performance_gates': True, 'model_calls': 0,
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (D / 'SUMMARY.json').write_text(json.dumps(out, indent=2) + '\n'); print(json.dumps(out))
    except BaseException as e:
        (D / 'STOP.json').write_text(json.dumps({'error': repr(e), 'no_GPU_or_measurement_changes': True}, indent=2) + '\n')
        raise


if __name__ == '__main__': main()
