"""Bounded, read-only inspection of existing Owner recovery evidence.

No source changes, signals, model imports, or remote writes. Credentials stay
inside the approved helper. Only compact timing/energy fields return locally.
"""
import hashlib
import json
from pathlib import Path
import shlex
import sys

HERE = Path(__file__).resolve().parent
REMOTE = r'''
import datetime,hashlib,json,pathlib,platform
base=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells')
rows=[]
def read_events(path):
 h=hashlib.sha256(); n=0; size=0; items=[]
 with path.open('rb') as f:
  for line in f:
   h.update(line);size+=len(line);n+=1
   items.append((n,json.loads(line)))
 return items,dict(path=str(path),bytes=size,sha256=h.hexdigest(),lines=n)
for fault in ('owner_after_durable','owner_before_durable'):
 for arm in ('conservative','fullcall'):
  for repeat in (0,1):
   cell=base/('SC_FORMAL_SHORT28_v1_BAC009S0908W0369_'+fault+'_'+arm+'_r'+str(repeat))
   events,identity=read_events(cell/'supervisor.jsonl')
   compact=[]
   for line,r in events:
    kind=r.get('kind'); e=r.get('event',{}); ek=e.get('kind')
    if kind in ('fault_triggered','owner_group_death_confirmed','recovery_durable_prefix_ready','owner_started','recovered_owner_neural_ready','durable_fact_replayed') or (kind=='owner_event' and ek in ('owner_ready','worker_started')):
     item=dict(line=line,kind=kind,observed=r.get('observed'),owner_epoch=r.get('owner_epoch'),site=r.get('site'),event_kind=ek,event_observed=e.get('observed'),event_owner_epoch=e.get('owner_epoch'))
     for k in ('pid','pgid','recovered_frontiers','newly_applied_facts'):
      if k in r:item[k]=r[k]
      if k in e:item['event_'+k]=e[k]
     if ek=='owner_ready':
      item['workers']={slot:{k:w.get(k) for k in ('worker','gpu','pid','sent_perf','model_load_seconds','full_load_warmup_seconds')} for slot,w in e['workers'].items()}
      item['warmup']={slot:{k:v for k,v in w.get('neural_ready_warmup',{}).items() if k!='original_record'} for slot,w in e['workers'].items()}
     if kind=='durable_fact_replayed':item['consumer_observed']=r.get('row',{}).get('observed')
     compact.append(item)
   summary=json.loads((cell/'SUMMARY.json').read_bytes())
   # Compact original metrics only, retaining their existing names.
   metrics={k:v for k,v in summary.items() if any(x in k.lower() for x in ('energy','recover','rto','fault','service','cold','time'))}
   energy_path=cell/'ENERGY.json'
   if energy_path.exists():metrics['ENERGY.json']=json.loads(energy_path.read_bytes())
   consumer,consumer_id=read_events(cell/'consumer.jsonl')
   fault_t=next(r.get('observed') for _,r in events if r.get('kind')=='fault_triggered')
   first_new=next(((line,{k:r.get(k) for k in ('observed','kind','owner_epoch','recovery_replay','transition_id','journal_sequence','certified_frontier','visible_frontier')}) for line,r in consumer if r.get('observed',0)>fault_t and r.get('kind')=='canonical' and not r.get('recovery_replay',False)),None)
   power_path=cell/'power.jsonl'
   # Inspect schema and selected interval integrations below, never output all rows.
   power,power_id=read_events(power_path)
   power_schema=power[:1]
   rows.append(dict(cell_id=cell.name,supervisor_identity=identity,consumer_identity=consumer_id,power_identity=power_id,events=compact,original_metrics=metrics,first_new_consumer_fact=first_new,power_schema=power_schema))
print(json.dumps(dict(scope='read-only existing eight Owner-crash cells; zero model calls/signals/remote writes',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=platform.node(),rows=rows)))
'''

def main():
    sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    client = ssh_client()
    try:
        stdin, stdout, stderr = client.exec_command('python3 -B -', timeout=60)
        stdin.write(REMOTE)
        stdin.flush()
        stdin.channel.shutdown_write()
        raw, err = stdout.read(), stderr.read()
        code = stdout.channel.recv_exit_status()
        if code:
            raise RuntimeError('read-only evidence inspection failed: '+err.decode('utf8', errors='replace'))
        result = json.loads(raw)
        result['local_reader_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        out = HERE/'FORMAL_RECOVERY_RAW_PHASES_v1.json'
        if out.exists():
            raise FileExistsError(out)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
        print(json.dumps(dict(output=str(out),cells=len(result['rows']),bytes=out.stat().st_size)))
    finally:
        client.close()

if __name__ == '__main__':
    main()
