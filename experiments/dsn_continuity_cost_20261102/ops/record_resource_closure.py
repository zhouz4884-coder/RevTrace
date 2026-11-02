"""Read-only final process-generation and CUDA release observation."""
from pathlib import Path
import json
from remote import Remote,E
plan=json.loads((E/'cost/plan_v1/PLAN.json').read_bytes())
handle=json.loads((E/'cost/COST_NN_V1_HANDLE.json').read_bytes())
script='C='+repr(dict(cells=plan['cells'],controller=handle))+'\n'+r'''
from pathlib import Path
import datetime,json,subprocess
def proc(pid,ticks):
 p=Path('/proc')/str(pid)/'stat'
 if not p.exists():return dict(pid=pid,original_start_ticks=ticks,original_process_alive=False,state='absent')
 s=p.read_text().split();same=int(s[21])==ticks
 return dict(pid=pid,original_start_ticks=ticks,current_start_ticks=int(s[21]),same_generation=same,state=s[2],original_process_alive=same and s[2] not in ('Z','X'))
rows=[]
for cell in C['cells']:
 raw=Path(cell['out']);members=[]
 for p in sorted(raw.glob('owner_e*/owner_events.jsonl')):
  for line in p.read_text().splitlines():
   row=json.loads(line)
   if row.get('kind')=='worker_started':members.append(proc(row['pid'],row['start_ticks']))
 for line in (raw/'supervisor.jsonl').read_text().splitlines():
  row=json.loads(line)
  if row.get('kind')=='owner_started':members.append(proc(row['pid'],row['start_ticks']))
 assert members and not any(r['original_process_alive'] for r in members),cell['cell_id']
 rows.append(dict(cell_id=cell['cell_id'],members=members))
controller=proc(C['controller']['pid'],C['controller']['start_ticks']);assert not controller['original_process_alive']
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True).strip();assert not gpu
print(json.dumps(dict(gate='PASS_NN16_GENERATION_BOUND_OWNERS_WORKERS_AND_CUDA_RELEASED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cells=len(rows),controller=controller,CUDA_compute_processes=gpu,owned_processes=rows,scope='Read-only post-completion resource observation; no process signalled or restarted')))
'''
with Remote() as c:
 raw=c.python(script);r=json.loads(raw);p=E/'FINAL_RESOURCE_CLOSURE.json';assert not p.exists();p.write_bytes(raw)
 print(json.dumps({k:v for k,v in r.items() if k!='owned_processes'}))
