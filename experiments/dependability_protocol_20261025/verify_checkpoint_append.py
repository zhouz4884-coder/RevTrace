from pathlib import Path
import argparse,concurrent.futures,hashlib,json,subprocess,urllib.request
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';prefix='experiments/dependability_protocol_20261025/'
ap=argparse.ArgumentParser();ap.add_argument('--version',type=int,required=True);a=ap.parse_args();v=a.version
d=json.loads((W/f'GITHUB_CHECKPOINT_DELTA_PREPUSH_v{v}.json').read_text());commit=d['commit']
assert subprocess.check_output(['git','ls-remote','https://github.com/zhouz4884-coder/RevTrace.git','refs/heads/main'],text=True).split()[0]==commit
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
def entries(ref):
 out={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:meta,path=row.split(b'\t',1);out[path]=meta
 return out
before=entries(d['base']);after=entries(commit);assert all(after.get(k)==val for k,val in before.items())
names=[f'CHECKPOINT_DELTA_v{v}.json','figures/causal_protocol_v1.pdf','ROLE_PROBE_CPU_GATE_v1.json','audit_n5_formal_v1.py']
if v>=4:names=[f'CHECKPOINT_DELTA_v{v}.json','N5_NORMAL_DECISION_v1.json','N5_NORMAL_REPORT.zh.md','n5_postnormal_collected_v1/postnormal_cpu_v1/SUMMARY.json']
def verify(name):
 try:
  url='https://raw.githubusercontent.com/zhouz4884-coder/RevTrace/'+commit+'/'+prefix+name
  with urllib.request.urlopen(url,timeout=20) as r:raw=r.read(2_000_000)
  assert raw==(G/prefix/name).read_bytes();return dict(path=name,status='PASS_REMOTE_RAW_BYTES',sha256=hashlib.sha256(raw).hexdigest())
 except Exception as e:return dict(path=name,status='READ_OR_BYTE_CHECK_FAILED',error_type=type(e).__name__)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:checks=list(pool.map(verify,names))
out=dict(commit=commit,status='PASS_REF_TREE_AND_ALL_BOUNDED_RAW' if all(r['status']=='PASS_REMOTE_RAW_BYTES' for r in checks) else 'REF_TREE_PASS_PARTIAL_RAW_VERIFICATION',
 previous_entries_preserved=len(before),added_files=len(after)-len(before),checks=checks,anonymous_mirror_verified=False,manuscript_unchanged=True,goal_complete=False)
target=W/f'GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v{v}.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
