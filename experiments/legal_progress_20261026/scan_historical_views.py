"""Retrospective opportunities on recorded host/Consumer cuts, NO GPU claims."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import deepcopy
import sys,json,time,hashlib,csv,argparse
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
    floor=defaultdict(int);ops=[];host_ops=[];checked=0;canonicals=0;queries=[];owner_base=None
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
    return dict(attempt=str(D),stage=stage,status='PASS_NATIVE_CONSUMER_REPLAY',actual_rows_checked=checked,
        canonical_updates=canonicals,opportunities=len(ops),host_only_upper_bound_opportunities=len(host_ops),
        config=dict(rho=cfg.get('rho'),proposal_barrier=cfg.get('proposal_barrier'),adapter=cfg.get('model_adapter','qwen')),
        controlled=stage!='normal',cell=cell,trace_identity=[identity(D/'events.jsonl'),identity(actual_path)],
        query_ms=queries),ops,host_ops
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    summaries=[];op=[];upper=[]
    try:
        for stage in ['normal','fault','boundary','post_sync','boundary_pilot','post_sync_pilot']:
            done=read(BASE/stage/'SUMMARY.json');freeze=read(BASE/stage/'FREEZE.json')
            for name,cell in zip(done['completed'],freeze['cells']):
                for D in sorted((BASE/stage/name).glob('attempt[01]')):
                    if not (D/'config.json').exists():continue
                    r,o,u=scan_attempt(D,stage,cell);summaries.append(r);op+=o;upper+=u
        result=dict(status='COMPLETE_CK5_RETROSPECTIVE_NATIVE_SELECTION_SCAN',attempts=summaries,
            opportunities=op,host_only_upper_bounds=upper,
            counts=dict(attempts=len(summaries),canonical_updates=sum(r.get('canonical_updates',0) for r in summaries),
                consumer_known_opportunities=len(op),host_only_upper_bounds=len(upper)),
            not_claimed='new GPU/service execution, natural population rate, improved whole Goodput, partial WER or independent sources per row')
        (a.output/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
    except BaseException as exc:
        import traceback
        (a.output/'STOP.json').write_text(json.dumps(dict(error=traceback.format_exc(),completed=summaries),indent=2)+'\n');raise
if __name__=='__main__':main()
