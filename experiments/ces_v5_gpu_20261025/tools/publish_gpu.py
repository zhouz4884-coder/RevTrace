"""Add only the completed bounded GPU-stage prefix; never stage root edits."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time
W=Path(__file__).resolve().parent;D=W/'delivery'
G=W.parent/'online_admission_20261022/git_delivery_stage_v1'
prefix='experiments/ces_v5_gpu_20261025/'


def git(*args,input=None):
    return subprocess.check_output(['git','-c','credential.helper=manager','-c','http.version=HTTP/1.1',
        '-C',str(G),*args],input=input,timeout=180).decode().strip()


def tree(ref):
    result={}
    for line in git('ls-tree','-r',ref).splitlines():
        meta,path=line.split('\t',1);mode,kind,oid=meta.split();assert kind=='blob'
        result[path]=(mode,oid)
    return result


m=json.loads((D/'MANIFEST.json').read_text())
assert m['status']=='COMPLETE_AUDITED_BOUNDED_V5_GPU_STAGE'
assert m['online_cells']==48 and m['GPU_queue_closed'] and m['manuscript_edits'] is False
files={p.relative_to(D).as_posix():p for p in D.rglob('*') if p.is_file()}
assert set(files)=={r['path'] for r in m['files']}|{'MANIFEST.json'}
for r in m['files']:assert r['sha256']==hashlib.sha256(files[r['path']].read_bytes()).hexdigest()
assert not git('diff','--cached','--name-only')
base=git('ls-remote','origin','refs/heads/main').split()[0]
assert base=='c6d5ece015c88fcc58963410f7f80a2d2248f109','Remote changed; inspect and preserve the new base before delivery'
assert git('rev-parse','HEAD')==base
old=tree(base);assert not any(p.startswith(prefix) for p in old)
target=G/prefix;assert not target.exists();shutil.copytree(D,target)
git('read-tree',base);git('add','--force','--',prefix)
index={}
for line in git('ls-files','--stage').splitlines():
    meta,path=line.split('\t',1);mode,oid,stage=meta.split();assert stage=='0';index[path]=(mode,oid)
assert all(index.get(p)==v for p,v in old.items())
assert set(index)-set(old)=={prefix+r for r in files}
for rel,p in files.items():
    raw=p.read_bytes();oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert index[prefix+rel]==('100644',oid),rel
newtree=git('write-tree','--missing-ok')
commit=git('-c','user.name=Research Artifact','-c','user.email=artifact@invalid.example',
    'commit-tree',newtree,'-p',base,input=b'Archive bounded CES V5 GPU pilot, complete negative results and independent CPU diagnosis\n')
git('update-ref','refs/heads/main',commit,base)
record={'base':base,'commit':commit,'tree':newtree,'prior_blobs_preserved':len(old),'new_files':len(files),
    'manifest_sha256':hashlib.sha256((D/'MANIFEST.json').read_bytes()).hexdigest(),
    'scope':'additive bounded V5 GPU pilot only; no manuscript edits','time_unix':time.time()}
(W/'GITHUB_PREPUSH.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
git('-c','http.postBuffer=524288000','-c','http.lowSpeedLimit=0','push','origin','HEAD:refs/heads/main')
assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
published=tree(commit);assert all(published.get(p)==v for p,v in old.items())
assert set(published)-set(old)=={prefix+r for r in files}
for rel,p in files.items():
    raw=p.read_bytes();oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert published[prefix+rel]==('100644',oid)
assert git('rev-parse',commit+'^')==base
record.update(status='REMOTE_REF_AND_ADDITIVE_CONTENT_ADDRESSED_TREE_VERIFIED',
    verified_remote_ref=True,exact_new_blob_hashes=len(files),all_prior_blobs_preserved=len(old),
    verification_route='Native Git fresh remote ref and content-addressed commit/tree; byte-exact new blob hashes',
    verification_limit='Does not mean every remote blob was separately downloaded after push')
(W/'FINAL_DELIVERY_VERIFIED.json').write_text(json.dumps(record,indent=2)+'\n')
state=json.loads((W/'ACTIVE_STATE.json').read_text());state.update(GitHub_commit=commit,GitHub_delivery='VERIFIED',
    phase='COMPLETE_AUDITED_BOUNDED_V5_GPU_STAGE_AND_GITHUB_DELIVERY',GPU_queue_closed=True)
(W/'ACTIVE_STATE.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(record),flush=True)
