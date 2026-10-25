from pathlib import Path
import subprocess,json,hashlib,tarfile
W=Path(__file__).resolve().parent;S=W/'runtime_A';git=lambda *a:subprocess.check_output(['git','-C',str(S),*a])
assert not git('status','--porcelain').strip();commit=git('rev-parse','HEAD').decode().strip();rows=[]
for n in git('ls-files').decode().splitlines():
 p=S/n;b=p.read_bytes();assert b==git('show',commit+':'+n)
 rows.append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
M=W/'A_SOURCE_MANIFEST.json';assert not M.exists();M.write_text(json.dumps({'code_commit':commit,'files':rows},indent=2)+'\n')
p=W/'SOURCE_A.tar.gz';assert not p.exists()
with tarfile.open(p,'w:gz') as t:
 for r in rows:t.add(S/r['path'],arcname='runtime_A/'+r['path'])
 t.add(M,arcname='runtime_A/SOURCE_MANIFEST.json')
print(json.dumps({'commit':commit,'archive_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'files':len(rows)}))
