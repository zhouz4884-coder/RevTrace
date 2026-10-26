"""Retrospective opportunities on recorded host/Consumer cuts, NO GPU claims."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import deepcopy
import sys,json,time,hashlib,csv,argparse,bisect
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
BASE=B/'results/revtrace/dependability_20261025/ck5_v6'
R=B/'projects/revtrace_dependability_20261025/ck5_v6/runtime'
sys.path.insert(0,str(R/'src'))
from revtrace.envelope_display import EnvelopeView
from revtrace.dgft import digest_tokens
def read(p):return json.loads(p.read_text())
def rows(p):
    raw=p.read_bytes().splitlines(keepends=True);out=[]
    for i,line in enumerate(raw):
        try:out.append(json.loads(line))
        except (json.JSONDecodeError,UnicodeDecodeError):assert i==len(raw)-1 and not line.endswith(b'\n')
    return out
def identity(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def choose(view,s,nodes,floor):
    # Same compatibility implementation and proof pool, no future root oracle.
    eligible=[n for n in nodes if n['audio_end_sample']>s['F'] and n.get('display_revision',0)>floor
        and n.get('contract_epoch')==s.get('epoch') and n.get('contract_digest')==view.contract
        and view._compatible(s,n,s.get('Psha'))]
    return max(eligible,key=lambda n:(n['audio_end_sample'],n.get('display_revision',0),n['job_id']),default=None)
def scan_attempt(D,stage,cell):
    cfg=read(D/'config.json');sessions=read(D/'sessions.json');e=rows(D/'events.jsonl')
    actual_path=D/'consumer.jsonl'
    if not actual_path.exists():actual_path=D/'consumer-live.jsonl'
    if not actual_path.exists():return dict(attempt=str(D),status='CENSORED_NO_ACTUAL_CONSUMER_TRACE',stage=stage),[],[]
    actual=rows(actual_path);lookup=defaultdict(list)
    for r in actual:lookup[r['source_kind'],r['session_id'],r['server_time']].append(r)
    wr=rows(D/'worker_records.jsonl') if (D/'worker_records.jsonl').exists() else []
    worker={r['job']['job_id']:r for r in wr};publications=[r for r in e if r['kind']=='display']
    rate=cfg.get('sample_rate',16000);fine=round(cfg.get('fine_seconds',2)*rate)
    v=EnvelopeView(policy='two_lane',fine_samples=fine,strict_bound=True)
    origins={s['session_id']:s['offset'] for s in sessions};duration={s['session_id']:s['duration'] for s in sessions}
    floor=defaultdict(int);ops=[];host_ops=[];checked=0;canonicals=0;queries=[];owner_base=None;permissive=[]
    for event in e:
        # A SIGKILL can leave more owner events than actually flushed consumer
        # applications. Only replay the observed FIFO prefix, never that tail.
        if actual and checked==len(actual):break
        kind=event['kind']
        if kind=='run-start':owner_base=event['t0_perf'];floor.clear()
        if kind=='view-mode' and event['mode'] in ['CERTIFIED-ONLY','RECOVERY']:
            floor[event['session_id']]=max(floor[event['session_id']],event['display_revision'])
        k=(kind,event.get('session_id'),event.get('displayed',event.get('time')))
        matches=lookup.get(k,[]);observed=matches[0]['observed_perf'] if matches else None
        row=v.consume(event,observed)
        if row is None:continue
        assert matches,(D,k,'native replay produced unobserved row')
        a=matches.pop(0);checked+=1
        for key in ['canonical_version','certified_frontier','valid_visible_frontier','visible_text']:
            assert row[key]==a[key],(D,key,'native replay disagrees with actual Consumer')
        if kind!='canonical-display' or not row['canonical_version']:continue
        canonicals+=1;sid=row['session_id'];s=v.states[sid];mode=v.modes.get(sid,'NORMAL')
        if mode in ['CERTIFIED-ONLY','RECOVERY']:continue
        # Main cut: candidates already admitted to the actual consumer FIFO.
        before=time.perf_counter_ns();selected=choose(v,s,list(s['nodes'].values()),floor[sid]);queries.append((time.perf_counter_ns()-before)/1e6)
        F=selected['audio_end_sample'] if selected else s['F'];old=row['valid_visible_frontier']
        assert F>=old,'complete scan cannot lose a currently compatible tentative'
        if F>old:
            w=worker.get(selected['job_id']);assert w is not None,'candidate lacks recorded actual worker result'
            host_received=w['result']['received_perf'];assert host_received<=a['consumer_received_perf']
            assert selected['output_projection_sha256']==digest_tokens(w['result']['state_tokens'])
            origin=cfg.get('episode_origin_perf',owner_base)
            deadlines=[]
            for target in range(((old//fine)+1)*fine,F+1,fine):
                release=origin+origins[sid]+target/rate
                deadlines.append(dict(target=target,release=release,display_deadline=release+2,original_apply_before_display_deadline=observed<=release+2))
            ops.append(dict(attempt=str(D),stage=stage,source_id=w['job']['source_id'],session_id=sid,
                canonical_version=s['version'],canonical_frontier=s['F'],actual_frontier=old,oracle_frontier=F,
                extra_audio_seconds=(F-old)/rate,candidate_job=selected['job_id'],candidate_branch=selected.get('branch_generation'),
                host_received=host_received,actual_consumer_cut=observed,candidate_age_seconds=observed-host_received,
                current_owner=owner_base,mode=mode,withdrawal_revision_floor=floor[sid],deadlines=deadlines,
                original_clock_remaining_display_opportunities=sum(x['original_apply_before_display_deadline'] for x in deadlines),
                text_sha256=hashlib.sha256(selected['text'].encode()).hexdigest(),
                quality='partial-prefix WER not inferred without text/audio alignment; actual source and selected text retained',
                actual_candidate_text=selected['text'],evidence_tier='retrospective already-applied-publication opportunity, not real new enqueue/apply performance'))
        loose=choose(v,s,list(s['nodes'].values()),-2)
        LF=loose['audio_end_sample'] if loose else s['F']
        if LF>old:permissive.append(dict(session_id=sid,canonical_version=s['version'],actual=old,loose_frontier=LF,
            candidate_job=loose['job_id'],cut=observed,scope='temporary-mode-only interpretation; no invented irreversible withdrawal TTL'))
        # Host/published upper-bound cut. Queued-but-unapplied items require a new
        # registry interface; never count them as the existing Consumer's win.
        extra=[]
        for n in publications:
            if n['session_id']!=sid or n.get('contract_epoch')!=s.get('epoch'):continue
            w=worker.get(n['job_id'])
            if w is None or w['result'].get('received_perf',float('inf'))>observed:continue
            if owner_base+n['time']>observed:continue
            extra.append(n)
        proof=deepcopy(s);proof['nodes'].update({n['job_id']:n for n in extra})
        upper=choose(v,proof,list(proof['nodes'].values()),floor[sid]);UF=upper['audio_end_sample'] if upper else s['F']
        if UF>max(F,old):host_ops.append(dict(attempt=str(D),stage=stage,session_id=sid,canonical_version=s['version'],
            actual=old,consumer_known=F,host_published_upper_bound=UF,job=upper['job_id'],cut=observed,
            scope='requires host registry delivery; queued publication not yet applied; not a measured service benefit'))
    assert checked==len(actual),'unreplayed observed consumer rows'
    # All owner-validated returned private rows, including never-published rows.
    # This is a NEW registry/reauthorization upper bound, not the deployed view.
    cuts=defaultdict(list)
    for a in actual:cuts[a['session_id']].append(a)
    rendered={r['job_id']:owner_base+r['time'] for r in e if r['kind']=='render-checked'}
    host=[]
    for r in wr:
        j=r['job'];z=r['result']
        if j['role']!='proposal' or 'text_binding' not in z or 'received_perf' not in z:continue
        ctx=z.get('execution_context_audit',{})
        if ctx.get('fault_override') or ctx.get('executed_prompt_tokens',j['prompt_tokens'])!=j['prompt_tokens']:continue
        if ctx.get('actual_audio_sha256',j['prefix_audio_sha256'])!=j['prefix_audio_sha256']:continue
        ready=max(z['received_perf'],rendered.get(j['job_id'],owner_base+r['time']),owner_base+r['time'])
        n=dict(job_id=j['job_id'],session_id=j['session_id'],audio_end_sample=j['audio_end_sample'],text=z['text'],
            chunk_id=j['chunk_id'],end_window=j['end_window'],branch_generation=j.get('branch_generation'),
            input_projection_sha256=digest_tokens(j['prompt_tokens']),output_projection_sha256=digest_tokens(z['state_tokens']),
            contract_epoch=j['contract_epoch'],contract_digest=j['contract_digest'],display_revision=-1,
            host_verified_ready=ready,was_published=any(p['job_id']==j['job_id'] for p in publications))
        host.append(n)
    host.sort(key=lambda n:n['host_verified_ready']);quarantine=[];pool=defaultdict(dict)
    timeline_events=[(n['host_verified_ready'],0,n) for n in host]
    for a in actual:
        if a['source_kind']=='canonical-display':timeline_events.append((a.get('consumer_received_perf',a['observed_perf']),1,a))
    timeline_events.sort(key=lambda x:(x[0],x[1]))
    for available,kind,payload in timeline_events:
        if kind==0:
            n=payload;sid=n['session_id'];pool[sid][n['job_id']]=n
            timeline=cuts[sid];ts=[r['observed_perf'] for r in timeline];ix=bisect.bisect_right(ts,available)-1
            if ix<0:continue
            a=timeline[ix];cut=available;cut_kind='host-result-registration'
        else:
            a=payload;sid=a['session_id'];timeline=cuts[sid];cut=a['observed_perf'];cut_kind='canonical-application-plan'
        if a['canonical_version']==0 or a.get('envelope_mode') in ['CERTIFIED-ONLY','RECOVERY']:continue
        s=dict(version=a['canonical_version'],F=a['certified_frontier'],Psha=a.get('certified_P_sha256'),epoch=a['canonical_epoch'],nodes=pool[sid])
        candidate=choose(v,s,list(pool[sid].values()),-2)
        if candidate is None or candidate['was_published'] or candidate['audio_end_sample']<=a['valid_visible_frontier']:continue
        # Same candidate can be exposed at multiple subsequent receive cuts;
        # retain every cut and expose unique IDs separately in aggregation.
        release_origin=cfg.get('episode_origin_perf',owner_base)+origins[sid];newfront=[]
        for q in range((a['valid_visible_frontier']//fine+1)*fine,candidate['audio_end_sample']+1,fine):
            prior=[r['observed_perf'] for r in timeline if r['observed_perf']<=cut and r['valid_visible_frontier']>=q]
            commits=[r['observed_perf'] for r in timeline if r['certified_frontier']>=q]
            deadline=release_origin+q/rate+2
            newfront.append(dict(frontier=q,already_had_legal_first_view=bool(prior),deadline=deadline,
                zero_extra_cost_cut_before_D=cut<=deadline,original_commit_before_C=bool(commits) and min(commits)<=release_origin+q/rate+8))
        quarantine.append(dict(attempt=str(D),stage=stage,session_id=sid,source_id=worker[candidate['job_id']]['job']['source_id'],
            job=candidate['job_id'],host_availability_cut=available,zero_extra_cost_apply_cut=cut,cut_kind=cut_kind,root_frontier=s['F'],root_P=s['Psha'],root_version=s['version'],
            actual_visible=a['valid_visible_frontier'],candidate_frontier=candidate['audio_end_sample'],
            extra_audio_seconds=(candidate['audio_end_sample']-a['valid_visible_frontier'])/rate,frontiers=newfront,
            scope='unpublished host-result reauthorization upper bound only; no new actual application, no future/fault label used by selector'))
    return dict(attempt=str(D),stage=stage,status='PASS_NATIVE_CONSUMER_REPLAY',actual_rows_checked=checked,
        canonical_updates=canonicals,opportunities=len(ops),host_only_upper_bound_opportunities=len(host_ops),
        config=dict(rho=cfg.get('rho'),proposal_barrier=cfg.get('proposal_barrier'),adapter=cfg.get('model_adapter','qwen')),
        controlled=stage not in ['normal','formal_normal'],cell=cell,trace_identity=[identity(p) for p in [D/'events.jsonl',actual_path,D/'worker_records.jsonl',D/'config.json',D/'sessions.json'] if p.exists()],
        query_ms=queries,permissive_consumer_opportunities=permissive,quarantine_opportunities=quarantine,
        registered_host_private_rows=len(host)),ops,host_ops
def main():
    global BASE
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--study',choices=['ck5','n5'],required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if a.study=='n5':BASE=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
    summaries=[];op=[];upper=[]
    try:
        stages=['normal','fault','boundary','post_sync','boundary_pilot','post_sync_pilot'] if a.study=='ck5' else ['formal_normal','formal_fault','recovery_development']
        for stage in stages:
            done=read(BASE/stage/'SUMMARY.json');freeze=read(BASE/stage/'FREEZE.json')
            for name,cell in zip(done['completed'],freeze['cells']):
                for D in sorted((BASE/stage/name).glob('attempt[01]')):
                    if not (D/'config.json').exists():continue
                    r,o,u=scan_attempt(D,stage,cell);summaries.append(r);op+=o;upper+=u
        result=dict(status='COMPLETE_RETROSPECTIVE_NATIVE_SELECTION_AND_QUARANTINE_SCAN',study=a.study,attempts=summaries,
            opportunities=op,host_only_upper_bounds=upper,
            counts=dict(attempts=len(summaries),canonical_updates=sum(r.get('canonical_updates',0) for r in summaries),
                consumer_known_opportunities=len(op),host_only_upper_bounds=len(upper),
                permissive_consumer_cuts=sum(len(r.get('permissive_consumer_opportunities',[])) for r in summaries),
                quarantine_reauthorization_cuts=sum(len(r.get('quarantine_opportunities',[])) for r in summaries),
                registered_host_private_rows=sum(r.get('registered_host_private_rows',0) for r in summaries)),
            not_claimed='new GPU/service execution, natural population rate, improved whole Goodput, partial WER or independent sources per row')
        (a.output/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
    except BaseException as exc:
        import traceback
        (a.output/'STOP.json').write_text(json.dumps(dict(error=traceback.format_exc(),completed=summaries),indent=2)+'\n');raise
if __name__=='__main__':main()
