"""Freeze a new owned source tree without altering the legacy checkout HEAD."""
from pathlib import Path
import argparse,hashlib,json,subprocess

E=Path(__file__).resolve().parents[1];R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
p.add_argument('--name',required=True);p.add_argument('--predecessor');a=p.parse_args()
source=a.source.resolve(strict=True)
assert source.is_relative_to(E.resolve()) and source!=E.resolve()
assert a.name.replace('_','').isalnum()
package=E/'packages';package.mkdir(exist_ok=True)
manifest=package/(a.name+'_SOURCE.json');bundle=package/(a.name+'_SOURCE.bundle')
assert not manifest.exists() and not bundle.exists()
def git(c,*args):return subprocess.check_output(['git','-C',str(c),*args],stderr=subprocess.PIPE).decode().strip()
if not (source/'.git').exists():
    subprocess.run(['git','init','-q','-b','codex/'+a.name.lower(),str(source)],check=True)
    subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
    subprocess.run(['git','-C',str(source),'config','user.name','RevTrace Research'],check=True)
    subprocess.run(['git','-C',str(source),'config','user.email','research@revtrace.local'],check=True)
    (source/'.gitattributes').write_bytes(b'* -text\n')
    subprocess.run(['git','-C',str(source),'add','--force','--all'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(source),'commit','-q','-m','Freeze '+a.name+' source'],check=True,capture_output=True)
assert git(source,'config','--get','core.autocrlf')=='false'
assert not git(source,'status','--porcelain','--untracked-files=all')
commit=git(source,'rev-parse','HEAD');rows=[]
for name in git(source,'ls-files').splitlines():
    f=source/name;assert f.is_file() and not f.is_symlink()
    b=f.read_bytes();assert len(b)<5_000_000
    assert subprocess.check_output(['git','-C',str(source),'show',commit+':'+name])==b
    rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
data=dict(code_commit=commit,source_commit=commit,predecessor_source_commit=a.predecessor,
          files=rows,scope='Complete frozen execution source; archive publication commit is separate.')
manifest.write_bytes((json.dumps(data,indent=2)+'\n').encode())
subprocess.run(['git','-C',str(source),'bundle','create',str(bundle),'--all'],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),commit+':refs/archive/revtrace/dsn_v11_closure_20261102/'+a.name.lower()],check=True,capture_output=True)
assert git(R,'cat-file','-t',commit)=='commit'
assert git(R,'rev-parse','HEAD')=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
print(json.dumps(dict(code_commit=commit,files=len(rows),source=str(source),manifest=str(manifest),
                     manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),bundle=str(bundle),
                     bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest())))
