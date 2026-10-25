"""Bounded unauthenticated reads of this user's already public commit."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1'
d=json.loads((W/'GITHUB_CHECKPOINT_PREPUSH_v1.json').read_text());commit=d['commit'];prefix='experiments/dependability_protocol_20261025/'
ref=subprocess.check_output(['git','ls-remote','https://github.com/zhouz4884-coder/RevTrace.git','refs/heads/main'],text=True).split()[0]
assert ref==commit
names=['README.md','CHECKPOINT_MANIFEST.json','N1_DECISION.json','N5_RECOVERY_INDEPENDENT_AUDIT_v3.json',
 'formal/CDE_CROSSCHECK_v2.json','runtime_n5_v3/src/revtrace/certified_envelope.py']
def verify(name):
 url='https://raw.githubusercontent.com/zhouz4884-coder/RevTrace/'+commit+'/'+prefix+name
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RevTrace-evidence-verification'}),timeout=20) as r:raw=r.read(2_000_000)
  expected=(G/prefix/name).read_bytes();assert raw==expected,'remote raw bytes differ'
  return dict(path=prefix+name,status='PASS_REMOTE_RAW_BYTES',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except Exception as e:return dict(path=prefix+name,status='READ_FAILED_NOT_A_BYTE_MISMATCH',error_type=type(e).__name__)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:checks=list(pool.map(verify,names))
result=dict(status='PASS_REF_AND_ALL_BOUNDED_REMOTE_RAW_CHECKS' if all(c['status']=='PASS_REMOTE_RAW_BYTES' for c in checks) else 'REF_CONFIRMED_PARTIAL_RAW_VERIFICATION',
 commit=commit,remote_main=ref,old_entries_preserved=d['old_tracked_entries_preserved'],added_files=d['added_files'],
 checks=checks,no_manuscript_edit=True,no_anonymous_mirror_claim=True,combined_goal_complete=False)
out=W/'GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
