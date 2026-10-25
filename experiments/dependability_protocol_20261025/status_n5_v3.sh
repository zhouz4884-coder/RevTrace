set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3')
for f in O.glob('*LAUNCH.json'):
 d=json.loads(f.read_text());p=Path('/proc')/str(d['pid'])
 d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(f.name,json.dumps(d))
for stage in ['recovery_development','formal_normal','formal_fault']:
 D=O/stage
 for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
  f=D/name
  if f.exists():print(stage,name,f.read_text()[:3500])
 for f in D.glob('*/attempt*/failure.json'):print('FAILURE',str(f),f.read_text())
 for f in D.glob('*/KILL.json'):
  d=json.loads(f.read_text());print('KILL',f.parent.name,json.dumps({k:d[k] for k in ['kill_perf','returncode','workers_exited_or_zombie','episode_origin_perf']}))
for f in O.glob('*controller.log'):print('CONTROLLER',f.name,f.read_text(errors='replace')[-1800:])
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
