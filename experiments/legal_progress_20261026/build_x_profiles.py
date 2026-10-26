"""Freeze paired target/seed recipes by recorded readiness, never match length."""
from pathlib import Path
import json,hashlib,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/dependability_20261025/lp1_20261026';N=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2/formal_normal'
P=B/'projects/revtrace_dependability_20261025/lp1_20261026'
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    dest=O/'X_PROFILES_v1.json';assert not dest.exists();freeze=read(N/'FREEZE.json');done=read(N/'SUMMARY.json');selected={}
    for rho,method in [(1,'fine_fair'),(3,'dgft_original')]:
        candidates=[(name,c) for name,c in zip(done['completed'],freeze['cells']) if c['method']==method and c['repeat']==0 and c['load']>=8]
        name,cell=min(candidates,key=lambda pair:(pair[1]['load'],done['completed'].index(pair[0])))
        D=N/name/'attempt0';ss=read(D/'sessions.json');rr=rows(D/'worker_records.jsonl')
        selected[rho]=(D,ss,rr,cell)
    ids=[s['source_id'] for s in selected[1][1]][:8]
    assert len(ids)==len(set(ids))==8
    assert ids==[s['source_id'] for s in selected[3][1]][:8]
    manifests=[B/'projects/revtrace_dependability_20261025/ck5_v6/INDEPENDENT_MANIFEST_v1.json']
    m=read(manifests[0]);sources={s['source_id']:s for s in m['sessions']};profiles=[]
    for rho in [1,3]:
        D,ss,rr,cell=selected[rho]
        for sid in ids:
            aa=sorted([r for r in rr if r['job']['role']=='authority' and r['job']['source_id']==sid],key=lambda r:r['job']['enqueue_perf'])
            assert aa
            target=next((r for r in aa if r['job']['chunk_id']>=2 and r['result'].get('model_input_audit',{}).get('rollback_prefix')),aa[0])
            j=target['job'];cut=j['enqueue_perf']
            ready=[r for r in rr if r['job']['role']=='proposal' and r['job']['source_id']==sid and r['job']['audio_end_sample']<=j['audio_end_sample'] and r['result']['received_perf']<=cut]
            seed=max(ready,key=lambda r:(r['job']['audio_end_sample'],r['result']['received_perf'],r['job']['job_id']),default=None)
            for rep in range(2):profiles.append(dict(id=f'{sid}-rho{rho}-r{rep}',source_id=sid,rho=rho,repeat=rep,
                source=sources[sid],target_job=j,original_target_result=target['result'],
                original_host_decision_cut=cut,selected_seed_job=seed['job'] if seed else None,
                original_seed_result=seed['result'] if seed else None,
                seed_rule='latest target frontier, then recorded HOST receive time, no future verification/match-length selection',
                actual_nonempty_feedback=bool(target['result'].get('model_input_audit',{}).get('rollback_prefix')),
                historical_cell=cell,raw_trace=str(D),raw_worker_sha256=sha(D/'worker_records.jsonl'),
                probe_scope='historical-ready-cut recipe; producer is freshly reexecuted/paid and all target modes freshly execute; not new online availability or serving Goodput'))
    result=dict(status='FROZEN32_METADATA_READY_TIME_TUPLES',profiles=profiles,unique_sources=8,tuples=32,
        model='Qwen3-ASR-1.7B',authority_dtype='float32',producer_dtype='float16',budget=256,batch_rows=1,
        manifest=str(manifests[0]),manifest_sha256=sha(manifests[0]),
        methods=['fresh','strict-full','prefix','revtrace-prefix'],
        cost_scope='actual fresh producer and target work per method, shared ordinary last-logit/audio-embedding optimization; parent is an explicitly given frozen condition; no deployed cost claim',
        scope='conditional-state GPU operator gate before any integrated service claim')
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],sources=ids,tuples=len(profiles),seed_ready=sum(p['selected_seed_job'] is not None for p in profiles),nonempty_feedback=sum(p['actual_nonempty_feedback'] for p in profiles))))
if __name__=='__main__':main()
