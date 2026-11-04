"""Publish explicit audited paths through the clean codex archive checkout."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
W=Path('C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--paths',type=Path,required=True);p.add_argument('--message',required=True);p.add_argument('--push',action='store_true');p.add_argument('--resume-owned-copy',action='store_true');a=p.parse_args()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],stderr=subprocess.PIPE).decode().strip()
assert W.resolve()!=R.resolve() and git('remote','get-url','origin')=='https://github.com/zhouz4884-coder/RevTrace.git'
assert git('branch','--show-current').startswith('codex/')
base=git('rev-parse','HEAD');assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]==base
names=json.loads(a.paths.read_text(encoding='utf-8-sig'));assert names and len(names)==len(set(names))
status=git('status','--porcelain','--untracked-files=all')
if a.resume_owned_copy:assert all(row[3:].strip('"') in names for row in status.splitlines()),'Unowned worktree change blocks resume'
else:assert not status
for n in names:
 rel=Path(n);src=(R/rel).resolve();dst=(W/rel).resolve()
 assert not rel.is_absolute() and src.is_relative_to(R.resolve()) and dst.is_relative_to(W.resolve())
 assert n.startswith(('experiments/dsn_editorial_v14_20261104/','Paper_DSN/revisions/20261104_dsn2027_release_v14/')) or n in {'Paper_DSN/CURRENT.md','experiments/LATEST_RESEARCH.json'}
 assert src.is_file() and not src.is_symlink() and src.stat().st_size<20_000_000
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
for i in range(0,len(names),50):
 chunk=names[i:i+50]
 subprocess.run(['git','-C',str(W),'add','--force','--',*chunk],capture_output=True,check=True)
 subprocess.run(['git','-C',str(W),'add','--renormalize','--',*chunk],capture_output=True,check=True)
staged=git('diff','--cached','--name-only').splitlines();assert staged and set(staged)==set(names)
queries=''.join(':'+n+'\n' for n in names).encode()
proc=subprocess.run(['git','-C',str(W),'cat-file','--batch'],input=queries,capture_output=True,check=True)
data=proc.stdout;offset=0
for n in names:
 end=data.index(b'\n',offset);head=data[offset:end].split();assert len(head)==3 and head[1]==b'blob';size=int(head[2]);start=end+1
 assert data[start:start+size]==(R/n).read_bytes(),n
 offset=start+size+1
assert offset==len(data)
subprocess.run(['git','-C',str(W),'commit','-m',a.message],capture_output=True,check=True)
head=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==base and not git('status','--porcelain','--untracked-files=all')
if a.push:
 subprocess.run(['git','-c','http.version=HTTP/1.1','-C',str(W),'push','origin','HEAD:main'],capture_output=True,check=True)
 assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]==head
print(json.dumps(dict(commit=head,parent=base,files=len(staged),all_staged_files_byte_matched=True,remote_main_verified=a.push)))
