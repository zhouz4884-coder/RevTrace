"""Independent observed P-chain, Consumer, immutable payload and metric audit.

Does not import production scheduling, retention or Consumer implementation.
Certificate/WAL replay and asset-backed rendering are separate checks.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,re,statistics

def read(p):return json.loads(p.read_text(encoding='utf8'))
def lines(p):return [json.loads(v) for v in p.read_text(encoding='utf8').splitlines() if v]
def digest(x):return hashlib.sha256(','.join(map(str,x)).encode('ascii')).hexdigest()
def edit(a,b):
    d=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        e=[i]
        for j,y in enumerate(b,1):e.append(min(e[-1]+1,d[j]+1,d[j-1]+(x!=y)))
        d=e
    return d[-1]
def quantile(xs,q):
    if not xs:return None
    xs=sorted(xs);x=(len(xs)-1)*q;i=int(x)
    return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(x-i)
def compatible(jid,F,P,jobs,results,nodes,fine):
    """Use full stored token tuples, not production hash-based traversal."""
    used=set()
    while True:
        if jid in used:return False
        used.add(jid);j=jobs[jid]
        if j['chunk_id']==round(F/fine) and tuple(j['prompt_tokens'])==P:return True
        options=[x for x in nodes if jobs[x]['end_window']==j['chunk_id'] and
            tuple(results[x]['state_tokens'])==tuple(j['prompt_tokens']) and
            jobs[x]['audio_end_sample']>=F and jobs[x]['audio_end_sample']<j['audio_end_sample'] and
            jobs[x].get('branch_generation')==j.get('branch_generation')]
        if len(options)!=1:return False
        jid=options[0]
        if jobs[jid]['audio_end_sample']==F:return tuple(results[jid]['state_tokens'])==P

def audit(C,refs):
    cfg=read(C/'config.json');res=read(C/'result.json');events=lines(C/'events.jsonl')
    sessions={r['session_id']:r for r in read(C/'sessions.json')};fine=cfg['fine_seconds']*16000
    records=lines(C/'worker_records.jsonl');jobs={r['job']['job_id']:r['job'] for r in records}
    results={r['job']['job_id']:r['result'] for r in records}
    enqueues={e['job_id']:e for e in events if e['kind']=='enqueue'}
    assert set(enqueues)==set(jobs)==set(results),'missing completed job in finished run'
    for jid,j in jobs.items():
        r=results[jid];a=r['execution_context_audit'];m=r['model_input_audit']
        assert not a['fault_override'] and a['executed_prompt_tokens']==j['prompt_tokens']
        assert a['actual_audio_sha256']==j['prefix_audio_sha256']==m['waveform_sha256']
        assert m['declared_prompt_tokens']==j['prompt_tokens'] and m['chunk_id']==j['chunk_id']
        assert m['max_new_tokens']==256 and m['do_sample'] is False
        assert r['runtime_digest']==j['runtime_digest']
        assert j['audio_start_sample']<j['audio_end_sample']
        assert j['audio_ready_perf']<=j['enqueue_perf']<=r['started_perf']<=r['model_started_perf']<=r['model_completed_perf']<=r['completed_perf']<=r['received_perf']
        assert r['terminated_by_eos']==(r['token_ids'][-1] in m['eos_token_ids'])
        assert len(r['token_ids'])<=256 and (r['terminated_by_eos'] or len(r['token_ids'])==256)
    captured={e['job_id']:e for e in events if e['kind']=='ipc-complete-captured'}
    delivered={e['job_id']:e for e in events if e['kind']=='ipc-complete-delivered'}
    if cfg['post_compute_order']:
        payloads=lines(C/'ipc_completed_payloads.jsonl');assert len(captured)==len(delivered)==len(payloads)==8
        for r in payloads:
            jid=r['job']['job_id'];raw=json.dumps(r['result'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            assert hashlib.sha256(raw).hexdigest()==captured[jid]['payload_sha256']==delivered[jid]['payload_sha256']
            actual=dict(results[jid]);actual.pop('received_perf');actual.pop('text_binding')
            assert actual==r['result'] and captured[jid]['physically_drained']
            assert r['result']['completed_perf']<=read(C/'provenance.json').get('unused',math.inf)
    consumer=lines(C/'consumer.jsonl');lookup={}
    for r in consumer:
        k=(r['session_id'],r['source_kind'],r['server_time']);assert k not in lookup;lookup[k]=r
    state={sid:{'F':0,'P':(),'version':0} for sid in sessions};nodes={sid:set() for sid in sessions}
    published={};generation={sid:0 for sid in sessions};view={};invalid_view=0;false_credit=0
    raw_stale=0;incompatible_pub=0;target_incompatible=0;fresh_rejections=0;frontiers=[];commits=[]
    first_raw={};first_legal={};commit_time={};seen_transactions=set();target_rows=[]
    for e in events:
        sid=e.get('session_id');kind=e['kind']
        if kind=='enqueue' and e['role']=='proposal':generation[sid]=e['branch_generation']
        if kind=='proposal-obsolete':fresh_rejections+=1
        if kind=='commit':
            s=state[sid];assert e['parent']==s['version'] and e['audio_start_sample']==s['F']
            assert (sid,e['segment_id']) not in seen_transactions;seen_transactions.add((sid,e['segment_id']))
            assert jobs[e['job_id']]['role']=='authority';assert e['next_prompt_tokens']==results[e['job_id']]['state_tokens']
            s.update(F=e['audio_end_sample'],P=tuple(e['next_prompt_tokens']),version=e['version'])
            for w in range(1,math.ceil(sessions[sid]['duration']/cfg['fine_seconds'])+1):
                F=min(round(w*fine),round(sessions[sid]['duration']*16000))
                if F<=s['F']:commit_time.setdefault((sid,F),e['installed'])
            commits.append(e)
        if kind not in ['display','canonical-display']:continue
        key=(sid,kind,e['displayed']);r=lookup.get(key);s=state[sid]
        if kind=='display':
            jid=e['job_id'];j=jobs[jid];nodes[sid].add(jid);published[jid]=e
            stale=j['audio_end_sample']<=s['F'] or j.get('branch_generation',0)!=generation[sid]
            iscompatible=compatible(jid,s['F'],s['P'],jobs,results,nodes[sid],fine)
            raw_stale+=int(stale);incompatible_pub+=int(not stale and not iscompatible)
            if jid in captured and not stale:target_incompatible+=int(not iscompatible)
            if jid in captured:target_rows.append({'job_id':jid,'session_id':sid,'birth_parent':j['parent'],
                'canonical_parent':s['version'],'target':j['audio_end_sample'],'F':s['F'],
                'covered_or_generation_stale':stale,'exact_chain_compatible':iscompatible,
                'actual_consumer_record':r is not None,'actual_visible_frontier':None if r is None else r['valid_visible_frontier']})
        if r is None:continue # Actual Consumer rejected without applying a view.
        assert r['certified_frontier']==s['F'] and r['canonical_version']==s['version']
        assert r['certified_text']==('' if not s['version'] else results[next(c['job_id'] for c in reversed(commits) if c['session_id']==sid)]['text'])
        assert not r['joined_suffix'] and r['observed']>=e['displayed']
        vf=r['valid_visible_frontier'];legal=True
        if vf>s['F']:
            options=[x for x in nodes[sid] if jobs[x]['audio_end_sample']==vf and results[x]['text']==r['visible_text']]
            legal=any(compatible(x,s['F'],s['P'],jobs,results,nodes[sid],fine) for x in options)
        if not legal:invalid_view+=1
        for w in range(1,math.ceil(sessions[sid]['duration']/cfg['fine_seconds'])+1):
            F=min(round(w*fine),round(sessions[sid]['duration']*16000));k=(sid,F)
            if F<=vf:
                first_raw.setdefault(k,r['observed'])
                if legal or F<=s['F']:first_legal.setdefault(k,r['observed'])
        view[sid]=r
    for sid,ss in sessions.items():
        prev=0
        for w in range(1,math.ceil(ss['duration']/cfg['fine_seconds'])+1):
            F=min(round(w*fine),round(ss['duration']*16000));key=(sid,F);ready=ss['offset']+F/16000
            raw=first_raw.get(key,math.inf)-ready;legal=first_legal.get(key,math.inf)-ready;commit=commit_time.get(key,math.inf)-ready
            credited=raw<=2 and commit<=8;good=legal<=2 and commit<=8
            false_credit+=int(credited and not good)
            frontiers.append({'session_id':sid,'frontier':F,'audio_seconds':(F-prev)/16000,
                'raw_display_latency':raw,'legal_display_latency':legal,'commit_latency':commit,
                'raw_dual_credit':credited,'legal_dual_credit':good});prev=F
    errors=words=0
    for row in res['final_states']:
        source=sessions[row['session_id']]['source_id'];ref=refs[source]['reference']
        a=re.findall(r"[a-z0-9']+",ref.lower());b=re.findall(r"[a-z0-9']+",row['text'].lower())
        errors+=edit(a,b);words+=len(a)
    wall=res['wall_seconds_including_arrival_and_drain']
    summary={'cell':C.name,'jobs':len(jobs),'commits':len(commits),'stale_publications':raw_stale,
        'incompatible_ahead_publications':incompatible_pub,'target_incompatible_ahead':target_incompatible,
        'illegal_actual_views':invalid_view,'false_dual_deadline_credits':false_credit,'freshness_rejections':fresh_rejections,
        'raw_goodput':sum(r['audio_seconds'] for r in frontiers if r['raw_dual_credit'])/wall,
        'legal_goodput':sum(r['audio_seconds'] for r in frontiers if r['legal_dual_credit'])/wall,
        'consumer_audio_rollbacks':sum(r['audio_rollback_samples']>0 for r in consumer),
        'consumer_erased_characters':sum(r['erased_characters'] for r in consumer),
        'legal_display_p99':quantile([r['legal_display_latency'] for r in frontiers],.99),
        'commit_p99':quantile([r['commit_latency'] for r in frontiers],.99),
        'WER_errors':errors,'WER_words':words,'WER_percent':100*errors/words,
        'GPU_J_per_audio_second_reported':res['energy_joules_per_audio_second'],
        'canonical_final_P':{str(k):list(v['P']) for k,v in state.items()},'target_rows':target_rows,
        'scope':'actual FIFO Consumer and full-token chain reconstruction; not a neural re-execution or asset render audit'}
    if cfg['consumer_policy']=='two_lane':assert invalid_view==false_credit==0
    if not cfg.get('diagnostic_omit_receive_freshness'):assert raw_stale==0
    return summary,frontiers

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    refs={r['source_id']:r for r in read(a.manifest)['sessions']};s=read(a.stage/'SUMMARY.json')
    a.output.mkdir(exist_ok=False);summaries=[];frontiers=[]
    for name in s['completed']:
        v,rows=audit(a.stage/name,refs);summaries.append(v);frontiers.extend([dict(cell=name,**r) for r in rows])
    (a.output/'SUMMARY.json').write_text(json.dumps({'status':'PASS_BOUNDED_INDEPENDENT_N1_AUDIT','cells':len(summaries),'runs':summaries},indent=2,allow_nan=False)+'\n')
    for filename,rows in [('RUNS.csv',[{k:v for k,v in s.items() if k not in ['canonical_final_P','target_rows']} for s in summaries]),('FRONTIERS.csv',frontiers)]:
        with (a.output/filename).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps([{k:r[k] for k in ['cell','stale_publications','incompatible_ahead_publications','illegal_actual_views','false_dual_deadline_credits','WER_percent']} for r in summaries]))
