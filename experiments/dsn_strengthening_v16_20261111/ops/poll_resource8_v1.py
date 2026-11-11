"""Bounded exact-PID live readback of the grouped resource comparison."""
from pathlib import Path
import datetime,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/RESOURCE8_V1';h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);identity=dict(pid=C['pid'],exists=p.exists(),active_owned_process=False)
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();identity.update(state=f[0],start_ticks=int(f[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest());identity['active_owned_process']=identity['start_ticks']==C['start_ticks'] and identity['cmdline_sha256']==C['cmdline_sha256'] and f[0]not in('Z','X')
out=Path(C['out']);records={}
for n in ['PROGRESS.json','GATE.json','SUMMARY.json']:
 q=out/n
 if q.exists():
  try:x=json.loads(q.read_bytes())
  except json.JSONDecodeError:records[n]={'write_in_progress':True};continue
  records[n]={k:x[k]for k in x if k in {'status','completed','planned','current','completed_trials','planned_trials','failure','contrasts'}}
q=out/'PARTIAL_RESULTS.json'
if q.exists():
 try:rows=json.loads(q.read_bytes())
 except json.JSONDecodeError:rows=[]
 records['completed_cells']=[dict(cell_id=r['cell_id'],strategy=r['strategy'],source_group_id=r['source_group_id'],repeat=r['repeat'],primary=r.get('primary'),resource_observations=r.get('resource_observations'))for r in rows]
cid=records.get('PROGRESS.json',{}).get('current')
if cid:
 cell=out/'cells'/cid;records['current_cell']=dict(cell_id=cid,origin_exists=(cell/'ORIGIN.json').exists(),gate=json.loads((cell/'GATE.json').read_bytes())if(cell/'GATE.json').exists()else None)
log=Path(C['log']);tail=''
if log.exists():
 with log.open('rb')as f:f.seek(max(0,log.stat().st_size-1600));tail=f.read().decode(errors='replace')
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw','--format=csv,noheader'],text=True).strip();owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controller=identity,records=records,gpus=gpus,compute_owners=owners,log_tail=tail)))
'''
with m.Remote()as c:raw=c.python(script,timeout=30)
(D/('POLL_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')).write_bytes(raw+b'\n')
x=json.loads(raw)
if 'completed_cells'in x['records']:
 x['records']['completed_cells']=[{k:r[k]for k in ('cell_id','strategy','source_group_id','repeat','primary')}for r in x['records']['completed_cells']]
 for row in x['records']['completed_cells']:
  p=row['primary'] or {};row['primary']={k:p[k]for k in ('offered_audio_seconds','dual_deadline_audio_credit_seconds','complete_coverage_and_original_quantile_pass','primary_linear_all_offered_D99','primary_linear_all_offered_C99')if k in p}
print(json.dumps(x))
