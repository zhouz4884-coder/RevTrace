"""Index-only additive Git delivery; preserve every old tracked blob/mode."""
from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';prefix='experiments/dependability_protocol_20261025/'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='d800523139d30486ca9158f06e750a2d80fcb9fc'
assert git('ls-tree','-r','--name-only',base,'--',prefix)==b''
def entries(ref):
 out={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();out[name.decode()]=(mode,oid)
 return out
before=entries(base)
for k,v in [('user.name','Research Artifact'),('user.email','artifact@example.invalid'),('core.autocrlf','false')]:
 subprocess.run(['git','-C',str(G),'config',k,v],check=True)
subprocess.run(['git','-C',str(G),'add','--',prefix],check=True)
changes=git('diff','--cached','--name-status','-z').split(b'\0');changes=[x for x in changes if x]
assert len(changes)==808*2
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].decode().startswith(prefix)
tree=git('write-tree').decode().strip();after=entries(tree)
assert all(after.get(path)==v for path,v in before.items()),'old content changed'
index=json.loads((G/prefix/'CHECKPOINT_MANIFEST.json').read_text());checks=[]
paths=[r['path'] for r in index['files']]+['CHECKPOINT_MANIFEST.json']
for name in paths:
 data=(G/prefix/name).read_bytes();oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()
 assert after[prefix+name][1]==oid,'line-ending/byte normalization changed source'
 checks.append(dict(path=prefix+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob=oid.decode()))
check=subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],capture_output=True,text=True)
if check.returncode:
 # Raw failed-test XML and byte-frozen historical fixtures must not be edited
 # to satisfy a formatting checker. Reject any OTHER new whitespace warning.
 allowed={prefix+n for n in ['CPU_N5_WIRING_v1.xml','CPU_N5_WIRING_v2.xml','CPU_N5_WIRING_v3.xml']}
 allowed.update(prefix+f'{r}/tests/test_r7_efsc_artifacts.py' for r in ['runtime','runtime_n5','runtime_n5_v2','runtime_n5_v3'])
 warned={line.split(':',1)[0] for line in check.stdout.splitlines() if line.startswith(prefix)}
 assert check.returncode==2 and warned==allowed,check.stdout
subprocess.run(['git','-C',str(G),'commit','-m','Archive bounded dependability protocol evidence and N5 development checkpoint; independent validation pending'],check=True)
commit=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==base
record=dict(status='PASS_ADDITIVE_TREE_AND_BYTE_VERIFICATION_BEFORE_PUSH',base=base,commit=commit,
 old_tracked_entries_preserved=len(before),added_files=len(checks),files=checks,
 manuscript_modified=False,anonymous_mirror_verified=False,goal_complete=False,
 preserved_raw_whitespace_warnings=check.stdout if check.returncode else None)
(W/'GITHUB_CHECKPOINT_PREPUSH_v1.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'}))
