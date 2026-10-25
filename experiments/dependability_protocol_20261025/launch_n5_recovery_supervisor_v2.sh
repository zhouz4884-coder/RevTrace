set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
old=B/'results/revtrace/dependability_20261025/n5_v3/RECOVERY_DEVELOPMENT_LAUNCH.json';d=json.loads(old.read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
O.mkdir(exist_ok=False)
subprocess.run([str(B/'envs/revbatch-cu128/bin/python'),'-m','pytest',str(P/'test_n5_supervisor_v2.py'),'-q','--junitxml='+str(P/'CPU_SUPERVISOR_V2_LINUX.xml')],check=True,cwd=P)
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_n5_validation_v2.py'),'--stage','recovery_development']
with (O/'recovery_development_controller.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 q=Path('/proc')/str(p.pid);d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
  controller_sha256=hashlib.sha256((P/'run_n5_validation_v2.py').read_bytes()).hexdigest(),expected=2,runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8')
 (O/'RECOVERY_DEVELOPMENT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
