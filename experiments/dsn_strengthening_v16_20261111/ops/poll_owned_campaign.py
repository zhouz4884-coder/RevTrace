"""Compact read-only status for an explicitly registered owned controller."""
from pathlib import Path
import argparse,datetime,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True,choices=['CONFIRM_NEW2_FULL_READY_V1','CONFIRM_LAST4_FULL_READY_V1']);a=ap.parse_args();D=E/'launch_ops'/a.tag;h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);ident=dict(pid=C['pid'],exists=p.exists(),active_owned_process=False)
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();ident.update(state=f[0],start_ticks=int(f[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest());ident['active_owned_process']=ident['start_ticks']==C['start_ticks'] and ident['cmdline_sha256']==C['cmdline_sha256'] and f[0]not in('Z','X')
out=Path(C['out']);records={}
for n in ['PROGRESS.json','GATE.json','SUMMARY.json']:
 q=out/n
 if q.exists():
  try:x=json.loads(q.read_bytes())
  except json.JSONDecodeError:records[n]={'write_in_progress':True};continue
  records[n]={k:x[k]for k in x if k in {'status','completed','planned','current','completed_trials','planned_trials','failure','comparison_bank_indices'}}
q=out/'PARTIAL_RESULTS.json'
if q.exists():
 try:rows=json.loads(q.read_bytes())
 except json.JSONDecodeError:rows=[]
 records['completed_cells']=[dict(cell_id=r['cell_id'],strategy=r['strategy'],source_id=r.get('source_id'),repeat=r['repeat'],primary={k:r['primary'].get(k)for k in ('offered_audio_seconds','dual_deadline_audio_credit_seconds','complete_coverage_and_original_quantile_pass')})for r in rows]
log=Path(C['log']);tail=''
if log.exists():
 with log.open('rb')as f:f.seek(max(0,log.stat().st_size-1500));tail=f.read().decode(errors='replace')
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu,power.draw','--format=csv,noheader'],text=True).strip();owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controller=ident,records=records,gpus=gpus,compute_owners=owners,log_tail=tail)))
'''
with m.Remote()as c:raw=c.python(script,timeout=30)
(D/('POLL_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')).write_bytes(raw+b'\n');print(raw.decode())
