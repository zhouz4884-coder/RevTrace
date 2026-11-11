"""Bounded archive inventory only; no experiment or original raw analysis."""
from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parents[1];H=E/'external_rule_ops';P=E/'external_rule_packages_v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
manifest=read(P/'SOURCE.json')
for f in manifest['files']:
 p=P/'plain_source'/f['path']
 if p.stat().st_size!=f['bytes'] or sha(p)!=f['sha256']:raise ValueError('complete plain source snapshot differs')
files=list((H/'RESULTS_V2').glob('*'))+list((P/'plain_source').rglob('*'))
names=['stage_run_v2.py','poll_v2.py','collect_close_v2.py','derive_bounded_tables_v2.py','make_publication_index_v2.py',
 'ROOT_IDLE_V2.json','ROOT_DEFAULT_PREFLIGHT_V2.json','ANALYSIS_EXPLICIT_PREFLIGHT_V2.json','PRELAUNCH_V2.json',
 'CONFIG_V2.json','ENVIRONMENT_V2.json','PREPARATION_RECORD_V2.json','PROCESS_LAUNCH_V2.json','CPU_RESOURCE_CLOSURE_V2.json',
 'FINAL_DEFAULT_SOURCE_GATE_V2.json','FINAL_ANALYSIS_SOURCE_GATE_V2.json','BOUNDED_INTERPRETATION_TABLES_V2.json','EXTERNAL_LA2_RESULTS_V2.zh.md']
files += [H/n for n in names]+[P/n for n in ('SOURCE.json','source.bundle','FREEZE_RECEIPT.json')]
files += [E/'review'/n for n in ('EXTERNAL_DECISION_RULE_FEASIBILITY_v1.zh.md','EXTERNAL_LA2_PRELAUNCH_REVIEW_v1.zh.md')]
# Preserve the first unexecuted freeze transparently; its source history is also
# fully reachable from the complete v2 bundle. No nested .git is published.
files += [E/'external_rule_packages_v1'/n for n in ('SOURCE.json','source.bundle','FREEZE_RECEIPT.json')]
records=[]
for p in sorted(set(files)):
 if p.is_dir():continue
 if not p.is_file():raise ValueError('publication component missing: '+str(p))
 records.append(dict(path=p.relative_to(E).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
summary=read(H/'RESULTS_V2/SUMMARY.json')
index=dict(record_type='BOUNDED_COMPLETE_LA2_OFFLINE_CPU_PUBLICATION_INDEX',experiment_id='REVTRACE-V16-EXTERNAL-LA2-SHADOW-20261111-V2',
 actual_analysis_source=manifest['code_commit'],source_manifest_sha256=sha(P/'SOURCE.json'),complete_plain_source_files=len(manifest['files']),
 complete_plain_source_matches_manifest=True,full_execution_bundle_sha256=sha(P/'source.bundle'),
 root_execution_ref='refs/revtrace/execution/v16-external-la2-shadow-v2',unexecuted_source_v1_preserved=True,
 original_NN='de0936b2e30179d63aeef6e235cd1af685578c58',original_driver='f367c4e1068a9391a0e99d8537c94995a3388e13',
 actual_binding_auditor='0d54630951dff6e1a423a1652704ee39eea0b8ce',published_rule_author='6da90b44b7e50d79695e68166d2a2c7609c75abb',
 fixed_recorded_cells=summary['cells'],cell_rule_rows=summary['cell_rule_rows'],focused_CPU_controls=summary['focused_CPU_controls'],gate=summary['status'],
 frozen_config_sha256=sha(H/'RESULTS_V2/CONFIG.json'),actual_environment_sha256=sha(H/'RESULTS_V2/ENVIRONMENT.json'),
 all_actual_SUP_rows_and_credit_identical=summary['all_actual_SUP_rows_and_credit_identical'],
 selected_original_G_unchanged=summary['selected_original_G_unchanged'],all_final_actual_texts_equal=summary['all_final_actual_texts_equal'],
 new_model_calls=0,new_GPU_serving_trials=0,CPU_active=False,CURRENT_modified=False,
 estimator='Offline observer over fixed actual AlignAtt/C/U candidate schedule; both compute retention and required SUP are common to each within-cell comparison',
 do_not_stage_embedded_git_checkouts=['external_rule_dev_v1','external_rule_source_v1','external_rule_source_v2'],
 raw_original_model_logs_stay_on_8TB=True,files=records,total_files=len(records),total_bytes=sum(r['bytes'] for r in records))
with (P/'PUBLICATION_INDEX.json').open('x',encoding='utf8') as f:json.dump(index,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(index=str(P/'PUBLICATION_INDEX.json'),files=len(records),bytes=index['total_bytes'],sha256=sha(P/'PUBLICATION_INDEX.json'))))
