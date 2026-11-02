"""Serial fresh-process full4f service confirmation. Never prune SLO misses."""
from __future__ import annotations
import argparse,importlib.metadata,pathlib,subprocess,sys,time,traceback
from confirmation_common import NN4F,SUPPORT,need,read,sha,put,canonical,disk,verify_source,selected_sources,validate_matrix,reference_binding,child_env

def aggregate(results,plan):
    sources=[];pairs=[]
    for source in plan['sources']:
        sid=source['source_id'];own=[r for r in results if r['source_id']==sid]
        for rep in (0,1):
            by={r['strategy']:r for r in own if r['repeat']==rep}
            if len(by)!=2:continue
            c,f=by['conservative'],by['fullcall'];cp,fp=c['primary'],f['primary']
            need(abs(cp['offered_audio_seconds']-fp['offered_audio_seconds'])<1e-10,'paired offered denominator differs')
            pairs.append(dict(source_id=sid,speaker_id=source['speaker_id'],repeat=rep,offered_audio_s=cp['offered_audio_seconds'],conservative_credit_audio_s=cp['dual_deadline_audio_credit_seconds'],fullcall_credit_audio_s=fp['dual_deadline_audio_credit_seconds'],paired_credit_gain_audio_s=fp['dual_deadline_audio_credit_seconds']-cp['dual_deadline_audio_credit_seconds'],conservative_D99=cp['primary_linear_all_offered_D99'],fullcall_D99=fp['primary_linear_all_offered_D99'],conservative_C99=cp['primary_linear_all_offered_C99'],fullcall_C99=fp['primary_linear_all_offered_C99']))
        if len(own)==4:
            item=dict(source_id=sid,speaker_id=source['speaker_id'],timing_repeats=2)
            for policy in ('conservative','fullcall'):
                chosen=[r for r in own if r['strategy']==policy]
                item[policy]=dict(offered_audio_s=sum(r['primary']['offered_audio_seconds'] for r in chosen),credit_audio_s=sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in chosen),original_D2_C8_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in chosen),trials=2,common_model_drain_board_J=sum(r['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'] for r in chosen))
            item['paired_credit_gain_audio_s']=item['fullcall']['credit_audio_s']-item['conservative']['credit_audio_s']
            item['paired_credit_gain_percentage_points']=100*item['paired_credit_gain_audio_s']/item['conservative']['offered_audio_s']
            item['paired_common_model_drain_energy_difference_J']=item['fullcall']['common_model_drain_board_J']-item['conservative']['common_model_drain_board_J'];sources.append(item)
    return dict(status='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS' if len(results)==plan['expected_trials'] else 'PARTIAL_FROZEN_QUEUE_PRESERVED',planned_trials=plan['expected_trials'],completed_trials=len(results),independent_speakers=plan['expected_source_count'],source_level_pairs=sources,repeat_pairs=pairs,cells=results,actual_NN_source_commit=NN4F,reference_generation_separate_from_service_trials=True,Root_actual_trace_audit_pending=True,no_frontier_or_repeat_pseudoreplication=True)

def run(a):
    plan=read(a.plan);identity=verify_source(pathlib.Path(__file__).parent,a.manifest,plan['driver']['source_commit']);need(identity==plan['driver'],'driver complete identity differs')
    base=verify_source(plan['actual_NN']['source_root'],plan['actual_NN']['source_manifest'],NN4F);need(base==plan['actual_NN'],'actual NN dependency changed')
    support=verify_source(plan['production_support']['source_root'],plan['production_support']['source_manifest'],SUPPORT);need(support==plan['production_support'],'production support changed')
    sys.path.insert(0,support['source_root']);import common,external_power,audit_results,run_paired_campaign
    pre=read(a.prelaunch);need(pre['plan_sha256']==sha(a.plan),'frozen plan differs')
    common.root_preflight_receipt(pre['root_noarg_preflight'],pre['root_noarg_preflight_sha256'],identity['source_commit'],identity['source_manifest_sha256'])
    need(pre['exclusive_GPU_window_authorized_by_root'] is True,'Root exclusive GPU window missing')
    need(sha(plan['selection_receipt']['path'])==plan['selection_receipt']['sha256'] and sha(plan['reference_receipt']['path'])==plan['reference_receipt']['sha256'],'selection/reference receipt changed')
    sources=selected_sources(read(plan['selection_receipt']['path']),plan['expected_source_count']);need(sources==plan['sources'],'selection full objects changed');validate_matrix(plan['cells'],sources)
    need(plan['metadata_seed']==20261102 and plan['runtime_environment']=={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'} and plan['original_D2_seconds']==2. and plan['original_C8_seconds']==8. and plan['all_offered_including_partial_EOS'] is True,'frozen service contract changed')
    reference=reference_binding(plan['reference_receipt']['path'],plan['selection_receipt']['path'],sources)
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
                result=audit_results.audit_cell(cell,cfg,ref_details,observer);result.update(speaker_id=cell['speaker_id'],actual_READY_gate=ready_gate,initial_worker_allocator_observations=captured)
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
