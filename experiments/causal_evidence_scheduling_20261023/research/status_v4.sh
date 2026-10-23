set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
from pathlib import Path
import collections,json,sys
O=Path(sys.argv[1])/'results/revtrace/ces_20261023'
for name in ['pilot_v4/PROGRESS.json','pilot_v4/STOP.json','pilot_v4/SUMMARY.json']:
 p=O/name
 if p.exists():print(name,p.read_text())
for p in sorted((O/'pilot_v4').glob('*/result.json')):
 r=json.loads(p.read_text());rs=[json.loads(l) for l in (p.parent/'worker_records.jsonl').read_text().splitlines()]
 ar=[t for t in rs if t['job']['role']=='authority'];vr=[t for t in ar if t['job']['ces_operation']=='verify']
 print(json.dumps({'cell':p.parent.name,'wall':r['wall_seconds_including_arrival_and_drain'],
  'commit_P99_server':r['commit_p99_seconds'],'operations':dict(collections.Counter(t['job']['ces_operation'] for t in ar)),
  'verified_accepts':sum(t['result']['online_verification']['candidate_accepted'] for t in vr)}))
if (O/'pilot_v4/STOP.json').exists():
 for p in (O/'pilot_v4').glob('*.log'):
  if not (p.parent/p.stem/'result.json').exists():print(p.name,p.read_text()[-4500:])
PY
