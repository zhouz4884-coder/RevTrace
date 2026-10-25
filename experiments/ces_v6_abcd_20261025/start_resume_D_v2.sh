set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import os,json,subprocess,time,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
assert not (O/'RESUME_D_v2_LAUNCH.json').exists() and not (O/'RESUME_D_v2_STARTED.json').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
with (O/'RESUME_D_v2_CONTROLLER.log').open('xb') as f:
 p=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_resume_D_v2.py'),'--base',str(B)],cwd=P,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
r={'pid':p.pid,'time_unix':time.time(),'source_controller_sha256':hashlib.sha256((P/'run_resume_D_v2.py').read_bytes()).hexdigest(),'resume_of_CPU_postcheck_only_no_old_GPU_rerun':True}
(O/'RESUME_D_v2_LAUNCH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
