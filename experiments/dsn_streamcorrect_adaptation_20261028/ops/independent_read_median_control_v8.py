"""Read bounded existing control records only; no model, GPU, or remote writes."""
import datetime
import json
import pathlib
import shlex
import sys

T=pathlib.Path(__file__).resolve().parents[1]
REMOTE=r'''
import datetime,hashlib,json,pathlib,subprocess
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028';P=B/'projects/revtrace_dsn_streamcorrect_20261028'
r=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='bounded existing evidence read only; no model/GPU',records={},sources={})
for relative in ['native_campaign_v6_controller/GATE.json','native_campaign_v6_controller/SUMMARY.json',
 'median_gpu_gate_v7/GATE.json','median_gpu_gate_v7/SUMMARY.json','MEDIAN_GPU_GATE_v7_HANDLE.json',
 'median_gpu_gate_v8/GATE.json','median_gpu_gate_v8/SUMMARY.json','median_gpu_gate_v8/PRELAUNCH_RECORD.json',
 'median_gpu_gate_v8/ENVIRONMENT.json','median_gpu_gate_v8/ACTUAL_NATIVE_INPUT_DOMAIN.json','MEDIAN_GPU_GATE_v8_HANDLE.json']:
 p=O/relative
 if p.exists():
  s=p.stat()
  if s.st_size<=262144:r['records'][relative]=dict(bytes=s.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),value=json.loads(p.read_text()))
  else:r['records'][relative]=dict(bytes=s.st_size,content_omitted=True)
for version in ['v6','v7','v8']:
 p=P/('SOURCE_'+version+'.json');root=P/('runtime_source_'+version)
 if p.exists():
  m=json.loads(p.read_text());row=dict(commit=m['source_commit'],manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),files=len(m['files']))
  if root.exists():
   row['actual_git_head']=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
   row['actual_git_clean']=not bool(subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip())
   for n in ['native_triton_compat.py','native_bridge.py','run_median_gpu_gate.py']:
    q=root/n
    if q.exists():row[n+'_sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
  r['sources'][version]=row
for name in ['median_gpu_gate_v8.log','native_campaign_v6_controller.log']:
 p=O/name
 if p.exists():
  with p.open('rb') as f:f.seek(max(0,p.stat().st_size-5000));r[name+'_tail']=f.read().decode(errors='replace')
print(json.dumps(r))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    _,stdout,stderr=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python -B -c '+shlex.quote(REMOTE),timeout=40)
    data=stdout.read();diagnostic=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Bounded evidence read failed; observation failure is not worker death')
    result=json.loads(data);folder=T/'independent_triton_review_v7';folder.mkdir(exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=folder/('CONTROL_EVIDENCE_'+stamp+'.json');path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(evidence=str(path),**result),indent=2))
finally:c.close()
