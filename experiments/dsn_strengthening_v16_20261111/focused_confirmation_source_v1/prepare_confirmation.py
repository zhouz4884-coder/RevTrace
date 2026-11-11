"""Metadata-fixed Full/Ready confirmation; derive exact measured parent slice."""
import argparse,copy,pathlib
from confirmation_common import (RUNTIME,SUPPORT,MAIN_ARMS,SEED,need,read,sha,put,verify_source,selected_sources,
    abba_blocks,validate_matrix,reference_binding,disk)
from focused_common import REFERENCE_GENERATOR,validate_focus_selection,original_contract
from bind_reference_subset import derive_subset
def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','base-source','base-manifest','support-source','support-manifest','reference-generator-source','reference-generator-manifest','bank-receipt','parent-selection','parent-reference','indices','template','environment','out','raw-root'):p.add_argument('--'+n,required=True)
    a=p.parse_args();own=verify_source(pathlib.Path(__file__).parent,a.manifest);base=verify_source(a.base_source,a.base_manifest,RUNTIME);support=verify_source(a.support_source,a.support_manifest,SUPPORT);gen=verify_source(a.reference_generator_source,a.reference_generator_manifest,REFERENCE_GENERATOR)
    indices=[int(x) for x in a.indices.split(',')];need(indices in ([2,3],[4,5,6,7]),'only next2 or remaining4 declared slices')
    bank=read(a.bank_receipt);ordered=sorted(selected_sources(bank,8),key=lambda s:(s['speaker_id'],s['source_id']));sources=[copy.deepcopy(ordered[i]) for i in indices]
    parent_sources=selected_sources(read(a.parent_selection),4);parent=reference_binding(a.parent_reference,a.parent_selection,parent_sources,REFERENCE_GENERATOR)
    out=disk(a.out);out.mkdir(parents=True,exist_ok=False);raw=disk(a.raw_root)
    selection=dict(status=bank['status'],metadata_first=True,model_calls=0,no_concat=True,no_trim=True,no_resample=True,selection_use='focused_full_ready_confirmation',comparison_bank_indices=indices,parent_bank_receipt=dict(path=a.bank_receipt,sha256=sha(a.bank_receipt)),sources=sources,new_independent_speakers=0,new_comparison_voices=len(sources))
    validate_focus_selection(selection,sources);put(out/'SELECTION_RECEIPT.json',selection)
    reference=derive_subset(a.parent_reference,a.parent_selection,out/'SELECTION_RECEIPT.json',out/'BOUND_REFERENCE',REFERENCE_GENERATOR)
    template=read(a.template);warm=original_contract(parent,template);settings0=template['settings'];configs=out/'configs';configs.mkdir();cells=[];blocks,orders=abba_blocks(sources,False)
    for block in blocks:
        s=block['source'];rep=block['repeat']
        for arm in block['strategies']:
            cid=f'SC_V16_CONFIRM_{s["source_id"]}_{arm}_r{rep}';cfg=copy.deepcopy(template);settings=copy.deepcopy(settings0);settings.update(source_commit=RUNTIME,sources=[copy.deepcopy(s)],model_sources=[copy.deepcopy(warm),copy.deepcopy(s)],primary_gpu=rep,record_state_telemetry=True,record_resources=True)
            cfg.pop('cost_observer',None);cfg.update(cell_id=cid,experiment_id=cid,source_commit=RUNTIME,arm=arm,repeat=rep,position=len(cells),stage='focused_confirmation_'+str(indices[0])+'_'+str(indices[-1]),cohort='existing_bank_new_comparison_voices',settings=settings,maximum_service_seconds=240,maximum_owner_restarts=2,fault={'kind':'none'},require_reference=True,reference_kind='strict',reference_details=reference['reference_details']['path'],reference_details_sha256=reference['reference_details']['sha256'],reference_gate=reference['reference_gate']['path'],reference_gate_sha256=reference['reference_gate']['sha256'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
            path=configs/(cid+'.json');put(path,cfg);cells.append(dict(cell_id=cid,source_id=s['source_id'],speaker_id=s['speaker_id'],strategy=arm,estimand_role='main',repeat=rep,primary_gpu=rep,position=len(cells),version='final',config=str(path),config_sha256=sha(path),out=str(raw/'cells'/cid),log=str(raw/'logs'/(cid+'.log')),external_power=str(raw/'external'/(cid+'.jsonl'))))
    validate_matrix(cells,sources,False)
    plan=dict(experiment_id='REVTRACE_V16_FULL_READY_BANK_'+str(indices[0])+'_'+str(indices[-1])+'_V1',phase='focused_confirmation',driver=own,actual_NN=base,production_support=support,reference_generator=gen,expected_source_count=len(sources),expected_trials=len(cells),expected_main_trials=len(cells),expected_auxiliary_trials=0,main_arms=list(MAIN_ARMS),auxiliary_arms=[],include_auxiliary=False,metadata_seed=SEED,
        comparison_bank_indices=indices,selection_receipt=dict(path=str(out/'SELECTION_RECEIPT.json'),sha256=sha(out/'SELECTION_RECEIPT.json')),reference_receipt=dict(path=str(out/'BOUND_REFERENCE/REFERENCE_RECEIPT.json'),sha256=sha(out/'BOUND_REFERENCE/REFERENCE_RECEIPT.json')),reference_binding=reference,
        template=dict(path=a.template,sha256=sha(a.template)),environment_record=a.environment,environment_sha256=sha(a.environment),environment_python=read(a.environment)['executable'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},sources=sources,r0_orders_by_speaker=orders,cells=cells,maximum_process_seconds=720.,original_D2_seconds=2.,original_C8_seconds=8.,all_offered_including_partial_EOS=True,
        raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),ready_reuse_positive_is_gate=False,zero_ready_reuse_is_equivalence_proof=False,resource_drift_reject_or_retry=False,resource_difference_diagnostic_threshold=.02,cadence=dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000,all_length_strata_identical=True),new_independent_speakers=0,new_comparison_voices=len(sources),
        evidence_phase='new focused confirmation voices; pilot first2 remain a separately labelled development cohort',aggregation_rule='N4/N8 combines speaker paired effects with phase labels, never calls timing repeats independent speakers',reference_cost_scope='measured parent f367 cost linked, derived slice has zero NEW neural calls')
    put(out/'SERVICE_PLAN.json',plan)
if __name__=='__main__':main()
