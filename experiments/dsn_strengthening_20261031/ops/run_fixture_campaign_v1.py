"""Serial frozen real-neural timing fixtures; delegates each hard watchdog."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time,traceback

def main(a):
    P=pathlib.Path(a.project);S=P/'paired_resident_source_v2';sys.path.insert(0,str(S))
    from common import read,put,sha,need,verify_checkout,root_preflight_receipt,child_environment
    from process_cleanup import process_identity
    from run_paired_campaign import stop_owned_processes
    planpath=P/'BUFFER4_v1_FROZEN.json';plan=read(planpath);out=pathlib.Path(plan['raw_result_location']);out.mkdir(parents=True,exist_ok=False)
    identity=verify_checkout(S,P/'PAIRED_RESIDENT_SOURCE_v2.json');root_preflight_receipt(a.root_receipt,sha(a.root_receipt),identity['source_commit'],identity['source_manifest_sha256'])
    cpu=pathlib.Path(a.cpu_gate);gate=read(cpu);need(gate['status']=='PASS_FORMAL_FIXTURE25_LINUX_CPU_ZERO_SKIP' and gate['source_commit']==plan['source_commit'] and gate['tests']==25 and gate['skipped']==gate['errors']==gate['failures']==0 and gate['shared_environment_sha256']==plan['environment_sha256'],'formal fixture CPU receipt differs')
    for dep in plan['dependencies'].values():verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit'])
    need(sha(plan['environment_record'])==plan['environment_sha256'] and sha(plan['reference_details'])==plan['reference_details_sha256'] and sha(plan['reference_gate'])==plan['reference_gate_sha256'],'frozen fixture env/reference differs')
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,source_hierarchy=plan['source_identity'],shared_environment_sha256=plan['environment_sha256'],formal_CPU_gate_sha256=sha(cpu),root_noarg_preflight_sha256=sha(a.root_receipt),queue_wrapper_sha256=sha(__file__)))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=plan['source_commit'],queue_orchestrator_source_commit=identity['source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];env=child_environment(plan);(out/'logs').mkdir()
    try:
        for cell in plan['cells']:
            need(sha(cell['config'])==cell['config_sha256'],'cell config changed');need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=5).strip(),'physical resources occupied before fresh fixture')
            for dep in plan['dependencies'].values():verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit'])
            put(out/'PROGRESS.json',dict(completed=len(results),planned=4,current=cell['cell_id']),replace=True)
            put(out/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],code_commit=plan['source_commit'],harness_source_commit=plan['harness_source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=cell['out'],aggregate_summary_location=cell['out']+'/SUMMARY.json',gate_decision_location=cell['buffer_gate']))
            child=None;ticks=None;timed_out=False;handled=False
            try:
                with (out/'logs'/(cell['cell_id']+'.log')).open('x') as log:
                    child=subprocess.Popen(cell['command'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env);physical=process_identity(child.pid);need(physical is not None,'fixture CLI exited before launch identity capture');ticks=physical['start_ticks']
                    try:rc=child.wait(timeout=1050) # strictly outside frozen900+40+5; original240 unchanged
                    except subprocess.TimeoutExpired:
                        timed_out=True;raise # one bounded finally cleanup; never retry/extend original service
                gates={name:read(cell[field]) if pathlib.Path(cell[field]).exists() else {'status':'MISSING_GATE'} for name,field in [('watchdog','watchdog_gate'),('buffer','buffer_gate'),('resident','resident_gate')]}
                expected='PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH' if cell['expect_match'] else 'PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MISMATCH_REJECTED'
                passed=not timed_out and rc==0 and gates['watchdog']['status']=='PASS_EXTERNAL_HARD_CLOCK_CHILD_AND_PHYSICAL_DRAIN' and gates['buffer']['status']==expected and gates['resident']['status']=='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE'
                result=dict(cell_id=cell['cell_id'],position=cell['position'],repeat=cell['repeat'],expect_match=cell['expect_match'],returncode=rc,outer_timed_out=timed_out,all_three_gates_and_exit_pass=passed,gates=gates);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True)
                # All predetermined cells continue after a mechanism-negative outcome
                # only when the actual physical resource state is confirmed empty.
                need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=5).strip(),'fixture returned with remaining CUDA owners; stop queue')
                need(not timed_out,'outer watchdog itself exceeded frozen fixture hard-clock boundary')
                if not passed:
                    status=gates['watchdog'].get('status','');cleanup=gates['watchdog'].get('cleanup',{})
                    need('UNVERIFIED' not in str(cleanup) and status!='MISSING_GATE','fixture physical cleanup is unverified; stop queue')
                handled=True
            finally:
                if child is not None and not handled:
                    try:
                        if ticks is None and child.poll() is None:
                            physical=process_identity(child.pid);need(physical is not None,'live child generation could not be captured for cleanup');ticks=physical['start_ticks']
                        release=stop_owned_processes(child,cell['out'],child_start_ticks=ticks,timeout=40,query_timeout=5)
                        put(out/(cell['cell_id']+'_OUTER_EXCEPTION_CLEANUP.json'),dict(status='PASS_OWNED_EXCEPTION_CLEANUP_TRIAL_STAYS_FAILED',release=release))
                    except BaseException:
                        put(out/(cell['cell_id']+'_OUTER_EXCEPTION_CLEANUP.json'),dict(status='FAIL_OWNED_EXCEPTION_CLEANUP_UNVERIFIED',confirmed_physical_release=False,failure=traceback.format_exc()));raise
        status='PASS_COMPLETE_FROZEN_BUFFER4_REAL_NN_WITNESSES' if all(r['all_three_gates_and_exit_pass'] for r in results) else 'NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED'
        put(out/'SUMMARY.json',dict(status=status,completed_cells=4,planned_cells=4,cells=results,scope=plan['gate_rule']));put(out/'GATE.json',dict(status=status,completed_cells=4,planned_cells=4))
    except BaseException:
        put(out/'SUMMARY.json',dict(status='FAIL_OR_INCOMPLETE_BUFFER4_PRESERVED',completed_cells=len(results),planned_cells=4,cells=results));put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_BUFFER4_PRESERVED',failure=traceback.format_exc(),completed_cells=len(results),incomplete_active_cell=cell['cell_id'] if 'cell' in locals() else None));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--root-receipt',required=True);p.add_argument('--cpu-gate',required=True);main(p.parse_args())
