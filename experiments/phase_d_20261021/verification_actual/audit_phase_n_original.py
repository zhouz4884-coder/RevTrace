"""Independent raw-event/WAL/power audit. Never calls the production scheduler."""
import argparse,hashlib,json,math,re,statistics,sys,unicodedata
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def normal(text,language):
    text=unicodedata.normalize('NFKC',text).lower()
    return re.findall(r"[a-z0-9']+",text) if language=='English' else [x for x in text if x.isalnum()]
def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]
def quantiles(values):
    return {k:None if not values else float(np.quantile(values,q)) for k,q in [('p50',.5),('p95',.95),('p99',.99)]}
def audit(cell,sdk,manifest):
    inputs=[p for p in cell.glob('*') if p.is_file() and p.name!='INDEPENDENT_AUDIT.json'];before={p.name:sha(p) for p in inputs}
    sys.path[:0]=[str(sdk/'src'),str(sdk/'scripts')]
    from audit_tc_live_qwen import audit as certificate_audit
    from audit_dsn_journal import audit as journal_audit
    cfg=json.loads((cell/'config.json').read_text());res=json.loads((cell/'result.json').read_text())
    provenance=json.loads((cell/'provenance.json').read_text());walpath=Path(provenance['durable_journal_path'])
    proof=certificate_audit(cell);walproof=journal_audit(walpath,cell)
    # Parse physical frames independently to bind actual display text to durable selection.
    raw=walpath.read_bytes();pos=0;waltext={};seq=0;previous=''
    while pos<len(raw):
        assert pos+4<=len(raw);length=int.from_bytes(raw[pos:pos+4],'big');start=pos+4;end=start+length
        assert end+32<=len(raw)
        payload=raw[start:end];digest=hashlib.sha256(payload).digest();assert digest==raw[end:end+32]
        rec=json.loads(payload);assert rec['sequence']==seq and rec['previous_sha256']==previous
        previous=digest.hex();seq+=1;pos=end+32
        if rec['kind']=='commit':waltext[rec['session_id'],rec['parent_checkpoint_id']+1]=rec['event']['committed_text']
    events=[json.loads(line) for line in (cell/'events.jsonl').read_text().splitlines()]
    deferred=[]
    if (cell/'worker_records.jsonl').exists():
        deferred=[json.loads(line) for line in (cell/'worker_records.jsonl').read_text().splitlines()]
    specs={s['session_id']:s for s in json.loads((cell/'sessions.json').read_text())}
    start=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    F=defaultdict(int);gen=defaultdict(int);rev=defaultdict(int);lastcanon={};D=defaultdict(int)
    jobs={};completed={};outcomes={};pub=defaultdict(list);commits=defaultdict(list);record={};counts=Counter()
    commit_by_job={};wal_by_job={};owner=None;physical=[];wait=[];acks=set();display_versions=set()
    visible={};invalid_visible_duration=defaultdict(float)
    for e in events:
        kind=e['kind'];sid=e.get('session_id')
        if kind=='segment-parent' and cfg['proposal_barrier']=='segment':gen[sid]+=1
        elif kind=='proposal-rebase':gen[sid]+=1
        elif kind=='enqueue':
            jobs[e['job_id']]=e
            if e['role']=='proposal':counts['covered_dispatch']+=e['audio_end_sample']<=F[sid]
        elif kind=='executor-complete':
            if e.get('gpu_model_started') is not None:
                assert e['started']<=e['gpu_model_started']<=e['gpu_model_completed']<=e['completed']<=e['received']
            completed[e['job_id']]=e
        elif kind=='worker-record':record[e['job']['job_id']]=e
        elif kind=='wal-owner-start':owner={'entered':e['time'],'job_ids':e['job_ids'],'physical':[]}
        elif kind=='wal-physical-timing':
            assert owner is not None;owner['physical'].append(e);physical.append(e)
        elif kind=='wal-owner-complete':
            assert owner is not None
            owner['exited']=e['time']
            for jid in owner['job_ids']:wal_by_job[jid]=dict(owner)
            owner=None
        elif kind=='authority-wait-interval':
            assert e['duration']>0 and abs(e['duration']-e['exited']+e['entered'])<1e-7
            wait.append(e)
        elif kind=='commit':
            assert e['audio_start_sample']==F[sid] and e['audio_end_sample']>F[sid]
            F[sid]=e['audio_end_sample'];commits[sid].append((F[sid],e['installed'],e['job_id']))
            commit_by_job[e['job_id']]=e
        elif kind in ['display','proposal-obsolete','proposal-skip']:
            key=sid,e['window'];assert key not in outcomes;outcomes[key]=kind
            if kind=='display':
                j=jobs[e['job_id']];covered=j['audio_end_sample']<=F[sid];invalid=j['branch_generation']!=gen[sid]
                counts['obsolete_publication']+=covered;counts['invalid_generation_publication']+=invalid
                if cfg['proposal_reconciliation']=='lazy':assert not covered and not invalid
                if not covered and not invalid:pub[sid].append((j['audio_end_sample'],e['displayed']))
            else:counts[kind]+=1
        if kind in ['display','canonical-display'] and cfg.get('display_protocol')=='canonical-snapshot-v1':
            if sid in visible and not visible[sid]['valid']:
                invalid_visible_duration[sid]+=e['displayed']-visible[sid]['time']
            valid_now=True if kind=='canonical-display' else not covered and not invalid
            visible[sid]={'time':e['displayed'],'valid':valid_now,'text':e['text'],'kind':kind}
            assert e['display_revision']>rev[sid];rev[sid]=e['display_revision']
            assert e['display_ever_frontier']>=D[sid];D[sid]=e['display_ever_frontier']
            counts['audio_rollback_samples']+=e['audio_rollback_samples'];counts['erased_characters']+=e['erased_characters']
            if kind=='canonical-display':
                assert isinstance(e['text'],str) and e['text']==waltext[sid,e['version']]
                assert e['audio_end_sample']==F[sid]
                c=commit_by_job[e['job_id']];assert c['segment_id']==e['transaction_id']
                assert c['version']==e['version'];display_versions.add((sid,e['version']))
                lastcanon[sid]=e['text'];pub[sid].append((F[sid],e['displayed']))
                counts['canonical_corrections_with_audio_rollback']+=e['audio_rollback_samples']>0
            assert e['canonical_snapshot']==lastcanon.get(sid,'')
        if kind=='install-ack':
            assert (sid,e['version']) in display_versions;acks.add((sid,e['version']))
    assert owner is None
    for sid,value in visible.items():
        if not value['valid']:invalid_visible_duration[sid]+=res['wall_seconds_including_arrival_and_drain']-value['time']
    for e in deferred:
        assert e['kind']=='worker-record';record[e['job']['job_id']]=e
    expected_windows={(sid,w) for sid,s in specs.items() for w in range(1,math.ceil(s['duration']/2)+1)}
    assert set(outcomes)==expected_windows
    expected_versions={(e['session_id'],e['version']) for e in events if e['kind']=='commit'}
    assert display_versions==acks==expected_versions
    if cfg['proposal_reconciliation']=='lazy':
        assert all(v['valid'] and v['text']==lastcanon[sid] for sid,v in visible.items())
    pts=[];lifecycles=[]
    for sid,s in specs.items():
        end=round(s['duration']*16000);prior=0
        for q in list(range(32000,end,32000))+[end]:
            release=s['offset']+q/16000
            display=min((t for b,t in pub[sid] if b>=q),default=math.inf)
            selected=min((r for r in commits[sid] if r[0]>=q),key=lambda r:r[1])
            committed=selected[1];j=jobs[selected[2]];done=completed[selected[2]]
            pts.append({'session_id':sid,'source_id':s['source_id'],'q':q,'weight_seconds':(q-prior)/16000,
                'display':None if math.isinf(display) else display-release,'commit':committed-release,
                'authority_job':j['job_id'],'coverage_accumulation_wait':j['audio_ready_perf']-start-release,
                'ready_to_enqueue':j['enqueue_perf']-j['audio_ready_perf'],
                'ready_to_eligible':j['eligible_perf']-j['audio_ready_perf'],
                'eligible_to_enqueue':j['enqueue_perf']-j['eligible_perf']});prior=q
    for jid,c in commit_by_job.items():
        j=jobs[jid];done=completed[jid];w=wal_by_job[jid]
        fsync=[p for p in w['physical'] if p['phase']=='fsync']
        lifecycles.append({'job_id':jid,'session_id':j['session_id'],'source_id':j['source_id'],
            'audio_end_sample':j['audio_end_sample'],'audio_release':j['audio_ready_perf']-start,
            'eligible':j['eligible_perf']-start,'enqueue':j['enqueue_perf']-start,
            'worker_started':done['started'],'worker_completed':done['completed'],
            'gpu_started':done.get('gpu_model_started'),'gpu_completed':done.get('gpu_model_completed'),'received':done['received'],
            'certified':c['certified'],'installed':c['installed'],
            'fsync_started':fsync[0]['started'] if fsync else None,'fsync_completed':fsync[-1]['completed'] if fsync else None,
            'ready_to_enqueue':j['enqueue_perf']-j['audio_ready_perf'],
            'enqueue_to_worker_start':done['started']-done['enqueue'],
            'enqueue_to_gpu_model_start':None if done.get('gpu_model_started') is None else done['gpu_model_started']-done['enqueue'],
            'worker_preprocessing':None if done.get('gpu_model_started') is None else done['gpu_model_started']-done['started'],
            'worker_execution_service':done['completed']-done['started'],
            'gpu_execution':None if done.get('gpu_model_started') is None else done['gpu_model_completed']-done['gpu_model_started'],
            'delivery':done['received']-done['completed'],
            'certificate_after_receive':c['certified']-done['received'],
            'owner_wal_call':w['exited']-w['entered']})
    pd=[math.inf if p['display'] is None else p['display'] for p in pts];pc=[p['commit'] for p in pts]
    p99d=float(np.quantile(pd,.99));p99c=float(np.quantile(pc,.99))
    grid=[];wall=res['wall_seconds_including_arrival_and_drain']
    for dd in [2.,5.,8.]:
        for dc in [4.,8.,12.,16.]:
            good=sum(p['weight_seconds'] for p in pts if p['display'] is not None and p['display']<=dd and p['commit']<=dc)
            grid.append({'display_deadline':dd,'commit_deadline':dc,'goodput':good/wall,
                'audio_fraction':good/res['audio_seconds'],'dual_p99_pass':p99d<=dd and p99c<=dc})
    samples=defaultdict(list)
    for p in json.loads((cell/'power_samples.json').read_text())['samples']:samples[p['gpu']].append(p)
    energy=0
    for rows in samples.values():
        rows.sort(key=lambda r:r['t']);energy+=sum((r['t']-l['t'])*(r['power_w']+l['power_w'])/2 for l,r in zip(rows,rows[1:]))
    assert abs(energy-res['power']['energy_joules'])<1e-5
    pool={s['source_id']:s for s in manifest['sessions']};unique={};replicas=defaultdict(list)
    for row in res['final_states']:
        source=specs[row['session_id']]['source_id'];unique.setdefault(source,row['text']);replicas[source].append(row['text'])
    assert all(len(set(v))==1 for v in replicas.values())
    quality=defaultdict(Counter)
    for source,text in unique.items():
        m=pool[source];ref=normal(m['reference'],m['language']);hyp=normal(text,m['language'])
        quality[m['language']]['errors']+=distance(ref,hyp);quality[m['language']]['reference_units']+=len(ref)
        quality[m['language']]['sources']+=1
    wait_total=sum(e['duration'] for e in wait);bits=defaultdict(float);unknown=0
    exact_execution=0.;exact_fsync=0.;both_execution_capacity=0.;all_model_clocks=all(d.get('gpu_model_started') is not None for d in completed.values())
    for e in wait:
        for k,v in e['bitmap'].items():
            if v is True:bits[k]+=e['duration']
            elif v is None and k=='self_exec_on_gpu':unknown+=e['duration']
        left,right=e['entered'],e['exited'];own=[]
        for jid in e['own_job_ids']:
            d=completed[jid]
            if d.get('gpu_model_started') is not None:own.append((max(left,d['gpu_model_started']),min(right,d['gpu_model_completed'])))
        # Same-session single-flight: no double-counted execution interval.
        measured=sum(max(0.,r-l) for l,r in own);exact_execution+=measured
        if e['bitmap']['worker_capacity_occupied']:both_execution_capacity+=measured
        for fs in physical:
            if fs['phase']=='fsync':exact_fsync+=max(0.,min(right,fs['completed'])-max(left,fs['started']))
    assert before=={p.name:sha(p) for p in inputs}
    output={'decision':'PASS_INDEPENDENT_ABC_CLOCK_WAL_AND_QUALITY','cell':cell.name,
        'source_commit':provenance['code_commit'],'raw_hashes':before,'wal_sha256':sha(walpath),
        'certificate_audit':proof,'wal_audit':walproof,'counts':dict(counts),'window_outcomes':dict(Counter(outcomes.values())),
        'display_missing':sum(p['display'] is None for p in pts),'display_p99':None if math.isinf(p99d) else p99d,'commit_p99':p99c,
        'xrt':res['audio_seconds']/wall,'wall_seconds':wall,'gpu_j_per_audio_second':energy/res['audio_seconds'],
        'quality':dict(quality),'final_projection':{str(r['session_id']):r['state']['prompt_tokens'] for r in res['final_states']},
        'grid':grid,'common_frontiers':pts,'authority_lifecycles':lifecycles,
        'common_frontier_stage_quantiles':{k:quantiles([p[k] for p in pts]) for k in ['coverage_accumulation_wait','ready_to_enqueue','ready_to_eligible','eligible_to_enqueue']},
        'job_stage_quantiles':{k:quantiles([p[k] for p in lifecycles if p[k] is not None]) for k in ['ready_to_enqueue','enqueue_to_worker_start','enqueue_to_gpu_model_start','worker_preprocessing','worker_execution_service','gpu_execution','delivery','certificate_after_receive','owner_wal_call']},
        'wait_target_seconds':wait_total,'overlapping_wait_bitmap_seconds':dict(bits),'unknown_execution_target_seconds':unknown,
        'posthoc_physical_execution_target_seconds':exact_execution if all_model_clocks else None,'posthoc_fsync_target_seconds':exact_fsync,
        'posthoc_both_execution_and_capacity_target_seconds':both_execution_capacity if all_model_clocks else None,
        'gpu_clock_scope':'synchronized model-call interval, not sum of individual CUDA kernel busy times; missing model clocks stay UNKNOWN',
        'wait_scope':'pending-target seconds, overlapping flags, not additive GPU wall or causal fractions',
        'physical_wal':physical,'actual_worker_names':sorted({e['worker'] for e in events if e['kind']=='executor-complete'}),
        'actual_batch_sizes':[len(e['job_ids']) for e in events if e['kind']=='batch-dispatched'],
        'captured_worker_records':len(record)}
    output['invalid_visible_slot_seconds']=sum(invalid_visible_duration.values())
    output['final_visible_text_matches_canonical']={str(sid):v['text']==lastcanon[sid] for sid,v in visible.items()}
    save(cell/'INDEPENDENT_AUDIT.json',output);return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    a=p.parse_args();manifest=json.loads(a.manifest.read_text());out=[]
    allowed=None
    if (a.root/'PROGRESS.json').exists() and not (a.root/'SUMMARY.json').exists():
        progress=json.loads((a.root/'PROGRESS.json').read_text());allowed=set(progress.get('completed',[]))
    for cell in sorted(a.root.iterdir()):
        if not (cell/'result.json').is_file():continue
        if allowed is not None and cell.name not in allowed:continue
        # Never reread a prior PASS as fresh evidence; rerun raw checks on request.
        row=audit(cell,a.sdk,manifest);out.append(row)
        print(json.dumps({'cell':cell.name,'audit':row['decision'],'display_p99':row['display_p99'],'commit_p99':row['commit_p99']}),flush=True)
    save(a.root/'INDEPENDENT_AUDIT_SUMMARY.json',{'cells':out,'raw_reconstruction':True})
