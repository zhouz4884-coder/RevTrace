"""Freeze grouped configs only after actual f367 full4/subset2 reference PASS."""
import argparse,copy,pathlib
from confirmation_common import RUNTIME,SUPPORT,read,sha,put,disk,verify_source,need
from resource_common import REFERENCE_GENERATOR,SEED,ARMS,blocks,validate_matrix,reference_contract,check_task_settings,validate_cell
def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','base-source','base-manifest','support-source','support-manifest','reference-generator-source','reference-generator-manifest','full-selection','subset-selection','full-reference','subset-reference','template','environment','config-dir','raw-root','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();own=verify_source(pathlib.Path(__file__).parent,a.manifest);base=verify_source(a.base_source,a.base_manifest,RUNTIME);support=verify_source(a.support_source,a.support_manifest,SUPPORT)
    generator=verify_source(a.reference_generator_source,a.reference_generator_manifest,REFERENCE_GENERATOR)
    groups,refs,ref_config=reference_contract(a.full_selection,a.subset_selection,a.full_reference,a.subset_reference,generator)
    template=read(a.template);warm=check_task_settings(template,ref_config);settings0=template['settings']
    configs=disk(a.config_dir);configs.mkdir(parents=True,exist_ok=False);raw=disk(a.raw_root);cells=[];ordered,orders=blocks(groups)
    for block in ordered:
        group=block['group'];rep=block['repeat'];reference=refs[group['group_id']]
        for arm in block['strategies']:
            cid=f'SC_V16_RESOURCE_{group["group_id"]}_{arm}_r{rep}';cfg=copy.deepcopy(template);settings=copy.deepcopy(settings0)
            settings.update(source_commit=RUNTIME,sources=copy.deepcopy(group['sources']),model_sources=[copy.deepcopy(warm)]+copy.deepcopy(group['sources']),primary_gpu=rep,record_state_telemetry=True,record_resources=True)
            cfg.pop('cost_observer',None);cfg.update(cell_id=cid,experiment_id=cid,source_commit=RUNTIME,arm=arm,repeat=rep,position=len(cells),stage='synchronous_multisession_resource_control',cohort='existing_four_nested_groups',settings=settings,maximum_service_seconds=240,maximum_owner_restarts=2,fault={'kind':'none'},require_reference=True,reference_kind='strict',reference_details=reference['reference_details']['path'],reference_details_sha256=reference['reference_details']['sha256'],reference_gate=reference['reference_gate']['path'],reference_gate_sha256=reference['reference_gate']['sha256'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
            path=configs/(cid+'.json');put(path,cfg)
            cell=dict(cell_id=cid,group_id=group['group_id'],source_count=group['source_count'],source_ids=group['source_ids'],strategy=arm,repeat=rep,primary_gpu=rep,position=len(cells),config=str(path),config_sha256=sha(path),out=str(raw/'cells'/cid),log=str(raw/'logs'/(cid+'.log')),external_power=str(raw/'external'/(cid+'.jsonl')))
            validate_cell(cfg,cell,group,ref_config);cells.append(cell)
    validate_matrix(cells,groups)
    plan=dict(experiment_id='REVTRACE_V16_SYNCHRONOUS_RESOURCE8_V1',driver=own,actual_NN=base,production_support=support,reference_generator=generator,
        source_selection=dict(full=dict(path=a.full_selection,sha256=sha(a.full_selection)),subset=dict(path=a.subset_selection,sha256=sha(a.subset_selection))),reference_receipts=dict(full=dict(path=a.full_reference,sha256=sha(a.full_reference)),subset=dict(path=a.subset_reference,sha256=sha(a.subset_reference))),references=refs,groups=groups,cells=cells,expected_trials=8,arms=list(ARMS),metadata_seed=SEED,r0_orders=orders,
        template=dict(path=a.template,sha256=sha(a.template)),environment_record=a.environment,environment_sha256=sha(a.environment),environment_python=read(a.environment)['executable'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},maximum_process_seconds=720.,raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),
        cadence=dict(sample_rate_hz=16000,release_seconds=.5,full_step_samples=8000,source_offsets=False,one_original_ingress_origin_for_all_sources=True),resources=dict(physical_GPUs=2,complete_FP32_workers=2,common_dispatcher='shared_canonical_first_round_robin_v1'),
        underlying_existing_speaker_ids=[s['speaker_id'] for s in groups[-1]['sources']],new_independent_speakers=0,waiting_chains_and_EOS_kept=True,zero_speculation_is_valid_boundary=True,resource_drift_above_2percent='diagnose_and_keep_all_outcomes',no_performance_based_retry_or_removal=True,reference_cost='full4 measured f367 reference remains separate paid work; no reference regeneration merely for new controller commit')
    put(a.out,plan)
if __name__=='__main__':main()
