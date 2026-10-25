set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,os,subprocess,time,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
assert not (O/'NEXT_STAGES_LAUNCH.json').exists() and not (O/'NEXT_STAGES_STARTED.json').exists()
with (O/'NEXT_STAGES_CONTROLLER.log').open('xb') as f:
 p=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_next_stages.py'),'--base',str(B)],cwd=P,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
r={'pid':p.pid,'time_unix':time.time(),'waits_for_corrected_B':True,'GPU_not_yet_claimed':True,'controller_sha256':hashlib.sha256((P/'run_next_stages.py').read_bytes()).hexdigest()}
(O/'NEXT_STAGES_LAUNCH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
