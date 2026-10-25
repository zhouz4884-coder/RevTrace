set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v2')
d=json.loads((O/'DEVELOPMENT_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
d['verified_live']=q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(json.dumps(d))
for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
 p=O/'development'/name
 if p.exists():print(json.dumps({name:json.loads(p.read_text())}))
for p in (O/'development').glob('*/attempt0/failure.json'):print(json.dumps({'path':str(p),'failure':json.loads(p.read_text())}))
for p in (O/'development').glob('*/attempt0.log'):
 if not (p.parent/'RUN_COMPLETE_PENDING_AUDIT.json').exists():print(json.dumps({'active_log':str(p),'tail':p.read_text(errors='replace')[-1800:]}))
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
