from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;S=W/'runtime'
git=lambda *a:subprocess.check_output(['git','-C',str(S),*a])
assert not git('status','--porcelain').strip()
commit=git('rev-parse','HEAD').decode().strip();files=[]
for n in git('ls-files').decode().splitlines():
 p=S/n;data=p.read_bytes();assert data==git('show',commit+':'+n),n
 files.append({'path':n,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
M=W/'SOURCE_MANIFEST.json';assert not M.exists()
M.write_text(json.dumps({'code_commit':commit,'baseline':'e45c66475ba1173a98b49b8c9e62f3e8cb45b333','files':files},indent=2)+'\n')
archive=W/'SOURCE_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
 for row in files:tf.add(S/row['path'],arcname='runtime/'+row['path'])
 tf.add(M,arcname='runtime/SOURCE_MANIFEST.json')
 for n in ['PROTOCOL.md','USER_PROTOCOL.txt','run_B_operator.py','fit_v6_profiles.py','audit_v6.py','audit_closed_helpers_v2.py','summarize_closed.py']:
  tf.add(W/n,arcname=n)
print(json.dumps({'source_commit':commit,'files':len(files),'manifest_sha256':hashlib.sha256(M.read_bytes()).hexdigest(),
 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size}))
