"""At most four unchanged-NN two-client interference trials; no scheduling repair."""
from __future__ import annotations
import argparse,os,pathlib,subprocess,sys,time,traceback
from common import read,put,sha,need,disk_path,verify_checkout,child_environment,lines
from external_power import ExternalObserver,nvml_snapshot,energy
from run_paired_campaign import validate_plan,ready_rows,check_ready,capture_ready_environment,stop_owned_processes

from interference_analysis import opportunity_decision,PASS
from interference_contract import ORDER,validate_contract
from interference_prerequisites import validate_prior_scopes
from build_interference_plan import RULE

def run(plan_path,manifest,prelaunch_path,out):
    plan=read(plan_path);prelaunch=read(prelaunch_path);need(plan['opportunity_rule']==RULE and plan['maximum_process_seconds']==720 and plan['maximum_failure_cleanup_seconds']==40,'unfrozen gate/process/cleanup bound');prior_gate=validate_prior_scopes(prelaunch['prior_scope_completion']);identity,environment=validate_plan(plan,manifest,prelaunch,paired=False);
    need([(c['arm'],c['repeat']) for c in plan['cells']]==[('conservative',0),('fullcall',0),('fullcall',1),('conservative',1)],'wrong prospective queue/repeat order')
    for cell in plan['cells']:
        config=read(cell['config']);validate_contract(config);need(config['opportunity_rule']==RULE and config['observation_wrapper_source_commit']==identity['source_commit'],'wrong observational source/rule');need(config['harness_source']==plan['harness_source'],'wrong harness config dependency');need(config['arm']==cell['arm'] and config['repeat']==cell['repeat']==config['settings']['primary_gpu'],'cell arm/repeat/GPU assignment differs')
    out=disk_path(out);need(str(out)==plan['raw_result_location'],'unfrozen resident output');out.mkdir(parents=True,exist_ok=False);put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(controller=identity,shared_environment=environment,actual_NN_source=plan['dependencies']['final'],prior_scope_completion=prior_gate))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],actual_NN_source_commit=plan['dependencies']['final']['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];env=child_environment(plan);attempted=0
    try:
        for index,cell in enumerate(plan['cells']):
            put(out/'PROGRESS.json',dict(completed=len(results),planned=4,current=cell['cell_id'],stage='unchanged59_observational_two_client_trial'),replace=True)
            dep=plan['dependencies']['final'];verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit']);need(not nvml_snapshot()['compute_processes'],'GPU occupied before resident fresh trial')
            raw=disk_path(cell['out']);raw.parent.mkdir(parents=True,exist_ok=True);need(not raw.exists(),'never overwrite/rerun a trial');log=disk_path(cell['log']);log.parent.mkdir(parents=True,exist_ok=True);powerpath=out/(cell['cell_id']+'_EXTERNAL_NVML.jsonl');observer=ExternalObserver(powerpath);captured={};child=None;child_ticks=None;completed=False
            put(out/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],harness_source_commit=identity['source_commit'],actual_NN_source_commit=dep['source_commit'],frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json')))
            command=[sys.executable,'-B',str(pathlib.Path(__file__).parent/'interference_entry.py'),'--config',cell['config'],'--manifest',dep['source_manifest'],'--out',str(raw)]
            try:
                observer.start()
                with log.open('x',encoding='utf8') as stream:
                    need(attempted<4,'maximum four actual launch attempts');attempted+=1
                    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                    from process_cleanup import process_identity
                    child_identity=process_identity(child.pid);need(child_identity is not None,'resident child exited before launch identity capture');child_ticks=child_identity['start_ticks'];deadline=time.perf_counter()+plan['maximum_process_seconds']
                    while child.poll() is None:
                        observer.check();capture_ready_environment(raw,observer,captured,environment);need(time.perf_counter()<deadline,'resident fresh-process wall bound exceeded');time.sleep(.1)
                    capture_ready_environment(raw,observer,captured,environment);need(child.returncode==0,'resident trial failed; retain and stop')
                ready=ready_rows(raw);ready_gate=check_ready(ready,environment);need(set(captured)=={str(r['pid']) for r in ready},'missing actual resident allocator evidence');observer.finish(not_before=time.perf_counter())
                summary=read(raw/'SUMMARY.json');need(summary['gate']==PASS,'resident complete task/clock/reference gate did not pass')
                events=lines(raw/'owner_e0/owner_events.jsonl');starts=[r for r in events if r['kind']=='worker_started'];need(len(starts)==2 and all(r['incarnation']==0 for r in starts),'normal resident silently reloaded/replaced model')
                dispatch=lines(raw/'owner_e0/dispatch.jsonl');pidset={r['pid'] for r in ready};need(dispatch and all(r['pid'] in pidset for r in dispatch),'resident dispatched through a different model process')
                origin=read(raw/'ORIGIN.json')['origin_perf'];eos=max(r['actual_Consumer_EOS_perf'] for r in summary['per_request'])
                result=dict(cell_id=cell['cell_id'],arm=cell['arm'],repeat=cell['repeat'],summary=summary,actual_READY_gate=ready_gate,worker_PIDs_continuous=sorted(pidset),per_request_executing_PIDs={sid:sorted({r['pid'] for r in dispatch if r['job']['source_id']==sid}) for sid in ORDER},initial_worker_allocator_observations=captured,external_common_energy=dict(origin_to_final_useful_certified_EOS=energy(powerpath,origin,eos),origin_to_confirmed_physical_model_drain=energy(powerpath,origin,observer.drain['confirmed_perf']),physical_drain_observation=observer.drain,original_resident_energy=summary['energy']))
                put(raw/'EXTERNAL_INTERFERENCE_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);completed=True
            finally:
                if child is not None and not completed:
                    try:release=stop_owned_processes(child,raw,child_start_ticks=child_ticks,known_members=list(captured.values()),timeout=plan['maximum_failure_cleanup_seconds']);put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),release)
                    except BaseException:
                        put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),dict(status='FAIL_EXTERNAL_CLEANUP_RELEASE_UNVERIFIED',confirmed_physical_release=False,failure=traceback.format_exc()));raise
                    finally:observer.close()
                else:observer.close()
            if index==1:
                decision=opportunity_decision(results);put(out/'SMOKE2_DECISION.json',decision)
                if decision['status']!='CONTINUE_PREWRITTEN_SECOND_OPPORTUNITY_PAIR':
                    put(out/'SUMMARY.json',dict(status=decision['status'],completed_cells=2,attempted_cells=attempted,planned_cells=4,unrun_frozen_cells=2,decision=decision,cells=results));put(out/'GATE.json',decision);return
        decision=opportunity_decision(results,final=True);put(out/'SUMMARY.json',dict(status=decision['status'],completed_cells=4,attempted_cells=attempted,planned_cells=4,decision=decision,cells=results));put(out/'GATE.json',decision)
    except BaseException:
        put(out/'SUMMARY.json',dict(status='FAIL_OR_INCOMPLETE_INTERFERENCE_SCOPE_PRESERVED',completed_cells=len(results),attempted_cells=attempted,planned_cells=4,unrun_frozen_cells=4-attempted,cells=results));put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_INTERFERENCE_SCOPE_PRESERVED',failure=traceback.format_exc()));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--manifest',required=True);p.add_argument('--prelaunch',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.plan,a.manifest,a.prelaunch,a.out)
