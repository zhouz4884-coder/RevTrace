"""Read only old real T1 events; no GPU operation, no new timing observations."""
from pathlib import Path
import json,sys,hashlib
B=Path(sys.argv[1]);O=B/'results/revtrace/phaseD_20261021';root=B/'results/revtrace/phaseN_20261021/t1_v4'
out=[];inputs=[]
for name in ['fine_certified-decoupled-obs1-r0','coarse-decoupled-obs1-r0','coarse-segment-obs1-r0']:
 p=root/name/'events.jsonl';raw=p.read_bytes();es=[json.loads(l) for l in raw.splitlines()];inputs.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()})
 done={e['job_id']:e for e in es if e['kind']=='executor-complete'};owners={};owner=None
 for e in es:
  if e['kind']=='wal-owner-start':owner={'entered':e['time'],'job_ids':e['job_ids'],'physical':[]}
  elif e['kind']=='wal-physical-timing':owner['physical'].append(e)
  elif e['kind']=='wal-owner-complete':
   owner['exited']=e['time']
   for jid in owner['job_ids']:owners[jid]=owner
   owner=None
 for c in es:
  if c['kind']!='commit' or c['session_id']!=0:continue
  d=done[c['job_id']];w=owners[c['job_id']]
  assert d['enqueue']<=d['gpu_model_started']<=d['gpu_model_completed']<=d['received']<=c['certified']<=c['installed']
  out.append({'cell':name,'session_id':0,'job_id':c['job_id'],'enqueue':d['enqueue'],'model_start':d['gpu_model_started'],'model_end':d['gpu_model_completed'],'received':d['received'],'certified':c['certified'],'installed':c['installed'],'wal_owner_start':w['entered'],'wal_owner_end':w['exited'],'fsync_intervals':[[x['started'],x['completed']] for x in w['physical'] if x['phase']=='fsync']})
(O/'TIMELINE_COMPONENTS.json').write_text(json.dumps({'tier':'CPU_READ_ONLY_OLD_REAL_GPU_LOGS_NOT_NEW_GPU_RUN','inputs':inputs,'records':out},indent=2)+'\n')
print('read-only timeline rows',len(out))
