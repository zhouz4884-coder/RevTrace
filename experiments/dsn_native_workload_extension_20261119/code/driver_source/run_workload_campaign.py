"""Fresh-process metadata-selected workload extension: three policies, no factorial claim.

All scientific inputs are frozen in the plan. SLO misses and zero opportunity
are outcomes, not reasons to skip/retry. Technical failures stop and preserve
the complete attempted prefix, with the full planned denominator still named.
"""
from __future__ import annotations
import argparse,hashlib,importlib,importlib.metadata,json,math,pathlib,subprocess,sys,time,traceback
from confirmation_common import SUPPORT,need,read,sha,put,canonical,disk,verify_source,child_env,validate_prelaunch
from job_accounting import audit_trial

from workload_conditions import CONDITIONS, CONDITION_SETTINGS, validate_matrix
from corpus_contract import selected_md68_sources

ADDITIVE_CONTINUITY_FIELDS = frozenset((
    'canonical_applications', 'nonempty_ahead_canonical_applications',
    'compatible_ahead_applications', 'compatible_ahead_preserved', 'compatible_ahead_changed',
    'refuted_ahead_applications', 'missing_witness_ahead_applications',
    'total_withdrawals', 'avoidable_withdrawals', 'necessary_withdrawals', 'unknown_withdrawals',
    'removed_audio_seconds', 'avoidable_removed_audio_seconds', 'necessary_removed_audio_seconds',
    'unknown_removed_audio_seconds', 'actual_consumer_rows',
    'total_gap_audio_seconds_x_wall_seconds', 'avoidable_gap_audio_seconds_x_wall_seconds',
    'necessary_gap_audio_seconds_x_wall_seconds', 'unknown_gap_audio_seconds_x_wall_seconds',
    'same_root_avoidable_gap_audio_seconds_x_wall_seconds',
    'same_root_necessary_gap_audio_seconds_x_wall_seconds',
    'same_root_unknown_gap_audio_seconds_x_wall_seconds',
    'observed_loss_window_union_area_audio_seconds_x_wall_seconds',
    'gap_right_censored_windows', 'gap_boundary_truncated_windows', 'gap_restored_windows'))


def validate_reference(plan,driver,base):
    binding=plan['reference_receipt'];need(sha(binding['path'])==binding['sha256'],'reference receipt changed')
    ref=read(binding['path']);need(ref['status'].startswith('PASS'),'reference generation failed')
    need(ref['actual_NN_source_commit']==base['source_commit'] and ref['generator_source_commit']==driver['source_commit'],'reference execution/generator source differs')
    need(ref['reference_only']is True and ref['actual_serving_runs']==0,'reference cost mixed with serving')
    need(ref['original_continuous_no_between_step_restore']is True and ref['restored_repeats_per_edge']==2,'continuous/restore reference contract differs')
    for key in ('reference_details','reference_gate','genesis'):
        info=ref[key];need(sha(info['path'])==info['sha256'],'reference artifact changed: '+key)
    need(plan['reference_details']['path']==ref['reference_details']['path'] and plan['reference_details']['sha256']==ref['reference_details']['sha256'],'plan reference details differ from completed receipt')
    gate=read(ref['reference_gate']['path'])
    need(gate['status']==ref['status'] and gate['all_original_full_state_C_IDs_equal']is True,'original complete-state/C/IDs reference gate failed')
    need(gate['actual_NN_source_commit']==base['source_commit'] and gate['generator_source_commit']==driver['source_commit'],'reference gate wrong source')
    by={s['source_id']:s for s in ref['sources']};need(len(by)==len(ref['sources']),'duplicate reference source')
    for source in plan['sources']:need(by.get(source['source_id'])==source,'campaign source is not exact measured-reference subset')
    details=read(ref['reference_details']['path']);need(isinstance(details,list),'raw original details array required')
    need(len({(r['source_id'],r['end'])for r in details})==len(details),'duplicate reference frontier')
    expected=sum((s['frames']+7999)//8000 for s in ref['sources'])
    need(len(details)==expected and gate['expected_original_steps']==expected,'reference original-step scope incomplete')
    need(gate['expected_sources']==gate['completed_sources']==len(by),'reference source scope incomplete')
    genesis=read(ref['genesis']['path'])
    for sid,source in by.items():
        own=sorted((r for r in details if r['source_id']==sid),key=lambda r:r['end'])
        need([r['end']for r in own]==list(range(8000,source['frames'],8000))+[source['frames']],'reference500ms/partialEOS cadence differs')
        previous=genesis[sid];need(previous['frontier']==0,'reference genesis changed')
        for row in own:
            need(canonical(row['original_full_start_cut'])==canonical(previous),'reference full start chain differs')
            for field in ('original_full_start_cut','original_full_cut'):
                state=row[field];need(state['contract']['stage_execution']['source_commit']==base['source_commit'],'old states relabelled as new source')
                need(state['contract']['source_sha']==source['audio_sha256'],'reference audio identity differs')
            need(row['continuous_original_no_between_step_restore']is True,'original reference path was restored between steps')
            previous=row['original_full_cut']
    return details


def terminal_times(events):
    unique={};duplicates=0
    for event in events:
        if event.get('kind')not in ('completed','abandoned'):continue
        record=event.get('record',{})
        if record:worker=record.get('worker_job_wall_seconds');infer=record.get('model_seconds')
        elif event.get('worker_job_begin_perf')is not None and event.get('worker_job_end_perf')is not None:
            worker=event['worker_job_end_perf']-event['worker_job_begin_perf'];infer=None
        else:worker=infer=None
        row=dict(job_id=event['job_id'],kind=event['kind'],source_id=event.get('source_id'),worker_wall_seconds=worker,observed_infer_wall_seconds=infer)
        if row['job_id']in unique:
            need(unique[row['job_id']]==row,'contradictory physical terminal');duplicates+=1;continue
        need(worker is None or math.isfinite(worker)and worker>=0,'invalid worker timer')
        need(infer is None or math.isfinite(infer)and infer>=0 and(worker is None or infer<=worker+1e-6),'invalid nested infer timer')
        unique[row['job_id']]=row
    return list(unique.values()),duplicates


def worker_ledger(root,accounting):
    events=[];dispatches={}
    for attempt in pathlib.Path(root).glob('owner_e*'):
        for line in (attempt/'dispatch.jsonl').read_text(encoding='utf8').splitlines():
            job=json.loads(line)['job'];need(job['job_id']not in dispatches,'duplicate dispatched physical identity');dispatches[job['job_id']]=job
        for line in (attempt/'worker_results.jsonl').read_text(encoding='utf8').splitlines():events.append(json.loads(line)['event'])
    rows,duplicates=terminal_times(events)
    need({r['job_id']for r in rows}==set(dispatches),'physical worker timers do not cover all dispatches')
    need(len(rows)==accounting['dispatches'],'worker ledger/accounting denominator differs')
    missing=sum(r['worker_wall_seconds']is None for r in rows);infer_missing=sum(r['observed_infer_wall_seconds']is None for r in rows)
    need(missing==0,'complete physical worker occupation missing')
    return dict(status='PASS_COMPLETE_WORKER_TERMINAL_TIMER_LEDGER',worker_seconds=sum(r['worker_wall_seconds']for r in rows),observed_infer_seconds=sum(r['observed_infer_wall_seconds']for r in rows if r['observed_infer_wall_seconds']is not None),total_infer_seconds=None if infer_missing else sum(r['observed_infer_wall_seconds']for r in rows),missing_worker_timers=missing,missing_infer_timers=infer_missing,unique_jobs=len(rows),duplicate_terminals=duplicates,per_job=rows,scope='Whole worker-job elapsed intervals; abort infer NA is not zero or GPU-active time')


def power_ownership(rows,ready,initial_boards,start,end):
    need(rows and rows[0]['time']<=start and rows[-1]['time']>=end,'sampled power does not bracket service/drain')
    workers={r['pid']:str(r['gpu'])for r in ready};need(len(workers)==2 and set(workers.values())=={'0','1'},'actual READY board ownership incomplete')
    expected={str(k):v['uuid']for k,v in initial_boards.items()};samples=0
    for row in rows:
        need(all(row['boards'][gpu]['uuid']==expected[gpu]for gpu in('0','1')),'physical GPU UUID changed during trial')
        for process in row['compute_processes']:
            need(process['pid']in workers,'foreign compute PID in measured trial window')
            need(process['gpu_uuid']==expected[workers[process['pid']]],'actual worker changed its assigned physical GPU')
        if start<=row['time']<=end:samples+=1
    need(samples>0,'no sampled service power observations')
    return dict(status='PASS_SAMPLED_TWO_BOARD_OWNED_WORKER_WINDOW',actual_READY_pids=sorted(workers),gpu_uuids=expected,all_recorded_samples=len(rows),service_samples=samples,foreign_compute_PID_samples=0,scope='Recorded NVML observations bracket the real service-to-physical-drain window; unsampled instants are not hardware-attested')


def aggregate(results, plan, failed_cells=()):
    results = list(results)
    sources = plan['sources']
    by = {(r['source_id'], r['repeat'], r['condition']): r for r in results}
    need(len(by) == len(results), 'duplicate completed source/repeat/condition')
    expected_keys = {(s['source_id'], rep, cond) for s in sources for rep in (0,1) for cond in CONDITIONS}
    need(set(by).issubset(expected_keys), 'unplanned result or missing policy interpretation')
    planned = 2 * sum(s['frames']/16000 for s in sources)
    totals = {}
    def pooled(rows):
        off = sum(r['primary']['offered_audio_seconds'] for r in rows)
        credit = sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in rows)
        continuity = {}
        for key in ADDITIVE_CONTINUITY_FIELDS:
            vals = [r['view_audit']['continuity'].get(key) for r in rows]
            if rows and all(isinstance(v,(float,int)) and not isinstance(v,bool) for v in vals):
                continuity[key] = sum(vals)
        return dict(observed_offered_audio_s=off, credit_audio_s=credit,
            whole_run_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in rows),
            worker_seconds=sum(r['worker_ledger']['worker_seconds'] for r in rows),
            both_board_J=sum(r['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'] for r in rows),
            D2_misses=sum(r['primary']['D2_misses_all_offered'] for r in rows),
            C8_misses=sum(r['primary']['C8_misses_all_offered'] for r in rows),
            continuity_totals=continuity)
    for condition in CONDITIONS:
        chosen = [r for r in results if r['condition'] == condition]
        row = pooled(chosen)
        complete = len(chosen) == 2 * len(sources)
        row.update(completed_trials=len(chosen), planned_trials=2*len(sources),
            planned_offered_audio_s=planned, unobserved_planned_audio_s=max(0.,planned-row['observed_offered_audio_s']),
            coverage_percent=(100*row['credit_audio_s']/planned if complete else None))
        totals[condition] = row
    repeat_pairs = []
    source_pairs = []
    for source in sources:
        sid = source['source_id']
        all_rows = {c:[by.get((sid,r,c)) for r in (0,1)] for c in CONDITIONS}
        if all(all(v is not None for v in rows) for rows in all_rows.values()):
            source_pairs.append(dict(source_id=sid,speaker_id=source['speaker_id'],
                conditions={c:pooled(rows) for c,rows in all_rows.items()}))
        for rep in (0,1):
            chosen = {c:by.get((sid,rep,c)) for c in CONDITIONS}
            if any(v is None for v in chosen.values()): continue
            off = {r['primary']['offered_audio_seconds'] for r in chosen.values()}
            need(len(off)==1, 'paired offered denominator differs')
            value = {c:r['primary']['dual_deadline_audio_credit_seconds'] for c,r in chosen.items()}
            cont = {c:r['view_audit']['continuity'] for c,r in chosen.items()}
            repeat_pairs.append(dict(source_id=sid,speaker_id=source['speaker_id'],repeat=rep,
                offered_audio_s=off.pop(),credit_audio_s=value,
                S_at_R1_audio_s=value['r1s1']-value['r1s0'],
                joint_minus_conservative_audio_s=value['r1s1']-value['conservative_s1'],
                continuity_by_condition=cont))
    done = len(results)==plan['expected_trials'] and not failed_cells
    return dict(status=('COMPLETE_NATIVE_WORKLOAD_EXTENSION_TASK_AND_ENDPOINTS' if done else
        'INCOMPLETE_NATIVE_WORKLOAD_EXTENSION_QUEUE_PRESERVED'), planned_trials=plan['expected_trials'],
        completed_trials=len(results),failed_attempts=list(failed_cells),speaker_clusters=len(sources),
        condition_totals=totals,source_level_pairs=source_pairs,repeat_pairs=repeat_pairs,cells=results,
        actual_NN_source_commit=plan['actual_NN']['source_commit'],
        no_opportunity_or_tie_is_failure=False,SLO_failures_retained=True,
        reference_generation_separate_from_service=True,repeats_do_not_add_speaker_clusters=True,
        factorial_interaction_not_estimated=True,
        scope='Complete three-policy workload extension; no R0 arms and no factorial interaction. All offered obligations retained; incomplete conditions have no full-plan estimate.')


def validate_cell(cell,cfg,plan,base):
    need(cfg['cell_id']==cell['cell_id']and cfg['arm']==cell['strategy'],'cell identity or underlying strategy differs')
    need(type(cfg.get('consumer_retain_views'))is bool and cfg['consumer_retain_views']==cell['consumer_retain_views'],'actual Consumer S configuration differs')
    need(cfg.get('condition',cell['condition'])==cell['condition'],'config factorial condition differs')
    settings=cfg['settings'];need(settings['source_commit']==base['source_commit']and settings['primary_gpu']==cell['primary_gpu'],'cell source/physical primary differs')
    need(settings['corrector_dtype']=='float32'and settings['max_ahead_frames']==32000,'shared neural precision/ahead contract differs')
    need(cfg['reference_kind']=='strict'and cfg['fault']['kind']=='none'and'cost_observer'not in cfg,'original execution/reference/fault contract differs')
    need(cfg['reference_details']==plan['reference_details']['path']and cfg['reference_details_sha256']==plan['reference_details']['sha256'],'cell strict reference changed')
    actual=settings['sources'];need(len(actual)==1 and actual[0]['source_id']==cell['source_id'],'cell source set differs')
    source=next(s for s in plan['sources']if s['source_id']==cell['source_id'])
    need(actual[0]==source,'cell complete immutable source/provenance differs')
    need(settings['model_sources']==[plan['warmup_source'],source] and settings['warmup']==plan['warmup'],'original warmup/test scope changed')


def run(a):
    plan=read(a.plan);identity=verify_source(pathlib.Path(__file__).parent,a.manifest,plan['driver']['source_commit']);need(identity==plan['driver'],'driver identity changed')
    base=verify_source(plan['actual_NN']['source_root'],plan['actual_NN']['source_manifest'],plan['actual_NN']['source_commit']);need(base==plan['actual_NN'],'actual runtime identity changed')
    support=verify_source(plan['production_support']['source_root'],plan['production_support']['source_manifest'],SUPPORT);need(support==plan['production_support'],'production support changed')
    audit_identity=verify_source(plan['view_audit']['source_root'],plan['view_audit']['source_manifest'],plan['view_audit']['source_commit']);need(audit_identity==plan['view_audit'],'independent view-audit source changed')
    validate_matrix(plan['cells'],plan['sources']);need(plan['expected_trials']==len(plan['cells']),'planned trial count differs')
    sel=plan['selection_receipt'];need(sha(sel['path'])==sel['sha256'],'workload selection receipt changed')
    need(selected_md68_sources(read(sel['path']),len(plan['sources']))==plan['sources'],'strict MD68 receipt/actual assets changed')
    need(plan['original_D2_seconds']==2. and plan['original_C8_seconds']==8.,'deadline changed')
    need(plan['cadence']==dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000),'500ms input contract differs')
    need(plan['runtime_environment']=={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},'allocator contract changed')
    pre=read(a.prelaunch);validate_prelaunch(pre,a.plan,identity,base)
    details=validate_reference(plan,identity,base)
    need(sha(plan['environment_record'])==plan['environment_sha256']and pathlib.Path(sys.executable).resolve()==pathlib.Path(plan['environment_python']).resolve(),'environment/interpreter changed')
    env=read(plan['environment_record'])
    for key,value in env['packages'].items():need(importlib.metadata.version(key)==value,'package changed: '+key)
    asset=pre['asset_byte_gate'];need(sha(asset['path'])==asset['sha256'],'asset gate changed');gate=read(asset['path'])
    need(gate['status'].startswith('PASS')and gate['all_asset_bytes_verified']is True and gate['asset_manifest_sha256']==env['assets_manifest_sha256'],'model-byte gate missing')
    need(sha(env['assets_manifest_path'])==env['assets_manifest_sha256'],'asset manifest changed')
    for s in plan['sources']:need(sha(s['path'])==s['audio_sha256'],'actual immutable audio changed')
    sys.path.insert(0,support['source_root']);import external_power,audit_results,run_paired_campaign
    sys.path.insert(0,base['source_root']);from resilience_storage import scan
    sys.path.insert(0,audit_identity['source_root']);view_module=importlib.import_module('audit_native_cell')
    out=disk(a.out);need(str(out)==plan['raw_result_location'],'unfrozen campaign output');out.mkdir(parents=True,exist_ok=False)
    for name in ('cells','logs','external','records'):(out/name).mkdir()
    put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,driver=identity,actual_NN=base,production_support=support,view_audit=audit_identity,original_environment=env,reference_receipt=plan['reference_receipt']))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],actual_NN_source_commit=base['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results=[];failed=[]
    try:
        for cell in plan['cells']:
            for item in (identity,base,support,audit_identity):need(verify_source(item['source_root'],item['source_manifest'],item['source_commit'])==item,'execution dependency drift before cell')
            need(sha(cell['config'])==cell['config_sha256'],'cell config changed');cfg=read(cell['config']);validate_cell(cell,cfg,plan,base)
            initial_gpu=external_power.nvml_snapshot();need(not initial_gpu['compute_processes'],'GPU already occupied; no launch')
            if 'gpu_uuids'in plan:need({str(k):v['uuid']for k,v in initial_gpu['boards'].items()if str(k)in('0','1')}==plan['gpu_uuids'],'physical allocated board identities changed')
            raw=disk(cell['out']);need(not raw.exists(),'never overwrite a trial')
            for key,folder in(('out','cells'),('log','logs'),('external_power','external')):need(disk(cell[key]).resolve().is_relative_to((out/folder).resolve()),'cell path outside its frozen campaign folder: '+key)
            observer=external_power.ExternalObserver(disk(cell['external_power']));captured={};child=None;ticks=None;done=False
            command=[sys.executable,'-B',str(pathlib.Path(base['source_root'])/'resilience_trial.py'),'--config',cell['config'],'--manifest',base['source_manifest'],'--out',cell['out']]
            put(out/'records'/(cell['cell_id']+'_PRELAUNCH.json'),dict(experiment_id=cell['cell_id'],code_commit=identity['source_commit'],actual_NN=base,view_audit=audit_identity,frozen_config=cell['config'],frozen_config_sha256=cell['config_sha256'],environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=cell['out'],aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),command=command,command_sha256=hashlib.sha256(canonical(command)).hexdigest()))
            put(out/'PROGRESS.json',dict(completed=len(results),planned=plan['expected_trials'],current=cell['cell_id'],condition=cell['condition'],SLO_misses_do_not_stop=True),replace=True)
            try:
                observer.start()
                with disk(cell['log']).open('x',encoding='utf8')as stream:
                    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=child_env(),start_new_session=True)
                    from process_cleanup import process_identity
                    launch=process_identity(child.pid);need(launch is not None,'child ended before identity capture');ticks=launch['start_ticks']
                    put(out/'records'/(cell['cell_id']+'_HANDLE.json'),dict(pid=child.pid,start_ticks=ticks,physical_identity=launch,command_sha256=hashlib.sha256(canonical(command)).hexdigest()))
                    deadline=time.perf_counter()+plan['maximum_process_seconds']
                    while child.poll()is None:
                        observer.check();run_paired_campaign.capture_ready_environment(raw,observer,captured,env);need(time.perf_counter()<deadline,'fresh load/service timeout');time.sleep(.1)
                    need(child.returncode==0,'original actual trial failed; preserve failed attempt')
                run_paired_campaign.capture_ready_environment(raw,observer,captured,env);ready=run_paired_campaign.ready_rows(raw);ready_gate=run_paired_campaign.check_ready(ready,env)
                need(set(captured)=={str(r['pid'])for r in ready},'actual initial allocator observations missing')
                observer.finish(not_before=time.perf_counter());need(not external_power.nvml_snapshot()['compute_processes'],'CUDA physical release incomplete')
                power_rows=[json.loads(line)for line in observer.path.read_text(encoding='utf8').splitlines()if line.strip()]
                ownership=power_ownership(power_rows,ready,initial_gpu['boards'],read(raw/'ORIGIN.json')['origin_perf'],observer.drain['confirmed_perf']);put(raw/'SAMPLED_ENERGY_OWNERSHIP.json',ownership)
                need(read(raw/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK','original task gate failed')
                result=audit_results.audit_cell(dict(cell,version=cell.get('version','final')),cfg,details,observer)
                accounting=audit_trial(raw,scan,closed=True);put(raw/'JOB_ACCOUNTING.json',accounting);need(accounting['status']=='PASS_DISJOINT_JOB_ACCOUNTING','job terminal accounting failed')
                worker=worker_ledger(raw,accounting);put(raw/'WORKER_TIMER_LEDGER.json',worker)
                view_audit=view_module.audit_trial_view(raw,base['source_root']);need(view_audit.get('status','').startswith('PASS'),'independent actual-view audit failed')
                put(raw/'INDEPENDENT_VIEW_AUDIT.json',view_audit)
                result.update(speaker_id=cell['speaker_id'],condition=cell['condition'],consumer_retain_views=cell['consumer_retain_views'],actual_READY_gate=ready_gate,initial_worker_allocator_observations=captured,sampled_energy_ownership=ownership,job_accounting=accounting,worker_ledger={k:v for k,v in worker.items()if k!='per_job'},view_audit=view_audit)
                put(raw/'EXTERNAL_FACTORIAL_AUDIT.json',result);results.append(result);put(out/'PARTIAL_RESULTS.json',results,replace=True);put(out/'SUMMARY.json',aggregate(results,plan),replace=True);done=True
            except BaseException:
                failed.append(dict(cell_id=cell['cell_id'],source_id=cell['source_id'],condition=cell['condition'],repeat=cell['repeat'],raw_result_location=cell['out'],original_offered_audio_s=cfg['settings']['sources'][0]['frames']/16000,failure=traceback.format_exc()));raise
            finally:
                if child is not None and not done:
                    try:put(out/'records'/(cell['cell_id']+'_FAILURE_CLEANUP.json'),run_paired_campaign.stop_owned_processes(child,raw,child_start_ticks=ticks,known_members=list(captured.values())))
                    except BaseException:
                        put(out/'records'/(cell['cell_id']+'_CLEANUP_UNVERIFIED.json'),dict(status='FAIL_OWNED_RELEASE_UNVERIFIED',failure=traceback.format_exc(),unrelated_processes_never_authorized=True));raise
                    finally:observer.close()
                else:observer.close()
        summary=aggregate(results,plan,failed);put(out/'SUMMARY.json',summary,replace=True)
        put(out/'GATE.json',dict(status=summary['status'],completed_trials=len(results),SLO_failures_retained=True,independent_view_audit=audit_identity,zero_opportunity_is_not_gate_failure=True));return summary
    except BaseException:
        put(out/'SUMMARY.json',aggregate(results,plan,failed),replace=True);put(out/'GATE.json',dict(status='FAIL_OR_INCOMPLETE_NATIVE_WORKLOAD_EXTENSION_PRESERVED',completed_trials=len(results),failed_attempts=failed,failure=traceback.format_exc()));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('plan','manifest','prelaunch','out'):parser.add_argument('--'+name,required=True)
    run(parser.parse_args())
