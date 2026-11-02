"""Complete frozen CPU12/NN16 accounting and bounded paper data.

No inclusive families are added. No null floor is subtracted. Semantic task
equality, work/Consumer counts and original/common energy windows stay explicit.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,statistics,struct,sys,traceback
from analysis_common import (OBSERVER,DRIVER,NN4F,SOURCES,need,read,put,sha,rows,
    canonical,csvout,disk,boot,verify_inventory,run_record,quantile)

COARSE=('WAL.complete_fact_commit','SUP.complete_consumer_apply','IO.actual_os_fsync')

def real_program_trace(path):
    previous='0'*64;sequence=0;selected=[];roots={}
    with pathlib.Path(path).open('rb') as f:
        while True:
            header=f.read(8)
            if not header:break
            need(len(header)==8 and header[:4]==b'RVN1','fact header invalid')
            n=struct.unpack('>I',header[4:])[0];need(n<=16*1024*1024,'fact too large')
            payload=f.read(n);checksum=f.read(32)
            need(len(payload)==n and hashlib.sha256(payload).digest()==checksum,'fact checksum invalid')
            obj=json.loads(payload);need(canonical(obj)==payload and obj['sequence']==sequence+1 and obj['previous']==previous,'fact chain changed')
            sequence+=1;previous=checksum.hex()
            if obj['kind']=='genesis':need(sequence==1,'genesis ordering');roots=obj['body']['initials'];continue
            need(obj['kind']=='canonical','unexpected fact kind');b=obj['body'];r=b['record'];j=b['job'];sid=b['source_id']
            need(roots[sid]==b['parent_state'] and j['start']==b['parent_state'] and j['source_id']==sid and j['end']==b['next_state']['frontier'],'owned complete fact chain invalid')
            need(r['start_state']==hashlib.sha256(canonical(b['parent_state'])).hexdigest() and r['end_state']==hashlib.sha256(canonical(b['next_state'])).hexdigest(),'complete state digest mismatch')
            need(r['role']=='authority' and r['candidate_handoff'] is False,'original full call authority missing')
            roots[sid]=b['next_state']
            selected.append(dict(source_id=sid,parent_state=b['parent_state'],next_state=b['next_state'],token_ids=r['token_ids'],selected_correction=r['selected_correction'],native_model_evaluated=r['native_model_evaluated']))
    return dict(selected_steps=len(selected),selected_program_sha256=hashlib.sha256(canonical(selected)).hexdigest(),
        digest_scope='complete selected parent/next states, original C, IDs and evaluated flag; excludes scheduling IDs/timestamps, whose bindings are independently checked')

def integral(path,start,end):
    values=list(rows(path));by={}
    for gpu in ('0','1'):
        pts=sorted((r['time'],r['boards'][gpu]['watts']) for r in values)
        need(len(pts)>=2 and pts[0][0]<=start<=end<=pts[-1][0],'external power window not bracketed')
        total=0.
        for (a,x),(b,y) in zip(pts,pts[1:]):
            left=max(a,start);right=min(b,end)
            if right<=left:continue
            need(b>a,'power timestamps not advancing')
            lo=x+(y-x)*(left-a)/(b-a);hi=x+(y-x)*(right-a)/(b-a);total+=(lo+hi)*(right-left)/2
        by[gpu]=total
    return sum(by.values()),by,values

def executor_account(path):
    counts=collections.Counter();intervals=collections.defaultdict(list);ready=[]
    for row in rows(path):
        e=row['event'];kind=e['kind'];counts[kind]+=1
        if kind=='ready':ready.append(e);continue
        if kind=='completed':
            r=e['record'];counts['completed_native_model_evaluated']+=int(r['native_model_evaluated'])
            a,b=r['worker_job_begin_perf'],r['worker_job_end_perf']
        elif kind=='abandoned':a,b=e['worker_job_begin_perf'],e['worker_job_end_perf']
        else:continue
        need(b>=a,'negative actual worker host interval')
        intervals[(row['physical_slot'],row['physical_incarnation'])].append((a,b))
    totals={}
    for key,spans in intervals.items():
        spans.sort();merged=[]
        for a,b in spans:
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        totals[str(key)]=sum(b-a for a,b in merged)
    return dict(counts=dict(counts),per_worker_host_interval_seconds=totals,
        cumulative_worker_host_intervals_seconds=sum(totals.values()),
        host_intervals_not_CUDA_kernel_time_or_serving_wall=True,initial_READY_workers=len(ready))

def family_row(phase,cell,meta,label,count,wall_ns,thread_ns,exclusive_ns,floor):
    need(count>0,'empty measured family')
    mw=wall_ns/count;mt=thread_ns/count
    return dict(phase=phase,cell_id=cell['cell_id'],source_id=cell['source_id'],policy=cell['arm'],repeat=cell['repeat'],
        observation=cell.get('observation',True),role=meta,label=label,count=count,
        observed_mean_wall_ms=mw/1e6,observed_mean_thread_cpu_ms=mt/1e6,
        observed_thread_cpu_median_ms=None,file_name=None,
        inclusive_wall_ms=wall_ns/1e6,exclusive_thread_cpu_ms=exclusive_ns/1e6,
        near_null_wall_floor=mw<=10*floor['wall_ns'],near_null_CPU_floor=mt<=10*floor['thread_cpu_ns'],
        floor_classification='heuristic10x null reference; not error bound',floor_subtracted=False,
        wall_CPU_same_bracket=False,independent_lock_wait=None,
        account='standalone real-object probe' if label.startswith('REPLAY_COMPONENT') or (phase=='cpu' and label.startswith('IDENTITY.')) else 'complete-object CPU replay' if phase=='cpu' else 'actual NN observed path')

def run(args):
    plan=read(args.config);identity,pre=boot(args.manifest,args.prelaunch,args.config);verify_inventory(plan['inputs'])
    cpu_root=pathlib.Path(plan['cpu_campaign']);nn_root=pathlib.Path(plan['nn_campaign'])
    cpu=read(cpu_root/'SUMMARY.json');nn=read(nn_root/'SUMMARY.json');matrix=read(nn_root/'CONFIG.json')
    need(cpu['status']=='COMPLETE_FROZEN_COST_CPU_CAMPAIGN' and len(cpu['cells'])==12,'CPU12 incomplete')
    need(nn['status']=='COMPLETE_FROZEN_COST_NN_CAMPAIGN' and len(nn['cells'])==16,'NN16 incomplete')
    need(read(cpu_root/'CONFIG.json')==matrix and tuple(matrix['fixed_sources'])==SOURCES,'phase plans or fixed sources differ')
    need(read(cpu_root/'ENVIRONMENT.json')['identity']['driver']['source_commit']==DRIVER and read(nn_root/'ENVIRONMENT.json')['identity']['driver']['source_commit']==DRIVER,'actual campaign driver changed')
    need(set(pre['calibration_inputs'])=={plan['calibration_summary'],plan['calibration_gate']},'Root must freeze both terminal calibration inputs in prelaunch')
    verify_inventory(pre['calibration_inputs'])
    calibration=read(plan['calibration_summary']);need(read(plan['calibration_gate'])['status']=='PASS_FIXED_NULL_TARGET_CLOCK_CALIBRATION','clock calibration missing')
    need(calibration['observer_source']==OBSERVER and calibration['loops']==4096 and calibration['repeats']==8,'wrong calibration scope')
    floor={k:statistics.median(r['wrapped_inner_spans'][k]['median'] for r in calibration['repeats_data']) for k in ('wall_ns','thread_cpu_ns','process_cpu_ns')}
    calibration_inputs={p:sha(p) for p in (plan['calibration_summary'],plan['calibration_gate'])}
    cpu_by={c['cell_id']:c for c in matrix['cpu_cases']};nn_by={c['cell_id']:c for c in matrix['cells']}
    need(set(cpu_by)=={c['cell_id'] for c in cpu['cells']} and set(nn_by)=={c['cell_id'] for c in nn['cells']},'frozen cost matrix IDs differ')
    out=disk(plan['raw_result_location']);out.mkdir(parents=True,exist_ok=False)
    run_record(out,plan['experiment_id'],identity,plan,dict(python=sys.version,executable=sys.executable,analysis_source=identity,observer_source=OBSERVER,driver_source=DRIVER,actual_NN_source=NN4F,calibration_inputs=calibration_inputs))
    families=[];nn_cells=[];audits=[];cpu_checks=[]
    try:
        for c in cpu['cells']:
            cell=cpu_by[c['cell_id']];s=c['summary'];m=c['span_audit']['metadata'];raw=pathlib.Path(c['raw_result_location'])
            need(s['actual_nn_source']==NN4F and s['observer_source_commit']==OBSERVER and s['original_inputs_unchanged'] and s['actual_fsync_enabled'],'CPU replay identity/durability changed')
            need(c['gate']['decision']=='PASS_REAL_COMPLETE_OBJECT_FACT_AND_CONSUMER_REPLAY' and sha(raw/'facts.wal')==s['original_and_replayed_facts_sha256'],'CPU full original journal check missing')
            need(sha(raw/'DRIVER_SPAN_AUDIT.json')==c['span_audit']['summary_sha256'] and not m['overflow'],'CPU span audit changed')
            for label,v in m['families'].items():
                families.append(family_row('cpu',cell,m['role'],label,v['count'],v['inclusive_wall_ns'],v['inclusive_thread_cpu_ns'],v['exclusive_thread_cpu_ns'],floor))
            cpu_checks.append(dict(cell_id=c['cell_id'],source_id=cell['source_id'],policy=cell['arm'],repeat=cell['repeat'],selected_steps=s['original_selected_transitions'],Consumer_applications=s['actual_consumer_rows'],owned_call_probes=s['owned_binding_probes'],full_input_probes=s['complete_input_pair_probes'],whole_journal_SHA_equal=True))
        for c in nn['cells']:
            cell=nn_by[c['cell_id']];raw=pathlib.Path(c['raw_result_location']);cfg=read(raw/'CONFIG.json');primary=c['primary']
            need(cfg['settings']['source_commit']==NN4F and cfg['cost_observer']['observer_source_commit']==OBSERVER and cfg['cost_observer']['enabled'] is cell['observation'],'NN execution role/mode mismatch')
            need(read(raw/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK' and sha(raw/'SUMMARY.json')==c['summary_sha256'],'original NN task gate changed')
            need(c['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE','original selected task/reference audit missing')
            trace=real_program_trace(raw/'facts.wal');need(trace['selected_steps']==c['semantic']['checked_steps'],'selected transition count differs')
            origin=read(raw/'ORIGIN.json')['origin_perf'];end=read(raw/'SERVICE_END.json')['service_end_perf']
            e=c['common_external_energy'];common=e['origin_to_confirmed_physical_model_drain'];drain=e['physical_drain_observation']
            need(common['begin_perf']==origin and common['end_perf']==drain['confirmed_perf'],'shared energy origin/drain differs')
            need(abs(common['seconds']-(drain['confirmed_perf']-origin))<1e-9,'shared energy duration differs')
            joules,boards,powerrows=integral(nn_root/'external'/(c['cell_id']+'.jsonl'),origin,drain['confirmed_perf'])
            need(abs(joules-common['total_joules'])<=max(1e-7,abs(joules)*1e-12),'independent common energy integral differs')
            need(all(abs(boards[g]-common['board_joules'][g])<=max(1e-7,abs(boards[g])*1e-12) for g in boards),'per-board integral differs')
            witness=[r for r in powerrows if r['observation_end_perf']==drain['confirmed_perf']]
            need(len(witness)==1 and not witness[0]['compute_processes'] and len(witness[0]['worker_process_states'])>=2 and all(v in ('absent','Z','X') for v in witness[0]['worker_process_states'].values()),'external physical drain witness incomplete')
            cons=list(rows(raw/'consumer.jsonl'));pub=list(rows(raw/'publications.jsonl'));roles=collections.Counter(r['kind'] for r in cons)
            executor=executor_account(raw/'owner_e0/worker_results.jsonl')
            need(executor['initial_READY_workers']==2 and len(cons)==len(pub),'normal actual worker/Consumer coverage changed')
            span=read(raw/'DRIVER_SPAN_AUDIT.json');need(sha(raw/'DRIVER_SPAN_AUDIT.json')==c['span_audit']['summary_sha256'],'actual NN span summary changed')
            owner_export=None
            for m in span['observer']:
                need(m['enabled'] is cell['observation'] and not m['overflow'],'NN span export invalid')
                if m['role']=='owner':owner_export=(m['export_end_ns_before_summary_write']-m['export_start_ns'])/1e6
            for v in span['families']:
                # These are strict service-window-contained samples, never all
                # startup/analysis spans or fabricated partial-CPU prorations.
                families.append(family_row('nn',cell,v['role'],v['label'],v['count'],v['inclusive_wall_ms']*1e6,
                    # Frozen summarizer has median thread CPU and exclusive sum,
                    # not inclusive thread sum: take the latter from raw roles
                    # only when not claiming per-service-call CPU mean.
                    0.,v['exclusive_thread_cpu_ms']*1e6,floor))
                families[-1]['observed_mean_thread_cpu_ms']=None
                families[-1]['near_null_CPU_floor']=None
                families[-1]['observed_thread_cpu_median_ms']=v['thread_cpu_us_median']/1000
                families[-1]['file_name']=v['file_name']
            row=dict(cell_id=c['cell_id'],source_id=cell['source_id'],policy=cell['arm'],repeat=cell['repeat'],observation=cell['observation'],
                offered_audio_s=primary['offered_audio_seconds'],offered_frontiers=primary['offered_frontiers'],D99_s=primary['primary_linear_all_offered_D99'],C99_s=primary['primary_linear_all_offered_C99'],
                dual_deadline_credit_audio_s=primary['dual_deadline_audio_credit_seconds'],D2_misses=primary['D2_misses_all_offered'],C8_misses=primary['C8_misses_all_offered'],EOS_D2_misses=primary['EOS_D2_misses'],whole_run_pass=primary['complete_coverage_and_original_quantile_pass'],
                physical_drain_window_s=common['seconds'],common_both_board_J=joules,board0_J=boards['0'],board1_J=boards['1'],original_SERVICE_END_window_s=end-origin,
                owner_export_ms_lower_bound_before_summary_write=owner_export,selected_program_sha256=trace['selected_program_sha256'],selected_steps=trace['selected_steps'],
                Consumer_applications=len(cons),canonical_Consumer_rows=roles['canonical'],private_Consumer_rows=roles['private'],publication_count=len(pub),
                completed_worker_jobs=executor['counts'].get('completed',0),abandoned_ASR_prefix_jobs=executor['counts'].get('abandoned',0),completed_model_evaluated=executor['counts'].get('completed_native_model_evaluated',0),
                cumulative_worker_host_intervals_s=executor['cumulative_worker_host_intervals_seconds'],raw_result_location=str(raw),actual_trace_checker_status='ROOT_SEPARATE_RECHECK_NOT_INFERRED_FROM_TASK_PASS')
            nn_cells.append(row);audits.append(dict(cell_id=c['cell_id'],trace=trace,executor=executor,external_drain_witness=drain))
        by={(r['source_id'],r['policy'],r['repeat'],r['observation']):r for r in nn_cells};pairs=[]
        for sid in SOURCES:
            for policy in ('conservative','fullcall'):
                for repeat in range(2):
                    off,on=by[(sid,policy,repeat,False)],by[(sid,policy,repeat,True)]
                    pair=dict(source_id=sid,policy=policy,repeat=repeat,off_cell=off['cell_id'],on_cell=on['cell_id'],same_selected_program=off['selected_program_sha256']==on['selected_program_sha256'],same_offered=off['offered_audio_s']==on['offered_audio_s'],
                        interpretation='total observation impact; may include scheduling changes and Owner export; not protocol removal tax')
                    for key in ('D99_s','C99_s','dual_deadline_credit_audio_s','common_both_board_J','physical_drain_window_s','completed_worker_jobs','abandoned_ASR_prefix_jobs','publication_count','EOS_D2_misses'):
                        pair[key+'_on_minus_off']=None if None in (off[key],on[key]) else on[key]-off[key]
                    pairs.append(pair)
        need(len(pairs)==8 and all(p['same_offered'] for p in pairs),'complete eight off/on pairs missing')
        coarse=[r for r in families if r['label'] in COARSE];group=collections.defaultdict(list)
        for r in coarse:group[(r['phase'],r['source_id'],r['policy'],r['role'],r['label'])].append(r)
        paper=[]
        for key,values in sorted(group.items()):
            means=[r['observed_mean_wall_ms'] for r in values]
            paper.append(dict(phase=key[0],source_id=key[1],policy=key[2],role=key[3],family=key[4],fresh_runs=len(values),
                observed_run_mean_wall_ms_min=min(means),observed_run_mean_wall_ms_median=statistics.median(means),observed_run_mean_wall_ms_max=max(means),
                call_counts_by_run=','.join(str(r['count']) for r in sorted(values,key=lambda r:r['repeat'])),
                units_and_scope='observed ms/call; range across fresh runs; inclusive families are separate',floor_subtracted=False))
        csvout(out/'CPU_REAL_OBJECT_CHECKS.csv',cpu_checks);csvout(out/'NN_CELLS.csv',nn_cells);csvout(out/'OBSERVATION_PAIRS.csv',pairs)
        csvout(out/'UNSUBTRACTED_FAMILY_FOOTPRINTS.csv',families);csvout(out/'PAPER_COARSE_FOOTPRINT.csv',paper)
        verify_inventory(plan['inputs']);verify_inventory(pre['calibration_inputs']);need(all(sha(p)==s for p,s in calibration_inputs.items()),'calibration changed during aggregation')
        same=all(p['same_selected_program'] for p in pairs)
        data=dict(status='PASS_COMPLETE_CPU12_NN16_UNSUBTRACTED_COST_ACCOUNTING' if same else 'PAIR_SELECTED_TRACE_DIFFERENCE_REQUIRES_DIAGNOSIS',analysis_source=identity['source_commit'],observer_source=OBSERVER,driver_source=DRIVER,actual_NN_source=NN4F,
            CPU_fresh_replays=12,NN_trials=16,off_on_pairs=8,independent_sources=2,clock_floor_reference_ns=floor,calibration_inputs=calibration_inputs,
            pair_selected_program_equal=all(p['same_selected_program'] for p in pairs),coarse_table=paper,NN_cells=nn_cells,off_on_pairs_data=pairs,raw_audit_details=audits,
            no_floor_subtraction=True,no_inclusive_family_sum=True,no_parallel_wall_sum=True,lock_wait_measured=False,
            whole_safety_actual_trace_counts='Root separate c4 check; never promoted from current task/reference PASS',
            limits=['CPU replay is not live scheduling or serving','standalone probes use real objects outside original Owner occupancy','short-function clock brackets differ; microsecond accuracy not claimed','off/on is observation impact, not net protocol overhead','two reused previously measured sources are not a new independent-generalization bank','timing repeats do not increase acoustic independent units or estimate production prevalence','NVML board energy excludes CPU/PSU and uses an upper observation bound for physical drain'])
        put(out/'PAPER_DATA.json',data);put(out/'SUMMARY.json',data)
        (out/'UNSUBTRACTED_FOOTPRINT_SCOPE.md').write_text(
            'These tables report observed, unsubtracted function footprints. Complete FactStore commits, whole Consumer applications and actual fsync are separate inclusive families; their times are not added. '
            'The original 3cf observer brackets wall time inside two CPU-clock reads, so a very short call may show CPU greater than wall without negative business blocking. Null-target calibration diagnoses this floor and is never subtracted. '
            'CPU complete-object replay, standalone full-input/identity probes and actual NN path spans remain separate. The eight off/on pairs measure total observation effects under the original task, including scheduling changes and Owner export before original SERVICE_END. '
            'The actual shared energy window runs from original origin through externally confirmed physical model drain. Original task/reference and Consumer checks do not replace Root’s separately frozen actual-trace refinement audit.\n',encoding='utf8')
        put(out/'GATE.json',dict(status=data['status'],pair_selected_program_equal=data['pair_selected_program_equal'],Root_actual_trace_safety_check_separate=True))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_COST_AGGREGATION_PRESERVED',failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('config','manifest','prelaunch'):p.add_argument('--'+n,required=True)
    run(p.parse_args())
