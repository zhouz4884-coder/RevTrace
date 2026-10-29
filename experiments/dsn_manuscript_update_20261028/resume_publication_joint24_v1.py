"""Resume a reviewed process snapshot after git rejected ignored checkout paths."""
import hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
T=Path(__file__).resolve().parent
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace').resolve()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],text=True,encoding='utf8').strip()
manifest=T/'PROCESS_joint24_started_v1.json'
d=json.loads(manifest.read_text())
skipped=[x for x in d['files'] if x['path'].startswith('experiments/dsn_streamcorrect_adaptation_20261028/') and any(re.search(r'_source_v\d+$',p) for p in Path(x['path']).parts)]
assert {Path(x['path']).parts[2] for x in skipped}=={'primary_quantiles_source_v1','feedback_characterization_source_v1'}
d['files']=[x for x in d['files'] if x not in skipped]
d['publication_stage_repair']='Ignore standalone analysis execution checkouts; retain their ordinary snapshots and/or frozen bundles when available.'
manifest.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')
(W/manifest.relative_to(R)).write_bytes(manifest.read_bytes())
paths=[x['path'] for x in d['files']]+[manifest.relative_to(R).as_posix()]
spec=T/'PROCESS_joint24_started_v1.bin'
spec.write_bytes(b''.join(x.encode()+b'\0' for x in sorted(paths)))
pending=set(subprocess.check_output(['git','-C',str(W),'diff','--cached','--name-only','-z']).decode().split('\0'))-{''}
assert pending<=set(paths),'unreviewed staged file'
subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','--pathspec-from-file='+str(spec),'--pathspec-file-nul'],check=True)
index={}
for raw in subprocess.check_output(['git','-C',str(W),'ls-files','--stage','-z']).split(b'\0'):
 if raw:
  h,name=raw.split(b'\t',1);index[name.decode()]=h.decode().split()[1]
for row in d['files']:
 data=(W/row['path']).read_bytes()
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
 assert index[row['path']]==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
payload=manifest.read_bytes();mname=manifest.relative_to(R).as_posix()
assert index[mname]==hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
git('commit','-m','Record timely-progress continuity findings and launch joint retention-exit study')
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
subprocess.run(['git','-C',str(W),'-c','http.version=HTTP/1.1','push','origin','HEAD:main'],check=True)
assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
receipt=dict(stage='joint24_started_v1',commit=commit,tree=tree,files=len(paths),bytes=sum(x['bytes'] for x in d['files'])+len(payload),remote_main_verified=True,skipped_ignored_execution_checkouts=len(skipped),initial_stage_failure='git-add exit1 for ignored standalone execution checkouts; no remote write occurred before repair')
(T/'PUBLICATION_joint24_started_v1.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
