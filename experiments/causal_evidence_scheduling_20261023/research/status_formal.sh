set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
from pathlib import Path
import json,sys
O=Path(sys.argv[1])/'results/revtrace/ces_20261023'
for name in ['FORMAL_PID.json','FORMAL_PROGRESS.json','FORMAL_STOP.json','FORMAL_EXECUTION_SUMMARY.json']:
 p=O/name
 if p.exists():
  x=json.loads(p.read_text())
  if isinstance(x.get('completed'),list):x['completed_count']=len(x.pop('completed'))
  print(name,json.dumps(x))
if (O/'FORMAL_STOP.json').exists():
 logs=sorted((O/'formal_v1').glob('*.log'),key=lambda p:p.stat().st_mtime)
 for p in logs[-2:]:print(p.name,p.read_text()[-4000:])
PY
