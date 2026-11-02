"""Freeze4N actual-service cells only after strict selection/reference PASS."""
from __future__ import annotations
import argparse,copy,pathlib
from confirmation_common import NN4F,SUPPORT,SEED,need,read,sha,put,verify_source,selected_sources,abba_blocks,validate_matrix,reference_binding
def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','selection-receipt','reference-receipt','template','environment','base-source','base-manifest','support-source','support-manifest','config-dir','raw-root','out'):p.add_argument('--'+n,required=True)
    p.add_argument('--expected-sources',required=True,type=int);a=p.parse_args()
    driver=verify_source(pathlib.Path(__file__).parent,a.manifest);base=verify_source(a.base_source,a.base_manifest,NN4F);support=verify_source(a.support_source,a.support_manifest,SUPPORT)
    receipt=read(a.selection_receipt);sources=selected_sources(receipt,a.expected_sources);reference=reference_binding(a.reference_receipt,a.selection_receipt,sources)
    template=read(a.template);need(template['settings']['source_commit']==NN4F,'template is not final4f')
    settings0=template['settings'];warmid=settings0['warmup']['source_id'];warms=[s for s in settings0['model_sources'] if s['source_id']==warmid]
    need(len(warms)==1 and warmid not in {s['source_id'] for s in sources},'fixed original neural warmup missing/selected as new test input')
    need(settings0['max_ahead_frames']==32000 and len(settings0['sources'])==1,'template original lookahead/single-chain contract changed')
    configs=pathlib.Path(a.config_dir);configs.mkdir(parents=True,exist_ok=False);raw=pathlib.Path(a.raw_root);blocks,orders=abba_blocks(sources);cells=[]
    for block in blocks:
        source=block['source'];rep=block['repeat']
        for strategy in block['strategies']:
            cid=f'SC_NEWTEST_{source["source_id"]}_{strategy}_r{rep}';cfg=copy.deepcopy(template);settings=copy.deepcopy(settings0)
            settings.update(source_commit=NN4F,sources=[copy.deepcopy(source)],model_sources=[copy.deepcopy(warms[0]),copy.deepcopy(source)],primary_gpu=rep,record_state_telemetry=True)
            cfg.pop('cost_observer',None)
            cfg.update(cell_id=cid,experiment_id=cid,source_commit=NN4F,arm=strategy,repeat=rep,position=len(cells),stage='strict_new_test_speaker_confirmation',cohort='strict_frozen_new_test_speakers',settings=settings,
                maximum_service_seconds=240,maximum_owner_restarts=2,fault={'kind':'none'},require_reference=True,reference_kind='strict',reference_details=reference['reference_details']['path'],reference_details_sha256=reference['reference_details']['sha256'],reference_gate=reference['reference_gate']['path'],reference_gate_sha256=reference['reference_gate']['sha256'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
            path=configs/(cid+'.json');put(path,cfg)
            cells.append(dict(cell_id=cid,source_id=source['source_id'],speaker_id=source['speaker_id'],strategy=strategy,repeat=rep,primary_gpu=rep,position=len(cells),version='final',config=str(path),config_sha256=sha(path),out=str(raw/'cells'/cid),log=str(raw/'logs'/(cid+'.log')),external_power=str(raw/'external'/(cid+'.jsonl'))))
    validate_matrix(cells,sources)
    plan=dict(experiment_id='REVTRACE_STRICT_NEW_TEST_SPEAKER_CONFIRMATION_20261102_V1',driver=driver,actual_NN=base,production_support=support,expected_source_count=len(sources),expected_trials=len(cells),metadata_seed=SEED,
        selection_receipt=dict(path=a.selection_receipt,sha256=sha(a.selection_receipt)),reference_receipt=dict(path=a.reference_receipt,sha256=sha(a.reference_receipt)),reference_binding=reference,
        template=dict(path=a.template,sha256=sha(a.template)),environment_record=a.environment,environment_sha256=sha(a.environment),environment_python=read(a.environment)['executable'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},
        sources=sources,r0_orders_by_speaker=orders,cells=cells,maximum_process_seconds=720.,original_D2_seconds=2.,original_C8_seconds=8.,all_offered_including_partial_EOS=True,
        raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),
        continuation='all4N regardless of performance; only identity/technical/semantic/resource failure stops and preserves remaining cells',
        source_unit='distinct speaker; two timing repeats do not add acoustic units',reference_cost_scope='original/restore reference generation is separate, never counted as serving success',actual_trace_refinement='Root separate frozen c4 audit after complete neural queue')
    put(a.out,plan)
if __name__=='__main__':main()

