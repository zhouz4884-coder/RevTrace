set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,os,subprocess,time,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
for n in ['B_LAUNCH.json','B_GPU_STARTED.json','B_CONTROLLER.log']:assert not (O/n).exists(),n
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert json.loads((O/'SOURCE_EXPOSURE_AUDIT.json').read_text())['speaker_unseen_count']==16
with (O/'B_CONTROLLER.log').open('xb') as f:
 p=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_B_operator_v2.py'),'--base',str(B)],cwd=P,
  stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
r={'pid':p.pid,'time_unix':time.time(),'scope':'standalone operator, not serving','script_sha256':hashlib.sha256((P/'run_B_operator_v2.py').read_bytes()).hexdigest()}
(O/'B_LAUNCH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
