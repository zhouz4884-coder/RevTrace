set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/ck5_v6')
def read(p):return json.loads(p.read_text())
version='v3' if (O/'CAMPAIGN_PROGRESS_v3.json').exists() else 'v2'
for name in ['CAMPAIGN_PROGRESS_'+version+'.json','CAMPAIGN_STOP_'+version+'.json','CAMPAIGN_COMPLETE_'+version+'.json']:
 if (O/name).exists():print(name,read(O/name))
for stage in ['boundary_pilot','post_sync_pilot','normal','fault','boundary','post_sync']:
 p=O/stage
 if (p/'SUMMARY.json').exists():
  d=read(p/'SUMMARY.json');print(stage,'COMPLETE',len(d['completed']),d['expected'])
 elif (p/'PROGRESS.json').exists():
  d=read(p/'PROGRESS.json');print(stage,len(d['completed']),d['expected'],d.get('current'))
 if (p/'STOP.json').exists():print('STAGE_STOP',stage,read(p/'STOP.json'))
print('gpu_apps',subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip())
PY
