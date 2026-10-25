set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import os,json,subprocess,time,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
assert not (O/'COLLECTION_WAIT_LAUNCH.json').exists() and not (O/'collection_v1').exists()
script="""from pathlib import Path
import json,subprocess,sys,time
O,P,B=map(Path,sys.argv[1:])
try:
 while not (O/'RESUME_D_v2_SUMMARY.json').exists():
  if any((O/n).exists() for n in ['RESUME_D_v2_STOP.json','D_SEQUENCE_STOP.json','D_development_STOP.json','D_heldout_STOP.json']):raise RuntimeError('D not complete; no collection')
  time.sleep(5)
 assert json.loads((O/'RESUME_D_v2_SUMMARY.json').read_text())['GPU_queue_closed']
 # Let completed controllers close their logs, without delaying GPU release.
 for marker in ['RESUME_D_v2_STARTED.json','D_SEQUENCE_STARTED.json']:
  pid=json.loads((O/marker).read_text())['pid']
  for _ in range(20):
   cmd=Path('/proc',str(pid),'cmdline')
   if not cmd.exists():break
   text=cmd.read_bytes().replace(b'\\0',b' ').decode(errors='replace')
   if 'revtrace_ces_v6_abcd_20261025' not in text:break
   time.sleep(.1)
  else:raise RuntimeError('Owned controller still closing; inspect rather than duplicate')
 with (O/'COLLECTOR.log').open('xb') as f:subprocess.run([sys.executable,str(P/'collect_v6_v2.py'),'--base',str(B)],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
except BaseException as e:
 (O/'COLLECTION_WAIT_STOP.json').write_text(json.dumps({'error':repr(e),'all_raw_preserved':True})+'\\n');raise
"""
with (O/'COLLECTION_WAIT_CONTROLLER.log').open('xb') as f:
 p=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-u','-c',script,str(O),str(P),str(B)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
r={'pid':p.pid,'time_unix':time.time(),'CPU_only_wait_then_collection':True,'new_GPU_calls':0,'collector_sha256':hashlib.sha256((P/'collect_v6_v2.py').read_bytes()).hexdigest()}
(O/'COLLECTION_WAIT_LAUNCH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
