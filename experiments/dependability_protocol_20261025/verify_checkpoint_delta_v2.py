from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';prefix='experiments/dependability_protocol_20261025/'
d=json.loads((W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v2.json').read_text());commit=d['commit']
ref=subprocess.check_output(['git','ls-remote','https://github.com/zhouz4884-coder/RevTrace.git','refs/heads/main'],text=True).split()[0];assert ref==commit
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
def entries(ref):
 out={}
 for r in git('ls-tree','-r','-z',ref).split(b'\0'):
  if r:
   meta,name=r.split(b'\t',1);out[name]=meta
 return out
before=entries(d['base']);after=entries(commit);assert all(after.get(k)==v for k,v in before.items())
def verify(name):
 url='https://raw.githubusercontent.com/zhouz4884-coder/RevTrace/'+commit+'/'+prefix+name
 try:
  with urllib.request.urlopen(url,timeout=20) as r:data=r.read(2_000_000)
  assert data==(G/prefix/name).read_bytes()
  return dict(path=prefix+name,status='PASS_REMOTE_RAW_BYTES',sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:return dict(path=prefix+name,status='FAILED_READ_OR_MISMATCH',error_type=type(e).__name__)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:checks=list(p.map(verify,['CHECKPOINT_DELTA_v2.json','UNIFIED_FAULT_MATRIX_v1.md','figures/cost_boundary_v1.pdf']))
result=dict(commit=commit,main_ref_verified=True,previous_entries_preserved=len(before),added_files=len(after)-len(before),checks=checks,
 status='PASS_REF_ADDITIVE_TREE_AND_BOUNDED_RAW' if all(c['status']=='PASS_REMOTE_RAW_BYTES' for c in checks) else 'REF_TREE_PASS_PARTIAL_RAW_VERIFICATION',
 anonymous_mirror_verified=False,original_manuscript_unchanged=True,combined_goal_complete=False)
out=W/'GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v2.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
