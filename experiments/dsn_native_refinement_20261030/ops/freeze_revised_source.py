"""Freeze a revised CPU specification without modifying previous source/results."""
import argparse,datetime,hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
def git(cwd,*args):return subprocess.check_output(['git','-C',str(cwd),*args],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
p=argparse.ArgumentParser();p.add_argument('--version',type=int,required=True);a=p.parse_args();n=a.version
assert n>=2;S=F/f'source_v{n}';P=F/'packages'
git(S,'config','core.autocrlf','false');git(S,'config','user.name','RevTrace Research');git(S,'config','user.email','source@revtrace.local')
git(S,'add','-A');git(S,'commit','-m',f'spec: refine execution and controls v{n}')
commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
files=[]
for name in git(S,'ls-files').splitlines():
    f=S/name;files.append(dict(path=name,bytes=f.stat().st_size,sha256=sha(f)))
manifest=P/f'SOURCE_v{n}.json'
put(manifest,dict(source_commit=commit,code_commit=commit,files=files,scope='separate CPU specification source; no neural method changes'))
snapshot=F/f'source_snapshot_v{n}';snapshot.mkdir(exist_ok=False)
for row in files:
    target=snapshot/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((S/row['path']).read_bytes())
bundle=P/f'SOURCE_v{n}.bundle';git(S,'bundle','create',str(bundle),'HEAD')
git(R,'fetch',str(bundle),f'HEAD:refs/research/dsn-native-refinement-20261030-v{n}')
base=json.loads((F/'MODEL_PLAN_v1_FROZEN.json').read_bytes());base.update(experiment_id=f'REVTRACE_FULLSPEC_REFINEMENT_FINITE_SPEC_V{n}',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=commit,source_manifest_sha256=sha(manifest),revision_reason='Fix development harness and align separate Owner/session/physical fences; original bounds unchanged; no formal/neural outcome adaptation.')
for key in ('intended_raw_result_location','intended_summary_location','intended_gate_location'):
    base[key]=base[key].replace('formal_model_v1',f'formal_model_v{n}')
put(F/f'MODEL_PLAN_v{n}_FROZEN.json',base)
dev=dict(base);dev.update(experiment_id=f'DEV_ONLY_FULLSPEC_REFINEMENT_V{n}',scope='Bounded local DEVELOPMENT smoke only, not formal completion. '+base['scope'])
put(F/f'DEVELOPMENT_PLAN_v{n}_FROZEN.json',dev)
put(F/f'FREEZE_RECORD_v{n}.json',dict(source_commit=commit,source_manifest_sha256=sha(manifest),source_files=len(files),bundle_sha256=sha(bundle),plan_sha256=sha(F/f'MODEL_PLAN_v{n}_FROZEN.json'),formal_run_executed=False,models_or_GPU_launched=False))
print(json.dumps(dict(source_commit=commit,source_files=len(files),manifest=str(manifest),manifest_sha256=sha(manifest),formal_run_executed=False),indent=2))

