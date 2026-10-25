set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025')
C=next(p for p in (O/'A').iterdir() if p.is_dir())
rows=[json.loads(x) for x in (C/'worker_records.jsonl').read_text().splitlines()]
es=[json.loads(x) for x in (C/'events.jsonl').read_text().splitlines()]
def small(r):
 if isinstance(r,dict):return {k:(v if not isinstance(v,(list,dict)) else {'type':type(v).__name__,'len':len(v)}) for k,v in r.items()}
 return r
print(json.dumps({'cell':C.name,'result':small(json.loads((C/'result.json').read_text())),
 'job':small(rows[0]['job']),'result_row':small(rows[0]['result']),
 'batch_account':json.loads((C/'worker_batch_accounting.jsonl').read_text().splitlines()[0]),
 'event_kinds':sorted({r['kind'] for r in es}),'sample_events':[small(r) for r in es if r['kind'] in ['ces-decision','closed-loop-decision','commit','dispatch','v5-closed-loop-decision']][:8]}))
PY
