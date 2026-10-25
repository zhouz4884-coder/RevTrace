set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
d=json.loads((O/'FORMAL_NORMAL_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']),'still same live GPU controller'
assert json.loads((O/'formal_normal/SUMMARY.json').read_text())['cells']==105
assert not (O/'formal_normal/STOP.json').exists() and not (O/'POSTNORMAL_CPU_LAUNCH.json').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_n5_postnormal_cpu.py')]
with (O/'postnormal_cpu_controller.log').open('xb') as f:
 child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(child.pid)
 d=dict(pid=child.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
  script_sha256=hashlib.sha256((P/'run_n5_postnormal_cpu.py').read_bytes()).hexdigest(),new_GPU_calls=0)
 (O/'POSTNORMAL_CPU_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
