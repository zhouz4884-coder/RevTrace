set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/role_probe_v1')
for name in ['PILOT_LAUNCH.json','FORMAL_LAUNCH.json']:
 f=O/name
 if f.exists():
  d=json.loads(f.read_text());p=Path('/proc')/str(d['pid']);d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(name,json.dumps(d))
for stage in ['pilot','formal']:
 D=O/stage
 for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
  f=D/name
  if f.exists():
   d=json.loads(f.read_text());c=d.pop('completed',[]);d['completed_count']=len(c);d['last_completed']=c[-2:];print(stage,name,json.dumps(d))
 for f in D.glob('*/FAILURE.json'):print('CASE_FAILURE',str(f),f.read_text())
for f in O.glob('*controller.log'):print('CONTROLLER',f.name,f.read_text(errors='replace')[-1700:])
for f in (O/'pilot').glob('*.log'):
 if not (f.parent/f.stem/'RUN_COMPLETE_PENDING_AUDIT.json').exists():print('ACTIVE_CASE_LOG',f.name,f.read_text(errors='replace')[-1600:])
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
