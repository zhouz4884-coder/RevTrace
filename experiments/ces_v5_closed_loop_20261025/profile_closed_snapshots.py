"""Bounded exact CPU planner replay, never a model/GPU performance replay.

Run only after the complete serving stage and its independent safety audit.
Four predetermined r0 staggered cells; at most five largest *recorded host
planner wall* decisions per cell. All other service-book transitions are
reconstructed from the actual chronological dispatch/install events.
"""
from __future__ import annotations
import argparse,copy,cProfile,csv,dataclasses,hashlib,json,math,platform,pstats,sys,time
from pathlib import Path

MODES=('service_cost','reserved_progress','inherit','causal')

def read(p):return json.loads(p.read_text(encoding='utf8'))
def lines(p):return [json.loads(s) for s in p.read_text(encoding='utf8').splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalize(v):return json.dumps(json.loads(json.dumps(v,allow_nan=False)),sort_keys=True,allow_nan=False)
def equal(a,b,why):assert normalize(a)==normalize(b),why
def fingerprint(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def name(s):return f"{s['pool']}-{s['arrival']}-{s['traffic']}-{s['label']}-r{s['repeat']}"
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8')
def csvsave(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf8') as f:
        if keys:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def select_indices(events,count):
    assert 1<=count<=5
    decisions=[(i,e) for i,e in enumerate(events) if e['kind']=='ces-decision']
    assert all(e['planner_wall_seconds']>=0 for _,e in decisions)
    return {i for i,_ in sorted(decisions,key=lambda x:(-x[1]['planner_wall_seconds'],x[0]))[:count]}

def replay_cell(C,output,count=5):
    """No alternative actions are installed; unselected decisions are not run."""
    from revtrace.ces_closed_loop import ClosedLoopState,PlannerConfig,choose_closed_loop
    from revtrace.ces_v5_policy import V5Target
    from revtrace.dgft import digest_tokens
    from audit_closed_helpers_v2 import restore_context,finite_tree
    cfg=read(C/'config.json');events=lines(C/'events.jsonl');method=cfg['ces_study']['method']
    assert method in MODES and cfg['rho']==1 and cfg['fine_seconds']==2
    result=read(C/'result.json')
    assert result['fine_window_accounting_complete'] and result['decision'] in ('PASS_PROTOCOL_COMPLETENESS','TOKEN_LIMIT_BOUNDARY')
    records=lines(C/'worker_records.jsonl');jobs={r['job']['job_id']:r['job'] for r in records}
    actual={x['session_id']:dict(x['state']) for x in read(C/'initial_states.json')}
    specs={s['session_id']:s for s in read(C/'sessions.json')}
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start');cd=fingerprint(cfg)
    book=ClosedLoopState(scope=(t0,cd));selected=select_indices(events,count)
    config=PlannerConfig(**cfg['ces_study']['closed_loop_config'])
    acks={};commits={};pending=None;decision=None;issued=False;rows=[];hot=[];di=-1
    for ei,e in enumerate(events):
        kind=e['kind']
        if kind=='ces-consumer-ack':
            s=specs[e['session_id']]
            for w in range(1,math.ceil(s['duration']/2)+1):
                if min(w*32000,round(s['duration']*16000))<=e['valid_visible_frontier']:
                    k=e['session_id'],w;acks[k]=min(acks.get(k,math.inf),e['observed_perf'])
        elif kind=='commit':
            j=jobs[e['job_id']];s=actual[e['session_id']]
            assert j['parent']==s['checkpoint_id']
            s.update(checkpoint_id=e['version'],audio_frontier_window=e['audio_end_sample'],prompt_tokens=e['next_prompt_tokens'])
            commits[e['session_id'],j['end_window']]=e
        elif kind=='closed-loop-service-retired':
            s=actual[e['session_id']]
            assert e['actual_durable_install_observed']
            installed=[v for (sid,_),v in commits.items() if sid==e['session_id'] and t0+v['installed']==e['installed_perf']]
            assert len(installed)==1 and installed[0]['audio_end_sample']==s['audio_frontier_window']
            retired=book.admitted(e['session_id'],epoch=s['contract_epoch'],frontier=s['audio_frontier_window'],now=e['installed_perf'])
            equal(retired,e['retired'],'Actual retirement mismatch')
            equal(book.to_audit(),e['service_book'],'Post-install book mismatch')
        elif kind=='closed-loop-observation':
            assert pending is None and decision is None and e['prediction_not_authorization']
            now=e['observed_perf'];contexts={int(k):restore_context(v['target_context']) for k,v in e['contexts'].items()}
            finite_tree(e['contexts'])
            for sid,c in contexts.items():
                s=actual[sid];k=c.identity
                assert k.sid==sid and k.epoch==s['contract_epoch'] and k.parent_version==s['checkpoint_id']
                assert k.parent_digest==digest_tokens(s['prompt_tokens']) and k.frontier_start==s['audio_frontier_window']
                assert k.contract_digest==cd
                equal(dataclasses.asdict(c.identity),e['contexts'][str(sid)]['identity'],'Identity mismatch')
                equal([dataclasses.asdict(u) for u in c.successors],e['contexts'][str(sid)]['released_successors'],'Successor mismatch')
                for u in c.successors:
                    assert u.release<=now
                    assert u.display_met==(acks.get((sid,u.window),math.inf)<=u.display_deadline)
            book.observe(contexts,now);equal(book.to_audit(),e['service_book'],'Observed service book mismatch')
            credit=sum((c['audio_end_sample']-c['audio_start_sample'])/16000 for key,c in commits.items()
                if acks.get(key,math.inf)<=t0+c['audio_ready']+cfg['ces_study']['display_slo']
                and c['installed']<=c['audio_ready']+cfg['ces_study']['commit_slo'])
            assert abs(credit-e['observed_credit_audio'])<1e-9 and e['elapsed_seconds']==now-t0
            pending=e,contexts
        elif kind=='ces-decision':
            di+=1;assert pending is not None and decision is None
            observation,contexts=pending;assert e['observed_perf']==observation['observed_perf']
            ts=[V5Target(**v) for v in e['features']];assert {t.sid for t in ts}==set(contexts)
            assert sorted(s for b in e['plan'] for s in b['sids'])==sorted(e['common_cut_sids'])
            if ei in selected:
                kwargs=dict(now=e['observed_perf'],mode=method,cal=cfg['ces_study']['calibration'],
                    limit=cfg['microbatch'],observed_credit_audio=observation['observed_credit_audio'],
                    elapsed_seconds=observation['elapsed_seconds'],display_slo=cfg['ces_study']['display_slo'],config=config)
                before=normalize(book.to_audit())
                # Ordinary replay then instrumented replay. Neither changes the
                # reconstructed original state; fresh deep-copy for each call.
                st=copy.deepcopy(book);begin=time.perf_counter();out=choose_closed_loop(ts,contexts,state=st,**kwargs);ordinary=time.perf_counter()-begin
                for k,v in out.items():equal(v,e[k],'Exact frozen replay mismatch: '+k)
                pr=cProfile.Profile();st2=copy.deepcopy(book);begin=time.perf_counter()
                measured=pr.runcall(choose_closed_loop,ts,contexts,state=st2,**kwargs);profile_wall=time.perf_counter()-begin
                equal(measured,out,'cProfile changed the exact decision output')
                assert normalize(book.to_audit())==before,'Profiling mutated original service book'
                stem=f'{C.name}-decision-{di:03d}';pr.dump_stats(str(output/(stem+'.prof')))
                save(output/(stem+'.json'),{'cell':C.name,'decision_index':di,'event_index':ei,
                    'observation':observation,'features':e['features'],'recorded_decision':e,
                    'replay_exact':True,'only_CPU_no_counterfactual_serving':True})
                stats=pstats.Stats(pr)
                for rank,(func,(cc,nc,tt,ct,_)) in enumerate(sorted(stats.stats.items(),key=lambda kv:(-kv[1][3],kv[0]))[:50],1):
                    hot.append(dict(cell=C.name,decision=di,rank=rank,file=func[0],line=func[1],function=func[2],
                        primitive_calls=cc,total_calls=nc,exclusive_cpu_profile_s=tt,cumulative_profile_s=ct))
                rows.append(dict(cell=C.name,mode=method,decision=di,event_index=ei,
                    recorded_owner_planner_wall_s=e['planner_wall_seconds'],recorded_base_feature_wall_s=e['feature_wall_seconds'],
                    ordinary_exact_choose_wall_s=ordinary,instrumented_choose_wall_s=profile_wall,
                    operation=e['operation'],sids=json.dumps(e['sids']),score=e['score'],
                    targets=len(ts),released_successors=sum(len(c.successors) for c in contexts.values()),
                    private_CDF_points=sum(len(c.private_delay_distribution)+sum(len(u.private_delay_distribution) for u in c.successors) for c in contexts.values()),
                    plans_evaluated=e['plans_evaluated'],exact_all_planner_fields=True,
                    original_owner_context_build_not_in_replay=True))
            decision=e;pending=None
        elif kind=='closed-loop-service-dispatch':
            assert decision is not None and not issued
            assert e['decision_token']==decision['decision_token'] and e['actual_dispatch_perf']>=decision['observed_perf']
            receipt=book.record_dispatch(decision,contexts,now=e['actual_dispatch_perf'])
            for k,v in receipt.items():equal(v,e[k],'Actual dispatch book mismatch: '+k)
            issued=True
        elif kind=='batch-dispatched' and e['role']=='authority':
            assert decision is not None and issued
            dispatched=[jobs[jid] for jid in e['job_ids']]
            assert {j['session_id'] for j in dispatched}==set(decision['sids'])
            for j in dispatched:
                k=contexts[j['session_id']].identity
                assert j['ces_operation']==decision['operation'] and j['parent']==k.parent_version and j['contract_epoch']==k.epoch
                assert j['parent_prompt_digest']==k.parent_digest and j['contract_digest']==k.contract_digest
                assert (j['audio_start_sample'],j['audio_end_sample'])==(k.frontier_start,k.frontier_end)
                assert j['audio_ready_perf']<=j['enqueue_perf'] and j['enqueue_perf']>=decision['observed_perf']
            decision=None;issued=False
    assert pending is None and decision is None and not issued
    assert len(rows)==len(selected) and book.dispatches==di+1
    return rows,hot,{'cell':C.name,'actual_decisions':di+1,'profiled_decisions':len(rows),
        'service_dispatches_reconstructed':book.dispatches,'residual_records':len(book.records)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--stage',default='formal')
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--plan',type=Path,default=Path(__file__).with_name('PLAN.smoke.json'))
    ap.add_argument('--source-manifest',type=Path,default=Path(__file__).with_name('SOURCE_MANIFEST.json'))
    ap.add_argument('--audit-dir',type=Path);ap.add_argument('--max-decisions',type=int,default=5)
    ap.add_argument('--arrival',choices=['sync','staggered'],default='staggered');a=ap.parse_args()
    assert 1<=a.max_decisions<=5
    plan=read(a.plan);specs=plan['stages'][a.stage]['cells'];audit_dir=a.audit_dir or a.root/(a.stage+'_audit')
    audit=read(audit_dir/'SUMMARY.json')
    assert audit['status']=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT' and not audit['failures']
    assert audit['cells']==audit['expected_cells']==len(specs),'Wait for the complete stage; do not profile concurrently with serving'
    manifest=read(a.source_manifest)
    assert sha(a.source_manifest)==plan['runtime_manifest_sha256'] and manifest['code_commit']==plan['runtime_commit']
    for f in manifest['files']:
        assert sha(a.source/f['path'])==f['sha256'],f"Frozen source changed: {f['path']}"
    sys.path[:0]=[str(a.source/'src'),str(Path(__file__).resolve().parent)]
    selected=[]
    for mode in MODES:
        candidates=[s for s in specs if s['label']==mode and s['arrival']==a.arrival and s['repeat']==0 and s['traffic']=='mixed']
        assert len(candidates)==1,(mode,'Expected exactly the declared r0 Mixed cell')
        selected.append(candidates[0])
    assert not a.output.exists(),'Use a new profile output directory'
    a.output.mkdir(parents=True);rows=[];hot=[];checks=[];inputs=[]
    report={'status':'PREPARED_NOT_COMPLETE','CPU_only':True,'new_GPU_calls':0,'counterfactual_serving_claim':False,
        'selection':'One declared r0 Mixed cell per mode; largest recorded actual planner wall, tie event order',
        'arrival':a.arrival,'max_decisions_per_cell':a.max_decisions,
        'timing_scope':'Replay only choose_closed_loop; original timer also includes context build and observation logging',
        'instrumentation_scope':'cProfile perturbs CPU time. Ordinary replay precedes profiled replay; warm shared function caches may differ from original run',
        'runtime_commit':manifest['code_commit'],'source_manifest_sha256':sha(a.source_manifest),
        'script_sha256':sha(Path(__file__)),'audit_helper_sha256':sha(Path(__file__).with_name('audit_closed_helpers_v2.py')),
        'safety_audit_sha256':sha(audit_dir/'SUMMARY.json'),'python':sys.version,'platform':platform.platform()}
    try:
        for s in selected:
            C=a.root/a.stage/name(s)
            for fn in ('config.json','result.json','events.jsonl','worker_records.jsonl','initial_states.json','sessions.json'):
                p=C/fn;inputs.append({'cell':C.name,'file':fn,'bytes':p.stat().st_size,'sha256':sha(p)})
            r,h,c=replay_cell(C,a.output,a.max_decisions);rows.extend(r);hot.extend(h);checks.append(c)
        report.update(status='PASS_EXACT_BOUNDED_CPU_REPLAY',cells=checks,profiled_decisions=len(rows))
    except Exception as e:
        report.update(status='FAILED_REPLAY_NO_TIMING_CONCLUSION',error=repr(e),cells=checks)
        raise
    finally:
        csvsave(a.output/'SNAPSHOT_REPLAY.csv',rows);csvsave(a.output/'HOTSPOTS.csv',hot)
        save(a.output/'INPUT_MANIFEST.json',inputs);save(a.output/'SUMMARY.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
