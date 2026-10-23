set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_ces_20261023';O=B/'results/revtrace/ces_20261023'
assert not (O/'FINAL_CPU_PID.json').exists()
with (O/'FINAL_CPU_CONTROLLER.log').open('w') as f:q=subprocess.Popen([sys.executable,'-u',str(P/'run_final_cpu.py'),str(B)],cwd=P,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
x={'pid':q.pid,'started_unix':time.time(),'CPU_only_waits_existing_post':True,'script_sha256':hashlib.sha256((P/'run_final_cpu.py').read_bytes()).hexdigest()}
(O/'FINAL_CPU_PID.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
PY
