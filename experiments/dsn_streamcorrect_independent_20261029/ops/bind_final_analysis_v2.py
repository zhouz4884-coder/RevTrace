"""Mechanical hashes/paths after complete16; no endpoint choices or recount."""
import argparse,hashlib,json,pathlib,platform,sys
F=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--collection-root',type=pathlib.Path,required=True);a=ap.parse_args();bank=a.collection_root.resolve()
t=read(F/'FINAL_ANALYSIS_TEMPLATE_v2_FROZEN.json');common=t['common']
assert sha(F/'FINAL_ANALYSIS_TEMPLATE_v2_FROZEN.json')=='e417c524f1d9978334ee00a7da5b29f98ffb6519ce0c4ad763b8897c97a03343'
assert sha(F/'packages/ANALYSIS_SOURCE_v2.json')==t['source_manifest_sha256']
manifest=read(bank/'COLLECTION_MANIFEST.json');assert manifest['all_bytes_equal'] and manifest['source_commit']==common['actual_neural_source_commit']
for row in manifest['files']:
 p=bank/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
gate=read(bank/'campaign/GATE.json');assert gate['planned_cells']==gate['completed_cells']==16 and gate['all_full_task_fidelity_pass']
plan_path=F/'FINAL_SERVICE_v2_FROZEN.json';plan=read(plan_path)
assert sha(plan_path)=='cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a'
assert read(bank/'campaign/CONFIG.json')==plan
reference=read(common['reference_gate']);assert reference['reference_details_sha256']==sha(common['reference_details'])==plan['reference_details_sha256']
for key in ('source_receipt','metadata_selection','method_freeze','appraisal','reference_gate'):assert sha(common[key])==common[key+'_sha256']
primary=dict(common,experiment_id='SC_INDEPENDENT_FINAL_PRIMARY_RECOUNT_V2',collection_root=str(bank),collection_manifest_sha256=sha(bank/'COLLECTION_MANIFEST.json'),campaign_plan=str(plan_path.resolve()),campaign_plan_sha256=sha(plan_path),frozen_config_dir=str((F/'service_v1_configs').resolve()))
inputs={};cells=[]
for row in plan['cells']:
 cell_id=row['cell_id'];config=read(bank/cell_id/'CONFIG.json');frozen=F/'service_v1_configs'/pathlib.PurePosixPath(row['config']).name
 assert sha(frozen)==row['config_sha256'] and read(frozen)==config
 cells.append(dict(cell_id=cell_id,source_id=config['settings']['sources'][0]['source_id'],stage=config['stage'],cohort=config['cohort'],repeat=config['repeat'],arm=config['arm']))
 for name in ('CONFIG.json','ORIGIN.json','consumer.jsonl','canonical_wal.jsonl','PRIMARY_METRICS.json','CONTENT.json'):
  p=bank/cell_id/name;inputs[cell_id+'/'+name]=dict(bytes=p.stat().st_size,sha256=sha(p))
content=dict(common,experiment_id='SC_INDEPENDENT_FINAL_ACTUAL_G_CONTENT_RECOUNT_V2',raw_result_location=str(bank),cells=cells,inputs=inputs,
 frozen_environment=dict(python=sys.version,platform=platform.platform(),new_model_calls=0,execution='local offline only'),
 unchanged_endpoint_source_commit='c12803e3ab411ad7898a34a2e257fdee313df81c',max_input_bytes=t['content']['max_input_bytes'],max_output_bytes=t['content']['max_output_bytes'])
for name,value in [('FINAL_PRIMARY_ANALYSIS_v2_FROZEN.json',primary),('FINAL_CONTENT_ANALYSIS_v2_FROZEN.json',content)]:
 p=F/name;assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='MECHANICALLY_BOUND_AFTER_COMPLETE16_NOT_YET_ANALYZED',analysis_source_commit=common['analysis_source_commit'],collection_manifest_sha256=primary['collection_manifest_sha256'],primary_config_sha256=sha(F/'FINAL_PRIMARY_ANALYSIS_v2_FROZEN.json'),content_config_sha256=sha(F/'FINAL_CONTENT_ANALYSIS_v2_FROZEN.json'))))
