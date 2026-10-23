"""Add only the audited CES prefix; preserve every existing remote blob."""
from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;S=W/'delivery_final';G=W.parent/'online_admission_20261022/git_delivery_stage_v1'
prefix='experiments/causal_evidence_scheduling_20261023/'
def git(*a,input=None):return subprocess.check_output(['git','-c','credential.helper=manager','-c','http.version=HTTP/1.1','-C',str(G),*a],input=input).decode().strip()
manifest=json.loads((S/'MANIFEST.json').read_text());assert manifest['research_complete'] and manifest['formal_cells']==180
actual={p.relative_to(S).as_posix():p for p in S.rglob('*') if p.is_file()}
assert set(actual)=={r['path'] for r in manifest['files']}|{'MANIFEST.json'}
for r in manifest['files']:
 raw=actual[r['path']].read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
base=git('ls-remote','origin','refs/heads/main').split()[0]
assert not git('diff','--cached','--name-only')
if git('rev-parse','HEAD')!=base:
 git('fetch','--filter=blob:none','origin','main')
 assert git('rev-parse','FETCH_HEAD')==base
 oldhead=git('rev-parse','HEAD');git('merge-base','--is-ancestor',oldhead,base)
 git('update-ref','refs/heads/main',base,oldhead)
old={}
for row in git('ls-tree','-r',base).splitlines():
 m,p=row.split('\t',1);mode,kind,oid=m.split();assert kind=='blob';old[p]=(mode,oid)
assert not any(p.startswith(prefix) for p in old),'Existing CES prefix requires separate reconciliation, never overwrite'
D=G/prefix;assert not D.exists();shutil.copytree(S,D)
git('read-tree',base);git('add','--',prefix)
staged={}
for row in git('ls-files','--stage').splitlines():
 m,p=row.split('\t',1);mode,oid,level=m.split();assert level=='0';staged[p]=(mode,oid)
assert all(staged.get(p)==v for p,v in old.items())
assert set(staged)-set(old)=={prefix+rel for rel in actual}
for rel,p in actual.items():
 raw=p.read_bytes();oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert staged[prefix+rel]==('100644',oid)
tree=git('write-tree','--missing-ok');commit=git('-c','user.name=Research Artifact','-c','user.email=artifact@invalid.example','commit-tree',tree,'-p',base,input=b'Archive bounded CES implementation, strong-baseline formal evidence and audited contribution decision\n')
git('update-ref','refs/heads/main',commit,base)
record={'status':'PASS_ADDITIVE_CES_PREPUSH','base':base,'commit':commit,'tree':tree,'prior_blobs_preserved':len(old),
 'CES_files':len(actual),'manifest_sha256':hashlib.sha256((S/'MANIFEST.json').read_bytes()).hexdigest()}
(W/'GITHUB_PREPUSH.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
git('-c','http.postBuffer=524288000','-c','http.lowSpeedLimit=0','push','origin','HEAD:refs/heads/main')
assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
(W/'GITHUB_PUSH.json').write_text(json.dumps(dict(record,status='PUSHED_REF_VERIFIED_CONTENT_VERIFICATION_PENDING'),indent=2)+'\n')
