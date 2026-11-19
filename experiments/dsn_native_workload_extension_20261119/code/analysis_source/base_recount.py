"""Independent final arithmetic over two CLOSED, fully mirrored campaigns.

No runtime/audit/controller imports, neural packages, network, or new schedules.
Refuses incomplete counts before producing any final point estimate.
"""
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,pathlib,statistics,sys

E=pathlib.Path(__file__).resolve().parents[1]
NN='11453433c154aeffbff703c4c8dc9697421430e1'
COMPLETE='COMPLETE_NATIVE_FACTORIAL_AND_CONSERVATIVE_TASK_AND_ENDPOINTS'
CONDITIONS=('r0s0','r0s1','r1s0','r1s1','conservative_s1')
SETTINGS={'r0s0':('ready_only',False),'r0s1':('ready_only',True),
          'r1s0':('fullcall',False),'r1s1':('fullcall',True),'conservative_s1':('conservative',True)}
COUNTS=('canonical_applications','nonempty_ahead_canonical_applications','compatible_ahead_applications',
        'compatible_ahead_preserved','compatible_ahead_changed','refuted_ahead_applications',
        'missing_witness_ahead_applications','total_withdrawals','avoidable_withdrawals',
        'necessary_withdrawals','unknown_withdrawals','actual_consumer_rows',
        'gap_right_censored_windows','gap_boundary_truncated_windows','gap_restored_windows')
AREAS=('removed_audio_seconds','avoidable_removed_audio_seconds','necessary_removed_audio_seconds',
       'unknown_removed_audio_seconds','total_gap_audio_seconds_x_wall_seconds',
       'avoidable_gap_audio_seconds_x_wall_seconds','necessary_gap_audio_seconds_x_wall_seconds',
       'unknown_gap_audio_seconds_x_wall_seconds','same_root_avoidable_gap_audio_seconds_x_wall_seconds',
       'same_root_necessary_gap_audio_seconds_x_wall_seconds','same_root_unknown_gap_audio_seconds_x_wall_seconds',
       'observed_loss_window_union_area_audio_seconds_x_wall_seconds')
EFFECT_METRICS=('credit_audio_s','worker_seconds','both_board_J','avoidable_withdrawals',
                'necessary_withdrawals','unknown_withdrawals','removed_audio_seconds',
                'total_gap_audio_seconds_x_wall_seconds','avoidable_gap_audio_seconds_x_wall_seconds')
INPUTS={}

class NotReady(RuntimeError):pass

def need(ok,message):
    if not ok:raise ValueError(message)

def read(path):
    path=pathlib.Path(path)
    if not path.is_file():raise NotReady('Required mirror file missing: '+str(path))
    raw=path.read_bytes();INPUTS[str(path)]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    return json.loads(raw)

def finite(value,name,minimum=0.):
    need(not isinstance(value,bool)and isinstance(value,(int,float))and math.isfinite(value)and value>=minimum,'invalid '+name)
    return value

def close(a,b,name,tol=1e-7):need(abs(a-b)<=tol*max(1.,abs(a),abs(b)),'different '+name+': '+str((a,b)))

def quantile(values,q):
    values=sorted(values);position=(len(values)-1)*q;i=int(position);j=min(i+1,len(values)-1)
    return math.inf if math.isinf(values[j])else values[i]+(values[j]-values[i])*(position-i)

def nullable_equal(actual,expected,name):
    if math.isinf(expected):need(actual is None,name+' missing infinity marker')
    else:close(actual,expected,name)

def endpoint_recount(primary,source,origin):
    rows=primary['frontiers'];frames=source['frames'];ends=list(range(8000,frames,8000))+[frames]
    need(len(rows)==len(ends),'original offered-frontier count differs')
    ds=[];cs=[];weights=[];previous=0;credit=0.
    for row,F in zip(rows,ends):
        need(row['source_id']==source['source_id']and row['frontier']==F,'frontier/source cadence differs')
        need(type(row['is_EOS'])is bool and row['is_EOS']==(F==frames),'EOS classification differs')
        w=(F-previous)/16000;previous=F;weights.append(w);close(row['audio_seconds'],w,'original interval weight')
        close(row['offer'],origin+F/16000,'original interval ready clock')
        d=math.inf if row['D']is None else finite(row['D'],'D')
        c=math.inf if row['C']is None else finite(row['C'],'C')
        need(type(row['D2'])is bool and row['D2']==(d<=2.),'D2 indicator differs')
        need(type(row['C8'])is bool and row['C8']==(c<=8.),'C8 indicator differs')
        ds.append(d);cs.append(c)
        if d<=2. and c<=8.:credit+=w
    d99,c99=quantile(ds,.99),quantile(cs,.99)
    expected=dict(offered_frontiers=len(ends),offered_audio_seconds=sum(weights),
        dual_deadline_audio_credit_seconds=credit,D2_misses_all_offered=sum(x>2. for x in ds),
        C8_misses_all_offered=sum(x>8. for x in cs),missing_D_frontiers=sum(math.isinf(x)for x in ds),
        missing_C_frontiers=sum(math.isinf(x)for x in cs),EOS_D2_misses=int(ds[-1]>2.),
        original_quantile_test_pass=d99<=2. and c99<=8.,
        complete_coverage_and_original_quantile_pass=all(math.isfinite(x)for x in ds+cs)and d99<=2. and c99<=8.)
    for key,value in expected.items():
        if isinstance(value,bool):need(primary[key]is value,'different primary '+key)
        elif isinstance(value,int):need(primary[key]==value,'different primary '+key)
        else:close(primary[key],value,'primary '+key)
    nullable_equal(primary['primary_linear_all_offered_D99'],d99,'D99')
    nullable_equal(primary['primary_linear_all_offered_C99'],c99,'C99')
    return expected

def factorial(values):
    y00,y01,y10,y11=(values[c]for c in CONDITIONS[:4])
    return dict(interaction=y11-y10-y01+y00,S_at_R0=y01-y00,S_at_R1=y11-y10,
        R_at_S0=y10-y00,R_at_S1=y11-y01,joint_minus_snapshot=y11-y00,
        joint_minus_conservative=y11-values['conservative_s1'],
        ready_S1_minus_conservative=y01-values['conservative_s1'])

def paired_diagnostic(values):
    """All eight sources retained, including zero effects; repeated timing rows travel together."""
    values=list(values);n=len(values);need(n==8,'diagnostic must retain all eight source clusters')
    observed=abs(math.fsum(values));tol=1e-9*max(1.,observed)
    extreme=sum(abs(math.fsum(s*v for s,v in zip(signs,values)))>=observed-tol
                for signs in itertools.product((-1,1),repeat=n))
    return dict(source_clusters=n,positive=sum(v>1e-9 for v in values),zero=sum(abs(v)<=1e-9 for v in values),
        negative=sum(v< -1e-9 for v in values),observed_sum=math.fsum(values),assignments=2**n,
        two_sided_extreme_assignments=extreme,conditional_sign_fraction=extreme/2**n,
        scope='Descriptive sign-label enumeration of these fixed eight source pairs; zero effects kept and both timing repeats kept together; no population/deployment significance guarantee.')

def load_reference(folder,expected_nn):
    receipt=read(folder/'REFERENCE_RECEIPT.json');gate=read(folder/'GATE.json');summary=read(folder/'SUMMARY.json')
    need(gate['status']==receipt['status']==summary['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES','reference gate failed')
    for obj in (receipt,gate,summary):
        need(obj['actual_NN_source_commit']==expected_nn,'reference execution source differs')
        need(obj['reference_only']is True and obj['actual_serving_runs']==0,'reference cost mixed with serving')
    need(gate['all_original_full_state_C_IDs_equal']is True,'original state/C/IDs reference failed')
    sources={s['source_id']:s for s in receipt['sources']};need(len(sources)==8 and len({s['speaker_id']for s in sources.values()})==8,'reference speaker bank differs')
    steps=sum((s['frames']+7999)//8000 for s in sources.values());need(steps==141,'original reference-step denominator differs')
    need(gate['expected_sources']==gate['completed_sources']==8 and gate['expected_original_steps']==141,'reference incomplete')
    need(receipt['original_continuous_no_between_step_restore']is True and receipt['restored_repeats_per_edge']==2,'continuous/restored reference contract differs')
    ledger=receipt['ledger'];need(ledger['continuous_original_step_completed']==141 and ledger['restored_original_input_full_step_completed']==282,'reference continuous/restore ledger incomplete')
    for key,filename in [('reference_details','REFERENCE_DETAILS.json'),('reference_gate','GATE.json'),('genesis','GENESIS.json')]:
        read(folder/filename);need(INPUTS[str(folder/filename)]['sha256']==receipt[key]['sha256'],'reference artifact SHA differs: '+key)
    return receipt,sources

def energy_window_binding(cell,native,origin,end,events):
    """Bind independently defined GPU-drain and runtime-completion windows.

    Physical model workers may have exited before the Supervisor finishes
    Owner joining/FIFO/bookkeeping. Neither observer clock orders the other.
    """
    common=cell['common_external_energy'];energy=common['origin_to_confirmed_physical_model_drain']
    drain=common['physical_drain_observation'];confirmed=finite(drain['confirmed_perf'],'external physical-drain confirmation')
    observation_begin=finite(drain['observation_begin_perf'],'external drain observation begin')
    runtime_end=finite(end['service_end_perf'],'runtime completion marker');origin_perf=finite(origin['origin_perf'],'service origin')
    need(confirmed>=origin_perf and observation_begin<=confirmed,'external physical-drain window has invalid bounds')
    need(energy['begin_perf']==origin_perf and energy['end_perf']==confirmed,'external energy window is not bound to origin and physical drain')
    close(energy['seconds'],confirmed-origin_perf,'external physical-drain window duration')
    pids=set(drain['worker_pids']);ownership=cell['sampled_energy_ownership'];ready=set(cell['actual_READY_gate']['worker_pids'])
    need(len(pids)==2 and pids==set(ownership['actual_READY_pids'])==ready,'physical-drain proof is not for the two actual READY model workers')
    need(events,'actual canonical Consumer events missing')
    last_canonical=max(finite(e['observed'],'actual canonical application time')for e in events)
    need(last_canonical<=confirmed,'external model-drain energy window ends before actual final canonical application')
    eos=[f for f in cell['primary']['frontiers']if f['is_EOS']]
    need(eos and all(f['C']is not None for f in eos),'actual certified EOS clock missing')
    eos_consumed=max(f['offer']+finite(f['C'],'original EOS certification latency')for f in eos)
    need(eos_consumed<=confirmed+1e-7,'external model-drain energy window ends before useful certified EOS')
    original=common['original_source_energy']
    need(original==native['energy'],'preserved original runtime energy object differs')
    need(original['status']=='PASS_ACTUAL_BOTH_BOARD_SERVICE_INTERVAL','original runtime energy interval unavailable')
    need(original['origin_perf']==origin_perf and original['service_end_perf']==runtime_end,'original energy is not bound to its own runtime service window')
    need(set(original['service']['gpu_joules'])=={'0','1'},'original source energy misses a physical board')
    close(original['service']['total_joules'],sum(original['service']['gpu_joules'].values()),'original both-board energy sum')
    return dict(service_origin_perf=origin_perf,external_observation_begin_perf=observation_begin,
        external_physical_drain_perf=confirmed,runtime_service_end_perf=runtime_end,
        runtime_end_minus_external_drain_seconds=runtime_end-confirmed,
        last_canonical_application_perf=last_canonical,certified_EOS_consume_perf=eos_consumed,
        actual_READY_worker_pids=sorted(pids),original_source_energy=original,
        scope='External both-board energy ends at the first recorded confirmation of model-worker exit/CUDA emptiness. Original source energy ends at runtime SERVICE_END after Owner/Supervisor completion. Both are preserved separately; different observers/windows are not subtracted as CPU-stage energy.')

def check_cell(campaign,cell,planned,source,plan,reference_sha):
    cid=cell['cell_id'];raw=campaign/'cells'/cid
    cfg=read(raw/'CONFIG.json');gate=read(raw/'GATE.json');native=read(raw/'SUMMARY.json');origin=read(raw/'ORIGIN.json');end=read(raw/'SERVICE_END.json')
    external=read(raw/'EXTERNAL_FACTORIAL_AUDIT.json');view=read(raw/'INDEPENDENT_VIEW_AUDIT.json')
    job=read(raw/'JOB_ACCOUNTING.json');worker=read(raw/'WORKER_TIMER_LEDGER.json');ownership=read(raw/'SAMPLED_ENERGY_OWNERSHIP.json')
    view_summary=read(raw/'view_audit/SUMMARY.json');view_gate=read(raw/'view_audit/GATE.json')
    events=read(raw/'view_audit/CANONICAL_SUPPORT_EVENTS.json');windows=read(raw/'view_audit/OBSERVED_LOSS_WINDOWS.json')
    need(external==cell,'per-cell external audit differs from final campaign summary')
    need(view==view_summary==cell['view_audit'],'per-cell view audit differs from closed summary')
    need(gate['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK','original trial technical/task gate failed')
    need(gate['cell_id']==view['cell_id']==cid,'per-cell technical/audit identity differs')
    need(native['gate']=='PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT','native original endpoint gate failed')
    need(gate['source_commit']==plan['actual_NN']['source_commit'],'actual trial gate source differs')
    need(view['status']==view_gate['status']=='PASS_NATIVE_VIEW_APPLICATION_AUDIT','view application gate failed')
    condition=cell['condition'];strategy,retain=SETTINGS[condition]
    need(cell['strategy']==cfg['arm']==planned['strategy']==strategy,'underlying retention strategy differs')
    need(cfg['consumer_retain_views']is retain and cell['consumer_retain_views']is retain,'actual S flag differs')
    need(view['consumer_retain_views']is retain,'independent view audit used the wrong S flag')
    need(view_gate['consumer_retain_views']is retain,'view gate used the wrong S flag')
    need(cfg.get('condition',condition)==condition and cfg['cell_id']==cid,'configuration condition/cell differs')
    need(cfg['source_commit']==cfg['settings']['source_commit']==view['runtime_execution_commit']==plan['actual_NN']['source_commit'],'actual source roles differ')
    need(cfg['repeat']==cell['repeat']==planned['repeat']and cfg['settings']['primary_gpu']==planned['primary_gpu']==cell['repeat'],'fresh-repeat/physical primary changed')
    need(cfg['fault']['kind']=='none'and cfg['reference_kind']=='strict'and'cost_observer'not in cfg,'frozen fault/reference/observer contract changed')
    need(cfg['settings']['corrector_dtype']=='float32'and cfg['settings']['max_ahead_frames']==32000,'precision/ahead contract changed')
    actual=cfg['settings']['sources'];need(len(actual)==1,'one source per original cell required')
    for key in ('source_id','path','audio_sha256','frames'):need(actual[0][key]==source[key],'immutable input differs: '+key)
    need(cfg['reference_details_sha256']==reference_sha,'cell original-reference bytes differ')
    frozen_path=E/'plans/configs'/campaign.name/pathlib.PurePosixPath(planned['config']).name
    frozen_cfg=read(frozen_path);need(frozen_cfg==cfg,'actual configuration differs from frozen input')
    need(INPUTS[str(frozen_path)]['sha256']==planned['config_sha256'],'frozen configuration SHA differs')
    need(job['status']=='PASS_DISJOINT_JOB_ACCOUNTING'and worker['status']=='PASS_COMPLETE_WORKER_TERMINAL_TIMER_LEDGER','original terminal/timer accounting failed')
    for key in ('dispatches','counts','partition_count','Owner_admitted_ready_reuse','unique_promoted_jobs'):
        need(job.get(key)==cell['job_accounting'].get(key)==view['job_accounting'].get(key),'job-accounting binding differs: '+key)
    need(job['dispatches']==job['partition_count']==worker['unique_jobs'],'dispatch/terminal conservation differs')
    need(worker['missing_worker_timers']==0,'worker occupation has missing measurements')
    for key in ('status','worker_seconds','observed_infer_seconds','total_infer_seconds','missing_worker_timers','missing_infer_timers','unique_jobs','duplicate_terminals'):
        need(worker.get(key)==cell['worker_ledger'].get(key),'worker-ledger binding differs: '+key)
    if worker['missing_infer_timers']:need(worker['total_infer_seconds']is None,'missing inference timer replaced by zero')
    need(ownership==cell['sampled_energy_ownership'],'energy ownership binding differs')
    need(ownership['status']=='PASS_SAMPLED_TWO_BOARD_OWNED_WORKER_WINDOW'and ownership['foreign_compute_PID_samples']==0,'sampled energy ownership failed')
    need(ownership['gpu_uuids']==plan['gpu_uuids'],'physical board UUID differs')
    need(cell['actual_READY_gate']['status'].startswith('PASS'),'actual neural READY gate failed')
    need(cell['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE'and cell['semantic']['actual_NN_source_commit']==plan['actual_NN']['source_commit'],'full selected-trace reference failed')
    ref=view['original_reference'];need(ref['status']=='PASS_COMPLETE_ORIGINAL_REFERENCE'and ref['reference_kind']=='strict'and ref['mismatches']==0 and ref['reference_sha256']==reference_sha,'independent strict original reference failed')
    expected_steps=(source['frames']+7999)//8000
    need(cell['semantic']['checked_steps']==ref['checked_steps']==view['original_durable_facts_applied']==expected_steps,'original full-step counts differ')
    need(view['neural_modules_imported']==[]and view['benefit_or_nonzero_activation_required']is False,'view audit executed neural work or selected on outcome')
    primary=endpoint_recount(cell['primary'],source,origin['origin_perf'])
    for key,value in primary.items():
        if key=='EOS_D2_misses'and key not in native['primary']:continue
        need(key in native['primary'],'original native endpoint absent: '+key)
        if isinstance(value,(int,bool)):need(native['primary'][key]==value,'original/current primary differs: '+key)
        else:close(native['primary'][key],value,'original/current primary '+key)
    for key in ('primary_linear_all_offered_D99','primary_linear_all_offered_C99'):
        need(native['primary'][key]==cell['primary'][key],'original/current primary quantile differs')
    need(native['primary']['cell_id']==cid and native['primary']['arm']==strategy and native['primary']['repeat']==cell['repeat'],'original primary identity differs')
    input_bindings={r['path']:r for r in view['input_files']}
    for filename in ('CONFIG.json','SERVICE_END.json'):
        need(filename in input_bindings and input_bindings[filename]['sha256']==INPUTS[str(raw/filename)]['sha256'],'independent audit input binding differs: '+filename)
    need(finite(end['service_end_perf'],'service end')>=origin['origin_perf'],'original service window regressed')
    continuity=view['continuity']
    for key in COUNTS:need(type(continuity[key])is int and continuity[key]>=0,'invalid continuity counter: '+key)
    for key in AREAS:finite(continuity[key],'continuity '+key)
    need(continuity['total_withdrawals']==sum(continuity[c+'_withdrawals']for c in ('avoidable','necessary','unknown')),'withdrawal classes do not close')
    close(continuity['removed_audio_seconds'],sum(continuity[c+'_removed_audio_seconds']for c in ('avoidable','necessary','unknown')),'cumulative dropped audio classes')
    for cls in ('avoidable','necessary','unknown'):close(continuity[cls+'_gap_audio_seconds_x_wall_seconds'],continuity['same_root_'+cls+'_gap_audio_seconds_x_wall_seconds'],'same-root gap alias')
    close(continuity['service_end_perf'],end['service_end_perf'],'view-audit service end')
    need(len(events)==continuity['canonical_applications']==expected_steps,'actual canonical support-event count differs')
    need(len(windows)==continuity['total_withdrawals'],'one actual loss window per recorded drop required')
    for key,field in [('gap_right_censored_windows','right_censored'),('gap_boundary_truncated_windows','boundary_truncated'),('gap_restored_windows','restored')]:need(continuity[key]==sum(bool(w[field])for w in windows),'window censor/restoration count differs')
    need(all(w['classification']in ('avoidable','necessary','unknown')and w['end']>=w['start']for w in windows),'invalid recorded loss window')
    energy=cell['common_external_energy']['origin_to_confirmed_physical_model_drain'];finite(energy['total_joules'],'both-board energy')
    need(set(energy['board_joules'])=={'0','1'},'both physical energy boards required')
    close(energy['total_joules'],sum(energy['board_joules'].values()),'both-board energy sum')
    if 'begin_perf'in energy:close(energy['begin_perf'],origin['origin_perf'],'external energy origin')
    energy_binding=energy_window_binding(cell,native,origin,end,events)
    # S1 preservation is a checked protocol action, never a nonzero-opportunity gate.
    if retain:need(continuity['compatible_ahead_changed']==0 and continuity['compatible_ahead_preserved']==continuity['compatible_ahead_applications'],'declared S1 failed its compatible-application action')
    return dict(cell_id=cid,campaign=campaign.name,source_id=source['source_id'],speaker_id=source['speaker_id'],
        condition=condition,strategy=strategy,repeat=cell['repeat'],frozen_position=planned['position'],consumer_retain_views=retain,
        offered_audio_s=primary['offered_audio_seconds'],offered_frontiers=primary['offered_frontiers'],
        credit_audio_s=primary['dual_deadline_audio_credit_seconds'],whole_run_pass=primary['complete_coverage_and_original_quantile_pass'],
        D99=cell['primary']['primary_linear_all_offered_D99'],C99=cell['primary']['primary_linear_all_offered_C99'],
        D2_misses=primary['D2_misses_all_offered'],C8_misses=primary['C8_misses_all_offered'],EOS_D2_misses=primary['EOS_D2_misses'],
        worker_seconds=worker['worker_seconds'],observed_infer_seconds=worker['observed_infer_seconds'],total_infer_seconds=worker['total_infer_seconds'],
        missing_infer_timers=worker['missing_infer_timers'],dispatches=job['dispatches'],both_board_J=energy['total_joules'],
        original_reference_steps=expected_steps,raw_result_location=cell['raw_result_location'],
        **{k:continuity[k]for k in COUNTS+AREAS},gap_scope=continuity['gap_scope'],
        service_origin_perf=energy_binding['service_origin_perf'],external_observation_begin_perf=energy_binding['external_observation_begin_perf'],
        external_physical_drain_perf=energy_binding['external_physical_drain_perf'],runtime_service_end_perf=energy_binding['runtime_service_end_perf'],
        runtime_end_minus_external_drain_seconds=energy_binding['runtime_end_minus_external_drain_seconds'],
        last_canonical_application_perf=energy_binding['last_canonical_application_perf'],certified_EOS_consume_perf=energy_binding['certified_EOS_consume_perf'],
        original_source_energy=energy_binding['original_source_energy'],energy_window_scope=energy_binding['scope'])

def total(rows):
    keys=('offered_audio_s','offered_frontiers','credit_audio_s','worker_seconds','both_board_J','dispatches',
          'observed_infer_seconds','missing_infer_timers','original_reference_steps','D2_misses','C8_misses','EOS_D2_misses')+COUNTS+AREAS
    out={k:math.fsum(r[k]for r in rows)for k in keys};out['trials']=len(rows)
    count_keys=set(COUNTS)|{'offered_frontiers','dispatches','missing_infer_timers','original_reference_steps','D2_misses','C8_misses','EOS_D2_misses'}
    for key in count_keys:out[key]=sum(r[key]for r in rows)
    out['whole_run_passes']=sum(r['whole_run_pass']for r in rows)
    out['coverage_percent']=100*out['credit_audio_s']/out['offered_audio_s']
    out['total_infer_seconds']=None if out['missing_infer_timers']else math.fsum(r['total_infer_seconds']for r in rows)
    return out

def write_csv(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf8')as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(rows)

def run(args):
    INPUTS.clear()
    folders=[pathlib.Path(x).resolve()for x in(args.campaign or [E/'gpu_results/PILOT20_V1',E/'gpu_results/CONFIRM60_V1'])]
    need(len(folders)==2 and len(set(folders))==2,'exactly pilot20 and confirmation60 campaigns required')
    summaries=[]
    # Read count/status headers only before any individual outcomes or final output.
    for folder in folders:
        summary=read(folder/'SUMMARY.json')
        if summary.get('status')!=COMPLETE or summary.get('completed_trials')!=summary.get('planned_trials'):
            raise NotReady(folder.name+' has not completed its whole frozen matrix')
        summaries.append(summary)
    need(sorted(s['planned_trials']for s in summaries)==[20,60]and sum(s['completed_trials']for s in summaries)==80,'final 20+60 count differs')
    receipt,refs=load_reference(pathlib.Path(args.reference).resolve(),args.expected_nn)
    reference_sha=receipt['reference_details']['sha256'];all_rows=[];expected_keys=set();source_map={};component_identities=[]
    for folder,summary in zip(folders,summaries):
        plan=read(folder/'CONFIG.json');local_plan=read(E/'plans'/(folder.name+'_PLAN.json'));need(plan==local_plan,'mirrored campaign differs from frozen plan')
        gate=read(folder/'GATE.json');record=read(folder/'RUN_RECORD.json')
        need(gate['status']==COMPLETE and gate['completed_trials']==summary['completed_trials'],'campaign final gate incomplete')
        need(not summary.get('failed_attempts'),'technical failed attempts must be reviewed, not silently omitted')
        need(summary['actual_NN_source_commit']==plan['actual_NN']['source_commit']==record['actual_NN_source_commit']==args.expected_nn,'campaign runtime identities differ')
        need(record['code_commit']==plan['driver']['source_commit']==receipt['generator_source_commit'],'campaign/generator execution source differs')
        need(record['frozen_config_sha256']==INPUTS[str(folder/'CONFIG.json')]['sha256'],'actual campaign config bytes differ from run record')
        need(plan['reference_details']['sha256']==reference_sha and plan['reference_receipt']['sha256']==INPUTS[str(pathlib.Path(args.reference).resolve()/'REFERENCE_RECEIPT.json')]['sha256'],'campaign measured reference differs')
        need(plan['expected_trials']==summary['planned_trials']==10*len(plan['sources']),'campaign full planned scope differs')
        need(plan['cadence']==dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000),'source cadence changed')
        need(plan['original_D2_seconds']==2. and plan['original_C8_seconds']==8.,'deadlines changed')
        need(plan['zero_opportunity_is_not_failure']is True and plan['positive_difference_is_not_gate']is True,'outcome-dependent continuation/filtering contract changed')
        component_identities.append({k:plan[k]for k in ('driver','actual_NN','view_audit','production_support')})
        planned={c['cell_id']:c for c in plan['cells']};need(len(planned)==len(plan['cells']),'duplicate planned cell')
        cells=summary['cells'];need(len(cells)==len(planned)and {c['cell_id']for c in cells}==set(planned),'completed cell IDs differ from whole frozen plan')
        for source in plan['sources']:
            sid=source['source_id'];need(sid not in source_map,'pilot/confirmation source overlap')
            need(sid in refs and all(source[k]==refs[sid][k]for k in ('speaker_id','frames','audio_sha256','path')),'source differs from measured reference bank')
            source_map[sid]=source
            expected_keys.update((sid,repeat,condition)for repeat in (0,1)for condition in CONDITIONS)
        for cell in cells:
            need(cell['source_id']in source_map and cell['speaker_id']==source_map[cell['source_id']]['speaker_id'],'cell source identity differs')
            all_rows.append(check_cell(folder,cell,planned[cell['cell_id']],source_map[cell['source_id']],plan,reference_sha))
        # Campaign summaries are independently reconstructed from their own cells.
        for condition in CONDITIONS:
            t=total([r for r in all_rows if r['campaign']==folder.name and r['condition']==condition]);stored=summary['condition_totals'][condition]
            for key,field in [('trials','completed_trials'),('offered_audio_s','observed_offered_audio_s'),('credit_audio_s','credit_audio_s'),('worker_seconds','worker_seconds'),('both_board_J','both_board_J'),('whole_run_passes','whole_run_passes')]:close(t[key],stored[field],'campaign total '+condition+'/'+field)
            for key,value in stored.get('continuity_totals',{}).items():close(t[key],value,'campaign continuity '+condition+'/'+key)
    need(all(x==component_identities[0]for x in component_identities),'execution component identities changed between pilot and confirmation')
    by={(r['source_id'],r['repeat'],r['condition']):r for r in all_rows}
    need(len(all_rows)==len(by)==80 and set(by)==expected_keys,'unique eight-source five-condition two-repeat matrix differs')
    need(set(source_map)==set(refs)and len({s['speaker_id']for s in source_map.values()})==8,'final eight-speaker reference bank differs')
    condition_totals={c:total([r for r in all_rows if r['condition']==c])for c in CONDITIONS}
    for c,t in condition_totals.items():
        close(t['offered_audio_s'],137.864125,'all-offered denominator '+c);need(t['trials']==16 and t['offered_frontiers']==282,'condition repetition/frontier denominator differs')
    scopes={json.dumps(r['gap_scope'],sort_keys=True)for r in all_rows};need(len(scopes)==1,'continuity metric scopes changed across conditions')
    source_rows=[];source_effects=[];repeat_effects=[]
    for sid in sorted(source_map):
        values={c:total([by[sid,rep,c]for rep in (0,1)])for c in CONDITIONS}
        for c,t in values.items():source_rows.append(dict(source_id=sid,speaker_id=source_map[sid]['speaker_id'],condition=c,**t))
        source_effects.append(dict(source_id=sid,speaker_id=source_map[sid]['speaker_id'],offered_audio_s=values['r1s1']['offered_audio_s'],effects={metric:factorial({c:values[c][metric]for c in CONDITIONS})for metric in EFFECT_METRICS}))
        for rep in (0,1):repeat_effects.append(dict(source_id=sid,repeat=rep,effects={metric:factorial({c:by[sid,rep,c][metric]for c in CONDITIONS})for metric in EFFECT_METRICS}))
    pooled={metric:factorial({c:condition_totals[c][metric]for c in CONDITIONS})for metric in EFFECT_METRICS}
    for metric in EFFECT_METRICS:
        for contrast,value in pooled[metric].items():close(value,math.fsum(s['effects'][metric][contrast]for s in source_effects),'source-factorial conservation')
    credit_diagnostics={contrast:paired_diagnostic(s['effects']['credit_audio_s'][contrast]for s in source_effects)for contrast in pooled['credit_audio_s']}
    rawtot=condition_totals['r1s1'];cons=condition_totals['conservative_s1'];ready=condition_totals['r0s1']
    anchor=dict(full_minus_conservative_credit_audio_s=rawtot['credit_audio_s']-cons['credit_audio_s'],
        full_minus_conservative_credit_pp=100*(rawtot['credit_audio_s']-cons['credit_audio_s'])/137.864125,
        ready_S1_minus_conservative_credit_audio_s=ready['credit_audio_s']-cons['credit_audio_s'],
        full_minus_conservative_worker_seconds=rawtot['worker_seconds']-cons['worker_seconds'],
        full_minus_conservative_energy_J=rawtot['both_board_J']-cons['both_board_J'],
        full_relative_worker_percent=100*(rawtot['worker_seconds']/cons['worker_seconds']-1),
        full_relative_energy_percent=100*(rawtot['both_board_J']/cons['both_board_J']-1),
        scope='Same newly measured runtime, five-policy campaign, source bank, original references and physical-drain energy window.')
    result=dict(status='PASS_INDEPENDENT_COMPLETE80_NATIVE_FACTORIAL_RECOUNT',record_type='EXISTING_COMPLETED_FROZEN_SERVING_DATA_RECOUNT_NOT_NEW_EXPERIMENT',
        actual_NN_source_commit=args.expected_nn,source_clusters=8,trials=80,conditions=5,timing_repeats_per_condition=2,
        all_offered_audio_seconds_per_condition=137.864125,all_offered_frontiers_per_condition=282,
        original_reference_steps_checked=sum(r['original_reference_steps']for r in all_rows),reference_ledger=receipt['ledger'],
        condition_totals=condition_totals,source_level=source_rows,source_factorial_effects=source_effects,
        repeat_factorial_effects=repeat_effects,pooled_factorial_effects=pooled,credit_source_paired_conditional_diagnostics=credit_diagnostics,
        conservative_anchor=anchor,gap_scope=json.loads(next(iter(scopes))),execution_components=component_identities[0],
        energy_window_bindings=[dict(cell_id=r['cell_id'],condition=r['condition'],source_id=r['source_id'],repeat=r['repeat'],
            **{k:r[k]for k in ('service_origin_perf','external_observation_begin_perf','external_physical_drain_perf','runtime_service_end_perf',
                'runtime_end_minus_external_drain_seconds','last_canonical_application_perf','certified_EOS_consume_perf','original_source_energy','energy_window_scope')})for r in all_rows],
        no_SLO_or_zero_opportunity_filtering=True,no_source_replacement_or_favorable_retry=True,
        recount_scope='Scalar conservation and original per-frontier endpoint arithmetic from frozen reports; detailed deployed view/source/ref/task checks are the separate frozen audit gates, not remeasured model service.',
        recount_code_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),input_manifest=INPUTS)
    out=pathlib.Path(args.out).resolve();need(not out.exists(),'never overwrite an independent recount result');out.mkdir(parents=True)
    (out/'SUMMARY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    write_csv(out/'CONDITION_TOTALS.csv',[dict(condition=c,**t)for c,t in condition_totals.items()])
    write_csv(out/'SOURCE_CONDITION_TOTALS.csv',source_rows)
    write_csv(out/'ALL80_CELLS.csv',[{k:v for k,v in r.items()if not isinstance(v,(dict,list))}for r in sorted(all_rows,key=lambda r:(r['source_id'],r['repeat'],r['condition']))])
    effect_rows=[dict(source_id=s['source_id'],metric=metric,**effects)for s in source_effects for metric,effects in s['effects'].items()]
    write_csv(out/'SOURCE_FACTORIAL_EFFECTS.csv',effect_rows)
    md=['# Native R×S＋Conservative：独立完整重算','',
        '80格全部完成并通过原任务、身份、物理计时/能量与实际Consumer审计；8个speaker cluster，各条件两次fresh重复。所有offered/EOS和SLO失败保留。','',
        '| 条件 | 信用s / 137.864125 | Coverage% | Pass/16 | Worker-s | 两板kJ | 兼容机会 | 可避免/必要/未知撤回 | 全高水位面积 | 同根可避免面积 | 截尾/边界 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for c,t in condition_totals.items():md.append('| '+c+' | '+' | '.join([f"{t['credit_audio_s']:.6f}",f"{t['coverage_percent']:.3f}",str(t['whole_run_passes']),f"{t['worker_seconds']:.3f}",f"{t['both_board_J']/1000:.3f}",str(t['compatible_ahead_applications']),'/'.join(str(t[k+'_withdrawals'])for k in('avoidable','necessary','unknown')),f"{t['total_gap_audio_seconds_x_wall_seconds']:.6f}",f"{t['avoidable_gap_audio_seconds_x_wall_seconds']:.6f}",str(t['gap_right_censored_windows'])+'/'+str(t['gap_boundary_truncated_windows'])])+' |')
    md+=['','## 预设对照','',
        '信用四臂交互：'+f"{pooled['credit_audio_s']['interaction']:+.6f}"+' audio-s。S在R1下：'+f"{pooled['credit_audio_s']['S_at_R1']:+.6f}"+'；S在R0下：'+f"{pooled['credit_audio_s']['S_at_R0']:+.6f}"+'。',
        '同runtime Full−Conservative信用：'+f"{anchor['full_minus_conservative_credit_audio_s']:+.6f}"+' audio-s；worker变化'+f"{anchor['full_relative_worker_percent']:+.3f}"+'%；能量变化'+f"{anchor['full_relative_energy_percent']:+.3f}"+'%。','',
        '全高水位面积包含必要/未知撤回；同根分类面积到恢复、下一canonical/epoch边界或观察结束为止。两列对象不同，不相加，也不将同根面积冒充完整跨root合法G。','',
        '两板主能量列保持原冻结的origin→外部模型排空确认窗口；runtime SERVICE_END及其原始能量对象另列在energy_window_bindings中。两个观察器/窗口不混并，也不把差值当CPU阶段能量。','',
        '逐source/重复效应、所有零机会/反向点及条件性sign-label枚举见JSON/CSV。枚举保留全部8个来源和两重复，不是部署总体显著性保证。',
        '原执行源：`'+args.expected_nn+'`。参照生成成本与80格服务测量分开。']
    (out/'REPORT.zh.md').write_text('\n'.join(md)+'\n',encoding='utf8')
    (out/'GATE.json').write_text(json.dumps(dict(status=result['status'],trials=80,source_clusters=8,all_conditions_complete=True),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],out=str(out),trials=80,source_clusters=8)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',action='append',help='Closed mirrored campaign directory; pass twice, or use the default PILOT20_V1/CONFIRM60_V1.')
    p.add_argument('--reference',default=str(E/'gpu_results/REFERENCE8_V3'))
    p.add_argument('--expected-nn',default=NN)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    try:run(args)
    except NotReady as error:
        print(json.dumps(dict(status='NOT_READY_NO_FINAL_POINT_ESTIMATE',reason=str(error))));sys.exit(2)
