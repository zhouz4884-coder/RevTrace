"""Freeze only original MD68 inputs and three policies, after actual reference PASS.

No GPU/model execution occurs here. The original warmup, models, FP32 calls,
500-ms cadence, D2/C8, 2-s ahead bound and strict original reference are shared.
"""
from __future__ import annotations
import argparse, copy, pathlib
from confirmation_common import (NN4F,PARENT_RUNTIME,SUPPORT,need,read,sha,put,
    verify_source,reference_binding,disk)
from corpus_contract import selected_md68_sources,validate_empty_selection,NO_GO
from workload_conditions import CONDITIONS,CONDITION_SETTINGS,WORKLOAD_SEED,workload_blocks,validate_matrix
VIEW_AUDIT='0571d51d85542e1eaf000be8082585a66e5978be'

def freeze_cells(template,sources,reference,configs,raw):
    settings0=template['settings']
    need(settings0['source_commit'] in (PARENT_RUNTIME,NN4F), 'unknown original template source')
    warm=copy.deepcopy(settings0['warmup']); warmid=warm['source_id']
    candidates=[s for s in settings0['model_sources'] if s['source_id']==warmid]
    need(len(candidates)==1 and warm['original_reference_start_state']['frontier']==24000,
         'original fixed neural warmup missing or changed')
    need(warmid not in {s['source_id'] for s in sources}, 'test source used as warmup')
    need(settings0['corrector_dtype']=='float32' and settings0['max_ahead_frames']==32000 and
         len(settings0['sources'])==1, 'template precision/ahead/single-chain differs')
    blocks,orders=workload_blocks(sources); cells=[]
    for block in blocks:
        source=block['source']; rep=block['repeat']
        for condition in block['conditions']:
            strategy,retain=CONDITION_SETTINGS[condition]
            cid=f'MD68_WORKLOAD_V1_{source["source_id"]}_{condition}_r{rep}'
            cfg=copy.deepcopy(template); settings=copy.deepcopy(settings0)
            settings.update(source_commit=NN4F,sources=[copy.deepcopy(source)],
                model_sources=[copy.deepcopy(candidates[0]),copy.deepcopy(source)],primary_gpu=rep,
                record_state_telemetry=True,record_resources=True)
            cfg.pop('cost_observer',None)
            cfg.update(cell_id=cid,experiment_id=cid,source_commit=NN4F,arm=strategy,condition=condition,
                consumer_retain_views=retain,repeat=rep,position=len(cells),stage='md68_original_workload',
                cohort='metadata_first_official_MD68_test',settings=settings,
                maximum_service_seconds=240,maximum_owner_restarts=2,fault={'kind':'none'},
                require_reference=True,reference_kind='strict',
                reference_details=reference['reference_details']['path'],
                reference_details_sha256=reference['reference_details']['sha256'],
                reference_gate=reference['reference_gate']['path'],
                reference_gate_sha256=reference['reference_gate']['sha256'],
                runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
            path=configs/(cid+'.json'); put(path,cfg)
            cells.append(dict(cell_id=cid,source_id=source['source_id'],speaker_id=source['speaker_id'],
                strategy=strategy,condition=condition,consumer_retain_views=retain,repeat=rep,primary_gpu=rep,
                position=len(cells),version='final',config=str(path),config_sha256=sha(path),
                out=str(raw/'cells'/cid),log=str(raw/'logs'/(cid+'.log')),
                external_power=str(raw/'external'/(cid+'.jsonl'))))
    validate_matrix(cells,sources)
    return cells,orders,warm,copy.deepcopy(candidates[0])

def main():
    p=argparse.ArgumentParser()
    for name in ('manifest','selection-receipt','reference-receipt','template','environment',
                 'base-source','base-manifest','support-source','support-manifest',
                 'view-audit-source','view-audit-manifest','config-dir','raw-root','out'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    driver=verify_source(pathlib.Path(__file__).parent,a.manifest)
    base=verify_source(a.base_source,a.base_manifest,NN4F)
    support=verify_source(a.support_source,a.support_manifest,SUPPORT)
    audit=verify_source(a.view_audit_source,a.view_audit_manifest,VIEW_AUDIT)
    receipt=read(a.selection_receipt)
    if receipt.get('status')==NO_GO:
        validate_empty_selection(receipt)
        put(a.out,dict(status=NO_GO,experiment_id='REVTRACE_MD68_WORKLOAD_EXTENSION_V1',driver=driver,
            selection_receipt=dict(path=a.selection_receipt,sha256=sha(a.selection_receipt)),
            expected_source_count=0,expected_trials=0,GPU_launch_ready=False,model_calls=0,
            no_source_relaxation_or_replacement=True))
        return
    sources=selected_md68_sources(receipt)
    ref=reference_binding(a.reference_receipt,a.selection_receipt,sources,driver['source_commit'])
    env=read(a.environment)
    need('packages' in env and 'executable' in env, 'complete environment/interpreter required')
    configs=disk(a.config_dir); configs.mkdir(parents=True,exist_ok=False); raw=disk(a.raw_root)
    cells,orders,warm,warm_source=freeze_cells(read(a.template),sources,ref,configs,raw)
    plan=dict(experiment_id='REVTRACE_MD68_WORKLOAD_EXTENSION_V1',
        phase='independent_original_MD68_test',conditions=list(CONDITIONS),driver=driver,actual_NN=base,
        production_support=support,view_audit=audit,expected_source_count=len(sources),
        expected_trials=len(cells),requested_source_count=4,actual_eligible_sources=len(sources),
        metadata_seed=WORKLOAD_SEED,sources=sources,cells=cells,r0_orders_by_speaker=orders,
        warmup=warm,warmup_source=warm_source,
        selection_receipt=dict(path=a.selection_receipt,sha256=sha(a.selection_receipt)),
        reference_receipt=dict(path=a.reference_receipt,sha256=sha(a.reference_receipt)),
        reference_details=ref['reference_details'],reference_binding=ref,
        template=dict(path=a.template,sha256=sha(a.template)),
        environment_record=a.environment,environment_sha256=sha(a.environment),environment_python=env['executable'],
        runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},
        maximum_process_seconds=720.,original_D2_seconds=2.,original_C8_seconds=8.,
        all_offered_including_partial_EOS=True,
        cadence=dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000),
        raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),
        gate_decision_location=str(raw/'GATE.json'),
        continuation='All prespecified cells, including misses, ties, zero opportunity and negative effects; technical failures preserve attempted prefix and all planned denominators, no favorable retry',
        primary_comparison='Actual same-runtime compatible-view loss at R1S0 versus R1S1; serial baseline anchors work, energy and deadlines',
        factorial_interaction_not_estimated=True,
        resource_drift_reject_or_retry=False,opportunity_nonzero_required=False,
        source_unit='One untouched official test utterance per new MD68 speaker; timing repeats add no acoustic units',
        reference_cost_scope='Fresh original continuous/restored reference generation is separate paid work, not service credit')
    put(a.out,plan)

if __name__=='__main__':main()
