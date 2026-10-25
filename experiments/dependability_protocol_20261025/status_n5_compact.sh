set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2')
d=json.loads((O/'FORMAL_NORMAL_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']
print(json.dumps({'identity':d}))
for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
 f=O/'formal_normal'/name
 if f.exists():
  r=json.loads(f.read_text());c=r.pop('completed',[]);r['completed_count']=len(c);r['last_completed']=c[-3:]
  print(json.dumps({name:r}))
for f in (O/'formal_normal').glob('*/attempt*/failure.json'):print(json.dumps({'failure_path':str(f),'failure':json.loads(f.read_text())}))
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
