"""Machine-local launch pointer; never relabel any completed source or result."""
import hashlib,json,pathlib
T=pathlib.Path(__file__).resolve().parents[1];R=T.parents[1];C=R/'experiments/repository_identity_20261027/CURRENT.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
pre=read(T/'SERVICE_PREREQUISITE_v1.json');assert pre['status']=='PASS_PILOT_SOURCE_ASSETS_ENVIRONMENT_AND_CPU118_NO_NEURAL_LAUNCH' and pre['tests']==118 and pre['skipped']==0
plan=T/'SERVICE_PILOT_v1_FROZEN.json';m=T/'packages/SOURCE_v3_LOCAL_PREFLIGHT.json';commit=read(m)['source_commit'];assert commit==pre['source_commit'] and sha(plan)==pre['plan_sha256']
backup=T/'CURRENT_BEFORE_SERVICE_PILOT_v1.json';assert not backup.exists();backup.write_bytes(C.read_bytes());x=read(C)
x.update(updated_date='2026-10-29',source_worktree=str(T/'source_v3'),source_commit=commit,source_manifest=str(m),source_manifest_sha256=sha(m),previous_pointer=str(backup),research_state=str(T/'CURRENT_STATUS.json'),GPU_queue='FROZEN_SOURCE0_THREE_ARM_NATIVE_SERVICE_PILOT',scope='Machine-local current launch pointer only; all old f0/native/profile/neuralEQ results preserve their original full commits.')
C.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8');p=read(plan);env=T/'service_cpu_v3/ENVIRONMENT.json'
record=dict(experiment_id=p['experiment_id'],code_commit=commit,frozen_config=str(plan),frozen_config_sha256=sha(plan),environment_record=str(env),environment_record_sha256=sha(env),raw_result_location=p['raw_result_location'],aggregate_summary_location=p['aggregate_summary_location'],gate_decision_location=p['gate_decision_location'],source_manifest=str(m),source_manifest_sha256=sha(m),prerequisite_gate=str(T/'SERVICE_PREREQUISITE_v1.json'),prerequisite_gate_sha256=sha(T/'SERVICE_PREREQUISITE_v1.json'),GPU_launched=False)
target=T/'SERVICE_PRELAUNCH_RECORD_v1.json';assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
status=read(T/'CURRENT_STATUS.json');status.update(status='READY_FROZEN_SOURCE0_THREE_ARM_NATIVE_SERVICE_PILOT',source_commit=commit,actual_serving_cells=0,GPU_launched=False,remote_resources_released=True,service_plan_sha256=sha(plan),scope=p['scope'],next_action='Root independent no-argument preflight and actual source/plan/CPU gate launch; no online result exists yet')
(T/'CURRENT_STATUS.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(source_commit=commit,prelaunch_record=str(target),GPU_launched=False)))
