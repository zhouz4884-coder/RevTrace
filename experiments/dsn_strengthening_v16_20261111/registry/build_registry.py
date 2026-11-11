"""Bounded artifact registry, not a scientific experiment or raw-log analysis."""
from pathlib import Path
import csv,datetime,hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(E).as_posix()
def digest(p):return dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p)) if p.exists() else 'MISSING'
files=[Path(p) for p in subprocess.check_output(['rg','--files',str(E),'-g','!**/.git/**','-g','!**/__pycache__/**'],text=True).splitlines()]
records=[]
for p in sorted(x for x in files if x.name=='RUN_RECORD.json'):
 d=read(p);g=p.parent/'GATE.json';s=p.parent/'SUMMARY.json'
 records.append(dict(path=rel(p),record=d,gate=read(g) if g.exists() else 'MISSING',summary_keys=list(read(s)) if s.exists() else 'MISSING'))
with (O/'RECORD_INVENTORY.json').open('w',encoding='utf8') as f:json.dump(records,f,ensure_ascii=False,indent=2)
manifests=[]
for p in sorted(files):
 if p.suffix.lower()!='.json' or 'source' not in p.name.lower() or p.stat().st_size>200000:continue
 try:m=read(p)
 except (ValueError,OSError):continue
 if not isinstance(m,dict):continue
 commit=m.get('code_commit',m.get('source_commit'))
 if not isinstance(commit,str) or not re.fullmatch('[a-f0-9]{40}',commit):continue
 if not isinstance(m.get('files'),list) or not m['files'] or not all(isinstance(f,dict) and 'path' in f and 'sha256' in f for f in m['files']):continue
 bundles=[p.with_suffix('.bundle'),p.parent/'SOURCE.bundle',p.parent/'source.bundle']
 bundles=[b for b in bundles if b.exists()]
 manifests.append(dict(commit=commit,manifest=digest(p),complete_source_files=len(m['files']),bundles=[digest(b) for b in sorted(set(bundles))]))

def tier(path):
 if path.startswith('gpu_results/'):
  if '/cells/' in path:return 'REAL_GPU_SERVING_CHILD'
  if '/REFERENCE_' in path:return 'REAL_GPU_REFERENCE_NOT_SERVING'
  return 'LOGICAL_GPU_CAMPAIGN_CONTROLLER'
 if path.startswith('history_ops/'):return 'CPU_REANALYSIS_OF_HISTORICAL_RUNS'
 if path.startswith('final_n8_worker_ops/'):return 'CPU_FINISHING_EXISTING_LOG_ARITHMETIC_NO_NEW_SCENARIO'
 if path.startswith('external_rule_ops/'):return 'CPU_OFFLINE_FIXED_SCHEDULE_RULE_ADAPTER'
 if path.startswith('FORMAL_ACTION_'):return 'CPU_BOUNDED_HANDWRITTEN_FORMAL_MODEL'
 if path.startswith('EOS_'):return 'CPU_OFFLINE_ENDPOINT_DIAGNOSTIC'
 if path.startswith('readiness_'):return 'CPU_ASSET_AND_ENVIRONMENT_READINESS'
 if path.startswith('MAGICDATA_'):return 'CPU_HEADER_METADATA_CONTROLS_NO_AUDIO_ACQUISITION'
 if 'PILOT_PREPARATION' in path:return 'METADATA_PREPARATION_NOT_REFERENCE_OR_SERVICE'
 return 'CPU_CONTROLS_NO_MODEL'

def field(d,*keys):
 return next((d[k] for k in keys if d.get(k) is not None),'MISSING')
def meta(d,folder,filename,pathkeys,hashkeys):
 p=folder/filename;expected=field(d,*hashkeys)
 return dict(recorded_path=field(d,*pathkeys),recorded_sha256=expected,local_mirror=digest(p),
  local_matches_recorded_sha256=(sha(p)==expected) if p.exists() and expected!='MISSING' else 'MISSING')

dedup={}
for x in records:
 d=x['record'];key=(field(d,'experiment_id'),field(d,'raw_result_location'),field(d,'code_commit','source_commit'))
 folder=(E/x['path']).parent;summary=read(folder/'SUMMARY.json') if (folder/'SUMMARY.json').exists() else {}
 g=x['gate'];status=g.get('status',g.get('gate','MISSING')) if isinstance(g,dict) else 'MISSING'
 if key in dedup:
  dedup[key]['run_record_aliases'].append(digest(E/x['path']));continue
 inferred=tier(x['path']);completed=not status.startswith(('FAIL','NO_GO')) and status!='MISSING'
 row=dict(experiment_id=key[0],execution_commit=key[2],raw_result_location=key[1],tier=inferred,
  state='FAILED_PRESERVED' if status.startswith(('FAIL','NO_GO')) else 'COMPLETED_METADATA_ONLY' if inferred.startswith('METADATA_') else 'COMPLETED' if completed else 'MISSING_GATE',
  gate_status=status,run_record=digest(E/x['path']),run_record_aliases=[],
  frozen_config=meta(d,folder,'CONFIG.json',('frozen_config',),('frozen_config_sha256','config_sha256')),
  environment=meta(d,folder,'ENVIRONMENT.json',('environment_record',),('environment_record_sha256','environment_sha256')),
  aggregate_summary=dict(recorded_path=field(d,'aggregate_summary_location'),local_mirror=digest(folder/'SUMMARY.json')),
  gate=dict(recorded_path=field(d,'gate_decision_location'),local_mirror=digest(folder/'GATE.json')),
  source_manifest_recorded=field(d,'source_manifest'),source_manifest_sha256_recorded=field(d,'source_manifest_sha256'),
  complete_source_manifest_candidates=[m for m in manifests if m['commit']==key[2]],
  execution_roles=field(d,'execution_roles','actual_execution_roles','actual_NN_source_commit'),
  tests_or_controls=field(summary,'tests','CPU_controls','controls','focused_CPU_controls','independent_controls','controls_passed'),
  errors=field(summary,'errors'),failures=field(summary,'failures'),skipped=field(summary,'skipped'),
  new_model_calls=field(summary,'new_model_calls','model_calls'),GPU_calls=field(summary,'GPU_calls'),
  actual_new_serving_trial_count=1 if inferred=='REAL_GPU_SERVING_CHILD' else 0,
  actual_new_reference_campaign_count=1 if inferred=='REAL_GPU_REFERENCE_NOT_SERVING' else 0,
  logical_child_count=summary.get('completed_trials',0) if inferred=='LOGICAL_GPU_CAMPAIGN_CONTROLLER' else 0,
  count_rule='Controller/summary is a container; only child GPU cell counts toward new serving trial total',
  evidence_scope=field(summary,'scope','evidence_tier','interpretation','roles'),
  summary_selected_counts={k:(dict(count=len(summary[k]),full_data_in_hashed_summary=True) if isinstance(summary[k],list) else summary[k]) for k in ('cells','expected_cells','audited_complete_cells','cell_rule_rows','checked_events','checked_edit_operations','H3_contrasts_checked','H3_factorials_checked','new8_exact_assignments_checked','expected_sources','completed_sources','original_continuous_steps','ledger','actual_serving_runs','reference_only','speaker_clusters','new_independent_speakers','controls','CPU_controls','test_modules','ast_parsed','AST_parsed') if k in summary},
  failure_record=g.get('failure','MISSING') if isinstance(g,dict) and not completed else 'NONE_RECORDED',
  exact_run_record=d)
 if '/cells/' in x['path']:
  row['parent_campaign_folder']=x['path'].split('/cells/')[0]
  cfg=read(folder/'CONFIG.json') if (folder/'CONFIG.json').exists() else {}
  row['cell_metadata']={k:cfg[k] for k in ('cell_id','stage','cohort','arm','repeat','source_commit') if k in cfg}
  row['cell_metadata']['source_ids']=[s.get('source_id') for s in cfg.get('settings',{}).get('sources',[])]
  row['parent_controller_commit']=field(read(E/row['parent_campaign_folder']/'RUN_RECORD.json'),'code_commit') if (E/row['parent_campaign_folder']/'RUN_RECORD.json').exists() else 'MISSING'
  row['performance_primary']=summary.get('primary','MISSING')
  row['technical_task_PASS_is_not_performance_PASS']=True
 dedup[key]=row
rows=list(dedup.values())
for m in manifests:
 used_rows=[r for r in rows if r['execution_commit']==m['commit']]
 m['used_by_experiment_ids']=[r['experiment_id'] for r in used_rows]
 m['executed_tiers']=sorted({r['tier'] for r in used_rows})
 m['new_GPU_campaign_or_reference_role_observed']=any('GPU' in r['tier'] for r in used_rows)
 m['scope_note']='CPU-only historical runtime/driver versions are not relabeled as later NNde09 GPU sources'

# Reference-subset derivations do not regenerate paid references.
binding_artifacts=[]
for p in files:
 if p.name=='GATE.json' and ('BOUND_REFERENCE' in str(p) or 'PILOT_BOUND_REFERENCE' in str(p)):
  binding_artifacts.append(dict(artifact=digest(p),gate=read(p),tier='METADATA_REFERENCE_SUBSET_DERIVATION_NOT_NEW_GPU',RUN_RECORD='MISSING_NOT_A_NEW_REFERENCE_RUN'))

planned=[]
active_campaigns=[]
lastplan=E/'baseline_ops/FOCUSED_LAST4_PREPARATION_V1/SERVICE_PLAN.json'
if lastplan.exists():
 plan=read(lastplan)
 active_handle=E/'launch_ops/CONFIRM_LAST4_FULL_READY_V1/HANDLE.json'
 active_pre=E/'launch_ops/CONFIRM_LAST4_FULL_READY_V1/RUN_RECORD_PRELAUNCH.json'
 running=active_handle.exists() and not any(r['experiment_id']==plan['experiment_id'] for r in rows)
 if running:
  h=read(active_handle);pre=read(active_pre)
  active_campaigns.append(dict(experiment_id=plan['experiment_id'],tier='ACTUAL_GPU_CAMPAIGN_RUNNING_ROOT_LAUNCH_HANDLE',state='RUNNING_NOT_COMPLETE',
   execution_commit=pre['code_commit'],actual_NN_source_commit=pre['actual_NN_source_commit'],raw_result_location=pre['raw_result_location'],
   prelaunch_record=digest(active_pre),exact_prelaunch_record=pre,actual_RUN_RECORD_local='MISSING_NOT_COLLECTED',SUMMARY='MISSING_RUNNING',GATE='MISSING_RUNNING',
   launch_handle=digest(active_handle),exact_launch_handle=h,planned_trials=16,completed_child_count='UNKNOWN_NO_LOCAL_CLOSED_CHILD_RECORDS',
   authority='Root launch update13:54:15UTC + local HANDLE; no remote liveness or raw analysis performed'))
 planned.append(dict(experiment_id=plan['experiment_id'],tier='RUNNING_CAMPAIGN_FROZEN_PLAN' if running else 'PLANNED_GPU_CAMPAIGN_NOT_STARTED_AT_ROOT_REQUEST',state='RUNNING_BY_ROOT_NOT_COMPLETE' if running else 'FROZEN_PLAN_NOT_RUN',
  plan=digest(lastplan),planned_controller=plan['driver'],planned_NN=plan['actual_NN'],expected_trials=plan['expected_trials'],
  RUN_RECORD='MISSING',execution_commit='MISSING',ENVIRONMENT='MISSING',SUMMARY='MISSING',GATE='MISSING',
  raw_result_location=plan['raw_result_location'],source_of_status='Root later update: campaign launched13:54:15UTC; child status unknown absent local records' if running else 'Root registry request: last16 not yet started; older WORKING_STATE is not authoritative over completed gates'))
 for cell in plan['cells']:
  cp=E/'baseline_ops/FOCUSED_LAST4_PREPARATION_V1/configs'/(cell['cell_id']+'.json')
  planned.append(dict(experiment_id=cell['cell_id'],tier='PLANNED_GPU_CHILD_NO_LOCAL_RUN_RECORD' if running else 'PLANNED_GPU_CHILD_NOT_RUN',state='PENDING_OR_STARTED_NOT_LOCALLY_MIRRORED' if running else 'FROZEN_CONFIG_NOT_RUN',
   parent_experiment_id=plan['experiment_id'],planned_controller_commit=plan['driver']['source_commit'],planned_NN_commit=plan['actual_NN']['source_commit'],
   source_id=cell.get('source_id'),speaker_id=cell.get('speaker_id'),strategy=cell.get('strategy'),repeat=cell.get('repeat'),
   config=digest(cp),raw_result_location=cell['out'],RUN_RECORD='MISSING',execution_commit='MISSING',environment='MISSING',SUMMARY='MISSING',GATE='MISSING'))
completed_ids={r['experiment_id'] for r in rows if r['state']=='COMPLETED'}
planned=[p for p in planned if p['experiment_id'] not in completed_ids]
last16_complete='REVTRACE_V16_FULL_READY_BANK_4_7_V1' in completed_ids

used={r['execution_commit'] for r in rows}
unrun=[dict(commit=m['commit'],source_manifest=m['manifest'],bundles=m['bundles'],state='FROZEN_SOURCE_NO_RUN_RECORD_FOUND',RUN_RECORD='MISSING',SUMMARY='MISSING',GATE='MISSING') for m in manifests if m['commit'] not in used]
proposals=[
 ('MAGICDATA test audio/header acquisition','header_ops/remote_header_v1.py','FROZEN_SOURCE_MODE_UNRUN','3e5bedcc08ea1872707a7d01c965252e639abde4','Header12 controls completed; official audio archive/acquisition mode not run'),
 ('loader constructor/subphase observer','loader_profiler_dev','UNFROZEN_UNINTEGRATED_NOT_RUN','MISSING','AST/source proposal only; no new NNde Ctor_nofault measurement'),
 ('EOS stage profiler','review/EOS_STAGE_PROBE_PREDECLARED_v1.json','PREDECLARED_NOT_IMPLEMENTED_OR_RUN','MISSING','Prospective probe; EOS endpoint diagnostic is separately completed'),
 ('warm-worker/adoption','review/WARM_WORKER_ADOPTION_OPPORTUNITY_v1.zh.md','MEMO_ONLY_NOT_IMPLEMENTED','MISSING','No warm-worker NN4 or recovery run'),
 ('continuous-original fastpath','review/ORIGINAL_CONTINUOUS_BASELINE_OPPORTUNITY_v1.zh.md','MEMO_ONLY_NOT_IMPLEMENTED','MISSING','No replacement continuous-native baseline measurement'),
 ('resource conditional dispatch branch','review/RESOURCE_ALLOCATION_OPPORTUNITY_DECISION_v1.zh.md','DEFERRED_NOT_IMPLEMENTED','MISSING','Resource8 measurements complete; new scheduling branch not measured'),
 ('61 early development checks','review/BASELINE_DESIGN.zh.md','UNFROZEN_DEVELOPMENT_REPORTED_NOT_FORMAL','MISSING','No formal ID/config/env/result gate; not merged into baseline203/214/225 formal counts')]
for name,path,state,commit,note in proposals:
 p=E/path;unrun.append(dict(name=name,evidence=digest(p) if p.is_file() else dict(path=path,exists=p.exists()),state=state,commit=commit,note=note,RUN_RECORD='MISSING',config='MISSING',environment='MISSING',SUMMARY='MISSING',GATE='MISSING'))

historical_paths=[
 'experiments/dsn_strengthening_v16_20261111/MISSED_STRONG_EVIDENCE.zh.md',
 'experiments/dsn_strengthening_v16_20261111/review/HISTORICAL_EVIDENCE.zh.md',
 'experiments/physical_retirement_20261028/analysis_tools/H3_INDEPENDENT_READING.zh.md',
 'experiments/dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md',
 'experiments/dsn_native_confirmation_20261102/FINAL_RESEARCH_REPORT.zh.md',
 'experiments/dsn_continuity_cost_20261102/FINAL_RESEARCH_REPORT.zh.md',
 'experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md',
 'experiments/dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT.zh.md',
 'experiments/dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT_20261030.zh.md',
 'experiments/dsn_manuscript_update_20261028/timely_continuity_v1/README.zh.md',
 'experiments/dsn_strengthening_v16_20261111/review/FORMAL_RECOVERY_OPPORTUNITIES.zh.md',
 'experiments/dsn_strengthening_v16_20261111/history_ops/HISTORY_CPU_RESULTS.zh.md',
 'experiments/dsn_strengthening_v16_20261111/history_ops/LEDGER_CPU_RESULTS_v2.zh.md',
 'experiments/dsn_strengthening_v16_20261111/history_ops/LEDGER_TIMESTAMP_CLARIFICATION.zh.md',
 'experiments/dsn_strengthening_v16_20261111/history_ops/LEDGER_FULL_BUDGET_DERIVED_v1.zh.md',
 'experiments/dsn_strengthening_v16_20261111/history_ops/EXPOSURE_CPU_RESULTS_v2.zh.md']
historical=[]
for name in historical_paths:
 p=R/name;historical.append(dict(path=name,exists=p.exists(),bytes=p.stat().st_size if p.exists() else None,sha256=sha(p) if p.exists() else 'MISSING',
  tier='REDISCOVERED_EXISTING_EVIDENCE_NOT_NEW_GPU_OR_INDEPENDENT_SAMPLE'))
r3=R/'experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/R3_BASELINE_SOURCES.md'
historical.append(dict(path=r3.relative_to(R).as_posix(),exists=r3.exists(),bytes=r3.stat().st_size if r3.exists() else None,sha256=sha(r3) if r3.exists() else 'MISSING',
 tier='PRIMARY_BASELINE_SOURCE_COMPANION_TO_7_REPORTS',exact_pointers=['FINAL_RESEARCH_REPORT.zh.md:78','R3_BASELINE_SOURCES.md:3-5'],
 note='Old PhaseD LA2/3 display-policy adaptation and repaired confirmed-display clearing already existed; new LA2 v2 is not the first-ever project implementation; no rescan of historical bank'))

groups=[]
for row in rows:
 if row['tier']=='REAL_GPU_SERVING_CHILD':continue
 children=[r for r in rows if r.get('parent_campaign_folder')==str(Path(row['run_record']['path']).parent).replace('\\','/')]
 groups.append(dict(experiment_id=row['experiment_id'],tier=row['tier'],state=row['state'],execution_commit=row['execution_commit'],
  gate_status=row['gate_status'],tests_or_controls=row['tests_or_controls'],child_GPU_cells=len(children),
  passed_child_task_gates=sum(c['state']=='COMPLETED' for c in children),raw_result_location=row['raw_result_location'],
  record=row['run_record']['path'],summary=row['aggregate_summary']['local_mirror'],gate=row['gate']['local_mirror']))

snapshot=[]
for n in ('WORKING_STATE.json','EXECUTION_CHECKPOINT.zh.md'):
 p=E/n;snapshot.append(digest(p))
closures=[]
for p in sorted(E.glob('launch_ops/*/RESOURCE_CLOSURE.json')):
 closures.append(dict(artifact=digest(p),record=read(p)))
payload=dict(record_type='COMPLETE_POST_MENTOR_ARTIFACT_EXPERIMENT_REGISTRY_NOT_NEW_EXPERIMENT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 scope='Everything locally recorded under dsn_strengthening_v16_20261111 since mentor review; historical reports indexed separately without relabeling old runs',
 deduplication_key=['experiment_id','raw_result_location','execution_commit'],
 counts=dict(closed_local_RUN_RECORD_records=len(rows),observed_closed_or_running_records=len(rows)+len(active_campaigns),aggregate_CPU_metadata_campaign_records=len(groups),actual_GPU_serving_child_cells_locally_closed=sum(r['actual_new_serving_trial_count'] for r in rows),
  actual_GPU_reference_campaigns=sum(r['actual_new_reference_campaign_count'] for r in rows),CPU_failed_records=sum(r['state']=='FAILED_PRESERVED' and r['tier'].startswith('CPU') for r in rows),
  active_root_campaigns=len(active_campaigns),planned_children_without_local_run_record=sum(p['tier'].startswith('PLANNED_GPU_CHILD') for p in planned)),
 precedence='Closed local RUN_RECORD/GATE/summary and latest Root status outrank stale generic WORKING_STATE/checkpoint fields; no remote liveness inferred',
 snapshots=snapshot,aggregate_groups=groups,executed_records=rows,active_campaigns=active_campaigns,planned_or_unobserved_children=planned,root_resource_closures=closures,
 frozen_sources=manifests,frozen_or_prospective_unrun=unrun,metadata_subset_bindings=binding_artifacts,historical_evidence_reports=historical,
 failure_classification=[dict(experiment_id='REVTRACE_V16_CPU_ASSET_ENV_READINESS_20261111_V1',classification='PACKAGE_INTERPRETER_IDENTITY_EXPECTATION_FAILURE_PRESERVED',followup='V2 separately frozen PASS; do not erase V1'),
  dict(experiment_id='DSN_V16_GROUPED_RESOURCE_DRIVER_CPU_V1',classification='SYNTHETIC_FIXTURE_MISSING_SPEAKER_ID',tests=4,errors=1,followup='V2 separate source PASS5'),
  dict(experiment_id='DSN_V16_FOCUSED_FULL_READY_CONFIRMATION_CPU_V1',classification='PACKAGING_OMITTED_TEST_FIXTURE_MODULE_IMPORT_ERROR',tests=4,errors=1,followup='V2 separate source PASS10')],
 independent_inventory_support=[digest(E/'review/FORMAL_READINESS_EOS_REGISTRY_ROWS_v1.json')],
 exclusions=['.git and caches','original model/data/Consumer raw logs','no reruns or new neural calls','archive Git HEAD never substitutes execution commit'],
 future_research_stop='User instructed: after current last16 finish, stop new research and start rewriting; this registry launches no experiments',
 master_link='RESEARCH_STRENGTHENING_AND_WRITING_MASTER.zh.md')
with (E/'EXPR_REGISTRY.json').open('w',encoding='utf8') as f:json.dump(payload,f,ensure_ascii=False,indent=2);f.write('\n')
flat=[]
for row in rows:
 flat.append(dict(experiment_id=row['experiment_id'],tier=row['tier'],state=row['state'],execution_commit=row['execution_commit'],parent_controller_commit=row.get('parent_controller_commit',''),
  raw_result_location=row['raw_result_location'],gate_status=row['gate_status'],tests_or_controls=row['tests_or_controls'],actual_new_serving_trial_count=row['actual_new_serving_trial_count'],
  RUN_RECORD=row['run_record']['path'],config=row['frozen_config']['recorded_path'],config_sha256=row['frozen_config']['recorded_sha256'],
  environment=row['environment']['recorded_path'],environment_sha256=row['environment']['recorded_sha256'],summary=row['aggregate_summary']['recorded_path'],gate=row['gate']['recorded_path']))
for p in planned:
 if p['tier']=='RUNNING_CAMPAIGN_FROZEN_PLAN':continue
 flat.append(dict(experiment_id=p['experiment_id'],tier=p['tier'],state=p['state'],execution_commit='MISSING',parent_controller_commit=p.get('planned_controller_commit',''),raw_result_location=p['raw_result_location'],gate_status='MISSING',tests_or_controls='',actual_new_serving_trial_count=0,RUN_RECORD='MISSING',config=p.get('config',p.get('plan','MISSING')).get('path','MISSING') if isinstance(p.get('config',p.get('plan')),dict) else 'MISSING',config_sha256=p.get('config',p.get('plan',{})).get('sha256','MISSING'),environment='MISSING',environment_sha256='MISSING',summary='MISSING',gate='MISSING'))
for a in active_campaigns:
 pre=a['exact_prelaunch_record'];flat.append(dict(experiment_id=a['experiment_id'],tier=a['tier'],state=a['state'],execution_commit=a['execution_commit'],parent_controller_commit=a['execution_commit'],raw_result_location=a['raw_result_location'],gate_status='MISSING_RUNNING',tests_or_controls='',actual_new_serving_trial_count=0,RUN_RECORD='MISSING_LOCAL_ACTUAL; '+a['prelaunch_record']['path'],config=pre['frozen_config'],config_sha256=pre['frozen_config_sha256'],environment=pre['environment_record'],environment_sha256=pre['environment_record_sha256'],summary=pre['aggregate_summary_location'],gate=pre['gate_decision_location']))
with (E/'EXPR_REGISTRY.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)

md=['# 导师评议后：完整实验与证据登记表','',
 '本文件是已有有界记录的清单，不是新科学实验。主记录见 [RESEARCH_STRENGTHENING_AND_WRITING_MASTER.zh.md](RESEARCH_STRENGTHENING_AND_WRITING_MASTER.zh.md)。JSON保留逐项身份与哈希，CSV便于筛选；本文分实验组与子cell两层。',
 '',f"快照：{payload['created_utc']}。去重后 {len(rows)} 项本地闭合RUN_RECORD，含{sum(r['actual_new_serving_trial_count'] for r in rows)}个真实GPU服务child cell；2个真实GPU参考campaign不算服务cell。"+('最后4来源16格已完整闭合，当前无运行controller；Root核查PID2952964已退出、CUDA空，资源闭合记录保留。' if last16_complete else '另有最后4来源16格campaign已于13:54:15UTC由Root启动，PID2952964/start615526505；其cell尚无本地闭合记录，不能算16格完成，也不能全写成未开始。'),'',
 '**计数规则：** controller/summary是容器，不再加一次GPU试验；参考连续/恢复step不是服务cell；203/214/225及50/56是有重叠的版本控制，不能当独立新增测试数相加。CPU编辑/影子/形式模型不算新GPU结果。失败记录保留，缺路径/记录写MISSING。旧WORKING_STATE仍含next2-running等过时字段，完成门与Root最新闭合状态优先。','',
 '## 一、实验组','', '| 实验ID | 层级 | 状态/控制数 | 子GPU cell | 实际执行源 | RUN_RECORD |','|---|---|---|---:|---|---|']
for g in groups:
 units='24 config routes (not24 unit tests)' if g['experiment_id']=='DSN_V16_ACTUAL_PILOT_ENTRY_ROUTE_CPU_V1' else str(g['tests_or_controls'])
 md.append(f"| {g['experiment_id']} | {g['tier']} | {g['state']} / {units} | {g['child_GPU_cells']} | {g['execution_commit']} | [{g['record']}]({g['record']}) |")
md+=['','两个参考：first4为69 continuous+138 restored，last4为72+144；原NN de0936，生成器f367，完整C/状态/IDs门PASS。'+('最后16完整闭合，PILOT24、RESOURCE8、next2确认8与last4确认16共56个本地闭合服务格。最终32主对照仅取Full/Ready：pilot8+next2的8+last4的16，见FINAL_N8_SUMMARY.json。' if last16_complete else '最后16已由Root启动，其RUN_RECORD/结果尚未镜像，登记为RUNNING而非完成。PILOT24、RESOURCE8、next2确认8共40个本地闭合服务格。')+'资源8整体性能失败与技术任务通过是不同字段，不能因任务PASS就写性能PASS。',
 '', '| 当前运行campaign | 实际启动身份 | 已完成child数 | 结果门 |','|---|---|---|---|',
 ('| 无，已全部闭合 | last16 controller4fb6 / NNde09 / PID2952964已退出，CUDA空 | 16/16原任务PASS | COMPLETE_FOCUSED_FULL_READY_CONFIRMATION_TASK_AND_ENDPOINTS |' if last16_complete else '| REVTRACE_V16_FULL_READY_BANK_4_7_V1 | controller4fb6 / NNde09 / PID2952964,start615526505 / 13:54:15UTC | UNKNOWN，无本地闭合child记录 | MISSING_RUNNING |'), '',
 '## 二、GPU逐cell附录','', '| cell ID | 原策略/重复 | 来源 | 技术状态 | NN执行源 | controller | RUN_RECORD |','|---|---|---|---|---|---|']
for r in rows:
 if r['tier']!='REAL_GPU_SERVING_CHILD':continue
 c=r['cell_metadata'];md.append(f"| {r['experiment_id']} | {c.get('arm')}/r{c.get('repeat')} | {', '.join(c.get('source_ids',[]))} | {r['gate_status']} | {r['execution_commit']} | {r['parent_controller_commit']} | [{r['run_record']['path']}]({r['run_record']['path']}) |")
md+=['','## 三、冻结但未运行、未集成或仅计划','', '| 名称/commit | 状态 | 入口 |','|---|---|---|']
for u in unrun:
 ent=u.get('source_manifest',u.get('evidence',{}));path=ent.get('path','MISSING') if isinstance(ent,dict) else 'MISSING'
 md.append(f"| {u.get('name',u.get('commit'))} | {u['state']} | {path} |")
md+=['', '| last16 cell | 计划策略/来源/重复 | RUN_RECORD / GATE |','|---|---|---|']
for p in planned:
 if p['tier'].startswith('PLANNED_GPU_CHILD'):md.append(f"| {p['experiment_id']} | {p['strategy']} / {p['source_id']} / r{p['repeat']} | MISSING_LOCAL / MISSING（campaign运行中） |")
md+=['','## 四、重新发现的历史证据入口（七核心报告及补充材料）','',
 '这些银行在导师评议前已经存在；本轮发现/重计不增加原声学n。H3 110格、PhaseD、36+12开发层、旧native正式12+witness2、新8确认保持不同合同/证据层。旧LA2/3及其修复也保留原身份。','']
for h in historical:md.append(f"- [{h['path']}]({h['path']})：{'PRESENT' if h['exists'] else 'MISSING'}，SHA {h['sha256']}。")
md+=['','详细RUN_RECORD、实际config/env路径与校验、完整manifest/bundle及MISSING字段见 [EXPR_REGISTRY.json](EXPR_REGISTRY.json)；逐行筛选见 [EXPR_REGISTRY.csv](EXPR_REGISTRY.csv)。这里只登记，不替主论文作正面结果筛选。','']
md+=['三次失败均保留：readinessV1 的package/interpreter身份预期检查；resource-driverV1的synthetic fixture缺speaker_id；focused-driverV1遗漏测试fixture模块。分别有新源V2结果，均未把旧失败改名为PASS。','',
 ('用户最新边界：最后16格已完成，停止新增研究实验，转入重写。另登记必要的final32既有job计时收尾派生：2个missing/duplicate控制、无新场景/模型，不作为新研究工作点。本文只是记录现有闭合结果，不启动新采集。' if last16_complete else '用户最新边界：当前最后16格完成后停止新增研究实验，转入重写。登记表只记录该正在运行的阶段；后续结果由Root闭合后刷新，本文没有启动任何测试、模型或新采集。'),'']
(E/'EXPR_REGISTRY.zh.md').write_text('\n'.join(md),encoding='utf8')
print(json.dumps(dict(counts=payload['counts'],source_manifests=len(manifests),unrun_or_prospective=len(unrun),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in (E/'EXPR_REGISTRY.json',E/'EXPR_REGISTRY.csv',E/'EXPR_REGISTRY.zh.md')])))
