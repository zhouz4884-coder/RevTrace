"""Independent N5 input/frame/actual-view/whole-offered service audit.

No scheduler, envelope rule, production Consumer or input-journal implementation
is imported. Neural/asset replay and canonical WAL replay are separate gates.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,re,struct,unicodedata

def read(p):return json.loads(p.read_text(encoding='utf8'))
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def wire(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(wire(x)).hexdigest()
def tokens(x):return hashlib.sha256(','.join(map(str,x)).encode()).hexdigest()
def edits(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]
def normalized(s):return unicodedata.normalize('NFKC',s).lower()
def quantile(xs,q):
    xs=sorted(xs)
    if not xs:return math.inf
    pos=(len(xs)-1)*q;i=int(pos);j=min(i+1,len(xs)-1)
    if math.isinf(xs[j]):return math.inf
    return xs[i]+(xs[j]-xs[i])*(pos-i)
def export_float(x):return x if math.isfinite(x) else None

def input_frames(path):
    data=path.read_bytes();offset=0;seq=0;prev='';out={};lastA={};lastC={};reject=set();origin=None;budget=None
    while offset<len(data):
        assert len(data)-offset>=4,'completed input log has partial header'
        length=struct.unpack_from('>I',data,offset)[0];assert 0<length<=1_000_000
        end=offset+4+length+32;assert end<=len(data),'completed input log has partial frame'
        raw=data[offset+4:offset+4+length];assert hashlib.sha256(raw).digest()==data[offset+4+length:end]
        r=json.loads(raw);assert r['sequence']==seq and r['previous_sha256']==prev
        if seq==0:assert r['kind']=='input-genesis'
        else:
            assert r['kind']=='envelope-snapshot';s=r['snapshot'];assert sha(s)==r['snapshot_sha256']
            if origin is None:origin=s['origin_perf'];budget=s['budget']
            assert s['origin_perf']==origin and s['budget']==budget
            held=0
            for key,v in s['sessions'].items():
                sid=int(key);O,A,C,R=(v[k] for k in ['offered','accepted','certified','reserved'])
                assert all(type(x) is int for x in [O,A,C,R])
                assert 0<=C<=A<=O and R>=A and A>=lastA.get(sid,0) and C>=lastC.get(sid,0)
                if sid in reject:assert v['rejected']
                if v['rejected']:assert A==C==0 and v['rejection_reason'];reject.add(sid)
                if A:assert len(v['accepted_prefix_sha256'])==64
                lastA[sid]=A;lastC[sid]=C;held+=R-C
            assert held<=budget
        out[seq]=r;prev=sha(r);seq+=1;offset=end
    return out

def chain(jid,F,P,jobs,results,published,fine):
    visited=set()
    while jid not in visited:
        visited.add(jid);j=jobs[jid]
        if j['chunk_id']==round(F/fine) and tuple(j['prompt_tokens'])==P:return True
        choices=[x for x in published if jobs[x]['end_window']==j['chunk_id'] and
            jobs[x].get('branch_generation')==j.get('branch_generation') and
            F<=jobs[x]['audio_end_sample']<j['audio_end_sample'] and
            tuple(results[x]['state_tokens'])==tuple(j['prompt_tokens'])]
        if len(choices)!=1:return False
        jid=choices[0]
        if jobs[jid]['audio_end_sample']==F:return tuple(results[jid]['state_tokens'])==P
    return False

def audit_episode(E,manifest):
    C=E/'attempt0';cfg=read(C/'config.json');result=read(C/'result.json');events=lines(C/'events.jsonl')
    record=lines(C/'worker_records.jsonl');consumer=lines(C/'consumer.jsonl')
    ctx=read(E/'CONTEXT.json');origin=ctx['origin_perf'];start=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    assert cfg['episode_origin_perf']==origin and cfg['result_delivery']=='row'
    assert cfg['verification_policy']=='canonical_generate' and cfg['trusted_text_binding'] and cfg['consumer_policy']=='two_lane'
    assert cfg['envelope']==read(E/'POLICY.json') and cfg['fine_seconds']==2 and cfg['sample_rate']==16000
    assert cfg['rho']==(1 if cfg.get('controlled_boundary_probe') or cfg['envelope']['method']=='fine_fair' else 3)
    assert result['contract_digest']==sha(cfg)
    workers=read(C/'workers.json');assert [w['gpu'] for w in workers]==[0,1]
    for w,role in zip(workers,['proposal','authority']):assert w['runtime_digest']==sha(cfg[role+'_runtime'])
    specs={r['session_id']:r for r in read(C/'sessions.json')};N=len(specs);fine=cfg['fine_seconds']*cfg['sample_rate']
    refs={r['source_id']:r for r in manifest['sessions']};frames=input_frames(E/'input.wal')
    assert N==len({r['source_id'] for r in specs.values()})
    for s in specs.values():
        source=refs[s['source_id']]
        assert s['audio_sha256']==source['audio_sha256'] and abs(s['duration']-source['duration'])<1e-7
    assert frames[0]['manifest_sha256']==cfg['manifest_sha256']
    assert frames[0]['policy_sha256']==sha({'envelope':cfg['envelope'],'manifest':cfg['manifest_sha256'],
        'origin_perf':origin,'rho':cfg['rho'],'sample_rate':cfg['sample_rate']})
    jobs={r['job']['job_id']:r['job'] for r in record};res={r['job']['job_id']:r['result'] for r in record}
    enqueues={e['job_id']:e for e in events if e['kind']=='enqueue'}
    assert set(jobs)==set(enqueues),'a completed pilot cannot hide an unfinished issued job'
    for jid,j in jobs.items():
        r=res[jid];m=r['model_input_audit'];receipt=r['_row_receipt'];binding=receipt['binding']
        body={k:v for k,v in r.items() if k not in ['_row_receipt','received_perf','text_binding']}
        assert sha(body)==receipt['payload_sha256']
        for k in ['job_id','session_id','role','parent','contract_epoch','contract_digest','runtime_digest','audio_start_sample','audio_end_sample','interval_audio_sha256']:
            assert binding[k]==j[k]
        assert r['runtime_digest']==j['runtime_digest'] and r['prefix_audio_sha256']==j['prefix_audio_sha256']
        assert r['execution_context_audit']['executed_prompt_tokens']==j['prompt_tokens'] and not r['execution_context_audit']['fault_override']
        assert m['declared_prompt_tokens']==j['prompt_tokens'] and m['waveform_sha256']==j['prefix_audio_sha256']
        assert m['dtype']==('float32' if j['role']=='authority' else 'float16')
        assert r['generated_tokens']==len(r['token_ids'])<=256
        assert r['terminated_by_eos']==(r['token_ids'][-1] in m['eos_token_ids'])
        assert r['terminated_by_eos'] or len(r['token_ids'])==256
        assert j['audio_ready_perf']<=j['enqueue_perf']<=r['started_perf']<=r['model_started_perf']<=receipt['terminal_perf']<=receipt['rendered_perf']<=receipt['emitted_perf']<=r['received_perf']
        expected=origin+specs[j['session_id']]['offset']+j['audio_end_sample']/16000
        assert abs(j['audio_ready_perf']-expected)<1e-7,'deadline was reset or future audio hidden'
    A={sid:0 for sid in specs};state={sid:dict(F=0,P=(),version=0) for sid in specs};generation={sid:0 for sid in specs}
    nodes={sid:set() for sid in specs};lookup={(r['session_id'],r['source_kind'],r['server_time']):r for r in consumer}
    assert len(lookup)==len(consumer)
    first_view={};first_cert={};provisional_seen=set();outcomes={};leases={};commits=[];seen_transactions=set();max_debt=max_reservation=0
    peak_unaccepted=0;retired=0;unauthorized=0;stale=0;illegal_view=0;certonly_violations=0;rejected=set()
    ack_count=0;input_sync_count=0;mode_counts=Counter()
    for e in events:
        kind=e['kind'];sid=e.get('session_id');at=start+e['time']
        if kind=='input-snapshot-synchronized':
            frame=frames[e['input_sequence']];assert frame['snapshot_sha256']==e['snapshot_sha256'];s=frame['snapshot']
            input_sync_count+=1
            for key,b in s['sessions'].items():
                slot=int(key);assert b['certified']==state[slot]['F'] and b['version']==state[slot]['version']
                offered_now=min(round(specs[slot]['duration']*16000),max(0,math.floor((at-origin-specs[slot]['offset'])/cfg['fine_seconds'])*round(fine)))
                if at>=origin+specs[slot]['offset']+specs[slot]['duration']:offered_now=round(specs[slot]['duration']*16000)
                assert b['offered']<=offered_now and b['accepted']>=A[slot]
                A[slot]=b['accepted']
            debt=sum(b['accepted']-b['certified'] for b in s['sessions'].values());held=sum(b['reserved']-b['certified'] for b in s['sessions'].values())
            max_debt=max(max_debt,debt);max_reservation=max(max_reservation,held)
        if kind=='input-ack':
            b=frames[e['input_sequence']]['snapshot']['sessions'][str(sid)]
            assert e['to_sample']==b['accepted'] and e['prefix_sha256']==b['accepted_prefix_sha256'];ack_count+=1
        if kind=='envelope-observation':peak_unaccepted=max(peak_unaccepted,e['pending_offered_audio_samples'])
        if kind=='envelope-mode':mode_counts[e['current']]+=1
        if kind=='private-generation-retired':generation[sid]=e['generation']
        if kind=='enqueue':
            j=jobs[e['job_id']];assert j['audio_end_sample']<=A[sid],('model consumed unaccepted input',j)
            if j['role']=='proposal':generation[sid]=j['branch_generation']
        # Drain accounting is deliberately in a separate deferred file. The
        # independent timestamp merge below checks the physical lease; this
        # event-only pass must not pretend a missing rich event means no drain.
        if kind=='commit':
            j=jobs[e['job_id']];r=res[e['job_id']];s=state[sid]
            assert j['role']=='authority' and e['parent']==s['version'] and j['prompt_tokens']==list(s['P'])
            assert e['audio_start_sample']==s['F'] and s['F']<e['audio_end_sample']<=A[sid]
            assert (sid,e['segment_id']) not in seen_transactions;seen_transactions.add((sid,e['segment_id']))
            assert e['segment_tokens']==r['token_ids'] and e['next_prompt_tokens']==r['state_tokens']
            assert e['certificate']['display_sha256']==tokens(r['token_ids']) and e['certificate']['feedback_state_sha256']==tokens(r['state_tokens'])
            state[sid]=dict(F=e['audio_end_sample'],P=tuple(e['next_prompt_tokens']),version=e['version']);commits.append(e)
        if kind in ['proposal-skip','proposal-obsolete','private-deadline-retired']:
            w=e['window'];assert (sid,w) not in outcomes;outcomes[sid,w]=kind
            if kind=='private-deadline-retired':
                assert not any(j['role']=='proposal' and j['session_id']==sid and j['end_window']==w for j in jobs.values())
                assert at>e['original_deadline_perf'];retired+=1
        if kind=='input-session-rejected':
            assert A[sid]==state[sid]['F']==0;rejected.add(sid)
            for w in range(1,math.ceil(specs[sid]['duration']/cfg['fine_seconds'])+1):
                assert (sid,w) not in outcomes;outcomes[sid,w]=kind
        if kind not in ['display','canonical-display','view-mode']:continue
        if kind=='display':
            j=jobs[e['job_id']];s=state[sid];nodes[sid].add(j['job_id'])
            assert (sid,j['end_window']) not in outcomes;outcomes[sid,j['end_window']]=kind
            stale+=int(j['audio_end_sample']<=s['F'] or j['branch_generation']!=generation[sid])
        row=lookup.get((sid,kind,e['displayed']))
        if row is None:continue
        s=state[sid];assert row['certified_frontier']==s['F'] and row['canonical_version']==s['version']
        assert row['canonical_epoch']==1 and row['observed_perf']>=start+e['displayed']
        vf=row['valid_visible_frontier']
        if vf>s['F']:
            candidates=[x for x in nodes[sid] if jobs[x]['audio_end_sample']==vf and res[x]['text']==row['visible_text']]
            legal=any(chain(x,s['F'],s['P'],jobs,res,nodes[sid],fine) for x in candidates)
            illegal_view+=int(not legal)
        if row['envelope_mode'] in ['CERTIFIED-ONLY','RECOVERY']:certonly_violations+=int(vf!=s['F'])
        for w in range(1,math.ceil(specs[sid]['duration']/cfg['fine_seconds'])+1):
            F=min(round(w*fine),round(specs[sid]['duration']*16000));key=(sid,F)
            if F<=vf:first_view.setdefault(key,row['observed_perf'])
            if F<=row['certified_frontier']:first_cert.setdefault(key,row['observed_perf'])
            if row['certified_frontier']<F<=vf:provisional_seen.add(key)
    # Physical accounting is deferred after the serving interval, but timestamps
    # are immutable observed drain facts, not row-duration sums.
    accounting=lines(C/'worker_batch_accounting.jsonl');all_batched=[]
    for b in accounting:
        ids=b['job_ids'];assert b['schema']=='row-cost-v1'
        for selected in b['selected_output_digests']:
            r=res[selected['job_id']];assert selected['Z_sha256']==tokens(r['token_ids']) and selected['P_sha256']==tokens(r['state_tokens'])
        assert set(b['row_receipt_digests'])==set(ids)
        for jid in ids:assert b['row_receipt_digests'][jid]==res[jid]['_row_receipt']['payload_sha256']
        all_batched+=ids
    assert sorted(all_batched)==sorted(jobs),'missing or double-counted paid physical batch'
    # Independently use dispatch/drain facts, not deferred rich-file write time.
    timeline=[]
    for e in events:
        if e['kind']=='batch-dispatched':timeline.append((start+e['time'],1,e['worker'],tuple(e['job_ids'])))
    for b in accounting:
        worker=jobs[b['job_ids'][0]]['_delivery']['worker']
        timeline.append((b['batch_drained_perf'],0,worker,tuple(b['job_ids'])))
    active={}
    for t,kind,worker,ids in sorted(timeline):
        if kind:
            assert worker not in active,'new physical dispatch before old actual drain';active[worker]=ids
        else:assert active.pop(worker)==ids
    assert not active and stale==illegal_view==certonly_violations==0
    expected={(sid,w) for sid,s in specs.items() for w in range(1,math.ceil(s['duration']/cfg['fine_seconds'])+1)}
    assert set(outcomes)==expected and len(commits)==result['certified_commits']
    frontiers=[];total_audio=sum(s['duration'] for s in specs.values());end=max(origin+max(s['offset']+s['duration'] for s in specs.values()),
        max(r['observed_perf'] for r in consumer),max(b['batch_drained_perf'] for b in accounting),start+result['wall_seconds_including_arrival_and_drain'])
    elapsed=end-origin
    for sid,s in specs.items():
        prev=0
        for w in range(1,math.ceil(s['duration']/cfg['fine_seconds'])+1):
            F=min(round(w*fine),round(s['duration']*16000));ready=origin+s['offset']+F/16000
            d=first_view.get((sid,F),math.inf)-ready;c=first_cert.get((sid,F),math.inf)-ready
            frontiers.append(dict(session_id=sid,frontier=F,audio_seconds=(F-prev)/16000,
                display_latency=d,commit_view_latency=c,dual_credit=d<=2 and c<=8,
                ever_legal_provisional_ahead_of_certified=(sid,F) in provisional_seen));prev=F
    d99=quantile([r['display_latency'] for r in frontiers],.99);c99=quantile([r['commit_view_latency'] for r in frontiers],.99)
    word_errors=word_count=char_errors=char_count=0
    for s in result['final_states']:
        ref=normalized(refs[specs[s['session_id']]['source_id']]['reference']);hyp=normalized(s['text'])
        a=re.findall(r"[a-z0-9']+",ref);b=re.findall(r"[a-z0-9']+",hyp)
        word_errors+=edits(a,b);word_count+=len(a)
        a=[x for x in ref if x.isalnum()];b=[x for x in hyp if x.isalnum()]
        char_errors+=edits(a,b);char_count+=len(a)
    power=read(E/'EPISODE_POWER.json');energy=0.;covered={}
    for gpu in [0,1]:
        xs=sorted((r for r in power['samples'] if r['gpu']==gpu),key=lambda x:x['t']);coverage=0.
        for a,b in zip(xs,xs[1:]):
            lo=max(origin,a['t']);hi=min(end,b['t'])
            if hi<=lo:continue
            slope=(b['power_w']-a['power_w'])/(b['t']-a['t'])
            p0=a['power_w']+slope*(lo-a['t']);p1=a['power_w']+slope*(hi-a['t'])
            energy+=.5*(p0+p1)*(hi-lo);coverage+=hi-lo
        covered[str(gpu)]=coverage/elapsed;assert covered[str(gpu)]>.98
    # Exact offered timeline, not just controller-observed queue samples. This
    # is OFFLINE assessment, never future information available to the policy.
    updates=[]
    for sid,s in specs.items():
        for w in range(1,math.ceil(s['duration']/cfg['fine_seconds'])+1):
            F=min(round(w*fine),round(s['duration']*16000))
            updates.append((origin+s['offset']+F/16000,0,sid,F))
    for e in events:
        if e['kind']=='input-snapshot-synchronized':updates.append((start+e['time'],1,None,e['input_sequence']))
        if e['kind']=='commit':updates.append((start+e['time'],2,e['session_id'],e['audio_end_sample']))
    offered={sid:0 for sid in specs};accepted=dict(offered);certified=dict(offered);terminal=set()
    pending_peak=unadmitted_peak=0;pending_area=unadmitted_area=0.;prior_t=origin;prior_pending=prior_unadmitted=0
    for at,kind,sid,value in sorted(updates):
        pending_area+=(at-prior_t)*prior_pending/16000;unadmitted_area+=(at-prior_t)*prior_unadmitted/16000;prior_t=at
        if kind==0:offered[sid]=value
        elif kind==1:
            for k,b in frames[value]['snapshot']['sessions'].items():
                slot=int(k);accepted[slot]=b['accepted']
                if b['rejected']:terminal.add(slot)
        else:certified[sid]=value
        assert all(certified[k]<=accepted[k]<=offered[k] for k in specs)
        prior_pending=sum(offered[k]-accepted[k] for k in specs if k not in terminal)
        prior_unadmitted=sum(offered[k]-certified[k] for k in specs)
        pending_peak=max(pending_peak,prior_pending);unadmitted_peak=max(unadmitted_peak,prior_unadmitted)
    pending_area+=(end-prior_t)*prior_pending/16000;unadmitted_area+=(end-prior_t)*prior_unadmitted/16000
    sync=[e for e in events if e['kind']=='wal-physical-timing' and e['phase']=='fsync']
    writes=[e for e in events if e['kind']=='wal-physical-timing' and e['phase']=='write']
    calls={tuple(e['job_ids']):e for e in events if e['kind']=='wal-owner-start'}
    ends=[e for e in events if e['kind']=='wal-owner-complete']
    assert len(sync)==len(writes)==len(calls)==len(ends)
    row_latency=[r['received_perf']-r['_row_receipt']['emitted_perf'] for r in res.values()]
    applied=[r['observed_perf']-(start+r['server_time']) for r in consumer]
    certified_seconds=sum(v['F']/16000 for v in state.values())
    summary=dict(episode=E.name,method=cfg['envelope']['method'],sources=N,whole_offered_frontiers=len(frontiers),
        unauthorized_admissions=unauthorized,stale_publications=stale,root_incompatible_actual_views=illegal_view,
        certified_only_violations=certonly_violations,rejected_sessions=len(rejected),unfinished_sources=sum(state[sid]['F']<round(s['duration']*16000) for sid,s in specs.items()),
        final_certified_audio_coverage=sum(v['F']/16000 for v in state.values())/total_audio,
        all_offered_audio_goodput_2_8=sum(r['audio_seconds'] for r in frontiers if r['dual_credit'])/elapsed,
        display_P50=export_float(quantile([r['display_latency'] for r in frontiers],.5)),display_P95=export_float(quantile([r['display_latency'] for r in frontiers],.95)),display_P99=export_float(d99),
        commit_view_P50=export_float(quantile([r['commit_view_latency'] for r in frontiers],.5)),commit_view_P95=export_float(quantile([r['commit_view_latency'] for r in frontiers],.95)),commit_view_P99=export_float(c99),
        whole_run_dual_P99_pass=d99<=2 and c99<=8,WER_errors=word_errors,WER_reference_words=word_count,
        all_offered_WER_percent=100*word_errors/word_count,all_offered_character_error_percent=100*char_errors/char_count,
        corpus_language='English; character metric is English CER, not a Mandarin result',
        original_episode_wall_seconds=elapsed,GPU_joules=energy,GPU_J_per_offered_audio_second=energy/total_audio,power_coverage=covered,
        accepted_debt_peak_audio_seconds=max_debt/16000,reserved_debt_peak_audio_seconds=max_reservation/16000,
        unaccepted_offered_peak_audio_seconds=peak_unaccepted/16000,input_ACKs=ack_count,input_snapshot_syncs=input_sync_count,
        private_expired_unissued=retired,physical_batches=len(accounting),recorded_complete_rows=len(record),
        controller_CPU_seconds=result['envelope_decision_CPU_seconds'],controller_host_seconds=result['envelope_decision_host_seconds'],
        controller_decisions=result['envelope_decisions'],input_fsync_seconds=result['input_fsync_seconds'],
        input_data_fsync_calls_including_genesis=result['input_fsync_calls'],
        input_journal_bytes=(E/'input.wal').stat().st_size,canonical_journal_bytes=(E/'canonical.wal').stat().st_size,
        mode_entries=dict(mode_counts),safety_audit='PASS_ALL_RECORDED_INPUT_WAL_ROW_CONSUMER_INVARIANTS')
    summary.update(valid_provisional_ahead_coverage_per_offered_audio=sum(r['audio_seconds'] for r in frontiers if r['ever_legal_provisional_ahead_of_certified'])/total_audio,
        explicit_rejected_offered_audio_seconds=sum(specs[sid]['duration'] for sid in rejected),
        uncompleted_offered_audio_seconds=total_audio-certified_seconds,
        final_accepted_audio_seconds=sum(accepted.values())/16000,
        final_accepted_uncertified_debt_audio_seconds=sum(accepted[k]-certified[k] for k in specs)/16000,
        exact_pending_unaccepted_peak_audio_seconds=pending_peak/16000,
        exact_unadmitted_offered_peak_audio_seconds=unadmitted_peak/16000,
        pending_unaccepted_area_audio_seconds_times_wall_seconds=pending_area,
        unadmitted_offered_area_audio_seconds_times_wall_seconds=unadmitted_area,
        GPU_J_per_certified_audio_second=energy/certified_seconds if certified_seconds else None,
        actual_row_emission_to_owner_receive_P50=quantile(row_latency,.5),
        actual_row_emission_to_owner_receive_P99=quantile(row_latency,.99),
        actual_publication_to_Consumer_applied_P50=quantile(applied,.5),actual_publication_to_Consumer_applied_P99=quantile(applied,.99),
        consumer_audio_rollback_events=sum(r['audio_rollback_samples']>0 for r in consumer),
        consumer_total_retracted_audio_seconds=sum(r['audio_rollback_samples'] for r in consumer)/16000,
        consumer_erased_characters=sum(r['erased_characters'] for r in consumer),
        canonical_commit_group_fsync_calls=len(sync),canonical_commit_group_fsync_seconds=sum(e['completed']-e['started'] for e in sync),
        canonical_commit_group_write_seconds=sum(e['completed']-e['started'] for e in writes),
        canonical_owner_WAL_call_seconds=sum(e['time']-calls[tuple(e['job_ids'])]['time'] for e in ends),
        trusted_render_host_wall_seconds=sum(e['host_cpu_wall_seconds'] for e in events if e['kind']=='render-checked'),
        consumer_CPU_seconds=result['consumer']['consumer_cpu_seconds'],consumer_max_queue_depth=result['consumer']['queue_max_depth'],
        cost_scope_note='IPC latencies include queue/scheduling/copy, not isolated pipe CPU; Render is host wall, controller/Consumer CPU are subsets; Canonical fsync counts commit groups, not initialization/directory calls; CPU power and total owner CPU not separately measured')
    return summary,frontiers

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',default='formal_normal',choices=['pilot','development','formal_normal'])
    p.add_argument('--manifest-name',default='INDEPENDENT_MANIFEST_v1.json')
    p.add_argument('--runtime-manifest',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(exist_ok=False);root=a.root;manifest=read(root/a.manifest_name);complete=read(root/a.stage/'SUMMARY.json')
    assert complete['cells']==complete['expected']==len(complete['completed'])
    assert not (root/a.stage/'STOP.json').exists()
    freeze=read(root/a.stage/'FREEZE.json');runtime=read(a.runtime_manifest)
    assert runtime['code_commit']==freeze['runtime_commit']
    assert hashlib.sha256((root/a.manifest_name).read_bytes()).hexdigest()==freeze.get('source_manifest_sha256',freeze.get('manifest_sha256'))
    source_shas={r['path']:r['sha256'] for r in runtime['files']}
    planned={}
    for c in freeze['cells']:
        name=(f"{c['method']}-{c['workload']}-r{c['repeat']}" if 'workload' in c else
              f"{c['method']}-c{c['load']}-{c['arrival']}-r{c['repeat']}")
        assert name not in planned;planned[name]=c
    assert list(planned)==complete['completed']
    if a.stage=='formal_normal':assert len(planned)==105
    summaries=[];fs=[]
    for name in complete['completed']:
        E=root/a.stage/name;c=planned[name];cfg=read(E/'attempt0/config.json');provenance=read(E/'attempt0/provenance.json')
        assert provenance['code_commit']==runtime['code_commit']
        for file,digest in provenance['source_sha256'].items():assert source_shas[file]==digest
        assert cfg['envelope']['method']==c['method'] and len(read(E/'attempt0/sessions.json'))==c['load']
        if 'offsets' in c:assert read(E/'ARRIVAL.json')['offsets']==c['offsets']
        s,r=audit_episode(E,manifest);summaries.append(s);fs.extend([dict(episode=name,**x) for x in r])
    metadata=dict(checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        frozen_config_sha256=hashlib.sha256((root/a.stage/'FREEZE.json').read_bytes()).hexdigest(),
        runtime_manifest_sha256=hashlib.sha256(a.runtime_manifest.read_bytes()).hexdigest(),runtime_commit=runtime['code_commit'],
        workload_manifest_sha256=hashlib.sha256((root/a.manifest_name).read_bytes()).hexdigest(),
        scope='independent recorded-input and actual-view/cost recount; WAL predicate and CPU processor replay separate')
    (a.output/'SUMMARY.json').write_text(json.dumps(dict(status='PASS_INDEPENDENT_INPUT_AND_ACTUAL_VIEW_RECOUNT',stage=a.stage,cells=len(summaries),metadata=metadata,episodes=summaries),indent=2,allow_nan=False)+'\n')
    with (a.output/'RUNS.csv').open('w',newline='') as f:
        rows=[{k:v for k,v in r.items() if k not in ['mode_entries','power_coverage']} for r in summaries]
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (a.output/'FRONTIERS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(fs[0]));w.writeheader();w.writerows(fs)
    print(json.dumps([{k:s[k] for k in ['episode','all_offered_audio_goodput_2_8','display_P99','commit_view_P99','whole_run_dual_P99_pass','GPU_J_per_offered_audio_second','all_offered_WER_percent','mode_entries','controller_CPU_seconds']} for s in summaries]))
