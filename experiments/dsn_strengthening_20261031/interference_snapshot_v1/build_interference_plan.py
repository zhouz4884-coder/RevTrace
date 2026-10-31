"""Freeze prospective inputs after root source review; never launch NN."""
from __future__ import annotations
import argparse,copy,pathlib
from common import B,FINAL,need,read,put,sha,verify_checkout,disk_path
from interference_contract import CONTRACT,CLIENTS,ORDER,OFFSET,validate_contract

UPSTREAM='a13fa0a335529dc188f7e738877a3acd027ce4a7'
UPSTREAM_MANIFEST='8cadffbfe9ffcc1eb3efdf5e2702e7afbc2ec932158c12dd197d6f0bdc334934'
RULE=dict(require_original_all_semantics_clocks=True,Conservative_all_four_requests_C8_misses=0,require_actual_B_ready_dispatch_inversion=True,B_C99_min_absolute_regression_seconds=1.,B_C99_min_relative_regression=.20,or_B_additional_C8_frontier_misses=4,shared_credit_gain_required=False,maximum_actual_trials=4,first_B_offset_seconds=2.,no_source_phase_threshold_retry=True)

def remote_disk_path(value):
    path=pathlib.PurePosixPath(value);need(path.is_absolute() and '..' not in path.parts and path.is_relative_to(pathlib.PurePosixPath(B)),'remote path outside designated 8TB disk');return value

def build(resident_plan,manifest,out,remote_source,remote_manifest,remote_inputs,raw_root):
    parent=read(resident_plan);identity=verify_checkout(pathlib.Path(__file__).parent,manifest)
    upstream=copy.deepcopy(parent['harness_source']);need(upstream['source_commit']==UPSTREAM and upstream['source_manifest_sha256']==UPSTREAM_MANIFEST,'exact a13 dependency required')
    for path in (remote_source,remote_manifest,remote_inputs,raw_root):remote_disk_path(path)
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);configs=out/'interference_opportunity_v1_configs';configs.mkdir()
    template=read(pathlib.Path(resident_plan).parent/'resident4_v2_configs'/'SC_RESIDENT4_V2_fullcall_r0.json')
    source_by={s['source_id']:s for s in template['settings']['sources']};need(set(source_by)==set(ORDER),'old four immutable sources required')
    harness=dict(source_root=remote_source,source_manifest=remote_manifest,source_manifest_sha256=sha(manifest),source_commit=identity['source_commit'])
    cells=[]
    for arm,rep in [('conservative',0),('fullcall',0),('fullcall',1),('conservative',1)]:
        cfg=copy.deepcopy(template);cid=f'SC_INTERFERENCE_OPPORTUNITY_V1_{arm}_r{rep}'
        cfg.pop('request_order',None);cfg.update(cell_id=cid,experiment_id=cid,repeat=rep,arm=arm,stage='fixed_two_client_interference_opportunity',request_contract=CONTRACT,clients=copy.deepcopy(CLIENTS),client_first_offsets={'A':0.,'B':OFFSET},maximum_owner_restarts=0,maximum_service_seconds=240,fault={'kind':'none'},harness_source=harness,execution_dependencies=[upstream],observation_wrapper_source_commit=identity['source_commit'],opportunity_rule=RULE)
        cfg['settings']['sources']=[copy.deepcopy(source_by[sid]) for sid in ORDER];cfg['settings']['primary_gpu']=rep
        warmid=cfg['settings']['warmup']['source_id'];model_by={s['source_id']:s for s in cfg['settings']['model_sources']};cfg['settings']['model_sources']=[model_by[warmid]]+[copy.deepcopy(source_by[sid]) for sid in ORDER]
        need(cfg['settings']['source_commit']==FINAL,'core NN marker changed');validate_contract(cfg)
        path=configs/(cid+'.json');put(path,cfg)
        cells.append(dict(cell_id=cid,arm=arm,repeat=rep,config=remote_inputs+'/interference_opportunity_v1_configs/'+path.name,config_sha256=sha(path),out=raw_root+'/cells/'+cid,log=raw_root+'/logs/'+cid+'.log'))
    plan={k:copy.deepcopy(parent[k]) for k in ('environment_python','environment_record','environment_sha256','runtime_environment','reference_details','reference_details_sha256','reference_gate','reference_gate_sha256','original_D2_seconds','original_C8_seconds','all_offered_including_EOS')}
    plan.update(controller_source_commit=identity['source_commit'],controller_source_root=remote_source,controller_manifest=remote_manifest,controller_manifest_sha256=sha(manifest),harness_source=harness,dependencies={'final':parent['dependencies']['final'],'upstream_a13':upstream},experiment_id='SC_TWO_CLIENT_ADMISSION_OPPORTUNITY4_V1',expected_cells=4,smoke_cells=2,maximum_process_seconds=720,maximum_failure_cleanup_seconds=40,opportunity_rule=RULE,cells=cells,raw_result_location=raw_root,aggregate_summary_location=raw_root+'/SUMMARY.json',gate_decision_location=raw_root+'/GATE.json',scope='At most four actual unchanged-NN59 trials; fixed 2s new-client interference. First pair hard stop, second pair only on opportunity. No scheduling change, phase sweep or credit-gain requirement.')
    put(out/'INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json',plan);return plan
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--resident-plan',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);p.add_argument('--remote-source',required=True);p.add_argument('--remote-manifest',required=True);p.add_argument('--remote-inputs',required=True);p.add_argument('--raw-root',required=True);a=p.parse_args();build(a.resident_plan,a.manifest,a.out,a.remote_source,a.remote_manifest,a.remote_inputs,a.raw_root)
