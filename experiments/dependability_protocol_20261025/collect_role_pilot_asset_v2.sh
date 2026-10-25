set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/role_probe_v2')
d=json.loads((O/'PILOT_ASSET_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
live=q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']
print('ASSET_HANDLE',json.dumps(dict(d,verified_live=live)))
p=O/'PILOT_ASSET_REPLAY_v2.json'
if p.exists():
 print('ASSET_RESULT',p.read_text());print('SHA',hashlib.sha256(p.read_bytes()).hexdigest())
else:print((O/'pilot_asset_audit.log').read_text()[-2500:])
PY
