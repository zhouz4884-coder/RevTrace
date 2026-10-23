"""Commit and freeze actual executable source bytes; never edits frozen SDK."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,sys
W=Path(__file__).resolve().parent;S=W/'runtime'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a]).decode().strip()
git('add','--','.gitignore','src','scripts','tests')
git('-c','user.name=Research Artifact','-c','user.email=artifact@invalid.example','commit','-q','-m','Implement bounded causal evidence planning with sealed operation choice and paid strict fallback')
files=[{'path':p,'sha256':hashlib.sha256((S/p).read_bytes()).hexdigest()} for p in git('ls-files').splitlines()]
meta={'code_commit':git('rev-parse','HEAD'),'parent_sdk':'2bc71af5457de5d065ff9e771d2fad428c5c6ed9',
 'schema':'CES-source-v1','files':files}
(S/'SOURCE_MANIFEST.json').write_text(json.dumps(meta,indent=2)+'\n')
archive=W/('runtime_v'+(sys.argv[1] if len(sys.argv)>1 else '1')+'.tar.gz');assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
 for r in files:tf.add(S/r['path'],arcname=r['path'],recursive=False)
 tf.add(S/'SOURCE_MANIFEST.json',arcname='SOURCE_MANIFEST.json')
print(json.dumps({'code_commit':meta['code_commit'],'files':len(files),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
