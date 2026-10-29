"""Root selects unchanged bdfa execution identity for the fixed final campaign."""
import hashlib,json,subprocess,sys
from pathlib import Path
I=Path(__file__).resolve().parents[1];R=I.parents[1];H=I.parent/'dsn_streamcorrect_stage_handoff_20261029'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
planpath=I/'FINAL_SERVICE_v2_FROZEN.json';plan=read(planpath)
assert plan['source_commit']=='bdfa3b1307d267a5a4caf6484e1ad465c39a592e' and plan['expected_cells']==16
assert sha(I/'REFERENCE_RESULTS_v1/GATE.json')==plan['original_reference_gate_sha256']
assert sha(I/'REFERENCE_RESULTS_v1/DETAILS.json')==plan['reference_details_sha256']
assert sha(I/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json')==plan['frozen_appraisal_sha256']
environment=I.parent/'dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence/FROZEN_ENVIRONMENT_v8.json'
assert sha(environment)==plan['environment_sha256']
manifest=H/'packages/SOURCE_v3_LOCAL_PREFLIGHT.json';assert read(manifest)['source_commit']==plan['source_commit']
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';backup=I/'CURRENT_BEFORE_FINAL_SERVICE_v2.json'
assert not backup.exists();backup.write_bytes(pointer.read_bytes());x=read(pointer)
x.update(source_worktree=str(H/'source_v3'),source_commit=plan['source_commit'],source_manifest=str(manifest),source_manifest_sha256=sha(manifest),research_state=str(I/'CURRENT_STATUS.json'),GPU_queue='FIXED_NEW4_SPEAKER_FINAL16_NATIVE_SERVICE',scope='Final unchanged bdfa full-call method; all earlier reference/component/acquisition runs retain separate actual execution sources.',previous_pointer=str(backup))
pointer.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True)
identity=json.loads(r.stdout);assert identity['gate']=='SOURCE_IDENTITY_PASS' and identity['code_commit']==plan['source_commit']
(I/'FINAL_SERVICE_ROOT_SOURCE_PREFLIGHT_v2.json').write_bytes(r.stdout)
record=dict(experiment_id=plan['experiment_id'],code_commit=plan['source_commit'],frozen_config=str(planpath),frozen_config_sha256=sha(planpath),environment_record=str(environment),environment_sha256=sha(environment),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['aggregate_summary_location'],gate_decision_location=plan['gate_decision_location'],expected_cells=16,GPU_launched=False)
out=I/'FINAL_SERVICE_ROOT_PRELAUNCH_RECORD_v2.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps(identity))
