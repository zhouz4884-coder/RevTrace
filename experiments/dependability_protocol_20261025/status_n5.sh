set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v1')
d=json.loads((O/'PILOT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(json.dumps(d))
for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
 p=O/'pilot'/name
 if p.exists():print(json.dumps({name:json.loads(p.read_text())}))
for p in (O/'pilot').glob('*/attempt0/failure.json'):print(json.dumps({'failure_path':str(p),'error':json.loads(p.read_text())}))
for p in (O/'pilot').glob('*/attempt0.log'):
 if not (p.parent/'RUN_COMPLETE_PENDING_AUDIT.json').exists():print(json.dumps({'active_log':str(p),'tail':p.read_text(errors='replace')[-2000:]}))
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
