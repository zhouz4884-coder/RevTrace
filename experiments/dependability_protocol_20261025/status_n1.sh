set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025')
for name in ['PILOT_LAUNCH.json','FORMAL_LAUNCH.json']:
 p=O/name
 if p.exists():
  d=json.loads(p.read_text());proc=Path('/proc')/str(d['pid'])
  d['verified_live']=proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']
  print(json.dumps({name:d}))
for stage in ['pilot','formal']:
 for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
  p=O/stage/name
  if p.exists():print(json.dumps({stage+'/'+name:json.loads(p.read_text())}))
 for p in (O/stage).glob('*/failure.json'):print(json.dumps({'failure_path':str(p),'failure':json.loads(p.read_text())}))
 for p in sorted((O/stage).glob('*.log')):
  if not (O/stage/p.stem/'result.json').exists():print(json.dumps({'active_log':str(p),'tail':p.read_text(errors='replace')[-2200:]}))
print(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
PY
