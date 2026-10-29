import pathlib,json,hashlib,datetime
T=pathlib.Path(__file__).resolve().parents[1];R=T.parents[1];C=R/'experiments/repository_identity_20261027/CURRENT.json';backup=T/'CURRENT_BEFORE_HANDOFF_EQ_v2.json'
if not backup.exists():backup.write_bytes(C.read_bytes())
x=json.loads(C.read_text(encoding='utf-8'));m=T/'packages/SOURCE_v2_LOCAL_PREFLIGHT.json';plan=T/'EQ_PLAN_v2_FROZEN.json';env=T/'remote_cpu_v2/ENVIRONMENT.json';commit=json.loads(m.read_text(encoding='utf-8'))['source_commit']
x.pop('analysis_source',None);x.pop('analysis_commit',None)
x.update(updated_date='2026-10-29',source_worktree=str(T/'source_v2'),source_commit=commit,source_manifest=str(m),source_manifest_sha256=hashlib.sha256(m.read_bytes()).hexdigest(),previous_pointer=str(backup),research_state=str(T/'CURRENT_STATUS.json'),GPU_queue='STAGE_HANDOFF_FOUR_SOURCE_EQ_PREREQUISITE',scope='Machine-local pointer only. Completed f0 and native v8 results retain original source identities.')
C.write_text(json.dumps(x,indent=2),encoding='utf-8')
record=dict(experiment_id='SC_STAGE_HANDOFF_FOUR_SOURCE_EQ_V2',code_commit=commit,frozen_config=str(plan),frozen_config_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),environment_record=str(env),environment_record_sha256=hashlib.sha256(env.read_bytes()).hexdigest(),raw_result_location=json.loads(plan.read_text(encoding='utf-8'))['raw_result_location'],aggregate_summary_location=json.loads(plan.read_text(encoding='utf-8'))['aggregate_summary_location'],gate_decision_location=json.loads(plan.read_text(encoding='utf-8'))['gate_decision_location'])
(T/'PRELAUNCH_RECORD_v2.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
(T/'CURRENT_STATUS.json').write_text(json.dumps(dict(status='READY_FROZEN_PROTECTED_PACKET_EQ_PREREQUISITE',source_commit=commit,neural_profile_runs_completed=0,GPU_launched=False,prerequisite_gate='PREREQUISITE_GATE_v2.json',current_pointer=str(C),scope='Four original full sources; actual original full C/U and identity projection equivalence control only; no serving cells'),indent=2),encoding='utf-8')
print(commit)
