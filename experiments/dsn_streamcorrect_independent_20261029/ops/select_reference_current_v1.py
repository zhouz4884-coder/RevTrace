"""Root-only machine pointer and prelaunch record for original-full reference."""
import hashlib,json,subprocess,sys
from pathlib import Path
I=Path(__file__).resolve().parents[1]; R=I.parents[1]
H=I.parent/'dsn_streamcorrect_stage_handoff_20261029'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
planpath=I/'ORIGINAL_FULL_REFERENCE_PLAN_v1_FROZEN.json'; plan=read(planpath)
assert plan['generator_source_commit']=='66abab7b8ce668a1a1ddefb65f6115af45e99cec'
assert read(I/'REFERENCE_CPU_RESULTS_v1/GATE.json')['CPU_tests']==13
assert sha(I/'REFERENCE_CPU_RESULTS_v1/GATE.json')=='4d495ecfb10c5c391e68ca6663e8d93145dfbf5d5076ff9094e616fd91570ecd'
pointer=R/'experiments/repository_identity_20261027/CURRENT.json'
backup=I/'CURRENT_BEFORE_REFERENCE_v1.json'
if not backup.exists():backup.write_bytes(pointer.read_bytes())
else:assert read(pointer)['source_commit']==plan['generator_source_commit']
x=read(pointer);candidate=read(H/'CURRENT_REFERENCE_CANDIDATE_v1.json')
for k in ['source_worktree','source_manifest','source_commit','source_manifest_sha256']:x[k]=candidate[k]
x.update(research_state=str(I/'CURRENT_STATUS.json'),GPU_queue='NEW4_ORIGINAL_FULL_REFERENCE_ONLY_NO_SERVING',scope='Actual generator66 identity; imported model runtime remains unchanged bdfa; original full reference is not serving evidence.',previous_pointer=str(backup))
pointer.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True)
identity=json.loads(r.stdout);assert identity['gate']=='SOURCE_IDENTITY_PASS' and identity['code_commit']==plan['generator_source_commit']
preflight=I/'REFERENCE_ROOT_SOURCE_PREFLIGHT_v1.json'
if not preflight.exists():preflight.write_bytes(r.stdout)
else:assert read(preflight)['code_commit']==identity['code_commit']
environment=I.parent/'dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence/FROZEN_ENVIRONMENT_v8.json'
assert sha(environment)==plan['frozen_environment_sha256']
record=dict(experiment_id=plan['experiment_id'],actual_source_commit=plan['generator_source_commit'],imported_model_runtime_commit=plan['model_runtime_commit'],frozen_config=str(planpath),frozen_config_sha256=sha(planpath),environment_record=str(environment),environment_sha256=sha(environment),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['aggregate_summary_location'],gate_decision_location=plan['gate_decision_location'],new_source_neural_calls_launched=False,reference_only=True)
out=I/'REFERENCE_ROOT_PRELAUNCH_RECORD_v1.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps(identity))
