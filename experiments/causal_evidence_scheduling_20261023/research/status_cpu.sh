set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O=$B/results/revtrace/ces_20261023
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
from pathlib import Path
import json,sys
O=Path(sys.argv[1])
for n in ['POST_PROGRESS.json','POST_STOP.json','POST_SUMMARY.json','FINAL_CPU_PROGRESS.json','FINAL_CPU_STOP.json','FINAL_CPU_SUMMARY.json']:
 p=O/n
 if p.exists():print(n,p.read_text())
for name in ['safety_metrics','processed_inputs','consumer_clock','paired_statistics']:
 p=O/('POST_'+name+'.log')
 if p.exists():print(name,'\n'.join(p.read_text().splitlines()[-6:]))
for p in O.glob('FINAL_CPU_*.log'):
 if p.name=='FINAL_CPU_CONTROLLER.log':continue
 print(p.name,'\n'.join(p.read_text().splitlines()[-5:]))
PY
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
