"""Fresh read-only machine, source and resource inventory; no model imports."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
for name in ['ops','baseline','inputs','packages','review','resource','plans']:(E/name).mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
code=r'''from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
def run(a):
 r=subprocess.run(a,capture_output=True,text=True);return dict(returncode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip()[:500])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
roots=[('runtime','projects/revtrace_dsn_native_resilience_20261030/source_v2','projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json'),('support','projects/revtrace_dsn_strengthening_20261031/paired_resident_source_v2','projects/revtrace_dsn_strengthening_20261031/PAIRED_RESIDENT_SOURCE_v2.json')]
sources=[]
for role,d,mp in roots:
 root=B/d;manifest=B/mp;m=json.loads(manifest.read_bytes());g=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
 rows=m['files'];assert g('rev-parse','HEAD')==m.get('code_commit',m.get('source_commit')) and not g('status','--porcelain','--untracked-files=all')
 assert set(g('ls-files').splitlines())=={r['path'] for r in rows}
 for row in rows:assert (root/row['path']).stat().st_size==row['bytes'] and sha(root/row['path'])==row['sha256']
 sources.append(dict(role=role,source_root=str(root),manifest=str(manifest),manifest_sha256=sha(manifest),commit=g('rev-parse','HEAD'),files=len(rows),clean=True))
v=os.statvfs(B)
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,executable=sys.executable,host_machine=platform.machine(),disk=dict(root=str(B),bytes=v.f_blocks*v.f_frsize,free_bytes=v.f_bavail*v.f_frsize),gpus=run(['nvidia-smi','--query-gpu=index,uuid,name,memory.total,memory.used,utilization.gpu,temperature.gpu','--format=csv,noheader']),compute_owners=run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader']),sources=sources,new_model_calls=0,scope='Read-only inventory, not environment validation or serving result')))
'''
with m.Remote() as c:raw=c.python(code,timeout=60)
out=E/'resource/INITIAL_REMOTE_READBACK.json';assert not out.exists();out.write_bytes(raw+b'\n')
gate=E/'resource/INITIAL_DEFAULT_SOURCE_GATE.json';subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(gate)],cwd=R,capture_output=True,check=True)
j=json.loads(raw);print(json.dumps(j))
