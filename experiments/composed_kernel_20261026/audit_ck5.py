"""Independent recorded-history recount; no scheduler/kernel imports."""
from pathlib import Path
import argparse,json,sys,importlib.util,hashlib,csv
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=Path(__file__).resolve().parent;O=B/'results/revtrace/dependability_20261025'/P.name
BASE=B/'projects/revtrace_dependability_20261025/n5_v3'
sys.path.insert(0,str(BASE))
def load(name,file):
    s=importlib.util.spec_from_file_location(name,BASE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
spec=importlib.util.spec_from_file_location('primary_independent',P/'audit_ck5_normal.py')
normal=importlib.util.module_from_spec(spec);spec.loader.exec_module(normal)
spec=importlib.util.spec_from_file_location('fault_independent',P/'audit_ck5_fault_v2.py')
fault=importlib.util.module_from_spec(spec);spec.loader.exec_module(fault)
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def live(h):
    p=Path('/proc')/str(h['pid'])/'stat'
    if not p.exists():return False
    s=p.read_text().rsplit(')',1)[1].split();return s[0]!='Z' and s[19]==str(h.get('start_ticks',h.get('linux_start_ticks')))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',required=True);a=ap.parse_args()
    stage=O/a.stage;done=read(stage/'SUMMARY.json');freeze=read(stage/'FREEZE.json')
    assert done['status']=='COMPLETE' and len(done['completed'])==done['expected']==len(freeze['cells'])
    assert not (stage/'STOP.json').exists()
    manifest=read(P/'INDEPENDENT_MANIFEST_v1.json');source=read(P/'runtime/SOURCE_MANIFEST.json')
    shas={r['path']:r['sha256'] for r in source['files']};out=[]
    for name,c in zip(done['completed'],freeze['cells']):
        E=stage/name;isfault=c['workload']=='fault_recovery'
        for attempt in range(2 if isfault else 1):
            D=E/f'attempt{attempt}';p=read(D/'provenance.json')
            assert p['code_commit']==source['code_commit']
            assert all(shas[file]==value for file,value in p['source_sha256'].items())
            assert all(not live(h) for h in read(D/'OWNED_WORKER_HANDLES.json'))
        r=fault.episode(E,manifest) if isfault else normal.audit_episode(E,manifest)[0]
        r.update(adapter=c['adapter'],readiness=c['readiness'],kernel=c['kernel'],repeat=c['repeat'])
        D=E/('attempt1' if isfault else 'attempt0')
        if c['kernel']:
            kt=read(D/'kernel_trace.json');assert len(kt['events'])>0
            r['kernel_events']=len(kt['events']);r['kernel_CPU_seconds']=kt['cpu_seconds']
            kinds={e['kind'] for e in kt['events']}
            assert {'input-synced','worker-ready','dispatch','row-complete','batch-drained','canonical-synced','install','view-applied'}<=kinds
        if isfault:
            k=read(E/'KILL.json');views=lines(D/'consumer.jsonl')
            initial={s['session_id']:s['state']['audio_frontier_window'] for s in read(D/'initial_states.json')}
            new=[v['observed_perf'] for v in views if v['certified_frontier']>initial[v['session_id']]]
            r['kill_to_first_new_certified_consumption_seconds']=min(new)-k['kill_perf'] if new else None
            r['kill_to_all_accepted_debt_drain_seconds']=max(v['observed_perf'] for v in views)-k['kill_perf']
            accepted_at_fault={sid:0 for sid in initial}
            for ack in k['server_input_ACKs']:accepted_at_fault[ack['session_id']]=max(accepted_at_fault[ack['session_id']],ack['to_sample'])
            debt_times=[]
            for sid,A in accepted_at_fault.items():
                if A>initial[sid]:
                    matches=[v['observed_perf'] for v in views if v['session_id']==sid and v['certified_frontier']>=A]
                    assert matches;debt_times.append(min(matches))
            r['kill_to_precrash_accepted_debt_drain_seconds']=max(debt_times)-k['kill_perf'] if debt_times else 0.
            r['accepted_uncertified_audio_at_fault_seconds']=sum(max(0,A-initial[sid]) for sid,A in accepted_at_fault.items())/16000
            ready=read(D/'EXECUTORS_READY.json')['observed_perf']
            recovered=[v['observed_perf'] for v in views if initial[v['session_id']]>0 and v['certified_frontier']>=initial[v['session_id']]]
            r['previous_fact_applied_before_worker_ready']=bool(recovered) and min(recovered)<ready
        if c.get('probe'):
            probe=read(D/'BOUNDARY_PROBE.json');assert probe['released']
            r['controlled_late_private_compatible_roots']=sum(w['P6_equals_A6'] for w in probe['witnesses'])
            r['controlled_late_private_incompatible_roots']=sum(not w['P6_equals_A6'] for w in probe['witnesses'])
            r['synthetic_coherent_injections']=len(probe['coherent_injection'])
            records=lines(D/'worker_records.jsonl');byjob={x['job']['job_id']:x for x in records}
            canon=[x for x in records if x['job']['role']=='authority']
            for transform in probe['coherent_injection']:
                original=json.loads(transform['original_message']['payload_json'])
                corrupted=json.loads(transform['corrupted_message']['payload_json'])
                allowed={'token_ids','state_tokens','text','generated_tokens','hit_token_limit','terminated_by_eos'}
                assert all(corrupted.get(k)==v for k,v in original.items() if k not in allowed)
                assert byjob[corrupted['job_id']]['result']['token_ids']==corrupted['token_ids']
                assert transform['job']['role']=='proposal'
            if c['probe']=='coherent':assert r['synthetic_coherent_injections']==1
            else:assert not r['synthetic_coherent_injections']
            r['probe_not_normal_capacity_or_natural_rate']=True
        out.append(r)
    target=O/(a.stage+'_AUDIT.json');assert not target.exists()
    target.write_text(json.dumps(dict(status='PASS_INDEPENDENT_RECORDED_SOURCE_INPUT_VIEW_WAL_COST',stage=a.stage,
        runs=out,source=source['code_commit'],checker_sha256=sha(Path(__file__)),
        scope='CPU recount of real GPU service; processor/render replay separate; same sources across repeats not independent samples'),indent=2)+'\n')
    with (O/(a.stage+'_RUNS.csv')).open('x',newline='') as f:
        keys=sorted(set().union(*(r.keys() for r in out)));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(out)
    print(json.dumps([{k:r.get(k) for k in ['episode','adapter','readiness','kernel','all_offered_audio_goodput_2_8',
        'kill_to_all_previous_certified_consumed_seconds','kill_to_first_new_certified_consumption_seconds']} for r in out]))
if __name__=='__main__':main()
