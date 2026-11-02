"""Frozen CPU12 / normal NN16 cost campaign. No performance-based pruning."""
from __future__ import annotations
import argparse, importlib.util, os, pathlib, subprocess, sys, time, traceback
from driver_common import (NN4F,OBSERVER,SUPPORT,GateError,need,read,sha,put,lines,canonical,
    disk,verify_source,matrix_shape,input_inventory,runtime_environment,check_environment)

def load_support(root,manifest):
    identity=verify_source(root,manifest,SUPPORT);sys.path.insert(0,str(pathlib.Path(root).resolve()))
    import process_cleanup as pc
    import run_paired_campaign as production
    import external_power as power
    import audit_results as audit
    return identity,pc,production,power,audit

def span_audit(raw,enabled,observer_root):
    raw=pathlib.Path(raw);summaries=[read(p) for p in (raw/'cost_spans').glob('*_SUMMARY.json')]
    roles={x['role']:x for x in summaries}
    need(set(roles)=={'owner','supervisor_consumer'} and len(summaries)==2,'normal cell observation exports incomplete')
    for m in summaries:
        need(m['enabled'] is enabled and not m['overflow'],'observation mode or span overflow')
        need(m.get('negative_exclusive_wall_before_clamp',0)==m.get('negative_exclusive_thread_before_clamp',0)==0,'negative exclusive timing residual requires diagnosis')
    if enabled:
        owner=roles['owner']['families'];consumer=roles['supervisor_consumer']['families']
        required={'OWNER.receive_validate_select','AU.durable_selected_commit','AU.validate_original_C_U_and_parent','WAL.complete_fact_commit','IO.actual_os_fsync'}
        need(required.issubset(owner) and 'SUP.complete_consumer_apply' in consumer,'critical complete protocol timing coverage missing')
        from common import verified_facts
        facts=sum(obj['kind']=='canonical' for obj in verified_facts(raw/'facts.wal'))
        need(owner['WAL.complete_fact_commit']['count']==facts,'timed durable commit count differs')
        need(consumer['SUP.complete_consumer_apply']['count']==len(lines(raw/'publications.jsonl')),'timed Consumer apply count differs')
    else:need(all(m['span_count']==0 for m in summaries),'off control unexpectedly captured spans')
    root=pathlib.Path(observer_root);sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('frozen_cost_span_summary',root/'summarize_spans.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    result=mod.summarize(raw)
    need(result['total_span_count']==sum(m['span_count'] for m in summaries),'span export rows disagree with summaries')
    put(raw/'DRIVER_SPAN_AUDIT.json',result)
    return dict(status='PASS_COMPLETE_ORIGINAL_PROTOCOL_SPAN_EXPORT',summary=str(raw/'DRIVER_SPAN_AUDIT.json'),summary_sha256=sha(raw/'DRIVER_SPAN_AUDIT.json'),roles=summaries)

def cpu_cleanup(child,ticks,pc):
    """No NVML calls or GPU signals in CPU phase; exact launched group only."""
    need(isinstance(ticks,int),'CPU launched PID generation not captured')
    proof=pc.group_proof(child.pid,ticks);proof,signalled=pc.signal_group(proof)
    child.wait(timeout=10)
    members=pc.process_group_members(child.pid)
    need(not [x for x in members if x['state'] not in ('Z','X')],'CPU same-session descendants remain')
    return dict(status='PASS_EXACT_CPU_CHILD_GROUP_TERMINATED',proof=proof,signal_sent=signalled,GPU_action=False)

def verify_dependencies(args,plan):
    driver=verify_source(pathlib.Path(__file__).parent,args.manifest)
    need(sha(args.observer_manifest)==plan['observer_manifest_sha256'],'observer manifest changed')
    observer=verify_source(args.observer_source,args.observer_manifest,OBSERVER)
    dep=plan['original_dependency']
    base=verify_source(dep['source_root'],dep['source_manifest'],NN4F)
    need(dep.get('source_manifest_sha256',dep.get('manifest_sha256'))==base['manifest_sha256'],'original base manifest binding differs')
    support,pc,production,power,audit=load_support(args.support_source,args.support_manifest)
    return dict(driver=driver,observer=observer,actual_NN=base,production_support=support),pc,production,power,audit

def validate_prelaunch(args,plan,identity,production):
    pre=read(args.prelaunch)
    need(pre['plan_sha256']==sha(args.plan),'prelaunch plan hash differs')
    need(pre['cpu_timeout_seconds']==args.cpu_timeout and pre['nn_timeout_seconds']==args.nn_timeout,'unfrozen per-process timeout')
    from common import root_preflight_receipt
    root_preflight_receipt(pre['root_noarg_preflight'],pre['root_noarg_preflight_sha256'],identity['driver']['source_commit'],identity['driver']['manifest_sha256'])
    if args.phase in ('nn','both'):
        need(pre['exclusive_GPU_window_authorized_by_root'] is True,'Root exclusive GPU window missing')
        asset=pre['asset_byte_gate'];need(sha(asset['path'])==asset['sha256'],'current asset-byte prerequisite changed')
        gate=read(asset['path']);need(gate['status'].startswith('PASS') and gate['all_asset_bytes_verified'] is True,'current actual model-byte gate missing')
    return pre

def summarize_observer(raw,observer_root):
    root=pathlib.Path(observer_root);sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('frozen_cost_span_summary_extra',root/'summarize_spans.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.summarize(raw)

def cpu_span_audit(raw,summary,observer_root):
    raw=pathlib.Path(raw);metas=[read(p) for p in (raw/'cost_spans').glob('*_SUMMARY.json')]
    need(len(metas)==1 and metas[0]['role']=='cpu_real_trace','CPU complete-object timing export missing')
    m=metas[0];need(m['enabled'] and not m['overflow'],'CPU timing mode/overflow invalid')
    need(m.get('negative_exclusive_wall_before_clamp',0)==m.get('negative_exclusive_thread_before_clamp',0)==0,'CPU timing negative residual')
    fs=m['families'];need(fs['WAL.complete_fact_commit']['count']==summary['original_selected_transitions'],'CPU full-fact timing coverage differs')
    need(fs['SUP.complete_consumer_apply']['count']==summary['actual_publications'],'CPU whole-Consumer timing coverage differs')
    account=summarize_observer(raw,observer_root);need(account['total_span_count']==m['span_count'],'CPU exported span rows differ')
    put(raw/'DRIVER_SPAN_AUDIT.json',account)
    return dict(status='PASS_REAL_OBJECT_CPU_SPAN_EXPORT',summary_sha256=sha(raw/'DRIVER_SPAN_AUDIT.json'),metadata=m)

def command_for(phase,cell,args,plan):
    dep=plan['original_dependency'];base=[sys.executable,'-B']
    if phase=='cpu':
        return base+[str(pathlib.Path(args.observer_source)/'trace_cost.py'),'--base-source',dep['source_root'],'--base-manifest',dep['source_manifest'],'--observer-manifest',args.observer_manifest,'--raw',cell['input_raw'],'--out',cell['output']]
    return base+[str(pathlib.Path(args.observer_source)/'observed_trial.py'),'--base-source',dep['source_root'],'--base-manifest',dep['source_manifest'],'--observer-manifest',args.observer_manifest,'--config',cell['config'],'--out',cell['out']]

def run(args):
    plan=read(args.plan);matrix_shape(plan)
    identity,pc,production,power,audit=verify_dependencies(args,plan)
    environment=check_environment(plan);pre=validate_prelaunch(args,plan,identity,production)
    out=disk(args.out);out.mkdir(parents=True,exist_ok=False);(out/'records').mkdir();(out/'logs').mkdir();(out/'external').mkdir()
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,identity=identity,original_environment=environment,phase=args.phase,prelaunch_sha256=sha(args.prelaunch)))
    put(out/'DRIVER_CONFIG.json',dict(plan=str(pathlib.Path(args.plan)),plan_sha256=sha(args.plan),phase=args.phase,cpu_timeout_seconds=args.cpu_timeout,nn_timeout_seconds=args.nn_timeout,execution_roles=identity,prelaunch_sha256=sha(args.prelaunch)))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id']+'_DRIVER_'+args.phase.upper(),code_commit=identity['driver']['source_commit'],execution_roles=identity,frozen_config=str(out/'DRIVER_CONFIG.json'),frozen_config_sha256=sha(out/'DRIVER_CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];phases=('cpu','nn') if args.phase=='both' else (args.phase,)
    original=read(plan['original_paired_plan']);need(sha(plan['original_paired_plan'])==plan['original_paired_plan_sha256'],'original paired plan changed')
    try:
        for phase in phases:
            cells=plan['cpu_cases'] if phase=='cpu' else plan['cells']
            for index,cell in enumerate(cells):
                # Every fresh child revalidates the exact executable role trees.
                current,_,_,_,_=verify_dependencies(args,plan);need(current==identity,'execution dependency identity drift')
                raw=disk(cell['output'] if phase=='cpu' else cell['out']);raw.parent.mkdir(parents=True,exist_ok=True);need(not raw.exists(),'never overwrite cost raw')
                if phase=='cpu':
                    templates=[c for c in original['cells'] if c['out']==cell['input_raw']]
                    need(len(templates)==1 and sha(templates[0]['config'])==cell['original_config_sha256'],'frozen real trace config template differs')
                    need(templates[0]['source_id']==cell['source_id'] and templates[0]['strategy']==cell['arm'] and templates[0]['repeat']==0 and templates[0]['version']=='final','CPU raw stratum differs')
                    need(read(pathlib.Path(cell['input_raw'])/'CONFIG.json')==read(templates[0]['config']),'raw config differs semantically from original frozen template')
                    inputs=input_inventory(cell['input_raw']);config_path=templates[0]['config'];config_sha=cell['original_config_sha256']
                else:
                    need(sha(cell['config'])==cell['config_sha256'],'frozen NN cell config changed')
                    cfg=read(cell['config']);need(cfg['cost_observer']['enabled'] is cell['observation'] and cfg['arm']==cell['arm'],'cell mode/policy differs')
                    need(cfg['settings']['source_commit']==NN4F and cfg['fault']['kind']=='none','changed cost normal source/contract')
                    inputs={s['path']:dict(bytes=pathlib.Path(s['path']).stat().st_size,sha256=sha(s['path'])) for s in cfg['settings']['sources']}
                    need(all(inputs[s['path']]['sha256']==s['audio_sha256'] for s in cfg['settings']['sources']),'actual accepted audio bytes differ')
                    config_path=cell['config'];config_sha=cell['config_sha256']
                cmd=command_for(phase,cell,args,plan);log=out/'logs'/(cell['cell_id']+'.log')
                record=out/'records'/(cell['cell_id']+'_PRELAUNCH.json')
                put(record,dict(experiment_id=cell['cell_id'],phase=phase,execution_roles=identity,code_commit=identity['driver']['source_commit'],frozen_config=config_path,frozen_config_sha256=config_sha,environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],frozen_inputs=inputs,command=cmd,command_sha256=__import__('hashlib').sha256(canonical(cmd)).hexdigest(),raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),original_root_preflight_sha256=pre['root_noarg_preflight_sha256']))
                put(out/'PROGRESS.json',dict(phase=phase,current=cell['cell_id'],phase_index=index,completed=len(results),no_performance_pruning=True),replace=True)
                child=None;ticks=None;observer=None;captured={};completed=False
                try:
                    if phase=='nn':
                        need(not power.nvml_snapshot()['compute_processes'],'unowned GPU work before cell; do not launch')
                        observer=power.ExternalObserver(out/'external'/(cell['cell_id']+'.jsonl'));observer.start()
                    with log.open('x',encoding='utf8') as stream:
                        child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=runtime_environment(plan,cpu=phase=='cpu'),start_new_session=True)
                        launched=pc.process_identity(child.pid);need(launched is not None,'child ended before PID-generation capture');ticks=launched['start_ticks']
                        put(out/'records'/(cell['cell_id']+'_HANDLE.json'),dict(pid=child.pid,start_ticks=ticks,command_sha256=__import__('hashlib').sha256(canonical(cmd)).hexdigest(),physical_launch_identity=launched,prelaunch_sha256=sha(record)))
                        deadline=time.perf_counter()+(args.cpu_timeout if phase=='cpu' else args.nn_timeout)
                        while child.poll() is None:
                            if observer:
                                observer.check();production.capture_ready_environment(raw,observer,captured,environment)
                            need(time.perf_counter()<deadline,'fresh cell wall timeout including model load')
                            time.sleep(.05 if phase=='cpu' else .1)
                        need(child.returncode==0,'child CLI failed; preserve raw and stop technical queue')
                    if phase=='cpu':
                        gate=read(raw/'GATE.json');need(gate['decision']=='PASS_REAL_COMPLETE_OBJECT_FACT_AND_CONSUMER_REPLAY','CPU real-object replay failed')
                        need(input_inventory(cell['input_raw'])==inputs,'original real trace changed during CPU child')
                        summary=read(raw/'SUMMARY.json')
                        result=dict(cell_id=cell['cell_id'],phase=phase,original_input_inventory=inputs,summary=summary,raw_result_location=str(raw),gate=gate,span_audit=cpu_span_audit(raw,summary,args.observer_source))
                    else:
                        production.capture_ready_environment(raw,observer,captured,environment)
                        ready=production.ready_rows(raw);ready_gate=production.check_ready(ready,environment)
                        need(set(captured)=={str(r['pid']) for r in ready},'actual initial worker allocator observations missing')
                        observer.finish(not_before=time.perf_counter());need(not power.nvml_snapshot()['compute_processes'],'NN returned without physical CUDA release')
                        need(read(raw/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK','original full task gate failed')
                        reference=read(cfg['reference_details']);need(sha(cfg['reference_details'])==cfg['reference_details_sha256'],'original reference details changed')
                        auditmeta=dict(cell,version='final',strategy=cell['arm'])
                        result=audit.audit_cell(auditmeta,cfg,reference,observer)
                        result.update(phase=phase,observation=cell['observation'],actual_READY_gate=ready_gate,initial_worker_allocator_observations=captured,span_audit=span_audit(raw,cell['observation'],args.observer_source))
                        recheck=dict(status='ROOT_CURRENT_ACTUAL_TRACE_RECHECK_REQUIRED',actual_NN_source=NN4F,observer_source=OBSERVER,driver_source=identity['driver']['source_commit'],raw_result_location=str(raw),original_reference=cfg['reference_details'],original_reference_sha256=cfg['reference_details_sha256'],already_completed=['original run_trial complete task/reference/clock gate','independent a13 selected full input/output/C/IDs trace/reference','independent all-offered Consumer endpoint recount','common external origin-to-confirmed-physical-model-drain energy','span mode/export/count/overflow coverage'],not_run_by_this_driver='separately frozen c4 whole-view and original-call actual-trace checker; Root supplies its manifest and binding')
                        put(raw/'ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json',recheck)
                    result['child_handle_sha256']=sha(out/'records'/(cell['cell_id']+'_HANDLE.json'))
                    put(raw/'DRIVER_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);completed=True
                finally:
                    if child is not None and not completed:
                        cleanup=out/'records'/(cell['cell_id']+'_FAILURE_CLEANUP.json')
                        try:
                            release=cpu_cleanup(child,ticks,pc) if phase=='cpu' else production.stop_owned_processes(child,raw,child_start_ticks=ticks,known_members=list(captured.values()))
                            put(cleanup,release)
                        except BaseException:
                            put(cleanup,dict(status='FAIL_OWNED_RELEASE_UNVERIFIED',failure=traceback.format_exc(),unrelated_work_never_signalled=True));raise
                        finally:
                            if observer:observer.close()
                    elif observer:observer.close()
                if phase=='nn' and index==3:
                    put(out/'INITIAL4_VALIDITY_GATE.json',dict(status='CONTINUE_ALL12_REMAINING_PREDECLARED_CELLS',decision_basis='identity, source-preserved task, physical release and observer validity; no latency/energy threshold'))
        summary=dict(status='COMPLETE_FROZEN_COST_'+args.phase.upper()+'_CAMPAIGN',completed_cells=len(results),cpu_cells=sum(r['phase']=='cpu' for r in results),NN_cells=sum(r['phase']=='nn' for r in results),cells=results,scope='real-object CPU footprint and actual NN off/on observation impact; not protocol-removal net overhead',root_actual_trace_recheck_pending=args.phase in ('nn','both'))
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],completed_cells=len(results),root_actual_trace_recheck_pending=summary['root_actual_trace_recheck_pending']));return summary
    except BaseException:
        put(out/'SUMMARY.json',dict(status='PARTIAL_TECHNICAL_FAILURE_PRESERVED',completed_cells=len(results),cells=results))
        put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_COST_CAMPAIGN_PRESERVED',completed_cells=len(results),failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=('cpu','nn','both'),required=True)
    for name in ('plan','manifest','prelaunch','observer-source','observer-manifest','support-source','support-manifest','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--cpu-timeout',type=float,default=180.);p.add_argument('--nn-timeout',type=float,default=600.)
    run(p.parse_args())

