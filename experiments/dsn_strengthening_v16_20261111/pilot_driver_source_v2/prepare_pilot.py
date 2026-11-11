"""CPU metadata-only preparation; never generates neural references or service."""
from __future__ import annotations
import argparse,copy,datetime,importlib.metadata,pathlib,subprocess,sys,wave,hashlib
from confirmation_common import (RUNTIME,SUPPORT,MAIN_ARMS,AUXILIARY_ARMS,SEED,need,read,sha,put,disk,
    verify_source,selected_sources,abba_blocks,validate_matrix)

def choose_existing_sources(bank,count=2):
    sources=selected_sources(bank,len(bank['sources']))
    need(len(sources)==8 and count in (2,4),'pilot/reference reuse metadata-first two/four of existing eight')
    return copy.deepcopy(sorted(sources,key=lambda s:(s['speaker_id'],s['source_id']))[:count])

def new_environment(old,old_path,readiness,readiness_path,driver,base):
    need(readiness['status']=='PASS_FROZEN_CPU_BYTE_AND_ENVIRONMENT_READINESS' and readiness['new_model_calls']==0,'current CPU byte/environment gate missing')
    packages={k:importlib.metadata.version(k) for k in old['packages']}
    workers={k:importlib.metadata.version(k) for k in old['worker_packages']}
    for k,v in readiness['environment']['packages'].items():need(importlib.metadata.version(k)==v,'readiness package drift')
    need(readiness['asset_manifest_sha256']==old['assets_manifest_sha256'],'asset set changed')
    return dict(record_type='NEW_V16_EXECUTION_METADATA_NOT_NEURAL_READY',actual_NN_source_commit=RUNTIME,
        metadata_preparer_commit=driver['source_commit'],runtime=base,executable=sys.executable,packages=packages,
        worker_packages=workers,runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},
        assets_manifest_path=old['assets_manifest_path'],assets_manifest_sha256=old['assets_manifest_sha256'],
        asr_parameter_dtypes=copy.deepcopy(old['asr_parameter_dtypes']),corrector_parameter_dtypes=copy.deepcopy(old['corrector_parameter_dtypes']),
        expected_parameter_layout_provenance=dict(path=old_path,sha256=sha(old_path),role='inherited expected layout only; actualv3 READY must be measured and compared'),
        current_readiness=dict(path=readiness_path,sha256=sha(readiness_path),source_commit=readiness['source_commit']),
        new_runtime_model_READY_observed=False,new_model_calls=0,cache_temperature='full SHA verification has warmed weight pages; no cold-cache claim')

def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','base-source','base-manifest','support-source','support-manifest','bank-receipt','template','old-environment','readiness-summary','readiness-gate','out','reference-raw','service-raw'):p.add_argument('--'+n,required=True)
    a=p.parse_args();driver=verify_source(pathlib.Path(__file__).parent,a.manifest);base=verify_source(a.base_source,a.base_manifest,RUNTIME);support=verify_source(a.support_source,a.support_manifest,SUPPORT)
    ready=read(a.readiness_summary);gate=read(a.readiness_gate)
    need(gate['status']==ready['status'] and gate['summary_sha256']==sha(a.readiness_summary) and gate['new_model_calls']==0,'current readiness gate/summary mismatch')
    bank=read(a.bank_receipt);reference_sources=choose_existing_sources(bank,4);sources=reference_sources[:2]
    for s in reference_sources:
        need(sha(s['path'])==s['audio_sha256'],'pilot full WAV changed')
        with wave.open(s['path'],'rb') as f:
            need(f.getframerate()==16000 and f.getnchannels()==1 and f.getsampwidth()==2 and f.getnframes()==s['frames'],'pilot original WAV header changed')
            need(hashlib.sha256(f.readframes(f.getnframes())).hexdigest()==s['header']['PCM_sha256'],'pilot PCM changed')
    out=disk(a.out);out.mkdir(parents=True,exist_ok=False);reference_raw=disk(a.reference_raw);service_raw=disk(a.service_raw)
    selection=dict(status=bank['status'],metadata_first=True,model_calls=0,no_concat=True,no_trim=True,no_resample=True,
        selection_use='existing_bank_pilot_reuse',new_independent_speakers=0,
        parent_bank_receipt=dict(path=a.bank_receipt,sha256=sha(a.bank_receipt),existing_speakers=8),
        selection_rule='lexicographically first two by speaker_id/source_id; no model outcomes read',sources=sources)
    put(out/'PILOT_SELECTION_RECEIPT.json',selection)
    reference_selection=copy.deepcopy(selection);reference_selection.update(selection_use='existing_bank_reference_first_four',selection_rule='lexicographically first four by speaker_id/source_id; no model outcomes read',sources=reference_sources)
    put(out/'REFERENCE_SELECTION_RECEIPT.json',reference_selection)
    env=new_environment(read(a.old_environment),a.old_environment,ready,a.readiness_summary,driver,base);put(out/'ENVIRONMENT.json',env)
    binding=dict(status='PASS_CURRENT_CPU_MODEL_BYTES_BOUND_NOT_MODEL_READY',all_asset_bytes_verified=True,
        asset_manifest_sha256=ready['asset_manifest_sha256'],current_readiness_summary=dict(path=a.readiness_summary,sha256=sha(a.readiness_summary)),current_readiness_gate=dict(path=a.readiness_gate,sha256=sha(a.readiness_gate)),actual_NN_source_commit=RUNTIME,new_model_calls=0)
    put(out/'ASSET_BYTE_BINDING.json',binding)
    config=dict(experiment_id='DSN_V16_PILOT_METADATA_PREPARATION_V1',driver=driver,actual_NN=base,support=support,
        bank_receipt=dict(path=a.bank_receipt,sha256=sha(a.bank_receipt)),readiness_summary=dict(path=a.readiness_summary,sha256=sha(a.readiness_summary)),reference_raw=str(reference_raw),service_raw=str(service_raw),metadata_only=True,new_model_calls=0)
    put(out/'CONFIG.json',config);put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=driver['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    gpu_rows={int(row.split(',')[0]):row.split(',')[1].strip() for row in ready['after']['gpus'].splitlines()}
    reference_plan=out/'REFERENCE_PLAN.json'
    cmd=[sys.executable,'-B',str(pathlib.Path(__file__).parent/'make_reference_plan.py'),'--manifest',a.manifest,'--template',a.template,
        '--selection-receipt',str(out/'REFERENCE_SELECTION_RECEIPT.json'),'--environment',str(out/'ENVIRONMENT.json'),
        '--base-source',a.base_source,'--base-manifest',a.base_manifest,'--asset-byte-gate',str(out/'ASSET_BYTE_BINDING.json'),
        '--gpu','0','--gpu-uuid',gpu_rows[0],'--cache-root',str(pathlib.Path(read(a.template)['settings']['cache_root'])),'--raw-out',str(reference_raw),'--out',str(reference_plan)]
    subprocess.run(cmd,check=True)
    blocks,orders=abba_blocks(sources,True);cells=[]
    for block in blocks:
        s=block['source'];rep=block['repeat']
        for strategy in block['strategies']:
            cid=f'SC_V16_pilot_existing_{s["source_id"]}_{strategy}_r{rep}'
            cells.append(dict(cell_id=cid,source_id=s['source_id'],speaker_id=s['speaker_id'],strategy=strategy,repeat=rep,primary_gpu=rep,position=len(cells),estimand_role='main' if strategy in MAIN_ARMS else 'auxiliary',config=str(out/'service_configs'/(cid+'.json')),config_status='PENDING_ACTUAL_NEW_REFERENCE_PASS',out=str(service_raw/'cells'/cid),log=str(service_raw/'logs'/(cid+'.log'))))
    validate_matrix(cells,sources,True)
    summary=dict(status='PASS_METADATA_PILOT_PREPARATION_REFERENCE_AND_SERVICE_NOT_RUN',driver=driver,actual_NN=base,production_support=support,
        expected_sources=2,reference_expected_sources=4,reference_source_ids=[s['source_id'] for s in reference_sources],expected_main_trials=20,expected_auxiliary_trials=4,expected_total_trials=24,main_arms=list(MAIN_ARMS),auxiliary_arms=list(AUXILIARY_ARMS),metadata_seed=SEED,r0_orders_by_speaker=orders,
        selection_receipt=dict(path=str(out/'PILOT_SELECTION_RECEIPT.json'),sha256=sha(out/'PILOT_SELECTION_RECEIPT.json')),environment_record=dict(path=str(out/'ENVIRONMENT.json'),sha256=sha(out/'ENVIRONMENT.json')),
        reference_selection_receipt=dict(path=str(out/'REFERENCE_SELECTION_RECEIPT.json'),sha256=sha(out/'REFERENCE_SELECTION_RECEIPT.json')),reference_plan=dict(path=str(reference_plan),sha256=sha(reference_plan)),planned_service_plan=str(out/'SERVICE_PLAN.json'),cells=cells,
        service_raw=str(service_raw),reference_raw=str(reference_raw),new_independent_speakers=0,new_model_calls=0,new_GPU_trials=0,
        neural_reference_pending=True,service_plan_not_yet_freezable=True,CURRENT_not_modified=True,
        remaining=[f'Root activate/recheck actual runtime{RUNTIME} plus explicit driver identity','Root exclusive GPU ownership and fresh asset/source recheck','execute new actualv3 continuous/restored full4 reference and obtain PASS receipt','derive the prespecified exact first2 reference subset','then freeze24 actual service configs/plan with new reference hashes','Root prelaunch/PID capture and service queue'],
        source_choice_uses_only_frozen_metadata=True,performance_outcomes_not_read=True)
    put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json'),GPU_launch_ready=False,new_model_calls=0));print(str(out/'SUMMARY.json'))
    src=pathlib.Path(__file__).resolve().parent;project=src.parent;root_gate=project/'root_gates/ROOT_NOARG_RUNTIME.json';driver_gate=project/'root_gates/DRIVER_EXPLICIT.json'
    def prelaunch_cmd(plan,target):
        return [sys.executable,'-B',str(src/'make_prelaunch.py'),'--manifest',a.manifest,'--plan',str(plan),'--root-noarg-preflight',str(root_gate),'--driver-explicit-preflight',str(driver_gate),'--asset-byte-gate',str(out/'ASSET_BYTE_BINDING.json'),'--exclusive-window-id','V16_ROOT_OWNED_REFERENCE_AND_PILOT','--out',str(target)]
    service_plan=out/'SERVICE_PLAN.json';ref_pre=out/'REFERENCE_PRELAUNCH.json';service_pre=out/'SERVICE_PRELAUNCH.json'
    subset_out=out/'PILOT_BOUND_REFERENCE'
    service_make=[sys.executable,'-B',str(src/'make_service_plan.py'),'--manifest',a.manifest,'--selection-receipt',str(out/'PILOT_SELECTION_RECEIPT.json'),'--reference-receipt',str(subset_out/'REFERENCE_RECEIPT.json'),'--template',a.template,'--environment',str(out/'ENVIRONMENT.json'),'--base-source',a.base_source,'--base-manifest',a.base_manifest,'--support-source',a.support_source,'--support-manifest',a.support_manifest,'--expected-sources','2','--phase','pilot_existing','--config-dir',str(out/'service_configs'),'--raw-root',str(service_raw),'--out',str(service_plan)]
    handoff=dict(status='CPU_PREPARED_ROOT_ACTIVATION_AND_NEW_REFERENCE_PENDING',driver=driver,runtime=base,support=support,metadata_preparation=str(out/'SUMMARY.json'),
        Root_gates_to_upload=dict(root_noarg_runtime=dict(path=str(root_gate),required_commit=RUNTIME,required_manifest_sha256=base['source_manifest_sha256']),driver_explicit=dict(path=str(driver_gate),required_commit=driver['source_commit'],required_manifest_sha256=driver['source_manifest_sha256'])),
        ordered_commands=[dict(step=1,role='CPU bind Root current/explicit gates to reference plan',command=prelaunch_cmd(reference_plan,ref_pre)),
            dict(step=2,role='ROOT_ONLY paid neural reference; not serving',command=[sys.executable,'-B',str(src/'run_reference.py'),'--plan',str(reference_plan),'--manifest',a.manifest,'--prelaunch',str(ref_pre)],expected_receipt=str(reference_raw/'REFERENCE_RECEIPT.json'),must_verify_owned_process_exit_and_CUDA_empty=True),
            dict(step=3,role='CPU bind prespecified exact pilot2 subset from measured full4 reference',command=[sys.executable,'-B',str(src/'bind_reference_subset.py'),'--manifest',a.manifest,'--parent-receipt',str(reference_raw/'REFERENCE_RECEIPT.json'),'--parent-selection',str(out/'REFERENCE_SELECTION_RECEIPT.json'),'--subset-selection',str(out/'PILOT_SELECTION_RECEIPT.json'),'--out',str(subset_out)]),
            dict(step=4,role='CPU freeze24 service configs only after new reference PASS',command=service_make),
            dict(step=5,role='CPU bind Root current/explicit gates to service plan',command=prelaunch_cmd(service_plan,service_pre)),
            dict(step=6,role='ROOT_ONLY actual24 service trials',command=[sys.executable,'-B',str(src/'run_confirmation.py'),'--plan',str(service_plan),'--manifest',a.manifest,'--prelaunch',str(service_pre),'--out',str(service_raw)])],
        reference_plan_sha256=sha(reference_plan),expected_main_trials=20,expected_auxiliary_trials=4,new_model_calls_so_far=0,new_GPU_trials_so_far=0,
        launcher_handle_requirement='Root records PID/start_ticks/full command SHA for paid reference; service driver records each actual trial handle and owns bounded cleanup',
        no_automatic_source_replacement=True,no_reference_PASS_manufactured=True,CURRENT_not_modified_by_this_preparation=True)
    put(out/'LAUNCH_HANDOFF.json',handoff)
if __name__=='__main__':main()
