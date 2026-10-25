from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;S=W/'runtime_D';git=lambda *a:subprocess.check_output(['git','-C',str(S),*a])
assert not git('status','--porcelain').strip()
commit=git('rev-parse','HEAD').decode().strip();files=[]
for name in git('ls-files').decode().splitlines():
 data=(S/name).read_bytes();assert data==git('show',commit+':'+name),name
 files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
M=W/'D_SOURCE_MANIFEST.json';assert not M.exists();M.write_text(json.dumps({'code_commit':commit,'baseline':'e135683d5bb681bf74f507375352e62b53604574','files':files},indent=2)+'\n')
T=W/'SOURCE_D.tar.gz';assert not T.exists()
with tarfile.open(T,'w:gz') as tf:
 for row in files:tf.add(S/row['path'],arcname='runtime_D/'+row['path'])
 tf.add(M,arcname='runtime_D/SOURCE_MANIFEST.json')
print(json.dumps({'commit':commit,'files':len(files),'manifest_sha256':hashlib.sha256(M.read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'bytes':T.stat().st_size}))
