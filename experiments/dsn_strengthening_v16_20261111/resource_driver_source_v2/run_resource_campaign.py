"""Serial fresh-process new-runtime service pilot. Never prune SLO misses."""
from __future__ import annotations
import argparse,importlib.metadata,pathlib,subprocess,sys,time,traceback
from confirmation_common import RUNTIME,SUPPORT,need,read,sha,put,canonical,disk,verify_source,child_env,validate_prelaunch
from job_accounting import resource_diagnostic
from resource_common import REFERENCE_GENERATOR,SEED,ARMS,validate_matrix,reference_contract,validate_cell
from group_audit import audit_group

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
    contrasts=[];diagnostics=[]
    for group in plan['groups']:
        for rep in (0,1):
            by={r['strategy']:r for r in results if r['source_group_id']==group['group_id'] and r['repeat']==rep}
            if set(by)!=set(ARMS):continue
            c,f=by['conservative'],by['fullcall'];cp,fp=c['primary'],f['primary']
            need(abs(cp['offered_audio_seconds']-fp['offered_audio_seconds'])<1e-8,'group paired denominator differs')
            contrasts.append(dict(group_id=group['group_id'],source_count=group['source_count'],repeat=rep,offered_audio_seconds=cp['offered_audio_seconds'],fullcall_minus_conservative_credit_seconds=fp['dual_deadline_audio_credit_seconds']-cp['dual_deadline_audio_credit_seconds'],per_source={sid:dict(fullcall_minus_conservative_credit_seconds=f['per_source_primary'][sid]['dual_deadline_audio_credit_seconds']-c['per_source_primary'][sid]['dual_deadline_audio_credit_seconds']) for sid in group['source_ids']}))
        for arm in ARMS:
            rows={r['repeat']:r for r in results if r['source_group_id']==group['group_id'] and r['strategy']==arm}
            if set(rows)=={0,1}:diagnostics.append(dict(group_id=group['group_id'],arm=arm,**resource_diagnostic(rows[0].get('resource_observations',{}),rows[1].get('resource_observations',{}))))
    return dict(status='COMPLETE_FROZEN_RESOURCE8_TASK_AND_ALL_SOURCE_ENDPOINTS' if len(results)==8 else 'PARTIAL_RESOURCE_QUEUE_PRESERVED',planned_trials=8,completed_trials=len(results),underlying_existing_speaker_ids=plan['underlying_existing_speaker_ids'],new_independent_speakers=0,contrasts=contrasts,resource_diagnostics=diagnostics,cells=results,actual_NN_source_commit=RUNTIME,reference_generator_commit=REFERENCE_GENERATOR,zero_conditional_dispatch_is_valid=True,no_maximum_capacity_or_natural_prevalence_claim=True)

def run(a):
    plan=read(a.plan);identity=verify_source(pathlib.Path(__file__).parent,a.manifest,plan['driver']['source_commit']);need(identity==plan['driver'],'driver complete identity differs')
    base=verify_source(plan['actual_NN']['source_root'],plan['actual_NN']['source_manifest'],RUNTIME);need(base==plan['actual_NN'],'actual NN dependency changed')
    support=verify_source(plan['production_support']['source_root'],plan['production_support']['source_manifest'],SUPPORT);need(support==plan['production_support'],'production support changed')
    sys.path.insert(0,support['source_root']);import common,external_power,audit_results,run_paired_campaign
    pre=read(a.prelaunch);validate_prelaunch(pre,a.plan,identity,base)
    generator=verify_source(plan['reference_generator']['source_root'],plan['reference_generator']['source_manifest'],REFERENCE_GENERATOR);need(generator==plan['reference_generator'],'reference generator changed')
    for record in [*plan['source_selection'].values(),*plan['reference_receipts'].values()]:need(sha(record['path'])==record['sha256'],'group selection/reference receipt changed')
    groups,refs,ref_cfg=reference_contract(plan['source_selection']['full']['path'],plan['source_selection']['subset']['path'],plan['reference_receipts']['full']['path'],plan['reference_receipts']['subset']['path'],generator)
    need(groups==plan['groups'] and refs==plan['references'],'group reference/source objects changed');validate_matrix(plan['cells'],groups)
    need(plan['metadata_seed']==SEED and plan['arms']==list(ARMS) and plan['cadence']==dict(sample_rate_hz=16000,release_seconds=.5,full_step_samples=8000,source_offsets=False,one_original_ingress_origin_for_all_sources=True),'synchronous resource protocol changed')
    sources=groups[-1]['sources']
    need(sha(plan['environment_record'])==plan['environment_sha256'] and pathlib.Path(sys.executable).resolve()==pathlib.Path(plan['environment_python']).resolve(),'environment/interpreter changed')
    env=read(plan['environment_record'])
    for key,value in env['packages'].items():need(importlib.metadata.version(key)==value,'package changed: '+key)
    asset=pre['asset_byte_gate'];need(sha(asset['path'])==asset['sha256'],'asset gate changed');asset_gate=read(asset['path'])
    need(asset_gate['status'].startswith('PASS') and asset_gate['all_asset_bytes_verified'] is True and asset_gate['asset_manifest_sha256']==env['assets_manifest_sha256'],'current complete model asset gate missing')
    need(sha(env['assets_manifest_path'])==env['assets_manifest_sha256'],'asset manifest changed')
    for s in sources:need(sha(s['path'])==s['audio_sha256'],'actual new source bytes differ')
    out=disk(a.out);need(str(out)==plan['raw_result_location'],'unfrozen campaign output');out.mkdir(parents=True,exist_ok=False)
    for name in ('cells','logs','external','records'):(out/name).mkdir()
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,driver=identity,actual_NN=base,production_support=support,original_environment=env,reference_only_receipts=plan['reference_receipts'],reference_cost_not_in_serving=True))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],actual_NN_source_commit=RUNTIME,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];group_map={g['group_id']:g for g in groups}
    try:
        for index,cell in enumerate(plan['cells']):
            need(verify_source(pathlib.Path(__file__).parent,a.manifest,identity['source_commit'])==identity,'driver source drift before launch')
            need(verify_source(support['source_root'],support['source_manifest'],SUPPORT)==support,'production support drift before launch')
            need(verify_source(base['source_root'],base['source_manifest'],RUNTIME)==base,'NN source drift before launch')
            need(sha(cell['config'])==cell['config_sha256'],'cell config changed');cfg=read(cell['config'])
            validate_cell(cfg,cell,group_map[cell['group_id']],ref_cfg);need('cost_observer' not in cfg,'cost observer changes serving')
            need(not external_power.nvml_snapshot()['compute_processes'],'GPU already occupied; do not launch')
            raw=disk(cell['out']);need(not raw.exists(),'never overwrite cell');observer=external_power.ExternalObserver(disk(cell['external_power']));captured={};child=None;ticks=None;done=False
            command=[sys.executable,'-B',str(pathlib.Path(base['source_root'])/'resilience_trial.py'),'--config',cell['config'],'--manifest',base['source_manifest'],'--out',cell['out']]
            put(out/'records'/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],code_commit=identity['source_commit'],driver=identity,actual_NN=base,production_support=support,frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],source_selection=plan['source_selection'],reference_receipts=plan['reference_receipts'],raw_result_location=cell['out'],aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),command=command,command_sha256=__import__('hashlib').sha256(canonical(command)).hexdigest()))
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
                sys.path.insert(0,base['source_root']);from resilience_storage import scan
                import endpoints
                result=audit_group(cell,cfg,read(refs[cell['group_id']]['reference_details']['path']),observer,audit_results=audit_results,endpoints=endpoints,scan=scan)
                result.update(actual_READY_gate=ready_gate,initial_worker_allocator_observations=captured,resource_observations=resource_observations(raw,ready))
                put(raw/'EXTERNAL_RESOURCE_GROUP_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);done=True
            finally:
                if child is not None and not done:
                    cleanup=out/'records'/(cell['cell_id']+'_FAILURE_CLEANUP.json')
                    try:put(cleanup,run_paired_campaign.stop_owned_processes(child,raw,child_start_ticks=ticks,known_members=list(captured.values())))
                    except BaseException:put(cleanup,dict(status='FAIL_PROVEN_OWNED_RELEASE_UNVERIFIED',failure=traceback.format_exc(),unrelated_processes_never_authorized=True));raise
                    finally:observer.close()
                else:observer.close()
        summary=aggregate(results,plan)
        put(out/'ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json',dict(status='PENDING_SEPARATE_FROZEN_C4_AUDIT',actual_NN_source=base,driver=identity,source_selection=plan['source_selection'],reference_receipts=plan['reference_receipts'],cells=[dict(cell_id=r['cell_id'],raw_result_location=r['raw_result_location']) for r in results],task_and_endpoint_checks_not_substitutes_for_full_actual_trace_refinement=True))
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],completed_trials=len(results),performance_misses_retained=True,Root_actual_trace_audit_pending=True));return summary
    except BaseException:
        summary=aggregate(results,plan);summary['failed_or_current_cell']=locals().get('cell');summary['remaining_planned_cells']=[c for c in plan['cells'] if c['cell_id'] not in {r['cell_id'] for r in results}];summary['failure_outcomes_and_raw_are_preserved_not_scored_as_success']=True
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_RESOURCE_QUEUE_PRESERVED',completed_trials=len(results),failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('plan','manifest','prelaunch','out'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
