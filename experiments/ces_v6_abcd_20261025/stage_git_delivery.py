"""Stage only the new experiment prefix in the existing authorized delivery clone."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--expected-base',required=True);a=p.parse_args()
repo=a.repo.resolve();artifact=a.artifact.resolve();prefix='experiments/ces_v6_abcd_20261025'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert Path(git('rev-parse','--show-toplevel').decode().strip()).resolve()==repo
assert git('rev-parse','HEAD').decode().strip()==a.expected_base
assert not git('diff','--cached','--name-only').strip(),'Preserve any staged work; do not reset'
dest=repo/prefix;assert not dest.exists();dest.resolve().relative_to(repo)
manifest=json.loads((artifact/'DELIVERY_FILES.json').read_text());expected={r['path']:r for r in manifest['files']}
expected['DELIVERY_FILES.json']={'sha256':hashlib.sha256((artifact/'DELIVERY_FILES.json').read_bytes()).hexdigest()}
actual={f.relative_to(artifact).as_posix() for f in artifact.rglob('*') if f.is_file()};assert actual==set(expected)
for name,r in expected.items():assert hashlib.sha256((artifact/name).read_bytes()).hexdigest()==r['sha256']
shutil.copytree(artifact,dest)
subprocess.run(['git','-C',str(repo),'add','--',prefix],check=True)
changed=git('diff','--cached','--name-status','-z').split(b'\0');changed=[x.decode() for x in changed if x]
assert len(changed)==2*len(expected)
assert all(changed[i]=='A' and changed[i+1].startswith(prefix+'/') for i in range(0,len(changed),2)),changed[:8]
staged={}
for raw in git('ls-files','--stage','-z','--',prefix).split(b'\0'):
 if not raw:continue
 meta,path=raw.split(b'\t',1);mode,oid,stage=meta.decode().split();assert stage=='0' and mode=='100644'
 staged[path.decode()[len(prefix)+1:]]=oid
assert set(staged)==set(expected)
for name in expected:
 data=(artifact/name).read_bytes();wanted=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert staged[name]==wanted,name
print(json.dumps({'status':'PASS_ONLY_NEW_PREFIX_STAGED_EXACT_BYTES','base':a.expected_base,'files':len(expected),'older_blobs_not_staged_or_deleted':True}))
