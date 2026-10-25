"""Freeze tested source/configs and an explicit bounded GPU smoke package."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;S=W/'runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf8')
def git(*args):return subprocess.check_output(['git','-C',str(S),*args])
assert not git('status','--porcelain').strip()
commit=git('rev-parse','HEAD').decode().strip()
assert commit=='e45c66475ba1173a98b49b8c9e62f3e8cb45b333'
gate=read(W/'INDEPENDENT_CPU_GATE.json');assert gate['tests']==367 and gate['failures']==0
for name,expected in gate['tested_source_sha256'].items():assert sha(W/name)==expected,name
review=read(W/'FINAL_RUNTIME_REVIEW_FINAL.json')
assert commit in json.dumps(review)
assert read(W/'INDEPENDENT_PROFILE_AUDIT_v1.json')['status']=='PASS_INDEPENDENT_EXTRACTED_PROFILE_ARITHMETIC_AND_FIT_AUDIT'
source=[]
for name in git('ls-files').decode().splitlines():
    p=S/name;raw=p.read_bytes();committed=git('show',commit+':'+name)
    assert raw==committed,(name,'tested bytes differ from committed blob')
    source.append({'path':name,'bytes':len(raw),'sha256':sha(p)})
save(W/'SOURCE_MANIFEST.json',{'code_commit':commit,'scope':'CPU-gated closed-loop runtime; GPU pending',
    'files':source,'prior_runtime_commit':'126dc815962e8f726b0cbdf214a19318b28a3629'})
config={'max_deferrals':2,'promise_quantile':.9,'max_successors_per_session':2,
    'max_scenario_combinations':16,'max_candidate_plans':8,'promise_tolerance_s':1e-6}
save(W/'CLOSED_CONFIG.json',config)
assets=read(W/'ASSET_IDENTITIES.json');plan=read(W/'PLAN.example.json')
plan.pop('template_status',None);plan.update(implementation_gates_complete=True,
    runtime_commit=commit,runtime_manifest_sha256=sha(W/'SOURCE_MANIFEST.json'),
    calibration_sha256=sha(W/'profiles_training_v1/CALIBRATION.json'),
    closed_config_sha256=sha(W/'CLOSED_CONFIG.json'),protocol_sha256=sha(W/'PROTOCOL.md'))
plan.update({k:v for k,v in assets.items() if k not in ('GPU_processes','new_GPU_calls')})
gates=['INDEPENDENT_CPU_GATE.json',gate['junit_file'],'FINAL_RUNTIME_REVIEW.md','FINAL_RUNTIME_REVIEW_FINAL.json',
    'INDEPENDENT_PROFILE_AUDIT_v1.json','DESIGN_REVIEW.md','PLANNER_IMPLEMENTATION.md']
plan['cpu_gate_files']=[{'path':n,'sha256':sha(W/n)} for n in gates]
plan['profile_files']=[{'path':'profiles_training_v1/'+n,'sha256':sha(W/'profiles_training_v1'/n)}
    for n in ['SUMMARY.json','INPUT_MANIFEST.json','PROPOSAL_ROWS.csv','PROPOSAL_BATCHES.csv','ROOT_COMPATIBILITY.csv','CELL_STATUS.csv']]
plan['formal_approved_after_smoke']=False
save(W/'PLAN.smoke.json',plan)
from run_closed_stage import validate_plan
validate_plan(plan,'smoke')
controllers=['run_closed_stage.py','audit_closed.py','audit_closed_helpers.py','summarize_closed.py','PROTOCOL.md']
archive=W/'SOURCE_AND_CONTROLLERS_smoke_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
    for row in source:tf.add(S/row['path'],arcname='runtime/'+row['path'],recursive=False)
    tf.add(W/'SOURCE_MANIFEST.json',arcname='runtime/SOURCE_MANIFEST.json')
    tf.add(W/'profiles_training_v1/CALIBRATION.json',arcname='CALIBRATION.json')
    for n in controllers+gates+['CLOSED_CONFIG.json','PLAN.smoke.json']:tf.add(W/n,arcname=n)
    for row in plan['profile_files']:tf.add(W/row['path'],arcname=row['path'])
record={'source_commit':commit,'files':len(source),'plan_sha256':sha(W/'PLAN.smoke.json'),
    'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
    'controllers':{n:sha(W/n) for n in controllers},'GPU_started':False,
    'smoke_performance_cells':4,'smoke_oracle_cells':2,'formal_proposed_cells':len(plan['stages']['formal']['cells']),
    'formal_approved':False,'tested_bytes_equal_committed_blobs':True}
save(W/'SMOKE_PACKAGE.json',record)
state=read(W/'ACTIVE_STATE.json');state.update(phase='SOURCE_FROZEN_READY_FOR_SMOKE',
    source_commit=commit,CPU_tests=367,CPU_independent_gate='PASS',profile_independent_gate='PASS',
    package_sha256=record['archive_sha256'],GPU_gate='PASS_CPU_AND_SOURCE_PENDING_REMOTE_PREFLIGHT')
for k in state['implementation_components']:state['implementation_components'][k]='IMPLEMENTED_CPU_VALIDATED_GPU_PENDING'
(W/'ACTIVE_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(record,indent=2))
