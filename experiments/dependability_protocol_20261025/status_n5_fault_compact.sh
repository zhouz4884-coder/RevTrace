set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2')
d=json.loads((O/'FORMAL_FAULT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(json.dumps(d))
for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
 p=O/'formal_fault'/name
 if p.exists():
  r=json.loads(p.read_text());c=r.pop('completed',[]);r['completed_count']=len(c);r['last_completed']=c[-3:];print(name,json.dumps(r))
for p in (O/'formal_fault').glob('*/attempt*/failure.json'):print('FAILURE',str(p),p.read_text())
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
