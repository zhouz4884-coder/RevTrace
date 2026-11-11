"""Exact24 endpoint diagnostic; EOS counterfactual edits no other observation."""
import hashlib,json,math,pathlib
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def read(spec):
    p=pathlib.Path(spec['path']);raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['sha256']:raise ValueError('frozen_input_changed:'+str(p))
    return json.loads(raw) if not spec.get('jsonl') else [json.loads(l) for l in raw.splitlines() if l.strip()]
def quantile(xs,q=.99):
    s=sorted(xs);pos=(len(s)-1)*q;i=int(pos);j=min(i+1,len(s)-1)
    return math.inf if math.isinf(s[j]) else s[i]+(s[j]-s[i])*(pos-i)
def finite(x):return x if math.isfinite(x) else None
def endpoints(n):return list(range(8000,n,8000))+[n]
def score(rows):
    d=quantile([math.inf if r['D'] is None else r['D'] for r in rows]);c=quantile([math.inf if r['C'] is None else r['C'] for r in rows])
    missingD=sum(r['D'] is None for r in rows);missingC=sum(r['C'] is None for r in rows)
    return dict(D99=finite(d),C99=finite(c),quantile_pass=d<=2 and c<=8,
        complete_coverage_and_original_quantile_pass=not missingD and not missingC and d<=2 and c<=8,
        D2_misses=sum(r['D'] is None or r['D']>2 for r in rows),C8_misses=sum(r['C'] is None or r['C']>8 for r in rows),
        credit_audio_seconds=sum(r['audio_seconds'] for r in rows if r['D'] is not None and r['D']<=2 and r['C'] is not None and r['C']<=8),
        offered_audio_seconds=sum(r['audio_seconds'] for r in rows),missing_D=missingD,missing_C=missingC)
def eos_counterfactual(rows,value):
    out=[dict(r) for r in rows]
    for r in out:
        if r['is_EOS']:r['D']=value if r['D'] is None else min(r['D'],value)
    return out
def recount(cell):
    files=cell['files'];cfg=read(files['config']);origin=read(files['origin'])['origin_perf'];actual=read(files['summary']);rows=read(files['consumer']);work=read(files['work'])
    if cfg['cell_id']!=cell['cell_id'] or cfg['settings']['source_commit']!='de0936b2e30179d63aeef6e235cd1af685578c58':raise ValueError('wrong_cell_or_NN')
    if len(cfg['settings']['sources'])!=1:raise ValueError('single_source_scope_required')
    source=cfg['settings']['sources'][0];sid=source['source_id'];n=source['frames'];obs=[r for r in rows if r['source_id']==sid]
    if any(not math.isfinite(r['observed']) for r in obs) or any(a['observed']>b['observed'] for a,b in zip(obs,obs[1:])):raise ValueError('invalid_Consumer_clock')
    fs=[];previous=0;first_rows={}
    for F in endpoints(n):
        ready=origin+F/16000
        dr=next((r for r in obs if r['observed']>=ready and r['visible_frontier']>=F),None)
        cr=next((r for r in obs if r['observed']>=ready and r['certified_frontier']>=F),None)
        fs.append(dict(frontier=F,audio_seconds=(F-previous)/16000,is_EOS=F==n,D=(dr['observed']-ready if dr else None),C=(cr['observed']-ready if cr else None),
            first_D_kind=dr.get('kind') if dr else None,first_D_private_job=dr.get('private_job') if dr else None,
            first_D_perf=dr['observed'] if dr else None,first_C_perf=cr['observed'] if cr else None));previous=F
    current=score(fs);p=actual['primary']
    expected=dict(D99=p['primary_linear_all_offered_D99'],C99=p['primary_linear_all_offered_C99'],D2_misses=p['D2_misses_all_offered'],C8_misses=p['C8_misses_all_offered'],credit_audio_seconds=p['dual_deadline_audio_credit_seconds'],offered_audio_seconds=p['offered_audio_seconds'],complete_coverage_and_original_quantile_pass=p['complete_coverage_and_original_quantile_pass'])
    for key,value in expected.items():
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            if abs(current[key]-value)>1e-8:raise ValueError('original_endpoint_not_reproduced:'+key)
        elif current[key]!=value:raise ValueError('original_endpoint_not_reproduced:'+key)
    counts={name:sum((r['D'] is None or r['D']>2) if metric=='D' else (r['C'] is None or r['C']>8) for r in fs if r['is_EOS']==eos) for name,metric,eos in [('EOS_D2_misses','D',True),('nonEOS_D2_misses','D',False),('EOS_C8_misses','C',True),('nonEOS_C8_misses','C',False)]}
    if counts['EOS_D2_misses']!=p['EOS_D2_misses'] or counts['nonEOS_D2_misses']!=p['nonEOS_D2_misses']:raise ValueError('original_EOS_split_not_reproduced')
    e=fs[-1];selected=[r for r in work if r['target']==n and r['selected_durable']]
    if len(selected)!=1:raise ValueError('EOS_selected_job_binding_not_unique')
    w=selected[0];ready=origin+n/16000
    eos_timing=dict(selected_original_EOS_job_id=w['job_id'],release_to_selected_dispatch_seconds=w['dispatch_perf']-ready,
        selected_worker_wall_seconds=w['worker_wall_seconds'],selected_full_infer_wall_seconds=w['observed_infer_wall_seconds'],
        first_display_minus_selected_dispatch_seconds=e['first_D_perf']-w['dispatch_perf'] if e['first_D_perf'] is not None else None,
        first_certified_minus_selected_dispatch_seconds=e['first_C_perf']-w['dispatch_perf'] if e['first_C_perf'] is not None else None,
        first_display_is_selected_job_projection=e['first_D_private_job']==w['job_id'],
        display_to_certified_seconds=e['first_C_perf']-e['first_D_perf'] if e['first_C_perf'] is not None and e['first_D_perf'] is not None else None,
        limitation='dispatch gap includes eligibility/scheduler/ingress; infer includes ASR/C/U/callback; no subphase or worker-begin absolute timestamps in bounded OP work; endpoint may be another job unless identity matches')
    return dict(cell_id=cell['cell_id'],source_id=sid,speaker_id=source['speaker_id'],strategy=cfg['arm'],repeat=cfg['repeat'],origin_perf=origin,frames=n,
        original=current,**counts,EOS=e,first_three=fs[:3],nonEOS_missed_frontiers=[r for r in fs if not r['is_EOS'] and (r['D'] is None or r['D']>2 or r['C'] is None or r['C']>8)],
        EOS_only_D_just_inside_2=score(eos_counterfactual(fs,1.999999)),EOS_only_D_zero_bestcase=score(eos_counterfactual(fs,0.0)),EOS_selected_job_timing=eos_timing,frontiers=fs)
def analyze(cfg):
    cells=[recount(c) for c in cfg['cells']]
    if len(cells)!=24 or len({r['cell_id'] for r in cells})!=24:raise ValueError('must_retain_exact24')
    arms=[]
    for arm in sorted({c['strategy'] for c in cells}):
        rs=[r for r in cells if r['strategy']==arm];den=sum(r['original']['offered_audio_seconds'] for r in rs)
        scenarios={k:dict(credit_audio_seconds=sum(r[k]['credit_audio_seconds'] for r in rs),credit_percent=100*sum(r[k]['credit_audio_seconds'] for r in rs)/den,
                          whole_run_original_quantile_passes=sum(r[k]['complete_coverage_and_original_quantile_pass'] for r in rs)) for k in ('original','EOS_only_D_just_inside_2','EOS_only_D_zero_bestcase')}
        arms.append(dict(strategy=arm,trials=len(rs),offered_audio_seconds=den,scenarios=scenarios,
            nonEOS_single_0_5s_weight_pp=50/den,EOS_weight_steps_pp=sorted({100*r['EOS']['audio_seconds']/den for r in rs}),
            interpretation='exact weighted endpoint increments, not plus-minus measurement uncertainty or statistical resolution'))
    ref=read(cfg['reference_config'])
    return dict(status='PASS_EXACT24_ENDPOINT_EOS_DIAGNOSTIC_NO_REPAIR',cells=cells,arms=arms,
        reference_sources=[r['source_id'] for r in ref['sources']],reference_warmup_source=ref['warmup']['source_id'],
        counterfactual_scope='Only each EOS D entry reduced; all other raw D/C, original n/offered weights/deadlines unchanged. Not a realizable alternate schedule or deployed repair.',new_model_calls=0,GPU_calls=0)
