"""Two-strategy finite resident smoke, then only the prewritten repeat pair."""
from __future__ import annotations
import argparse,os,pathlib,subprocess,sys,time,traceback
from common import read,put,sha,need,disk_path,verify_checkout,child_environment,lines
from external_power import ExternalObserver,nvml_snapshot,energy
from run_paired_campaign import validate_plan,ready_rows,check_ready,capture_ready_environment,stop_owned_processes

def resident_smoke(results):
    need(len(results)==2 and {r['arm'] for r in results}=={'fullcall','conservative'},'resident smoke pair incomplete')
    by={r['arm']:r['summary'] for r in results};full=by['fullcall'];control=by['conservative']
    useful=all(r['primary']['complete_coverage_and_original_quantile_pass'] for r in full['per_request'])
    df=full['primary']['primary_linear_all_offered_D99'];dc=control['primary']['primary_linear_all_offered_D99'];gain=full['primary']['dual_deadline_audio_credit_seconds']-control['primary']['dual_deadline_audio_credit_seconds']
    opportunity=gain>=1 or (df is not None and dc is not None and dc>0 and df<=.75*dc)
    return dict(status='CONTINUE_PREWRITTEN_SECOND_RESIDENT_PAIR' if useful and opportunity else 'NO_GO_RESIDENT_SMOKE_NO_CONTRACT_REPAIR',all_four_fullcall_requests_original_D2_C8_pass=useful,strong_real_E2E_opportunity=opportunity,credit_gain_audio_seconds=gain,no_source_or_gap_or_threshold_tuning_allowed=True)

def run(plan_path,manifest,prelaunch_path,out):
    plan=read(plan_path);identity,environment=validate_plan(plan,manifest,read(prelaunch_path),paired=False);out=disk_path(out);need(str(out)==plan['raw_result_location'],'unfrozen resident output');out.mkdir(parents=True,exist_ok=False);put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(controller=identity,shared_environment=environment,actual_NN_source=plan['dependencies']['final']))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],actual_NN_source_commit=plan['dependencies']['final']['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];env=child_environment(plan)
    try:
        for index,cell in enumerate(plan['cells']):
            dep=plan['dependencies']['final'];verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit']);need(not nvml_snapshot()['compute_processes'],'GPU occupied before resident fresh trial')
            raw=disk_path(cell['out']);raw.parent.mkdir(parents=True,exist_ok=True);log=disk_path(cell['log']);log.parent.mkdir(parents=True,exist_ok=True);powerpath=out/(cell['cell_id']+'_EXTERNAL_NVML.jsonl');observer=ExternalObserver(powerpath);captured={};child=None;child_ticks=None;completed=False
            put(out/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],harness_source_commit=identity['source_commit'],actual_NN_source_commit=dep['source_commit'],frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json')))
            command=[sys.executable,'-B',str(pathlib.Path(__file__).parent/'resident_entry.py'),'--config',cell['config'],'--manifest',dep['source_manifest'],'--out',str(raw)]
            try:
                observer.start()
                with log.open('x',encoding='utf8') as stream:
                    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                    from process_cleanup import process_identity
                    child_identity=process_identity(child.pid);need(child_identity is not None,'resident child exited before launch identity capture');child_ticks=child_identity['start_ticks'];deadline=time.perf_counter()+plan['maximum_process_seconds']
                    while child.poll() is None:
                        observer.check();capture_ready_environment(raw,observer,captured,environment);need(time.perf_counter()<deadline,'resident fresh-process wall bound exceeded');time.sleep(.1)
                    capture_ready_environment(raw,observer,captured,environment);need(child.returncode==0,'resident trial failed; retain and stop')
                ready=ready_rows(raw);ready_gate=check_ready(ready,environment);need(set(captured)=={str(r['pid']) for r in ready},'missing actual resident allocator evidence');observer.finish(not_before=time.perf_counter())
                summary=read(raw/'SUMMARY.json');need(summary['gate']=='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE','resident complete task/clock/reference gate did not pass')
                events=lines(raw/'owner_e0/owner_events.jsonl');starts=[r for r in events if r['kind']=='worker_started'];need(len(starts)==2 and all(r['incarnation']==0 for r in starts),'normal resident silently reloaded/replaced model')
                dispatch=lines(raw/'owner_e0/dispatch.jsonl');pidset={r['pid'] for r in ready};need(dispatch and all(r['pid'] in pidset for r in dispatch),'resident dispatched through a different model process')
                origin=read(raw/'ORIGIN.json')['origin_perf'];eos=max(r['actual_Consumer_EOS_perf'] for r in summary['per_request'])
                result=dict(cell_id=cell['cell_id'],arm=cell['arm'],repeat=cell['repeat'],summary=summary,actual_READY_gate=ready_gate,worker_PIDs_continuous=sorted(pidset),per_request_executing_PIDs={sid:sorted({r['pid'] for r in dispatch if r['job']['source_id']==sid}) for sid in read(cell['config'])['request_order']},initial_worker_allocator_observations=captured,external_common_energy=dict(origin_to_final_useful_certified_EOS=energy(powerpath,origin,eos),origin_to_confirmed_physical_model_drain=energy(powerpath,origin,observer.drain['confirmed_perf']),physical_drain_observation=observer.drain,original_resident_energy=summary['energy']))
                put(raw/'EXTERNAL_RESIDENT_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);completed=True
            finally:
                if child is not None and not completed:
                    try:release=stop_owned_processes(child,raw,child_start_ticks=child_ticks,known_members=list(captured.values()));put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),release)
                    except BaseException:
                        put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),dict(status='FAIL_EXTERNAL_CLEANUP_RELEASE_UNVERIFIED',confirmed_physical_release=False,failure=traceback.format_exc()));raise
                    finally:observer.close()
                else:observer.close()
            if index==1:
                decision=resident_smoke(results);put(out/'SMOKE2_DECISION.json',decision)
                if decision['status']!='CONTINUE_PREWRITTEN_SECOND_RESIDENT_PAIR':
                    put(out/'SUMMARY.json',dict(status=decision['status'],completed_cells=2,planned_cells=4,unrun_frozen_cells=2,decision=decision,cells=results));put(out/'GATE.json',decision);return
        put(out/'SUMMARY.json',dict(status='PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE',completed_cells=4,planned_cells=4,cells=results));put(out/'GATE.json',dict(status='PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE',scope=plan['scope']))
    except BaseException:
        put(out/'SUMMARY.json',dict(status='FAIL_OR_INCOMPLETE_RESIDENT_SCOPE_PRESERVED',completed_cells=len(results),planned_cells=4,cells=results));put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_RESIDENT_SCOPE_PRESERVED',failure=traceback.format_exc()));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--manifest',required=True);p.add_argument('--prelaunch',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.plan,a.manifest,a.prelaunch,a.out)
