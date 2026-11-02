"""Stage the original immutable c4 checker as an explicit dependency."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,P
R=E.parents[1];old=R/'experiments/dsn_native_refinement_20261030/packages'
manifest=old/'TRACE_SOURCE_v2.json';bundle=old/'TRACE_SOURCE_v2.bundle'
m=json.loads(manifest.read_bytes());assert m['source_commit']=='c4dde9ea9c7abf80fae084bc2293e193262c71e6'
C=dict(source=P+'/original_c4_source',manifest=P+'/ORIGINAL_C4_SOURCE_v2.json',bundle=P+'/ORIGINAL_C4_SOURCE_v2.bundle',commit=m['source_commit'],manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest())
script='C='+repr(C)+'\n'+r'''
from pathlib import Path
import hashlib,json,subprocess
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['manifest'])==C['manifest_sha256'] and sha(C['bundle'])==C['bundle_sha256']
s=Path(C['source'])
if not s.exists():
 subprocess.run(['git','clone','-q','--no-checkout',C['bundle'],str(s)],check=True)
 subprocess.run(['git','-C',str(s),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(s),'checkout','-q',C['commit']],check=True)
def git(*a):return subprocess.check_output(['git','-C',str(s),*a],text=True).strip()
m=json.loads(Path(C['manifest']).read_bytes())
assert git('rev-parse','HEAD')==C['commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (s/r['path']).stat().st_size==r['bytes'] and sha(s/r['path'])==r['sha256']
print(json.dumps(dict(gate='PASS_ORIGINAL_C4_COMPLETE_CLEAN_DEPENDENCY',files=len(m['files']),**C)))
'''
with Remote() as c:
 c.put(manifest,C['manifest']);c.put(bundle,C['bundle']);raw=c.python(script)
 p=E/'cost/C4_DEPENDENCY_STAGE.json';assert not p.exists();p.write_bytes(raw);print(raw.decode())
