"""Stage a new immutable CPU-only readiness check; never starts inference."""
from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'readiness_source';D=E/'readiness_ops';D.mkdir(exist_ok=True)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/readiness_v1';O=B+'/results/revtrace/dsn_strengthening_v16_20261111/readiness_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2);f.write('\n')
def git(root,*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
assert not (S/'.git').exists()
git(S,'init','-b','codex/v16-readiness-v1');git(S,'config','core.autocrlf','false')
git(S,'add','.gitattributes','README.md','readiness.py')
git(S,'-c','user.name=RevTrace research','-c','user.email=research@invalid','commit','-m','Freeze CPU asset and environment readiness without inference')
commit=git(S,'rev-parse','HEAD');files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in sorted(git(S,'ls-files').splitlines())]
manifest=D/'SOURCE.json';put(manifest,dict(code_commit=commit,files=files))
bundle=D/'SOURCE.bundle';git(S,'bundle','create',str(bundle.resolve()),'--all')
git(R,'fetch',str(bundle.resolve()),'refs/heads/codex/v16-readiness-v1:refs/revtrace/execution/dsn-v16-readiness-v1')
gate=R/'experiments/repository_identity_20261027/preflight.py'
for args,name in [([], 'ROOT_DEFAULT_PREFLIGHT.json'),(['--source',str(S.resolve()),'--manifest',str(manifest.resolve())],'EXPLICIT_SOURCE_PREFLIGHT.json')]:
    subprocess.run([sys.executable,'-B',str(gate),*args,'--output',str((D/name).resolve())],check=True,capture_output=True)
old=R/'experiments/dsn_native_resilience_20261030/FROZEN_ENVIRONMENT_v2.json';env=json.loads(old.read_bytes());put(D/'ENVIRONMENT_EXPECTED.json',env)
bank=R/'experiments/dsn_native_confirmation_20261102/confirmation/SERVICE_PLAN_v1.json';sources=json.loads(bank.read_bytes())['sources']
c=dict(experiment_id='REVTRACE_V16_CPU_ASSET_ENV_READINESS_20261111_V1',disk_root=B,packages=env['packages'],executable=env['executable'],assets_manifest=env['assets_manifest_path'],assets_manifest_sha256=env['assets_manifest_sha256'],source_bank=str(bank.resolve()),source_bank_sha256=sha(bank),audio_files=[dict(path=s['path'],bytes=s['archive_member']['bytes'],sha256=s['audio_sha256'])for s in sources],raw_result_location=O,scope='CPU hash/metadata only. Not a serving trial. SHA reads warm file cache.')
config=D/'CONFIG.json';put(config,c)
pre=dict(experiment_id=c['experiment_id'],code_commit=commit,source_commit=commit,source_manifest_sha256=sha(manifest),config_sha256=sha(config),frozen_config=str(config.resolve()),frozen_config_sha256=sha(config),environment_record=str((D/'ENVIRONMENT_EXPECTED.json').resolve()),environment_record_sha256=sha(D/'ENVIRONMENT_EXPECTED.json'),raw_result_location=O,aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',root_preflight_sha256=sha(D/'ROOT_DEFAULT_PREFLIGHT.json'),explicit_source_preflight_sha256=sha(D/'EXPLICIT_SOURCE_PREFLIGHT.json'))
put(D/'PRELAUNCH.json',pre)
spec=importlib.util.spec_from_file_location('approved_remote',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with m.Remote() as r:
    r.python('from pathlib import Path\np=Path('+repr(P)+')\np.mkdir(parents=True,exist_ok=False)\n')
    for n in ['SOURCE.bundle','SOURCE.json','CONFIG.json','PRELAUNCH.json','ENVIRONMENT_EXPECTED.json']:r.put(D/n,P+'/'+n)
    command=[env['executable'],'-B',P+'/source/readiness.py','--manifest',P+'/SOURCE.json','--config',P+'/CONFIG.json','--prelaunch',P+'/PRELAUNCH.json']
    remote='C='+repr(dict(root=P,command=command))+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess
p=Path(C['root']);source=p/'source'
subprocess.run(['git','clone','--quiet','--config','core.autocrlf=false',str(p/'SOURCE.bundle'),str(source)],check=True)
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
with (p/'process.log').open('xb') as stream:
 child=subprocess.Popen(C['command'],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
h=dict(pid=child.pid,start_ticks=int(ticks),command=C['command'],command_sha256=hashlib.sha256(json.dumps(C['command'],separators=(',',':')).encode()).hexdigest(),GPU_or_model_launch=False)
(p/'HANDLE.json').write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
'''
    raw=r.python(remote,timeout=30);(D/'HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
