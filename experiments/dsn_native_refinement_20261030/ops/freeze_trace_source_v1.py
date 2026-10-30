"""Freeze independent actual-trace checker; never touch runtime/CURRENT."""
import datetime,hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'trace_source_v1';P=F/'packages';P.mkdir(exist_ok=True)
def git(cwd,*args):return subprocess.check_output(['git','-C',str(cwd),*args],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
assert not (S/'.git').exists()
subprocess.run(['git','init','-b','codex/native-trace-refinement-20261030',str(S)],check=True,capture_output=True)
git(S,'config','core.autocrlf','false');git(S,'config','user.name','RevTrace Research');git(S,'config','user.email','source@revtrace.local')
git(S,'add','-A');git(S,'commit','-m','check: bind original full calls to durable facts and actual whole views')
commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
files=[]
for name in git(S,'ls-files').splitlines():
    p=S/name;files.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
manifest=P/'TRACE_SOURCE_v1.json';put(manifest,dict(source_commit=commit,code_commit=commit,files=files,
    scope='Independent CPU actual-trace structural refinement checker; synthetic controls are not actual serving evidence.'))
snapshot=F/'trace_source_snapshot_v1';snapshot.mkdir(exist_ok=False)
for row in files:
    dest=snapshot/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((S/row['path']).read_bytes())
bundle=P/'TRACE_SOURCE_v1.bundle';git(S,'bundle','create',str(bundle),'HEAD')
git(R,'fetch',str(bundle),'HEAD:refs/research/dsn-native-actual-trace-refinement-v1')
cfg=dict(experiment_id='DEV_ONLY_ACTUAL_TRACE_REFINEMENT_CONTROLS_V1',checker_source_commit=commit,
    checker_manifest_sha256=sha(manifest),mode='controls',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='Local bounded synthetic DEVELOPMENT controls only; actual new-runtime traces not yet read, no neural calls.')
put(F/'TRACE_DEVELOPMENT_CONFIG_v1_FROZEN.json',cfg)
put(F/'TRACE_FREEZE_RECORD_v1.json',dict(source_commit=commit,manifest_sha256=sha(manifest),source_files=len(files),
    bundle_sha256=sha(bundle),controls_config_sha256=sha(F/'TRACE_DEVELOPMENT_CONFIG_v1_FROZEN.json'),actual_trace_run_executed=False))
print(json.dumps(dict(source_commit=commit,source_files=len(files),manifest_sha256=sha(manifest),actual_trace_run_executed=False),indent=2))

