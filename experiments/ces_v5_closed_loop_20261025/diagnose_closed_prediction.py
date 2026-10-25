"""Selected first-physical-batch calibration; no unchosen model outcomes.

Pure post-run CPU analysis. Common-cut/planned_seconds forecasts include other
batches and successors and are NEVER compared directly with a first lease.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,statistics,sys
from collections import defaultdict
from pathlib import Path

def read(p):return json.loads(p.read_text(encoding='utf8'))
def lines(p):return [json.loads(s) for s in p.read_text(encoding='utf8').splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8')
def csvsave(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf8') as f:
        if fields:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def name(s):return f"{s['pool']}-{s['arrival']}-{s['traffic']}-{s['label']}-r{s['repeat']}"

def marginal_rows(outcomes):
    values=[]
    for o in outcomes:
        for fraction,times,default in ((1-o.reject_fraction,o.early_row_times,o.early_row),
                                       (o.reject_fraction,o.late_row_times,o.late_row)):
            times=times or (default,)
            if fraction>0:values.extend((t,o.weight*fraction/len(times)) for t in times)
    assert abs(sum(w for _,w in values)-1.)<1e-8
    return values

def cdf(values,t):return sum(w for v,w in values if v<=t)

def decision_batches(events):
    pending=None;index=-1;result={}
    for e in events:
        if e['kind']=='ces-decision':
            index+=1
            if e['operation'] is not None:
                assert pending is None
                pending=index,e,[]
        elif e['kind']=='enqueue' and e['role']=='authority':
            assert pending is not None and e['session_id'] in pending[1]['sids']
            pending[2].append(e['job_id'])
        elif e['kind']=='batch-dispatched' and e['role']=='authority':
            assert pending is not None
            idx,d,jobs=pending;assert set(jobs)==set(e['job_ids'])
            key=frozenset(jobs);assert key not in result
            result[key]=(idx,d,e);pending=None
    assert pending is None
    return result

def diagnose_cell(C,spec):
    from revtrace.ces_v5_policy import V5Target,predict_batch,_weighted_quantile
    cfg=read(C/'config.json');result=read(C/'result.json');cal=cfg['ces_study']['calibration']
    assert result['fine_window_accounting_complete'] and result['decision'] in ('PASS_PROTOCOL_COMPLETENESS','TOKEN_LIMIT_BOUNDARY')
    assert cfg['rho']==1 and cfg['fine_seconds']==2
    events=lines(C/'events.jsonl');records=lines(C/'worker_records.jsonl')
    accounts=lines(C/'worker_batch_accounting.jsonl');views=lines(C/'consumer.jsonl')
    byid={r['job']['job_id']:r for r in records};mapping=decision_batches(events)
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    commits={e['job_id']:e for e in events if e['kind']=='commit'}
    batches=[];rows=[];scenarios=[];matched=set()
    for a in accounts:
        rs=[byid[jid] for jid in a['job_ids']]
        roles={r['job']['role'] for r in rs};assert len(roles)==1
        if roles!={'authority'}:continue
        key=frozenset(a['job_ids']);idx,d,dispatch=mapping[key];matched.add(key)
        now=d['observed_perf'];op=d['operation'];n=len(rs);sids={r['job']['session_id'] for r in rs}
        assert len(sids)==n and sids==set(d['sids'])
        assert all(r['job']['ces_operation']==op for r in rs)
        features={f['sid']:f for f in d['features']};ts=[]
        for r in rs:
            j=r['job'];assert j['audio_ready_perf']<=now<=j['enqueue_perf']
            if features:
                f=features[j['session_id']];assert f['window']==j['end_window']
                assert abs(f['ready']-j['audio_ready_perf'])<1e-9
                assert abs(f['audio_seconds']-j['audio_end_sample']/16000)<1e-9
                assert abs(f['interval_seconds']-(j['audio_end_sample']-j['audio_start_sample'])/16000)<1e-9
                assert f['prompt_tokens']==len(j['prompt_tokens'])
                ts.append(V5Target(**f))
            else:
                assert cfg['ces_study']['method'] in ('fine','standard') and op=='generate'
                # These baseline costs use only known immutable input shape.
                # Missing candidate/history fields are NOT guessed as facts.
                ts.append(V5Target(sid=j['session_id'],window=j['end_window'],ready=j['audio_ready_perf'],
                    deadline=j['audio_ready_perf']+cfg['ces_study']['commit_slo'],candidate_ready=False,
                    same_birth=False,previous_reject=False,candidate_tokens=0,descendant_count=0,
                    descendant_seconds=0.,candidate_eta=None,audio_seconds=j['audio_end_sample']/16000,
                    interval_seconds=(j['audio_end_sample']-j['audio_start_sample'])/16000,prompt_tokens=len(j['prompt_tokens'])))
        outcomes=predict_batch(cal,op,ts);values=marginal_rows(outcomes)
        pred=sum(o.weight*o.lease for o in outcomes);q90=_weighted_quantile([(o.lease,o.weight) for o in outcomes],.9)
        rowmean=sum(v*w for v,w in values);row90=_weighted_quantile(values,.9)
        lease=a['batch_drained_perf']-a['worker_started_perf']
        phasewall=sum(p['completed_perf']-p['started_perf'] for p in a['phases'])
        assert lease>=0 and phasewall>=0
        first_enqueue=min(r['job']['enqueue_perf'] for r in rs)
        fallback=sum(bool(r['result'].get('online_verification',{}).get('fallback_used',False)) for r in rs)
        proof=[r['result'].get('online_verification') for r in rs]
        if op=='verify':assert all(v is not None for v in proof)
        if op=='generate':assert not any(v is not None for v in proof)
        common={'cell':C.name,'label':spec['label'],'runtime_method':cfg['ces_study']['method'],
            'arrival':spec['arrival'],'traffic':spec['traffic'],'repeat':spec['repeat'],'decision':idx,
            'batch_id':a['batch_id'],'operation':op}
        batches.append(dict(common,rows=n,selected_row_ids=json.dumps(a['job_ids']),
            predicted_first_lease_mean_s=pred,predicted_first_lease_P90_s=q90,
            actual_full_worker_lease_s=lease,actual_minus_predicted_mean_s=lease-pred,
            actual_over_predicted_mean=lease/pred,actual_lease_within_predicted_P90=lease<=q90,
            actual_model_phase_wall_sum_s=phasewall,lease_minus_model_phase_wall_s=lease-phasewall,
            actual_batch_result_complete_after_start_s=a.get('batch_result_complete_perf',a['batch_drained_perf'])-a['worker_started_perf'],
            actual_physical_calls=len(a['phases']),actual_fallback_K=fallback,
            actual_fallback_calls=sum(p['phase']=='fresh-FP32-fallback' for p in a['phases']),
            actual_fallback_executed_rows=sum(p.get('physical_batch_rows',0) for p in a['phases'] if p['phase']=='fresh-FP32-fallback'),
            predicted_fallback_K_mean=n*sum(o.weight*o.reject_fraction for o in outcomes),
            predicted_any_fallback_probability=sum(o.weight for o in outcomes if o.reject_fraction>0),
            shared_row_CDF_mean_s=rowmean,shared_row_CDF_P90_s=row90,
            snapshot_to_first_enqueue_s=first_enqueue-now,
            actual_feature_wall_s=d['feature_wall_seconds'],actual_authority_planner_wall_s=d['planner_wall_seconds'],
            actual_first_enqueue_to_worker_start_s=a['worker_started_perf']-first_enqueue,
            reported_planned_seconds_complete_cut_not_comparable=d.get('planned_seconds'),
            reported_complete_cut_wall_not_comparable=d.get('expected_cut_wall_seconds'),
            predictor_scope='Same frozen risk predictor on actual selected batch; not all baseline policies used this predictor online',
            input_scope='Original observed target features' if features else 'Known dispatched input shape only; baseline had no target snapshot',
            cost_clock='Worker started to Batch-drained, not kernel active time'))
        for si,o in enumerate(outcomes):
            scenarios.append(dict(common,scenario=si,weight=o.weight,lease_s=o.lease,
                early_row_s=o.early_row,late_row_s=o.late_row,reject_fraction=o.reject_fraction,
                early_row_times=json.dumps(o.early_row_times),late_row_times=json.dumps(o.late_row_times),source=o.source))
        delivery=max(0.,float(cal.get('v5_risk_model',{}).get('owner_delivery_seconds',0.)))
        for r,t in zip(rs,ts):
            j=r['job'];z=r['result'];receipt=z['_row_receipt'];start=a['worker_started_perf'];render=z['completed_perf']
            assert abs(z['started_perf']-start)<1e-7 and abs(render-receipt['rendered_perf'])<1e-7
            commit=commits[j['job_id']];installed=t0+commit['installed']
            consumers=[v['observed_perf'] for v in views if v['session_id']==j['session_id'] and v['certified_frontier']>=j['audio_end_sample']]
            applied=min(consumers) if consumers else None
            D=j['audio_ready_perf']+cfg['ces_study']['display_slo'];Cdue=t.deadline
            rows.append(dict(common,job_id=j['job_id'],session=j['session_id'],window=j['end_window'],
                actual_fallback_used=z.get('online_verification',{}).get('fallback_used'),
                actual_row_terminal_after_start_s=receipt['terminal_perf']-start,
                actual_row_rendered_after_start_s=render-start,
                rendered_within_predicted_shared_row_P90=render-start<=row90,
                predicted_shared_row_CDF_at_actual_render=cdf(values,render-start),
                predicted_shared_row_mean_s=rowmean,predicted_shared_row_P90_s=row90,
                actual_render_to_emission_s=receipt['emitted_perf']-render,
                actual_render_to_owner_receive_s=z['received_perf']-render,
                actual_owner_receive_to_install_s=installed-z['received_perf'],
                actual_render_to_install_s=installed-render,
                actual_render_to_certified_consumer_s=None if applied is None else applied-render,
                shared_owner_delivery_allowance_s=delivery,
                actual_certified_consumer_within_allowance=None if applied is None else applied-render<=delivery,
                display_slack_at_snapshot_s=D-now,commit_slack_at_snapshot_s=Cdue-now,
                display_slack_at_enqueue_s=D-j['enqueue_perf'],commit_slack_at_enqueue_s=Cdue-j['enqueue_perf'],
                snapshot_to_enqueue_s=j['enqueue_perf']-now,
                display_deadline_crossed_during_snapshot_to_enqueue=now<=D<j['enqueue_perf'],
                commit_deadline_crossed_during_snapshot_to_enqueue=now<=Cdue<j['enqueue_perf'],
                predicted_commit_by_C_from_snapshot=cdf(values,Cdue-now-delivery),
                predicted_commit_by_C_conditional_actual_worker_start=cdf(values,Cdue-start-delivery),
                actual_commit_latency_s=installed-j['audio_ready_perf'],
                actual_commit_by_C=installed<=Cdue,
                row_CDF_scope='Exchangeable selected-row calibration, not identity-specific outcomes or independent per-row trials'))
    assert matched==set(mapping),'Every actual first Authority batch must be costed once'
    return batches,rows,scenarios

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('root','source','output'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--stage',default='formal');ap.add_argument('--audit-dir',type=Path)
    ap.add_argument('--plan',type=Path,default=Path(__file__).with_name('PLAN.smoke.json'))
    ap.add_argument('--source-manifest',type=Path,default=Path(__file__).with_name('SOURCE_MANIFEST.json'))
    a=ap.parse_args();plan=read(a.plan);specs=plan['stages'][a.stage]['cells']
    audit_dir=a.audit_dir or a.root/(a.stage+'_audit');audit=read(audit_dir/'SUMMARY.json')
    assert audit['status']=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT' and not audit['failures']
    assert audit['cells']==audit['expected_cells']==len(specs),'Wait for all formal cells and safety audit'
    manifest=read(a.source_manifest)
    assert sha(a.source_manifest)==plan['runtime_manifest_sha256'] and manifest['code_commit']==plan['runtime_commit']
    for f in manifest['files']:assert sha(a.source/f['path'])==f['sha256'],f['path']
    sys.path.insert(0,str(a.source/'src'))
    assert not a.output.exists(),'Use new diagnostics output; retain previous evidence'
    a.output.mkdir(parents=True);batches=[];rows=[];scenarios=[];inputs=[];failures=[]
    for spec in specs:
        C=a.root/a.stage/name(spec)
        try:
            for fn in ('config.json','result.json','events.jsonl','worker_records.jsonl','worker_batch_accounting.jsonl','consumer.jsonl'):
                p=C/fn;inputs.append({'cell':C.name,'file':fn,'sha256':sha(p),'bytes':p.stat().st_size})
            b,r,s=diagnose_cell(C,spec);batches.extend(b);rows.extend(r);scenarios.extend(s)
        except Exception as e:failures.append({'cell':C.name,'error':repr(e),'requested_cell_retained':True})
    groups=defaultdict(list)
    for b in batches:groups[b['label'],b['arrival'],b['traffic'],b['repeat'],b['operation']].append(b)
    group_rows=[]
    for key,bs in sorted(groups.items()):
        group_rows.append(dict(zip(('label','arrival','traffic','repeat','operation'),key),
            actual_selected_batches=len(bs),predicted_first_lease_mean_s=statistics.mean(b['predicted_first_lease_mean_s'] for b in bs),
            actual_full_lease_mean_s=statistics.mean(b['actual_full_worker_lease_s'] for b in bs),
            actual_minus_predicted_mean_s=statistics.mean(b['actual_minus_predicted_mean_s'] for b in bs),
            observed_lease_P90_coverage=sum(b['actual_lease_within_predicted_P90'] for b in bs)/len(bs),
            actual_fallback_rows=sum(b['actual_fallback_K'] for b in bs),
            predicted_fallback_rows=sum(b['predicted_fallback_K_mean'] for b in bs),
            selected_workload_not_same_batch_counterfactual=True))
    for fn,v in [('CHOSEN_FIRST_BATCH.csv',batches),('CHOSEN_ROW_CLOCKS.csv',rows),('PREDICTED_SCENARIOS.csv',scenarios),('CELL_OPERATION_CALIBRATION.csv',group_rows)]:csvsave(a.output/fn,v)
    report={'status':'PASS_ACTUAL_SELECTED_COST_DIAGNOSIS' if not failures else 'FAILED_CELL_DIAGNOSIS_NO_COMPLETE_CLAIM',
        'requested_cells':len(specs),'failures':failures,'actual_selected_batches':len(batches),'actual_selected_rows':len(rows),
        'new_GPU_calls':0,'unchosen_counterfactual_outcomes':'unknown','common_cut_is_not_first_batch':True,
        'row_training_clock':'completed_perf (trusted render complete) minus started_perf',
        'lease_training_clock':'batch_drained_perf minus worker_started_perf',
        'kernel_active_time':'not measured','scope':'selected-action calibration; no savings from subtracting host planner wall',
        'runtime_commit':manifest['code_commit'],'script_sha256':sha(Path(__file__)),'plan_sha256':sha(a.plan),
        'safety_audit_sha256':sha(audit_dir/'SUMMARY.json')}
    save(a.output/'SUMMARY.json',report);save(a.output/'INPUT_MANIFEST.json',inputs);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
