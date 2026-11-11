"""Read-only phase integration and small source inspection of old raw evidence."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REMOTE = r'''
import datetime,hashlib,json,pathlib,platform
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
base=B/'results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells'
def load(path):return json.loads(path.read_bytes())
def lines(path):return [json.loads(x) for x in path.read_bytes().splitlines() if x]
def identity(path):return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def integrate(rows,start,end):
 by={}
 for gpu in ('0','1'):
  pts=sorted((r['time'],r['watts'][gpu]) for r in rows if gpu in r['watts'])
  assert len(pts)>=2 and pts[0][0]<=start<end<=pts[-1][0]
  value=0.
  for (a,x),(b,y) in zip(pts,pts[1:]):
   lo=max(start,a);hi=min(end,b)
   if hi>lo:
    vl=x+(y-x)*(lo-a)/(b-a);vh=x+(y-x)*(hi-a)/(b-a)
    value+=(vl+vh)/2*(hi-lo)
  by[gpu]=value
 return dict(seconds=end-start,gpu_joules=by,total_joules=sum(by.values()))
out=[]
for fault in ('owner_after_durable','owner_before_durable'):
 for arm in ('conservative','fullcall'):
  for repeat in (0,1):
   cell=base/('SC_FORMAL_SHORT28_v1_BAC009S0908W0369_'+fault+'_'+arm+'_r'+str(repeat))
   ev=lines(cell/'supervisor.jsonl');pw=lines(cell/'power.jsonl');s=load(cell/'SUMMARY.json');re=s['recovery']['events'][0]
   fault_t=re['fault_perf'];death=re['physical_death_confirmed_perf'];ready=re['replacement_ready_perf'];new=re['first_new_model_completed_after_fault_and_certified_consume_perf']
   start=next(r['observed'] for r in ev if r['kind']=='owner_started' and r['owner_epoch']==1)
   worker_starts=[r['event'] for r in ev if r['kind']=='owner_event' and r['event']['kind']=='worker_started' and r['event']['owner_epoch']==1]
   rd=next(r['event'] for r in ev if r['kind']=='owner_event' and r['event']['kind']=='owner_ready' and r['event']['owner_epoch']==1)
   death_row=next(r for r in ev if r['kind']=='owner_group_death_confirmed')
   phases={'fault_to_death':(fault_t,death),'death_to_owner_start':(death,start),'owner_start_to_ready':(start,ready),'ready_to_new_certified':(ready,new),'fault_to_new_certified':(fault_t,new),'origin_to_fault':(s['energy']['origin_perf'],fault_t),'new_certified_to_service_end':(new,s['energy']['service_end_perf']),'whole_service':(s['energy']['origin_perf'],s['energy']['service_end_perf'])}
   integrated={k:integrate(pw,*v) for k,v in phases.items()}
   assert abs(integrated['whole_service']['total_joules']-s['energy']['service']['total_joules'])<1e-6
   worker_rows=[]
   for slot,w in rd['workers'].items():
    ws=next(q for q in worker_starts if q['pid']==w['pid'])
    worker_rows.append(dict(slot=slot,gpu=w['gpu'],pid=w['pid'],worker_start_perf=ws['observed'],sent_perf=w['sent_perf'],model_load_seconds=w['model_load_seconds'],full_load_warmup_seconds=w['full_load_warmup_seconds'],warmup_seconds=w['neural_ready_warmup']['seconds'],inferred_constructor_begin_perf=w['sent_perf']-w['full_load_warmup_seconds'],pre_constructor_seconds=w['sent_perf']-w['full_load_warmup_seconds']-ws['observed'],note='constructor begin inferred from original duration and sent_perf; preceding audio/ready argument work introduces tiny timing slack'))
   # Earliest actual post-recovery dispatch and complete call receipts.
   owner=cell/'owner_e1'
   selected=[]
   for path in sorted(owner.glob('*.jsonl')):
    if path.name not in ('events.jsonl','worker_results.jsonl'):continue
    for num,r in enumerate(lines(path),1):
     e=r.get('event',{})
     if r.get('kind')=='dispatch' or e.get('kind')=='completed':
      if len([q for q in selected if q['file']==path.name])>=2:continue
      j=r.get('job',{});rec=e.get('record',{})
      selected.append(dict(file=path.name,line=num,kind=r.get('kind'),event_kind=e.get('kind'),observed=r.get('observed'),job_id=j.get('job_id',e.get('job_id')),dispatched_perf=j.get('dispatched_perf'),start=rec.get('start'),end=rec.get('end'),model_start=rec.get('model_start'),model_end=rec.get('model_end'),model_seconds=rec.get('model_seconds')))
   out.append(dict(cell_id=cell.name,phases=integrated,workers=worker_rows,post_recovery_first_events=selected,group_death_proof=death_row.get('proof'),supervisor_identity=identity(cell/'supervisor.jsonl'),power_identity=identity(cell/'power.jsonl')))
source=[]
paths=[B/'models/revtrace_streamcorrect_20261028/ultravox_b95bec8/ultravox_model.py',B/'models/revtrace_streamcorrect_20261028/ultravox_b95bec8/ultravox_config.py',B/'projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f/simul_whisper/simul_whisper.py']
for path in paths:
 text=path.read_text();arr=text.splitlines();hits=set()
 for i,line in enumerate(arr):
  if any(k in line for k in ('from_pretrained','torch.load','load_state_dict','def __init__','load_model(')):
   hits.update(range(max(0,i-2),min(len(arr),i+7)))
 source.append(dict(identity=identity(path),selected_lines=[dict(line=i+1,text=arr[i]) for i in sorted(hits)]))
print(json.dumps(dict(scope='read-only old raw power linear integration, same method as original Power.energy; both boards, no CPU energy, no new model execution',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=platform.node(),rows=out,source=source)))
'''

def main():
    sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    client=ssh_client()
    try:
        stdin,stdout,stderr=client.exec_command('python3 -B -',timeout=60)
        stdin.write(REMOTE);stdin.flush();stdin.channel.shutdown_write()
        raw,err=stdout.read(),stderr.read();rc=stdout.channel.recv_exit_status()
        if rc:raise RuntimeError(err.decode('utf8',errors='replace'))
        result=json.loads(raw);result['local_reader_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        out=HERE/'FORMAL_RECOVERY_PHASE_ENERGY_v1.json'
        if out.exists():raise FileExistsError(out)
        out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        print(json.dumps(dict(output=str(out),cells=len(result['rows']),bytes=out.stat().st_size)))
    finally:client.close()

if __name__=='__main__':main()
