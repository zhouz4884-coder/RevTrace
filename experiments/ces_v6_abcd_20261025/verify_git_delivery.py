"""Prove additive commit and exact new bytes; remote head checked separately."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--base',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prefix='experiments/ces_v6_abcd_20261025/'
def git(*args):return subprocess.check_output(['git','-C',str(a.repo),*args])
def tree(ref):
 out={}
 for raw in git('ls-tree','-r','-z',ref).split(b'\0'):
  if raw:
   meta,path=raw.split(b'\t',1);out[path.decode()]=meta.decode().split()[2]
 return out
old,new=tree(a.base),tree('HEAD');assert all(new.get(p)==oid for p,oid in old.items()),'Earlier evidence changed'
files={f.relative_to(a.artifact).as_posix():f for f in a.artifact.rglob('*') if f.is_file()}
added=set(new)-set(old);assert added=={prefix+n for n in files}
for name,path in files.items():
 data=path.read_bytes();oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert new[prefix+name]==oid,name
assert git('rev-list','--parents','-n','1','HEAD').decode().strip().split()[1:]==[a.base]
report={'status':'PASS_ADDITIVE_COMMIT_AND_ALL_DELIVERED_BYTES','base':a.base,'commit':git('rev-parse','HEAD').decode().strip(),'old_blobs_preserved':len(old),'new_files_verified':len(files),'artifact_manifest_sha256':hashlib.sha256((a.artifact/'DELIVERY_FILES.json').read_bytes()).hexdigest(),'remote_publication_not_verified_by_this_local_check':True}
assert not a.output.exists();a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
