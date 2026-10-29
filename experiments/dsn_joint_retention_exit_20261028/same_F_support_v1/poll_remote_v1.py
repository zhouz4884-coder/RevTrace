"""Future CPU-window use through remote.py; never execute during native timing."""
from pathlib import Path
import datetime,hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_physical_retirement_20261028/dsn_joint_same_F_support_v1'
result=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
path=P/'HANDLE_v1.json'
if not path.exists():result['status']='NOT_LAUNCHED'
else:
 h=json.loads(path.read_text());process=Path('/proc',str(h['pid']))
 try:
  ticks=process.joinpath('stat').read_text().rsplit(')',1)[1].split()[19];command=hashlib.sha256(process.joinpath('cmdline').read_bytes()).hexdigest()
  live=str(ticks)==str(h['start_ticks']) and command==h['command_sha256']
 except FileNotFoundError:live=False
 result.update(handle=h,exact_process_live=live)
 for name in ['SUMMARY.json','GATE.json','STOP.json']:
  p=Path(h['output'])/name
  if p.exists():result[name]=json.loads(p.read_text())
 log=Path(h['log'])
 if log.exists():result['log_tail']=log.read_text()[-3500:]
print(json.dumps(result))
