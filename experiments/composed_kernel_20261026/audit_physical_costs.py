"""Count actual recorded neural phases, distinct from rows and leases.
Already-started but incomplete work stays censored and paid, never zero cost.
"""
from pathlib import Path
import json,csv,hashlib
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def rows(p):
    if not p.exists():return []
    raw=p.read_bytes().splitlines(keepends=True);out=[]
    for i,s in enumerate(raw):
        try:out.append(json.loads(s))
        except (json.JSONDecodeError,UnicodeDecodeError):assert i==len(raw)-1 and not s.endswith(b'\n')
    return out
def main():
    assert any((O/n).exists() for n in ['CAMPAIGN_COMPLETE_v3.json','CAMPAIGN_COMPLETE_v2.json']);out=[]
    for stage in ['boundary_pilot','post_sync_pilot','normal','fault','boundary','post_sync']:
        done=read(O/stage/'SUMMARY.json');cfgs=read(O/stage/'FREEZE.json')['cells']
        for name,c in zip(done['completed'],cfgs):
            E=O/stage/name;final=1 if (E/'attempt1').exists() else 0
            for attempt in range(final+1):
                D=E/f'attempt{attempt}';cfg=read(D/'config.json')
                submissions=[];complete={};account=[]
                for f in D.glob('*.submissions'):submissions+=rows(f)
                for f in D.glob('worker-*-receipts.jsonl'):
                    for r in rows(f):
                        if r['kind']=='row-complete':
                            m=r['message'];assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
                            body=json.loads(m['payload_json']);complete[body['job_id']]=body
                        elif r['kind']=='batch-drained':account.append(r['physical_accounting'])
                if not complete:
                    for r in rows(D/'worker_records.jsonl'):complete[r['job']['job_id']]=r['result']
                if not account:account=rows(D/'worker_batch_accounting.jsonl')
                phases=[p for b in account for p in b['phases']]
                for b in account:
                    assert b['batch_drained_perf']>=b['worker_started_perf']
                    for p in b['phases']:assert p['completed_perf']>=p['started_perf']
                submitted_jobs=sum(len(s['jobs']) for s in submissions) if submissions else len(complete)
                submitted_batches=len(submissions) if submissions else len(account)
                out.append(dict(stage=stage,episode=name,adapter=c['adapter'],method=c['method'],attempt=attempt,
                    submitted_serving_batches=submitted_batches,submitted_serving_rows=submitted_jobs,
                    actual_complete_original_worker_rows=len(complete),drained_physical_batches=len(account),
                    complete_recorded_neural_phases_in_drained_batches=len(phases),
                    model_call_seconds_in_complete_phase_records=sum(p['completed_perf']-p['started_perf'] for p in phases),
                    observed_worker_lease_seconds_in_drained_batches=sum(b['batch_drained_perf']-b['worker_started_perf'] for b in account),
                    incomplete_or_not_drained_batches=submitted_batches-len(account),
                    rows_without_complete_neural_receipts=submitted_jobs-len(complete),
                    warmup_calls_separate_from_serving_phase_counts=2 if (D/'EXECUTORS_READY.json').exists() else None,
                    killed_attempt=attempt<final,
                    scope='original Worker observations; coherent injected Z not neural; incomplete work energy remains in full episode sampler'))
    dest=O/'PHYSICAL_COSTS_v1.json';assert not dest.exists();dest.write_text(json.dumps(dict(
        status='PASS_PHYSICAL_LEASE_ROW_PHASE_SCOPE_RECOUNT',runs=out,
        warning='sum of complete phase records excludes censored calls and startup warmup; it is not total GPU cost. Use full measured episode energy.'),indent=2)+'\n')
    with (O/'PHYSICAL_COSTS_v1.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print(json.dumps(dict(attempts=len(out),recorded_complete_rows=sum(r['actual_complete_original_worker_rows'] for r in out))))
if __name__=='__main__':main()
