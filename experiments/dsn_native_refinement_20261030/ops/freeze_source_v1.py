"""Freeze a separate specification source, never mutate legacy/native runtime."""
import datetime,hashlib,json,pathlib,subprocess,sys,platform
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'source_v1';P=F/'packages';P.mkdir(exist_ok=True)
def git(cwd,*args):return subprocess.check_output(['git','-C',str(cwd),*args],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
assert not (S/'.git').exists()
subprocess.run(['git','init','-b','codex/native-refinement-20261030',str(S)],check=True,capture_output=True)
git(S,'config','core.autocrlf','false');git(S,'config','user.name','RevTrace Research');git(S,'config','user.email','source@revtrace.local')
git(S,'add','-A');git(S,'commit','-m','spec: model full-call eligibility, ownership and durable refinement')
commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
files=[]
for name in git(S,'ls-files').splitlines():
    p=S/name;files.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
manifest=P/'SOURCE_v1.json';put(manifest,dict(source_commit=commit,code_commit=commit,files=files,
    scope='Finite symbolic specification and mutation controls; no neural code or serving measurements.'))
snapshot=F/'source_snapshot_v1';snapshot.mkdir(exist_ok=False)
for row in files:
    dest=snapshot/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((S/row['path']).read_bytes())
bundle=P/'SOURCE_v1.bundle';git(S,'bundle','create',str(bundle),'HEAD')
git(R,'fetch',str(bundle),'HEAD:refs/research/dsn-native-refinement-20261030-v1')
put(F/'FROZEN_ENVIRONMENT_v1.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
    scope='Local source freeze metadata only; actual CPU environment recorded by formal runner.'))
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
plan=dict(experiment_id='REVTRACE_FULLSPEC_REFINEMENT_FINITE_SPEC_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_commit=commit,source_manifest_sha256=sha(manifest),actual_neural_source_anchor='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',
    profiles={'normal_two_frontiers':dict(frontiers=2,max_issued=3,max_depth=12,max_faults=0,state_cap=150000),
              'failure_one_frontier':dict(frontiers=1,max_issued=2,max_depth=12,max_faults=1,state_cap=150000)},
    scope='Bounded symbolic complete-cut refinement with explicit original-C/U nondeterminism, mutations, Consumer and supported fault/recovery; not extracted implementation proof, real serving, unbounded liveness or natural prevalence.',
    intended_raw_result_location=B+'/results/revtrace/dsn_native_refinement_20261030/formal_model_v1',
    intended_summary_location=B+'/results/revtrace/dsn_native_refinement_20261030/formal_model_v1/SUMMARY.json',
    intended_gate_location=B+'/results/revtrace/dsn_native_refinement_20261030/formal_model_v1/GATE.json',
    models_or_GPU_launched=False)
put(F/'MODEL_PLAN_v1_FROZEN.json',plan)
put(F/'FREEZE_RECORD_v1.json',dict(source_commit=commit,source_manifest_sha256=sha(manifest),
    bundle_sha256=sha(bundle),source_files=len(files),plan_sha256=sha(F/'MODEL_PLAN_v1_FROZEN.json'),
    code_executed=False,model_calls=0,GPU_calls=0))
print(json.dumps(dict(source_commit=commit,source_files=len(files),source_manifest=str(manifest),
    source_manifest_sha256=sha(manifest),plan=str(F/'MODEL_PLAN_v1_FROZEN.json'),
    plan_sha256=sha(F/'MODEL_PLAN_v1_FROZEN.json'),CPU_controls_run=False,models_or_GPU_launched=False),indent=2))

