"""Publish only explicit bounded paths from the preserved root via a clean archive checkout."""
from pathlib import Path
import argparse,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
p=argparse.ArgumentParser();p.add_argument('--paths-json',type=Path,required=True)
p.add_argument('--message',required=True);p.add_argument('--push',action='store_true');a=p.parse_args()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],stderr=subprocess.PIPE).decode().strip()
assert git('config','--get','remote.origin.url')=='https://github.com/zhouz4884-coder/RevTrace.git'
assert git('branch','--show-current').startswith('codex/')
assert not git('status','--porcelain','--untracked-files=all')
before=git('rev-parse','HEAD')
assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]==before
names=json.loads(a.paths_json.read_text(encoding='utf-8-sig'));assert names and len(names)==len(set(names))
for name in names:
    rel=Path(name);src=(R/rel).resolve(strict=True);dest=(W/rel).resolve()
    assert not rel.is_absolute() and src.is_relative_to(R) and dest.is_relative_to(W)
    assert src.is_file() and not src.is_symlink() and src.stat().st_size<20_000_000
    assert name.startswith(('experiments/dsn_continuity_cost_20261102/','Paper_DSN/revisions/20261102_')) or name in {'Paper_DSN/CURRENT.md','experiments/LATEST_RESEARCH.json'}
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
subprocess.run(['git','-C',str(W),'add','--force','--',*names],check=True,capture_output=True)
subprocess.run(['git','-C',str(W),'add','--renormalize','--',*names],check=True,capture_output=True)
staged=git('diff','--cached','--name-only').splitlines()
assert staged and set(staged).issubset(names)
for name in names:assert subprocess.check_output(['git','-C',str(W),'show',':'+name])==(R/name).read_bytes(),name
subprocess.run(['git','-C',str(W),'commit','-m',a.message],check=True,capture_output=True)
head=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==before
assert not git('status','--porcelain','--untracked-files=all')
if a.push:
    subprocess.run(['git','-c','http.version=HTTP/1.1','-C',str(W),'push','origin','HEAD:main'],check=True)
    assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]==head
print(json.dumps(dict(commit=head,parent=before,files=len(staged),remote_main_verified=a.push,byte_identity_checked=True)))
