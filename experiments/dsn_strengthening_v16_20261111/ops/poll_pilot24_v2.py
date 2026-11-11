"""Bounded live readback of the exact owned 24-trial controller."""
from pathlib import Path
import datetime,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/PILOT24_V2';h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);ident=dict(pid=C['pid'],exists=p.exists(),active_owned_process=False)
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();ident.update(state=f[0],start_ticks=int(f[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest());ident['active_owned_process']=ident['start_ticks']==C['start_ticks'] and ident['cmdline_sha256']==C['cmdline_sha256'] and f[0] not in ('Z','X')
out=Path(C['out']);records={}
for n in ['PROGRESS.json','GATE.json','SUMMARY.json']:
 q=out/n
 if q.exists():
  try:x=json.loads(q.read_bytes())
  except json.JSONDecodeError:records[n]={'write_in_progress':True};continue
  records[n]={k:x[k]for k in x if k in {'status','completed','planned','current','completed_trials','planned_trials','failure','actual_NN_source_commit'}}
q=out/'PARTIAL_RESULTS.json'
if q.exists():
 try:rs=json.loads(q.read_bytes())
 except json.JSONDecodeError:rs=[]
 records['completed_cell_summaries']=[dict(cell_id=r['cell_id'],strategy=r['strategy'],source_id=r['source_id'],repeat=r['repeat'],primary={k:r['primary'].get(k)for k in ['offered_audio_seconds','dual_deadline_audio_credit_seconds','complete_coverage_and_original_quantile_pass']})for r in rs]
 if rs:
  cfg=json.loads((out/'CONFIG.json').read_bytes());first=cfg['cells'][0];ep=Path(first['external_power'])
  if ep.exists():
   firstrow=lastrow=None;count=0
   with ep.open()as f:
    for line in f:
     row=json.loads(line);firstrow=firstrow or row;lastrow=row;count+=1
   if firstrow and lastrow:records['first_cell_inclusive_observation']=dict(cell_id=first['cell_id'],seconds=lastrow['time']-firstrow['time'],samples=count,scope='external both-board observation span including fresh loading, warmup, actual service and physical release; not inference-only or exact Popen timestamp')
pr=records.get('PROGRESS.json',{});cid=pr.get('current')
if cid:
 cell=out/'cells'/cid;records['current_cell']=dict(cell_id=cid,output_exists=cell.exists(),origin_exists=(cell/'ORIGIN.json').exists(),gate=json.loads((cell/'GATE.json').read_bytes()) if (cell/'GATE.json').exists() else None)
 if (cell/'ORIGIN.json').exists():records['current_cell']['origin']=json.loads((cell/'ORIGIN.json').read_bytes())
log=Path(C['log']);tail=''
if log.exists():
 with log.open('rb')as f:f.seek(max(0,log.stat().st_size-1800));tail=f.read().decode(errors='replace')
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw','--format=csv,noheader'],text=True).strip();owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controller=ident,records=records,gpus=gpus,compute_owners=owners,log_tail=tail)))
'''
with m.Remote()as c:raw=c.python(script,timeout=30)
p=D/('POLL_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json');p.write_bytes(raw+b'\n')
x=json.loads(raw);rows=x['records'].get('completed_cell_summaries',[])
if rows:
 x['records']['completed_by_arm']=[dict(strategy=a,n=len(g),offered_audio_s=sum(r['primary']['offered_audio_seconds']for r in g),credit_audio_s=sum(r['primary']['dual_deadline_audio_credit_seconds']for r in g),whole_run_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass']for r in g))for a in sorted({r['strategy']for r in rows}) for g in [[r for r in rows if r['strategy']==a]]]
 x['records'].pop('completed_cell_summaries',None)
print(json.dumps(x))
