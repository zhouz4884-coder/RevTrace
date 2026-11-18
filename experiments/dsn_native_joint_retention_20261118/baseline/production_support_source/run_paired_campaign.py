"""Serial fresh-process two-version campaign; launches only after root gates."""
from __future__ import annotations
import argparse,importlib.metadata,json,os,pathlib,statistics,subprocess,sys,time,traceback
from common import need,read,put,sha,verify_checkout,disk_path,child_environment,root_preflight_receipt,lines
from external_power import ExternalObserver,nvml_snapshot
from audit_results import audit_cell
from endpoints import smoke_decision

def stop_owned_processes(child,raw,*,child_start_ticks=None,known_members=(),timeout=40.,query_timeout=2.):
    """Outer watchdog: stop this Supervisor first, then every proved Owner group.

    The final neural dependency's internal wait_cuda_release is unchanged. A CLI
    hang or unproved cleanup is a FAIL, never a released resource lease.
    """
    from process_cleanup import group_proof,signal_group,terminate_group,owned_worker_identities,descendant_session_proofs,CleanupError
    deadline=time.perf_counter()+timeout;events=[];proofs=[];errors=[];descendant_proofs=[]
    try:descendant_proofs=descendant_session_proofs(child.pid,child_start_ticks)
    except BaseException as exc:errors.append('descendant identity snapshot: '+repr(exc))
    path=pathlib.Path(raw)/'supervisor.jsonl'
    if path.exists():
        fragments=path.read_bytes().splitlines()
        for index,fragment in enumerate(fragments):
            try:events.append(json.loads(fragment))
            except json.JSONDecodeError:
                if index!=len(fragments)-1:errors.append('non-tail supervisor cleanup metadata corruption')
    started={r['pid']:r for r in events if r.get('kind')=='owner_started'}
    registered={r['event']['pid'] for r in events if r.get('event',{}).get('kind')=='owner_group_started' and r['event'].get('pid')==r['event'].get('pgid')}
    # Popen's generation is captured immediately after creation, before waiting.
    # Stop its session first so it cannot launch a replacement Owner during cleanup.
    try:
        proof=group_proof(child.pid,child_start_ticks,known_members=known_members);proof,unused=signal_group(proof);proofs.append(proof)
        if child.poll() is None:child.wait(timeout=max(.01,min(5.,deadline-time.perf_counter())))
    except BaseException as exc:errors.append('outer child session: '+repr(exc))
    # Re-read the complete metadata prefix after the Supervisor can no longer
    # spawn. This includes an Owner created between the first read and SIGKILL.
    if path.exists():
        for index,fragment in enumerate(path.read_bytes().splitlines()):
            try:
                row=json.loads(fragment)
                if row.get('kind')=='owner_started':started[row['pid']]=row
                event=row.get('event',{})
                if event.get('kind')=='owner_group_started' and event.get('pid')==event.get('pgid'):registered.add(event['pid'])
            except json.JSONDecodeError:pass
    if any(pathlib.Path(raw).glob('owner_e*')) and not started and not descendant_proofs:errors.append('Owner attempt exists without a provable launch/session identity')
    for proof in descendant_proofs:
        try:proof,unused=signal_group(proof);proofs.append(proof)
        except BaseException as exc:errors.append('proved descendant group '+str(proof['pid'])+': '+repr(exc))
    for pid,row in started.items():
        try:
            known=owned_worker_identities(raw,row['owner_epoch']);proof=group_proof(pid,row['start_ticks'],bound_event=pid in registered,known_members=known);proof,unused=signal_group(proof);proofs.append(proof)
        except BaseException as exc:errors.append('Owner group '+str(pid)+': '+repr(exc))
    releases=[]
    for proof in proofs:
        try:releases.append(terminate_group(None,proof,timeout=max(.01,deadline-time.perf_counter()),query_timeout=query_timeout))
        except BaseException as exc:errors.append('release '+str(proof['pid'])+': '+repr(exc))
    if errors:raise CleanupError('outer watchdog physical release remains unverified: '+'; '.join(errors))
    return dict(status='PASS_EXTERNAL_WATCHDOG_OWNED_GROUPS_AND_CUDA_RELEASE',releases=releases,original_trial_stays_failed=True)

def ready_rows(out):
    out=pathlib.Path(out)
    if (out/'READY.json').exists():return list(read(out/'READY.json').values())
    rows=[]
    for path in out.glob('owner_e*/worker_results.jsonl'):
        for row in lines(path):
            if row['event']['kind']=='ready':rows.append(row['event'])
    return rows
def check_ready(rows,environment):
    need(len(rows)==2,'normal paired cell must have exactly two fresh model workers')
    for row in rows:
        actual=row['environment'];warm=row['neural_ready_warmup']
        need(actual['autocast_enabled'] is False and actual['TF32'] is False,'precision controls changed')
        need(row['asr_parameter_dtypes']==environment['asr_parameter_dtypes'] and row['corrector_parameter_dtypes']==environment['corrector_parameter_dtypes'],'actual parameter precision/count differs')
        need(actual['packages']==environment['worker_packages'],'worker package identity differs')
        need(warm['neural_C_confirmed'] and warm['reset_to_genesis'] and not warm['warmup_packet_admitted'],'fixed learned C warmup not completed/reset')
        if 'PYTORCH_CUDA_ALLOC_CONF' in actual:need(actual['PYTORCH_CUDA_ALLOC_CONF']==environment['runtime_environment']['PYTORCH_CUDA_ALLOC_CONF'] and actual.get('PYTORCH_ALLOC_CONF') is None,'worker actual allocator differs')
    need({r['gpu'] for r in rows}=={0,1},'physical two-board assignment differs')
    return dict(status='PASS_TWO_ACTUAL_FRESH_FP32_READY_WORKERS',worker_pids=[r['pid'] for r in rows],allocator_legacy_record_rule='BDFA omits allocator in READY: inherited initial worker environment separately captured from /proc before model exit; missing READY field is not backfilled')

def capture_ready_environment(out,observer,captured,environment):
    observer.discover_workers(out)
    for pid in tuple(observer.worker_pids):
        if str(pid) in captured:continue
        path=pathlib.Path('/proc')/str(pid)/'environ'
        if not path.exists():continue
        selected={}
        for entry in path.read_bytes().split(b'\0'):
            if b'=' not in entry:continue
            key,value=entry.split(b'=',1)
            if key in (b'PYTORCH_CUDA_ALLOC_CONF',b'PYTORCH_ALLOC_CONF'):selected[key.decode()]=value.decode()
        need(selected.get('PYTORCH_CUDA_ALLOC_CONF')==environment['runtime_environment']['PYTORCH_CUDA_ALLOC_CONF'] and 'PYTORCH_ALLOC_CONF' not in selected,'actual initial worker allocator environment differs')
        from process_cleanup import process_identity
        identity=process_identity(pid);need(identity is not None,'worker exited before initial identity capture')
        captured[str(pid)]=dict(pid=pid,start_ticks=identity['start_ticks'],observed_perf=time.perf_counter(),initial_process_allocator_environment=selected,route='/proc/PID/environ whitelist only; no unrelated environment/secret captured')

def validate_plan(plan,manifest,prelaunch,*,paired=True):
    identity=verify_checkout(pathlib.Path(__file__).parent,manifest,plan['controller_source_commit']);need(sha(manifest)==plan['controller_manifest_sha256'],'controller manifest changed')
    root_preflight_receipt(prelaunch['root_noarg_preflight'],prelaunch['root_noarg_preflight_sha256'],identity['source_commit'],sha(manifest))
    need(prelaunch['exclusive_GPU_window_authorized_by_root'] is True,'no root-owned exclusive GPU window')
    need(sha(plan['environment_record'])==plan['environment_sha256'],'frozen shared environment changed');environment=read(plan['environment_record'])
    need(str(pathlib.Path(sys.executable).resolve())==str(pathlib.Path(plan['environment_python']).resolve()),'wrong actual environment interpreter')
    for package,version in environment['packages'].items():need(importlib.metadata.version(package)==version,'actual environment package differs: '+package)
    asset=prelaunch['asset_byte_gate'];need(sha(asset['path'])==asset['sha256'],'asset byte prerequisite changed');gate=read(asset['path'])
    need(gate['status'].startswith('PASS') and gate['all_asset_bytes_verified'] is True and gate['asset_manifest_sha256']==environment['assets_manifest_sha256'],'complete actual asset-byte prerequisite missing')
    need(sha(environment['assets_manifest_path'])==environment['assets_manifest_sha256'],'model asset manifest changed')
    count=32 if paired else 4;smoke=8 if paired else 2
    need(len(plan['cells'])==plan['expected_cells']==count and plan['smoke_cells']==smoke,'queue must be complete frozen scope')
    need(len({c['cell_id'] for c in plan['cells']})==count,'duplicate cell ID')
    for version,dependency in plan['dependencies'].items():
        need(sha(dependency['source_manifest'])==dependency['source_manifest_sha256'],'dependency manifest changed')
        verify_checkout(dependency['source_root'],dependency['source_manifest'],dependency['source_commit'])
    need(sha(plan['reference_details'])==plan['reference_details_sha256'] and sha(plan['reference_gate'])==plan['reference_gate_sha256'],'legal original reference bytes changed')
    need(read(plan['reference_gate'])['status'].startswith('PASS'),'legal original reference not passed')
    for cell in plan['cells']:
        need(sha(cell['config'])==cell['config_sha256'],'frozen cell config changed');config=read(cell['config']);dep=plan['dependencies'][cell['version'] if paired else 'final']
        need(config['cell_id']==cell['cell_id'] and config['settings']['source_commit']==dep['source_commit'],'wrong actual cell source')
        need(config['settings']['corrector_dtype']=='float32' and config['settings']['max_ahead_frames']==32000,'original config semantics changed')
        for source in config['settings']['model_sources']:need(sha(source['path'])==source['audio_sha256'],'immutable source/warmup audio differs')
        disk_path(cell['out']);disk_path(cell['log'])
        if paired:disk_path(cell['external_power'])
    return identity,environment

def aggregate(results,planned):
    comparisons=[];by={(r['source_id'],r['version'],r['strategy'],r['repeat']):r for r in results}
    for sid in sorted({r['source_id'] for r in results}):
        for strategy in ('conservative','fullcall'):
            for rep in (0,1):
                old=by.get((sid,'bdfa',strategy,rep));new=by.get((sid,'final',strategy,rep))
                if not old or not new:continue
                a=old['primary'];b=new['primary'];d0=a['primary_linear_all_offered_D99'];d1=b['primary_linear_all_offered_D99']
                comparisons.append(dict(source_id=sid,strategy=strategy,repeat=rep,bdfa_D99=d0,final_D99=d1,D99_difference_seconds=None if None in (d0,d1) else d1-d0,bdfa_pass=a['complete_coverage_and_original_quantile_pass'],final_pass=b['complete_coverage_and_original_quantile_pass'],dual_credit_difference_seconds=b['dual_deadline_audio_credit_seconds']-a['dual_deadline_audio_credit_seconds']))
    final=[r for r in results if r['version']=='final' and r['strategy']=='fullcall'];passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in final)
    return dict(status='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT' if len(results)==planned else 'GATED_PARTIAL_QUEUE_PRESERVED',planned_cells=planned,completed_cells=len(results),independent_speakers=4,repeated_runs_are_not_speakers=True,final_fullcall_original_gate_passes=passes,final_fullcall_runs=len(final),final_8of8_inheritance_established=len(final)==8 and passes==8,paired_comparisons=comparisons,no_statistical_equivalence_or_causal_code_defect_claim=True,cells=results)

def run(plan_path,manifest,prelaunch_path,out):
    plan=read(plan_path);prelaunch=read(prelaunch_path);identity,environment=validate_plan(plan,manifest,prelaunch);out=disk_path(out);need(str(out)==plan['raw_result_location'],'unfrozen output location');out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,controller=identity,environment=environment,prelaunch_sha256=sha(prelaunch_path),actual_NN_dependencies=plan['dependencies']))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],controller_source_commit=identity['source_commit'],actual_NN_sources={k:v['source_commit'] for k,v in plan['dependencies'].items()},frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),root_noarg_preflight_sha256=prelaunch['root_noarg_preflight_sha256']))
    results=[];reference=read(plan['reference_details']);env=child_environment(plan)
    try:
        for index,cell in enumerate(plan['cells']):
            dep=plan['dependencies'][cell['version']];nn_gate=verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit']);need(not nvml_snapshot()['compute_processes'],'GPU occupied before fresh paired cell')
            raw=disk_path(cell['out']);raw.parent.mkdir(parents=True,exist_ok=True);need(not raw.exists(),'never overwrite a cell');log=disk_path(cell['log']);log.parent.mkdir(parents=True,exist_ok=True);powerpath=disk_path(cell['external_power']);powerpath.parent.mkdir(parents=True,exist_ok=True)
            put(out/'PROGRESS.json',dict(completed=len(results),planned=32,current=cell['cell_id'],stage='source_gated_then_neural_load_and_original_service'),replace=True)
            put(out/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],controller_source_commit=identity['source_commit'],actual_NN_source=nn_gate,frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=cell['out'],aggregate_summary_location=cell['out']+'/SUMMARY.json',gate_decision_location=cell['out']+'/GATE.json'))
            command=[sys.executable,'-B',str(pathlib.Path(dep['source_root'])/dep['entry']),'--config',cell['config'],'--manifest',dep['source_manifest'],'--out',cell['out']];observer=ExternalObserver(powerpath);captured={};child=None;child_ticks=None;completed=False
            try:
                observer.start()
                with log.open('x',encoding='utf8') as stream:
                    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                    from process_cleanup import process_identity
                    child_identity=process_identity(child.pid);need(child_identity is not None,'outer child exited before launch identity capture');child_ticks=child_identity['start_ticks']
                    deadline=time.perf_counter()+plan['maximum_process_seconds']
                    while child.poll() is None:
                        observer.check();capture_ready_environment(raw,observer,captured,environment);need(time.perf_counter()<deadline,'fresh-process wall bound exceeded including load');time.sleep(.1)
                    capture_ready_environment(raw,observer,captured,environment);need(child.returncode==0,'actual neural cell failed; retain raw failure and stop')
                ready=ready_rows(raw);ready_gate=check_ready(ready,environment);need(set(captured)=={str(r['pid']) for r in ready},'did not capture both actual initial allocator environments')
                observer.finish(not_before=time.perf_counter());need(not nvml_snapshot()['compute_processes'],'cell returned before CUDA owners released')
                result=audit_cell(cell,read(cell['config']),reference,observer);result['actual_READY_gate']=ready_gate;result['initial_worker_allocator_observations']=captured;put(raw/'EXTERNAL_PAIRED_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);completed=True
            finally:
                if child is not None and not completed:
                    try:release=stop_owned_processes(child,raw,child_start_ticks=child_ticks,known_members=list(captured.values()));put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),release)
                    except BaseException:
                        put(raw.parent/(cell['cell_id']+'_EXTERNAL_FAILURE_CLEANUP.json'),dict(status='FAIL_EXTERNAL_CLEANUP_RELEASE_UNVERIFIED',confirmed_physical_release=False,failure=traceback.format_exc()));raise
                    finally:observer.close()
                else:observer.close()
            if index==7:
                decision=smoke_decision(results);put(out/'SMOKE8_DECISION.json',decision)
                if decision['status']!='CONTINUE_REMAINING_24_FROZEN_CELLS':
                    result=aggregate(results,32);result['stopping_decision']=decision;put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=decision['status'],completed=8,unrun_frozen_cells=24,causal_code_defect_established=False));return result
        result=aggregate(results,32);put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=result['status'],completed_cells=32,planned_cells=32,final_8of8_inheritance_established=result['final_8of8_inheritance_established']));return result
    except BaseException:
        put(out/'SUMMARY.json',aggregate(results,32));put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_PAIRED_CAMPAIGN_PRESERVED',completed_cells=len(results),planned_cells=32,failure=traceback.format_exc()));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--manifest',required=True);p.add_argument('--prelaunch',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.plan,a.manifest,a.prelaunch,a.out)
