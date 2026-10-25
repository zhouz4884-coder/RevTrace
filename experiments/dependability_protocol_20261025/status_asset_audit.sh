set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025')
d=json.loads((O/'FORMAL_ASSET_AUDIT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']
print(json.dumps(d))
q=O/'FORMAL_ASSET_AUDIT_v2.json'
if q.exists():
 r=json.loads(q.read_text());print(json.dumps({'status':r['status'],'cells':len(r['runs']),
  'rows':sum(x['rendered_complete_rows'] for x in r['runs']),'batches':sum(x['exact_reprocessed_physical_batches'] for x in r['runs'])}))
else:print((O/'formal_asset_audit_v2.log').read_text(errors='replace')[-2000:])
PY
