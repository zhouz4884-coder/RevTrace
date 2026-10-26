from pathlib import Path
import subprocess,hashlib,json,tarfile,sys
W=Path(__file__).resolve().parent;R=W/'runtime'
tag=sys.argv[1] if len(sys.argv)>1 else 'v1'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
if not (R/'.git').exists():
    git('init','-b','codex/composed-kernel-20261026')
    git('config','user.name','Research Artifact');git('config','user.email','artifact@example.invalid')
    git('config','core.autocrlf','false')
names=[str(p.relative_to(R)).replace('\\','/') for p in R.rglob('*') if p.is_file()
    and not set(p.relative_to(R).parts)&{'.git','__pycache__','.pytest_cache'}
    and p.suffix not in ['.pyc'] and p.name!='SOURCE_MANIFEST.json']
git('add','--',*names);git('commit','-m','Freeze composed kernel '+tag)
commit=git('rev-parse','HEAD').decode().strip();files=[]
for name in git('ls-files','-z').decode().split('\0'):
    if not name:continue
    data=(R/name).read_bytes();assert git('cat-file','blob','HEAD:'+name)==data
    files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
m=dict(code_commit=commit,base='408d75624104e7e11af3f0f2832263c632b10ed8',files=files)
dest=W/('SOURCE_'+tag+'.json');assert not dest.exists();dest.write_text(json.dumps(m,indent=2)+'\n')
with tarfile.open(W/('SOURCE_'+tag+'.tar.gz'),'w:gz') as t:
    for f in files:t.add(R/f['path'],arcname='runtime/'+f['path'])
    t.add(dest,arcname='runtime/SOURCE_MANIFEST.json')
print(json.dumps(dict(commit=commit,files=len(files),tag=tag)))
