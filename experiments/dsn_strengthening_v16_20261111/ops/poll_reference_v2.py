"""Read only the exact registered reference PID; timeout is not worker death."""
from pathlib import Path
import datetime,hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/REFERENCE_FULL4_V2'
h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);identity=dict(pid=C['pid'],expected_start_ticks=C['start_ticks'],exists=p.exists())
if p.exists():
 fields=(p/'stat').read_text().rsplit(')',1)[1].split();identity.update(state=fields[0],start_ticks=int(fields[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest())
 identity['same_generation']=identity['start_ticks']==C['start_ticks'];identity['same_command']=identity['cmdline_sha256']==C['cmdline_sha256'];identity['active_owned_process']=identity['same_generation'] and identity['same_command'] and identity['state'] not in ('Z','X')
identity.setdefault('active_owned_process',False)
out=Path(C['out']);records={}
for n in ['MODEL_READY.json','PROGRESS.json','GATE.json','SUMMARY.json','FAILURE.json']:
 q=out/n
 if q.exists():
  raw=q.read_bytes()
  try:records[n]=json.loads(raw)
  except json.JSONDecodeError:records[n]=dict(write_in_progress=True,bytes=len(raw))
for sid in (out/'sources').iterdir() if (out/'sources').exists() else []:
 q=sid/'LAST_ORIGINAL_INPUT_continuous.json'
 if q.exists():
  x=json.loads(q.read_bytes());records.setdefault('latest_original_edges',[]).append(dict(source=sid.name,frontier=x.get('end',x.get('frontier'))))
log=Path(C['log']);tail=''
if log.exists():
 with log.open('rb') as f:
  f.seek(max(0,log.stat().st_size-2200));tail=f.read().decode(errors='replace')
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw','--format=csv,noheader'],text=True).strip()
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),process=identity,records=records,log_tail=tail,gpus=gpus,compute_owners=owners)))
'''
with m.Remote() as c:raw=c.python(script,timeout=30)
x=json.loads(raw);poll=D/('POLL_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json');poll.write_bytes(raw+b'\n')
for k in ['SUMMARY.json','MODEL_READY.json']:
 if k in x['records']:
  item=x['records'][k]
  x['records'][k]={a:item[a]for a in item if a in {'status','actual_NN_source_commit','model_load_seconds','expected_sources','completed_sources','ledger','source_outcomes','original_warmup'}}
  if 'source_outcomes' in x['records'][k]:
   x['records'][k]['source_outcomes']=[dict(source_id=r['source_id'],all_equal=r['all_equal'],comparisons=len(r['comparisons'])) for r in x['records'][k]['source_outcomes']]
  if 'original_warmup' in x['records'][k]:
   w=x['records'][k]['original_warmup'];x['records'][k]['original_warmup']={a:w[a]for a in ('seconds','neural_C_confirmed','reset_to_genesis')}
print(json.dumps(x,ensure_ascii=True))
