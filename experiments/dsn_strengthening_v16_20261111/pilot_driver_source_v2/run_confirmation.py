"""Serial fresh-process new-runtime service pilot. Never prune SLO misses."""
from __future__ import annotations
import argparse,importlib.metadata,pathlib,subprocess,sys,time,traceback
from confirmation_common import NN4F,SUPPORT,SEED,MAIN_ARMS,phase_arms,need,read,sha,put,canonical,disk,verify_source,selected_sources,validate_matrix,reference_binding,child_env,validate_prelaunch,validate_phase_selection
from job_accounting import audit_trial,resource_diagnostic

def resource_observations(out,ready):
    values={}
    for key in ('model_load_seconds','full_load_warmup_seconds'):
        found=[r[key] for r in ready if isinstance(r.get(key),(int,float))]
        if found:values[key]=max(found)
    import json
    for path in pathlib.Path(out).glob('owner_e*/worker_results.jsonl'):
        for line in path.read_text(encoding='utf8').splitlines():
            row=json.loads(line)['event'].get('resource_snapshot',{})
            for key,value in row.items():
                if isinstance(value,(int,float)):values[key]=max(values.get(key,0),value)
    return values

def aggregate(results,plan):
    sources=[];pairs=[];diagnostics=[];arms=phase_arms(plan['include_auxiliary'])
    for source in plan['sources']:
        sid=source['source_id'];own=[r for r in results if r['source_id']==sid]
        for rep in (0,1):
            by={r['strategy']:r for r in own if r['repeat']==rep}
            if not all(arm in by for arm in MAIN_ARMS):continue
            f=by['fullcall'];fp=f['primary']
            for control in MAIN_ARMS:
                if control=='fullcall':continue
                c=by[control];cp=c['primary'];need(abs(cp['offered_audio_seconds']-fp['offered_audio_seconds'])<1e-10,'paired offered denominator differs')
                pairs.append(dict(source_id=sid,speaker_id=source['speaker_id'],repeat=rep,candidate='fullcall',control=control,offered_audio_s=cp['offered_audio_seconds'],candidate_credit_audio_s=fp['dual_deadline_audio_credit_seconds'],control_credit_audio_s=cp['dual_deadline_audio_credit_seconds'],paired_credit_gain_audio_s=fp['dual_deadline_audio_credit_seconds']-cp['dual_deadline_audio_credit_seconds']))
        if len(own)==2*len(arms):
            item=dict(source_id=sid,speaker_id=source['speaker_id'],timing_repeats=2)
            for policy in arms:
                chosen=[r for r in own if r['strategy']==policy]
                item[policy]=dict(estimand_role='main' if policy in MAIN_ARMS else 'auxiliary',offered_audio_s=sum(r['primary']['offered_audio_seconds'] for r in chosen),credit_audio_s=sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in chosen),original_D2_C8_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in chosen),trials=2,common_model_drain_board_J=sum(r['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'] for r in chosen))
                byrep={r['repeat']:r for r in chosen};diagnostics.append(dict(source_id=sid,arm=policy,**resource_diagnostic(byrep[0].get('resource_observations',{}),byrep[1].get('resource_observations',{}))))
            item['paired_credit_gain_audio_s']=item['fullcall']['credit_audio_s']-item['conservative']['credit_audio_s']
            item['paired_credit_gain_percentage_points']=100*item['paired_credit_gain_audio_s']/item['conservative']['offered_audio_s']
            item['paired_common_model_drain_energy_difference_J']=item['fullcall']['common_model_drain_board_J']-item['conservative']['common_model_drain_board_J'];sources.append(item)
    return dict(status='COMPLETE_FROZEN_V16_MAIN_AND_AUXILIARY_TASK_AND_ENDPOINTS' if len(results)==plan['expected_trials'] else 'PARTIAL_FROZEN_QUEUE_PRESERVED',planned_trials=plan['expected_trials'],completed_trials=len(results),planned_main_trials=plan['expected_main_trials'],planned_auxiliary_trials=plan['expected_auxiliary_trials'],speaker_clusters=plan['expected_source_count'],new_independent_speakers=plan['new_independent_speakers'],source_level_pairs=sources,repeat_pairs=pairs,resource_diagnostics=diagnostics,cells=results,main_cells=[r for r in results if r['strategy'] in MAIN_ARMS],auxiliary_cells=[r for r in results if r['strategy'] not in MAIN_ARMS],actual_NN_source_commit=NN4F,reference_generation_separate_from_service_trials=True,Root_actual_trace_audit_pending=True,no_frontier_or_repeat_pseudoreplication=True)

def run(a):
    plan=read(a.plan);identity=verify_source(pathlib.Path(__file__).parent,a.manifest,plan['driver']['source_commit']);need(identity==plan['driver'],'driver complete identity differs')
    base=verify_source(plan['actual_NN']['source_root'],plan['actual_NN']['source_manifest'],NN4F);need(base==plan['actual_NN'],'actual NN dependency changed')
    support=verify_source(plan['production_support']['source_root'],plan['production_support']['source_manifest'],SUPPORT);need(support==plan['production_support'],'production support changed')
    sys.path.insert(0,support['source_root']);import common,external_power,audit_results,run_paired_campaign
    pre=read(a.prelaunch);validate_prelaunch(pre,a.plan,identity,base)
    need(sha(plan['selection_receipt']['path'])==plan['selection_receipt']['sha256'] and sha(plan['reference_receipt']['path'])==plan['reference_receipt']['sha256'],'selection/reference receipt changed')
    selection=read(plan['selection_receipt']['path']);sources=selected_sources(selection,plan['expected_source_count']);need(sources==plan['sources'],'selection full objects changed');validate_phase_selection(selection,plan['phase'],sources);validate_matrix(plan['cells'],sources,plan['include_auxiliary'])
    need(plan['metadata_seed']==SEED and plan['runtime_environment']=={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'} and plan['original_D2_seconds']==2. and plan['original_C8_seconds']==8. and plan['all_offered_including_partial_EOS'] is True,'frozen service contract changed')
    need(plan['main_arms']==list(MAIN_ARMS) and plan['ready_reuse_positive_is_gate'] is False and plan['resource_drift_reject_or_retry'] is False,'estimand/sentinel policy differs')
    need(plan['cadence']==dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000,all_length_strata_identical=True),'length-specific cadence alteration forbidden')
    reference=reference_binding(plan['reference_receipt']['path'],plan['selection_receipt']['path'],sources,identity['source_commit'])
    need(reference==plan['reference_binding'],'reference binding drift')
    need(sha(plan['environment_record'])==plan['environment_sha256'] and pathlib.Path(sys.executable).resolve()==pathlib.Path(plan['environment_python']).resolve(),'environment/interpreter changed')
    env=read(plan['environment_record'])
    for key,value in env['packages'].items():need(importlib.metadata.version(key)==value,'package changed: '+key)
    asset=pre['asset_byte_gate'];need(sha(asset['path'])==asset['sha256'],'asset gate changed');asset_gate=read(asset['path'])
    need(asset_gate['status'].startswith('PASS') and asset_gate['all_asset_bytes_verified'] is True and asset_gate['asset_manifest_sha256']==env['assets_manifest_sha256'],'current complete model asset gate missing')
    need(sha(env['assets_manifest_path'])==env['assets_manifest_sha256'],'asset manifest changed')
    for s in sources:need(sha(s['path'])==s['audio_sha256'],'actual new source bytes differ')
    out=disk(a.out);need(str(out)==plan['raw_result_location'],'unfrozen campaign output');out.mkdir(parents=True,exist_ok=False)
    for name in ('cells','logs','external','records'):(out/name).mkdir()
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,driver=identity,actual_NN=base,production_support=support,original_environment=env,reference_only_receipt=plan['reference_receipt'],reference_cost_not_in_serving=True))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],actual_NN_source_commit=NN4F,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];ref_details=read(reference['reference_details']['path'])
    try:
        for index,cell in enumerate(plan['cells']):
            need(verify_source(pathlib.Path(__file__).parent,a.manifest,identity['source_commit'])==identity,'driver source drift before launch')
            need(verify_source(support['source_root'],support['source_manifest'],SUPPORT)==support,'production support drift before launch')
            need(verify_source(base['source_root'],base['source_manifest'],NN4F)==base,'NN source drift before launch')
            need(sha(cell['config'])==cell['config_sha256'],'cell config changed');cfg=read(cell['config'])
            need(cfg['arm']==cell['strategy'] and cfg['settings']['primary_gpu']==cell['primary_gpu'] and cfg['reference_kind']=='strict' and cfg['fault']['kind']=='none' and 'cost_observer' not in cfg,'cell execution contract changed')
            need(not external_power.nvml_snapshot()['compute_processes'],'GPU already occupied; do not launch')
            raw=disk(cell['out']);need(not raw.exists(),'never overwrite cell');observer=external_power.ExternalObserver(disk(cell['external_power']));captured={};child=None;ticks=None;done=False
            command=[sys.executable,'-B',str(pathlib.Path(base['source_root'])/'resilience_trial.py'),'--config',cell['config'],'--manifest',base['source_manifest'],'--out',cell['out']]
            put(out/'records'/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],code_commit=identity['source_commit'],driver=identity,actual_NN=base,production_support=support,frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],selection_receipt=plan['selection_receipt'],reference_receipt=plan['reference_receipt'],raw_result_location=cell['out'],aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),command=command,command_sha256=__import__('hashlib').sha256(canonical(command)).hexdigest()))
            put(out/'PROGRESS.json',dict(completed=len(results),planned=plan['expected_trials'],current=cell['cell_id'],performance_misses_do_not_stop_queue=True),replace=True)
            try:
                observer.start()
                with disk(cell['log']).open('x',encoding='utf8') as stream:
                    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=child_env(),start_new_session=True)
                    from process_cleanup import process_identity
                    launch=process_identity(child.pid);need(launch is not None,'child ended before identity capture');ticks=launch['start_ticks']
                    put(out/'records'/(cell['cell_id']+'_HANDLE.json'),dict(pid=child.pid,start_ticks=ticks,command_sha256=__import__('hashlib').sha256(canonical(command)).hexdigest(),physical_identity=launch))
                    deadline=time.perf_counter()+plan['maximum_process_seconds']
                    while child.poll() is None:
                        observer.check();run_paired_campaign.capture_ready_environment(raw,observer,captured,env);need(time.perf_counter()<deadline,'fresh load/service timeout');time.sleep(.1)
                    need(child.returncode==0,'original actual trial failed; preserve technical/semantic failure')
                run_paired_campaign.capture_ready_environment(raw,observer,captured,env);ready=run_paired_campaign.ready_rows(raw);ready_gate=run_paired_campaign.check_ready(ready,env)
                need(set(captured)=={str(r['pid']) for r in ready},'initial actual allocator observations missing')
                observer.finish(not_before=time.perf_counter());need(not external_power.nvml_snapshot()['compute_processes'],'CUDA physical release incomplete')
                need(read(raw/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK','original task gate failed')
                result=audit_results.audit_cell(cell,cfg,ref_details,observer)
                sys.path.insert(0,base['source_root']);from resilience_storage import scan
                accounting=audit_trial(raw,scan,closed=True);put(raw/'JOB_ACCOUNTING.json',accounting)
                need(accounting['status']=='PASS_DISJOINT_JOB_ACCOUNTING','complete disjoint job/authority accounting failed')
                result.update(speaker_id=cell['speaker_id'],estimand_role=cell['estimand_role'],actual_READY_gate=ready_gate,initial_worker_allocator_observations=captured,job_accounting=accounting,resource_observations=resource_observations(raw,ready))
                put(raw/'EXTERNAL_NEW_TEST_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);done=True
            finally:
                if child is not None and not done:
                    cleanup=out/'records'/(cell['cell_id']+'_FAILURE_CLEANUP.json')
                    try:put(cleanup,run_paired_campaign.stop_owned_processes(child,raw,child_start_ticks=ticks,known_members=list(captured.values())))
                    except BaseException:put(cleanup,dict(status='FAIL_PROVEN_OWNED_RELEASE_UNVERIFIED',failure=traceback.format_exc(),unrelated_processes_never_authorized=True));raise
                    finally:observer.close()
                else:observer.close()
        summary=aggregate(results,plan)
        put(out/'ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json',dict(status='PENDING_SEPARATE_FROZEN_C4_AUDIT',actual_NN_source=base,driver=identity,selection_receipt=plan['selection_receipt'],reference_receipt=plan['reference_receipt'],cells=[dict(cell_id=r['cell_id'],raw_result_location=r['raw_result_location']) for r in results],task_and_endpoint_checks_not_substitutes_for_full_actual_trace_refinement=True))
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],completed_trials=len(results),performance_misses_retained=True,Root_actual_trace_audit_pending=True));return summary
    except BaseException:
        put(out/'SUMMARY.json',aggregate(results,plan));put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_NEW_TEST_QUEUE_PRESERVED',completed_trials=len(results),failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('plan','manifest','prelaunch','out'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
