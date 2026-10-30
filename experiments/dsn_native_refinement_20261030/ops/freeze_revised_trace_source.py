"""Freeze a narrowed actual-trace schema revision, preserving all old runs."""
import argparse,datetime,hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
def git(cwd,*args):return subprocess.check_output(['git','-C',str(cwd),*args],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
 assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
p=argparse.ArgumentParser();p.add_argument('--version',type=int,required=True);a=p.parse_args();n=a.version
assert n>=2;S=F/f'trace_source_v{n}';P=F/'packages'
git(S,'config','core.autocrlf','false');git(S,'config','user.name','RevTrace Research');git(S,'config','user.email','source@revtrace.local')
git(S,'add','-A');git(S,'commit','-m',f'check: narrow actual-trace schema compatibility v{n}')
commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
files=[]
for name in git(S,'ls-files').splitlines():
 f=S/name;files.append(dict(path=name,bytes=f.stat().st_size,sha256=sha(f)))
manifest=P/f'TRACE_SOURCE_v{n}.json';put(manifest,dict(source_commit=commit,code_commit=commit,files=files,
 scope='Independent complete actual-trace structural refinement; no neural implementation or endpoint change.'))
snapshot=F/f'trace_source_snapshot_v{n}';snapshot.mkdir(exist_ok=False)
for row in files:
 target=snapshot/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((S/row['path']).read_bytes())
bundle=P/f'TRACE_SOURCE_v{n}.bundle';git(S,'bundle','create',str(bundle),'HEAD')
git(R,'fetch',str(bundle),f'HEAD:refs/research/dsn-native-actual-trace-refinement-v{n}')
cfg=dict(experiment_id=f'DEV_ONLY_ACTUAL_TRACE_REFINEMENT_CONTROLS_V{n}',checker_source_commit=commit,checker_manifest_sha256=sha(manifest),mode='controls',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Local bounded synthetic DEVELOPMENT controls only; no actual serving trace PASS.')
put(F/f'TRACE_DEVELOPMENT_CONFIG_v{n}_FROZEN.json',cfg)
put(F/f'TRACE_FREEZE_RECORD_v{n}.json',dict(source_commit=commit,manifest_sha256=sha(manifest),source_files=len(files),bundle_sha256=sha(bundle),controls_config_sha256=sha(F/f'TRACE_DEVELOPMENT_CONFIG_v{n}_FROZEN.json'),actual_trace_run_executed=False,revision_reason='Explicit actual accepted_input/frontier schema and raw-source/bounded-copy provenance; guards/endpoints/inputs unchanged.'))
print(json.dumps(dict(source_commit=commit,source_files=len(files),manifest_sha256=sha(manifest),actual_trace_run_executed=False),indent=2))

