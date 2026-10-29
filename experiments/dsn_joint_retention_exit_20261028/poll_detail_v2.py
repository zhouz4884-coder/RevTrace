from pathlib import Path
import datetime,hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_physical_retirement_20261028'
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
path=P/'DSN_JOINT_DETAIL_HANDLE_v2.json'
if path.exists():
 h=json.loads(path.read_text());proc=Path('/proc',str(h['pid']))
 try:
  ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
  command=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest()
  live=str(ticks)==str(h['start_ticks']) and command==h['command_sha256']
 except FileNotFoundError:live=False
 result.update(handle=h,exact_process_live=live)
 for name in ['SUMMARY.json','GATE.json']:
  f=Path(h['output'])/name
  if f.exists():result[name]=json.loads(f.read_text())
 log=Path(h['log'])
 if log.exists():result['log_tail']=log.read_text()[-3500:]
else:result['status']='NOT_LAUNCHED'
print(json.dumps(result))
