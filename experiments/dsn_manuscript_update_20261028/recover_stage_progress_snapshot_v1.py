"""Finish exactly the byte-verified snapshot after one ignored public-source path."""
import hashlib,json,subprocess
from pathlib import Path
T=Path(__file__).resolve().parent;R=T.parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
snapshot='stage_profile_eq_content_v1'
manifest=T/f'PROCESS_{snapshot}.json'
records=json.loads(manifest.read_text(encoding='utf8'))['files']
paths=[]
for item in records:
 rel=item['path'];data=(W/rel).read_bytes()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],rel
 assert (R/rel).read_bytes()==data,rel
 paths.append(rel)
rel=manifest.relative_to(R).as_posix();assert (W/rel).read_bytes()==manifest.read_bytes();paths.append(rel)
allow='experiments/dsn_streamcorrect_stage_handoff_20261029/author_reference/runs/run_single_eval_aishell.sh'
assert allow in paths
subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','-f',allow],check=True,capture_output=True)
index={}
for raw in subprocess.check_output(['git','-C',str(W),'ls-files','--stage','-z']).split(b'\0'):
 if not raw:continue
 head,name=raw.split(b'\t',1);index[name.decode()]=head.decode().split()[1]
for rel in paths:
 data=(W/rel).read_bytes()
 assert index[rel]==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),rel
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],text=True,encoding='utf8').strip()
staged=set(git('diff','--cached','--name-only').splitlines())
assert staged.issubset(paths),staged-set(paths)
git('commit','-m','Archive native stage profile, protected candidate equivalence and content evidence')
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
subprocess.run(['git','-C',str(W),'-c','http.version=HTTP/1.1','push','origin','HEAD:main'],check=True)
assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
receipt=dict(stage=snapshot,commit=commit,tree=tree,files=len(paths),bytes=sum((W/rel).stat().st_size for rel in paths),remote_main_verified=True,recovered_failure='Standard git add rejected the explicitly pinned public author shell example under an ignored runs directory; only that exact audited3540-byte path was added with force, all snapshot bytes reverified before commit.')
(T/f'PUBLICATION_{snapshot}.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))
