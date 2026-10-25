set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import os,json,subprocess,time,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
assert not (O/'B_sorted_LAUNCH.json').exists() and not (O/'B_sorted_GPU_STARTED.json').exists()
# A CPU-only waiting controller cannot claim the GPU before ABC succeeds.
script="""from pathlib import Path
import subprocess,sys,time,json
O=Path(sys.argv[1]);P=Path(sys.argv[2]);B=Path(sys.argv[3])
while not (O/'ABC_SUMMARY.json').exists():
 if (O/'ABC_STOP.json').exists():
  (O/'B_sorted_WAIT_STOP.json').write_text(json.dumps({'reason':'ABC failure; no GPU launched'})+'\\n');raise SystemExit(2)
 time.sleep(5)
assert json.loads((O/'ABC_SUMMARY.json').read_text())['GPU_queue_closed']
try:subprocess.run([sys.executable,'-u',str(P/'run_B_sorted.py'),'--base',str(B)],cwd=P,check=True)
except BaseException as e:
 (O/'B_sorted_STOP.json').write_text(json.dumps({'error':repr(e),'all_raw_retained':True})+'\\n');raise
"""
with (O/'B_sorted_CONTROLLER.log').open('xb') as f:
 p=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-u','-c',script,str(O),str(P),str(B)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
r={'pid':p.pid,'waiting_for':'ABC_SUMMARY.json','time_unix':time.time(),'GPU_not_yet_claimed':True,'script_sha256':hashlib.sha256((P/'run_B_sorted.py').read_bytes()).hexdigest()}
(O/'B_sorted_LAUNCH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
