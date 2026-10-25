set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,shutil,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
r={'time_unix':time.time(),'disk':shutil.disk_usage(B)._asdict(),
 'GPU':subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],text=True),
 'processes':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)}
for n in ['projects/revtrace_ces_v6_abcd_20261025','results/revtrace/ces_v6_abcd_20261025','data','datasets']:
 p=B/n;r[n]={'exists':p.exists(),'children':sorted(x.name for x in p.iterdir())[:45] if p.is_dir() else []}
O=B/'results/revtrace/ces_v5_closed_loop_20261025'
for n in ['formal_SUMMARY.json','COLLECTION_V3_LAUNCH.json']:
 p=O/n
 if p.exists():
  d=json.loads(p.read_text());r[n]={k:d[k] for k in ['status','performance_cells','GPU_queue_closed','pid'] if k in d}
print(json.dumps(r))
PY
