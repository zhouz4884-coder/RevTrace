"""Independent completed-pilot audit; only SFTP reads, no production admit()."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,hashlib,importlib.util,json,math,statistics


def main():
    p=argparse.ArgumentParser();p.add_argument('--remote',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    client=helper.ssh_client();sftp=client.open_sftp();sftp.get_channel().settimeout(30)
    hashes=[]
    def data(rel,lines=False):
        raw=sftp.open(a.remote+'/'+rel).read()
        hashes.append(dict(path=rel,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        return [json.loads(x) for x in raw.decode().splitlines() if x.strip()] if lines else json.loads(raw)
    def qt(xs,q):
        if not xs:return None
        xs=sorted(xs);z=(len(xs)-1)*q;i=int(z)
        return xs[i] if i==len(xs)-1 else xs[i]+(xs[i+1]-xs[i])*(z-i)
    outputs=[];common={};base=None
    try:
        summary=data('SUMMARY.json');freeze=data('FREEZE.json');assert summary['status']=='COMPLETE_DEVELOPMENT_PILOT'
        assert summary['expected']==len(summary['completed'])==6
        for name in summary['completed']:
            d=name+'/attempt0/'
            es=data(d+'events.jsonl',True);rr=data(d+'worker_records.jsonl',True)
            account=data(d+'worker_batch_accounting.jsonl',True);vs=data(d+'consumer.jsonl',True)
            cfg=data(d+'config.json');specs=data(d+'sessions.json');initial=data(d+'initial_states.json')
            result=data(d+'result.json');t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
            origin=cfg['episode_origin_perf'];policy=cfg['dispatch_wait']['policy']
            fail=[];decisions=[e for e in es if e['kind']=='dispatch-wait-decision']
            waits=[e for e in decisions if e['decision']=='wait']
            releases={(e['session_id'],e['window']):e for e in es if e['kind']=='dispatch-wait-release'}
            records={x['job']['job_id']:x for x in rr};assert len(records)==len(rr)
            jobkeys={(x['job']['role'],x['job']['session_id'],x['job']['end_window']):x for x in rr}
            assert len(jobkeys)==len(rr)
            bysid={s['session_id']:s for s in specs}
            canonical={sid:[] for sid in bysid};versions={sid:0 for sid in bysid};frontiers={sid:0 for sid in bysid}
            private={sid:[] for sid in bysid};before_wait={}
            obsoletes={e['job_id'] for e in es if e['kind']=='proposal-obsolete'}
            commits={e['job_id']:e for e in es if e['kind']=='commit'}
            dec_ids=set()
            for e in es:
                if e['kind']=='enqueue' and e['role']=='proposal':private[e['session_id']]=records[e['job_id']]['job']['prompt_tokens']
                if e['kind']=='executor-complete' and e['role']=='proposal' and e['job_id'] not in obsoletes:
                    private[e['session_id']]=records[e['job_id']]['result']['state_tokens']
                if e['kind']=='commit':
                    canonical[e['session_id']]=e['next_prompt_tokens'];versions[e['session_id']]=e['version'];frontiers[e['session_id']]=e['audio_end_sample']
                if e['kind']=='private-generation-retired':private[e['session_id']]=canonical[e['session_id']]
                if e['kind']=='dispatch-wait-decision':
                    sid,w=e['session_id'],e['window'];key=(sid,w)
                    if key in dec_ids:fail.append('duplicate wait decision '+str(key))
                    dec_ids.add(key);s=bysid[sid]
                    ready=origin+s['offset']+min(cfg['fine_seconds']*w,s['duration'])
                    if abs(ready-e['original_audio_ready_perf'])>1e-7:fail.append('changed original release')
                    if abs(ready+2-e['original_deadline_perf'])>1e-7:fail.append('changed D2')
                    if e['wait_until_perf']>e['original_deadline_perf']+1e-7 and e['decision']=='wait':fail.append('wait budget exceeds original deadline')
                    if e['canonical_parent']!=versions[sid] or e['canonical_frontier']!=frontiers[sid]:fail.append('nonobserved canonical state')
                    before_wait[key]=list(private[sid])
                    pending=e['pending_authority']
                    if pending:
                        j=records[pending['job_id']]['job'];ct=t0+commits[j['job_id']]['installed']
                        if not (j['enqueue_perf']<=e['observed_perf']<ct):fail.append('nonpending authority used')
                        if (j['session_id']!=sid or j['parent']!=versions[sid]):fail.append('wrong pending authority identity')
                if e['kind']=='dispatch-wait-cohort':
                    eligible={(r['session_id'],r['window']) for r in e['eligible']}
                    released={(r['session_id'],r['window']) for r in e['released']}
                    held={(r['session_id'],r['window']) for r in e['held']}
                    if released & held or (released|held)!=eligible:fail.append('cohort partition mismatch')
            paid=defaultdict(float);batchsizes=defaultdict(Counter);leases=defaultdict(list)
            for b in account:
                role=records[b['job_ids'][0]]['job']['role']
                paid[role]+=b['batch_result_complete_perf']-b['worker_started_perf']
                batchsizes[role][len(b['job_ids'])]+=1
                leases[b['worker']].append((b['worker_started_perf'],b['batch_drained_perf'],b['batch_id']))
            for worker,rs in leases.items():
                rs.sort()
                for previous,current in zip(rs,rs[1:]):
                    if previous[1]>current[0]+1e-7:fail.append('overlapping physical lease '+worker)
            details=[]
            for e in waits:
                key=(e['session_id'],e['window']);rel=releases.get(key)
                pending=e['pending_authority'];new=jobkeys.get(('proposal',*key))
                now=e['observed_perf'];pred=pending['remaining_estimate_seconds'] if pending else None
                actual=t0+commits[pending['job_id']]['installed']-now if pending else None
                details.append(dict(sid=key[0],window=key[1],reason=e['reason'],
                    wait_budget=e['wait_budget_seconds'],wait_actual=rel['waited_seconds'] if rel else None,
                    release_reason=rel['reason'] if rel else None,
                    eta=pred,actual_time_to_install=actual,
                    canonical_P_changed=rel['canonical_projection_changed'] if rel else None,
                    actual_next_declared_P_changed=(new['job']['prompt_tokens']!=before_wait[key]) if new else None,
                    job_created_after_wait=bool(new),
                    new_job_enqueue_after_wait=(new['job']['enqueue_perf']>=e['wait_until_perf'] or
                       (rel is not None and new['job']['enqueue_perf']>=now+rel['waited_seconds']-1e-6)) if new else None))
                if new and new['job']['enqueue_perf']<now:fail.append('job frozen before wait')
            deltas={};inputmap={}
            for key,x in jobkeys.items():
                j,r=x['job'],x['result'];mi=r['model_input_audit']
                inputmap[key]=dict(P=j['prompt_tokens'],chunk=j['chunk_id'],parent=j['parent'],
                    start=j['audio_start_sample'],end=j['audio_end_sample'],
                    ids=mi.get('unpadded_input_ids'),features=mi.get('row_features'),
                    batch_tensors=mi.get('batch_tensors'),Z=r['token_ids'],output_P=r['state_tokens'],text=r['text'],
                    eos=r['terminated_by_eos'],cap=r['hit_token_limit'])
            if base is None:base=inputmap
            for role in ['proposal','authority']:
                keys=[k for k in inputmap if k[0]==role and k in base]
                deltas[role]=dict(common=len(keys),P_changed=sum(inputmap[k]['P']!=base[k]['P'] for k in keys),
                    model_row_ids_or_features_changed=sum((inputmap[k]['ids'],inputmap[k]['features'])!=(base[k]['ids'],base[k]['features']) for k in keys),
                    batch_tensor_layout_changed=sum(inputmap[k]['batch_tensors']!=base[k]['batch_tensors'] for k in keys),
                    output_Z_P_text_stop_changed=sum(any(inputmap[k][f]!=base[k][f] for f in ['Z','output_P','text','eos','cap']) for k in keys))
            dlat=[];clat=[];good=0.;offered=0;unfinished=0;coverage=0
            for s in specs:
                sid=s['session_id'];total=round(s['duration']*cfg['sample_rate']);prev=0
                views=[v for v in vs if v['session_id']==sid]
                for F in list(range(32000,total,32000))+[total]:
                    release=origin+s['offset']+F/cfg['sample_rate'];weight=(F-prev)/cfg['sample_rate'];prev=F;offered+=weight
                    ds=[v['observed_perf']-release for v in views if v['valid_visible_frontier']>=F]
                    cs=[v['observed_perf']-release for v in views if v['certified_frontier']>=F]
                    if not ds or not cs:unfinished+=1;continue
                    dl,cl=min(ds),min(cs);dlat.append(dl);clat.append(cl);coverage+=weight
                    if dl<=2 and cl<=8:good+=weight
            wall=max(v['observed_perf'] for v in vs)-origin
            outputs.append(dict(policy=policy,actual_jobs=len(rr),actual_private_jobs=len([x for x in rr if x['job']['role']=='proposal']),
                decisions=len(decisions),active_waits=len(waits),wait_details=details,
                cohort_records=sum(e['kind']=='dispatch-wait-cohort' for e in es),
                proposal_skip_count=sum(e['kind']=='proposal-skip' for e in es),
                expired_private=sum(e['kind']=='private-deadline-retired' for e in es),
                actual_proposal_tokens=sum(x['result']['generated_tokens'] for x in rr if x['job']['role']=='proposal'),
                actual_caps=sum(x['result']['hit_token_limit'] for x in rr),
                paid_lease_seconds=dict(paid),batch_sizes={k:dict(v) for k,v in batchsizes.items()},
                immediate_pair_differences=deltas,offered_audio_seconds=offered,
                actual_certified_audio_seconds=coverage,unfinished_frontiers=unfinished,
                actual_dual_good_audio_seconds=good,consumer_wall_seconds=wall,
                consumer_display_p99=qt(dlat,.99),consumer_commit_p99=qt(clat,.99),
                checks=fail,notes='No runtime admit/step reused; source admissibility proof remains separate from these trace checks.'))
    finally:sftp.close();client.close()
    report=dict(status='COMPLETE_INDEPENDENT_SIX_ARM_TRACE_CHECK',source_commit=freeze['code_commit'],
        remote_path=a.remote,rows=outputs,inputs=hashes,
        scope='one development repeat,c4,sync,clean,raw_slack; no statistical or general performance claim',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))


if __name__=='__main__':main()
