"""Observe existing controllers only; never submits or restarts experiments."""
from pathlib import Path
import importlib.util,json,time
W=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
O='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_20261023'
names=['FORMAL_PROGRESS.json','FORMAL_STOP.json','FORMAL_EXECUTION_SUMMARY.json','POST_PROGRESS.json','POST_STOP.json','POST_SUMMARY.json']
started=time.monotonic();prior={};c=f=None;errors=0
try:
 while time.monotonic()-started<8*3600:
  try:
   if c is None:c=h.ssh_client();c.get_transport().set_keepalive(15);f=c.open_sftp();f.get_channel().settimeout(40)
   current={}
   for n in names:
    try:
     with f.open(O+'/'+n) as r:x=json.loads(r.read())
    except (FileNotFoundError,json.JSONDecodeError):continue
    if isinstance(x.get('completed'),list):x['completed_count']=len(x.pop('completed'))
    current[n]=x
    if prior.get(n)!=x:
     print(n,json.dumps(x),flush=True)
     with (W/'EXISTING_FORMAL_WATCH.jsonl').open('a') as out:out.write(json.dumps({'time_unix':time.time(),'file':n,'state':x})+'\n')
     prior[n]=x
    if n.endswith('STOP.json'):raise SystemExit('EXISTING_TASK_REQUIRES_ANALYSIS_NO_RESTART')
   errors=0
   if 'POST_SUMMARY.json' in current:print('READY_FINAL_AUDIT_AND_DELIVERY_NOT_GOAL_COMPLETE',flush=True);break
  except (OSError,EOFError) as e:
   errors+=1
   if c is not None:c.close()
   c=f=None
   if errors in [1,3]:print('OBSERVATION_ONLY_RETRY',type(e).__name__,'NO_WORKER_RESTART',flush=True)
  time.sleep(20)
 else:raise SystemExit('OBSERVATION_TIMEOUT_EXISTING_JOBS_UNTOUCHED')
finally:
 if c is not None:c.close()
