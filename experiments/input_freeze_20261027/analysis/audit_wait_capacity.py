"""Actual timing/visibility audit; read-only remote, no production admission code."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,hashlib,importlib.util,json,statistics


def q(xs,p):
    if not xs:return None
    xs=sorted(xs);z=(len(xs)-1)*p;i=int(z)
    return xs[i] if i==len(xs)-1 else xs[i]+(xs[i+1]-xs[i])*(z-i)


def stats(xs):
    return dict(n=len(xs),sum=sum(xs),p50=q(xs,.5),p95=q(xs,.95),p99=q(xs,.99),maximum=max(xs) if xs else None)


def overlap(a,b,intervals):
    cuts=sorted((max(a,x),min(b,y)) for x,y in intervals if min(b,y)>max(a,x))
    total=0;last=None
    for x,y in cuts:
        if last is None or x>=last:total+=y-x;last=y
        elif y>last:total+=y-last;last=y
    return total


def main():
    p=argparse.ArgumentParser();p.add_argument('--remote',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    sp=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);client=m.ssh_client();sf=client.open_sftp();sf.get_channel().settimeout(45)
    hashes=[]
    def load(path,lines=False):
        raw=sf.open(a.remote+'/'+path).read();hashes.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        return [json.loads(x) for x in raw.decode().splitlines() if x.strip()] if lines else json.loads(raw)
    rows=[];baseline=None;baselinecanon=None
    try:
        summary=load('SUMMARY.json');freeze=load('FREEZE.json')
        assert len(summary['completed'])==summary['expected']==6
        for cell in summary['completed']:
            pre=cell+'/attempt0/'
            es=load(pre+'events.jsonl',True);wr=load(pre+'worker_records.jsonl',True)
            batches=load(pre+'worker_batch_accounting.jsonl',True);consumer=load(pre+'consumer.jsonl',True)
            cfg=load(pre+'config.json');specs=load(pre+'sessions.json');res=load(pre+'result.json')
            t0=next(x['t0_perf'] for x in es if x['kind']=='run-start');origin=cfg['episode_origin_perf']
            sid_specs={x['session_id']:x for x in specs};records={r['job']['job_id']:r for r in wr}
            jobs={(r['job']['role'],r['job']['session_id'],r['job']['audio_end_sample']):r for r in wr}
            commits={e['job_id']:e for e in es if e['kind']=='commit'}
            versions={(e['session_id'],e['version']):e for e in commits.values()}
            actualcanon={(e['session_id'],e['audio_end_sample']):dict(parent=e['parent'],Z=e['segment_tokens'],P=e['next_prompt_tokens']) for e in commits.values()}
            canonicalchanges=[]
            if baselinecanon is None:baselinecanon=actualcanon
            else:
                for key,item in actualcanon.items():
                    if baselinecanon.get(key)!=item:canonicalchanges.append(dict(session_id=key[0],frontier=key[1]))
            inputmap={}
            for key,r in jobs.items():
                j,v=r['job'],r['result'];mi=v['model_input_audit']
                inputmap[key]=dict(P=j['prompt_tokens'],chunk=j['chunk_id'],root=j['audio_start_sample'],parent=j['parent'],
                    input_ids=mi.get('unpadded_input_ids'),features=mi.get('row_features'),batch=mi.get('batch_tensors'),
                    Z=v['token_ids'],output_P=v['state_tokens'],text=v['text'],EOS=v['terminated_by_eos'],cap=v['hit_token_limit'])
            if baseline is None:baseline=inputmap
            cross={}
            for role in ('proposal','authority'):
                keys=[k for k in inputmap if k[0]==role and k in baseline]
                cross[role]=dict(common=len(keys),missing_vs_immediate=sum(k[0]==role and k not in inputmap for k in baseline),
                    new_vs_immediate=sum(k[0]==role and k not in baseline for k in inputmap),
                    logical_P_changed=sum(inputmap[k]['P']!=baseline[k]['P'] for k in keys),
                    chunk_changed=sum(inputmap[k]['chunk']!=baseline[k]['chunk'] for k in keys),
                    root_or_parent_changed=sum((inputmap[k]['root'],inputmap[k]['parent'])!=(baseline[k]['root'],baseline[k]['parent']) for k in keys),
                    processed_row_changed=sum((inputmap[k]['input_ids'],inputmap[k]['features'])!=(baseline[k]['input_ids'],baseline[k]['features']) for k in keys),
                    physical_batch_changed=sum(inputmap[k]['batch']!=baseline[k]['batch'] for k in keys),
                    outputs_changed=sum(any(inputmap[k][x]!=baseline[k][x] for x in ['Z','output_P','text','EOS','cap']) for k in keys))
            byworker=defaultdict(list);rolecost=defaultdict(list);modelcost=defaultdict(list);counts=defaultdict(Counter);authority_intervals=[];physical_fail=[]
            for b in batches:
                role=records[b['job_ids'][0]]['job']['role'];byworker[b['worker']].append(b)
                rolecost[role].append(b['batch_result_complete_perf']-b['worker_started_perf'])
                modelcost[role].extend(x['completed_perf']-x['started_perf'] for x in b['phases'])
                counts[role][len(b['job_ids'])]+=1
                if role=='authority':authority_intervals.append((b['worker_started_perf'],b['batch_drained_perf']))
            for worker,bs in byworker.items():
                bs.sort(key=lambda b:b['worker_started_perf'])
                for prev,nextb in zip(bs,bs[1:]):
                    if prev['batch_drained_perf']>nextb['worker_started_perf']+1e-7:physical_fail.append(worker)
            cps=[];component=defaultdict(list)
            for r in wr:
                j,v=r['job'],r['result']
                if j['role']!='authority':continue
                sid=j['session_id'];F=j['audio_end_sample'];release=j['audio_ready_perf']
                parent_install=t0+versions[sid,j['parent']]['installed'] if j['parent'] else origin
                ack=min(t0+e['time'] for e in es if e['kind']=='input-ack' and e['session_id']==sid and e['to_sample']>=F)
                eligible=max(release,parent_install,ack)
                enqueue=j['enqueue_perf'];started=v['started_perf'];received=v['received_perf'];installed=t0+commits[j['job_id']]['installed']
                applied=min(e['observed_perf'] for e in consumer if e['session_id']==sid and e['certified_frontier']>=F)
                parts=dict(prerequisite_wait=eligible-release,owner_queue=enqueue-eligible,IPC_to_worker=started-enqueue,
                    worker_to_host_row=received-started,host_row_to_installed=installed-received,installed_to_consumer=applied-installed)
                assert all(x>=-1e-5 for x in parts.values()),parts
                assert abs(sum(parts.values())-(applied-release))<1e-5
                busy=overlap(eligible,enqueue,authority_intervals)
                for k,val in parts.items():component[k].append(val)
                cps.append(dict(session_id=sid,end=F,release=release-origin,canonical_parent=j['parent'],
                    parent_available=parent_install-origin,accepted_input_available=ack-origin,
                    prerequisite_binder='parent' if parent_install>=max(release,ack) else 'input' if ack>=release else 'release',
                    queue_authority_physically_busy_seconds=busy,queue_other_seconds=max(0,enqueue-eligible-busy),
                    commit_consumer_latency=applied-release,**parts))
            waits=[e for e in es if e['kind']=='dispatch-wait-decision' and e['decision']=='wait']
            releases={(e['session_id'],e['window']):e for e in es if e['kind']=='dispatch-wait-release'}
            outcomes={(e['session_id'],e['window']):e for e in es if e['kind']=='dispatch-wait-input-outcome'}
            feedback=[e for e in es if e['kind']=='dispatch-wait-feedback'];waitrows=[]
            for e in waits:
                key=e['session_id'],e['window'];r=releases.get(key);o=outcomes.get(key)
                pending=e['pending_authority'];actual=None
                if pending:actual=t0+commits[pending['job_id']]['installed']-e['observed_perf']
                waitrows.append(dict(session_id=key[0],window=key[1],reason=e['reason'],
                    budget=e['wait_budget_seconds'],gross_blocked=None if r is None else r['waited_seconds'],
                    suppression=None if r is None else r.get('policy_suppression_seconds'),
                    owner_lag=None if r is None else r.get('owner_observation_lag_seconds'),
                    closed_while_GPU_busy=None if r is None else not r.get('proposal_worker_available',True),
                    release_reason=None if r is None else r['reason'],covered=None if r is None else r['target_now_covered'],
                    P_changed=None if o is None else o['declared_P_changed'],
                    root_changed=None if o is None else o['root_frontier_changed'],
                    chunk_changed=None if o is None else o['chunk_changed'],
                    post_release_queue=None if o is None else o['post_release_to_enqueue_seconds'],
                    eta=None if pending is None else pending['remaining_estimate_seconds'],actual_to_install=actual))
            fronts=[];categories=Counter();D=[];C=[]
            for sp in specs:
                sid=sp['session_id'];total=round(sp['duration']*cfg['sample_rate']);prev=0
                views=[e for e in consumer if e['session_id']==sid]
                for F in list(range(32000,total,32000))+[total]:
                    release=origin+sp['offset']+F/cfg['sample_rate'];weight=(F-prev)/cfg['sample_rate'];prev=F
                    first=min((e for e in views if e['valid_visible_frontier']>=F),key=lambda e:e['observed_perf'])
                    cert=min((e for e in views if e['certified_frontier']>=F),key=lambda e:e['observed_perf'])
                    dl,cl=first['observed_perf']-release,cert['observed_perf']-release;D.append(dl);C.append(cl)
                    own=jobs.get(('proposal',sid,F))
                    own_late=(own['result']['received_perf']>release+2) if own else None
                    displays=[e for e in es if e['kind']=='display' and e['session_id']==sid and e['audio_end_sample']==F]
                    badviews=[]
                    for pub in displays:
                        v=[x for x in views if x['source_kind']=='display' and abs(x['server_time']-pub['displayed'])<1e-7]
                        badviews.extend(x for x in v if x['valid_visible_frontier']<F)
                    if dl<=2:cat='timely_legal_visible'
                    elif own is None:cat='miss_without_own_private_dispatch'
                    elif own_late:cat='miss_own_private_received_late'
                    elif badviews:cat='miss_timely_private_but_consumer_no_legal_coverage'
                    else:cat='miss_other_publication_or_coverage_path'
                    categories[cat]+=1
                    fronts.append(dict(session_id=sid,frontier=F,audio_seconds=weight,D=dl,C=cl,category=cat,
                        first_visible_source=first['source_kind'],own_private_dispatched=bool(own),own_private_late=own_late,
                        own_published_but_not_legally_visible=len(badviews),
                        first_visible_certified=(first['certified_frontier']>=F)))
            invalid_views=[e for e in consumer if e.get('source_kind')=='display' and e.get('tentative_invalidated')]
            obsoletes=[e for e in es if e['kind']=='proposal-obsolete']
            skips=[e for e in es if e['kind']=='proposal-skip'];expired=[e for e in es if e['kind']=='private-deadline-retired']
            last_release=max(origin+s['offset']+s['duration'] for s in specs)
            first_release=min(origin+s['offset']+min(cfg['fine_seconds'],s['duration']) for s in specs)
            output=dict(policy=cfg['dispatch_wait']['policy'],offered_frontiers=len(fronts),
                actual_private_jobs=sum(r['job']['role']=='proposal' for r in wr),authority_jobs=len(cps),
                active_waits=len(waits),wait_details=waitrows,
                wait_actual_input_outcomes=len(outcomes),wait_actual_P_changes=sum(o['declared_P_changed'] is True for o in outcomes.values()),
                wait_root_or_chunk_changes=sum(o['root_frontier_changed'] or o['chunk_changed'] for o in outcomes.values()),
                waits_covered_without_own_job=sum(r.get('covered') is True and (r['session_id'],r['window']) not in outcomes for r in waitrows),
                feedback_count=len(feedback),feedback_timely=sum(e['actual_D2_pass'] for e in feedback),
                source_policies_are_observational=True,
                physical_lease_seconds={r:stats(x) for r,x in rolecost.items()},
                actual_model_phase_seconds={r:stats(x) for r,x in modelcost.items()},
                physical_batch_sizes={r:dict(x) for r,x in counts.items()},
                arrival_interval_seconds=last_release-first_release,
                authority_lease_demand_divided_by_arrival_interval=sum(rolecost['authority'])/(last_release-first_release),
                authority_path_component_stats={k:stats(v) for k,v in component.items()},
                authority_queue_physically_busy=stats([r['queue_authority_physically_busy_seconds'] for r in cps]),
                authority_queue_other=stats([r['queue_other_seconds'] for r in cps]),
                authority_critical_paths=cps,visible_frontiers=fronts,
                display_miss_categories=dict(categories),consumer_rejected_incompatible_private_views=len(invalid_views),
                obsolete_completions=len(obsoletes),canonical_cover_skips=len(skips),expired_unissued=len(expired),
                paid_obsolete_row_wall_diagnostic_not_lease_sum=sum(e['job_execution_seconds'] for e in obsoletes),
                actual_cap_rows=sum(r['result']['hit_token_limit'] for r in wr),
                proposal_generated_tokens=sum(r['result']['generated_tokens'] for r in wr if r['job']['role']=='proposal'),
                canonical_history_difference_count=len(canonicalchanges),canonical_history_differences=canonicalchanges,
                comparison_to_immediate=cross,consumer_D99=q(D,.99),consumer_C99=q(C,.99),
                physical_overlap_failures=physical_fail,
                note='Critical-path sums are per-row latency; never sum them as physical GPU work. Input changes across free runs are observations, not matched-input causal effects.')
            rows.append(output)
            print(json.dumps({k:v for k,v in output.items() if k not in ['wait_details','authority_critical_paths','visible_frontiers','canonical_history_differences']},indent=2),flush=True)
    finally:sf.close();client.close()
    report=dict(status='COMPLETE_SIX_ARM_CAPACITY_TRACE_AUDIT',remote=a.remote,source_commit=freeze['code_commit'],
        source_freeze=freeze,rows=rows,inputs=hashes,new_GPU_calls=0,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
