set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
for n in ['projects/revtrace_ces_v6_abcd_20261025','projects/revtrace_online_admission_20261022','datasets/revtrace']:
 p=B/n; print(json.dumps({'path':str(p),'children':[v.name for v in p.iterdir()] if p.exists() else []}))
for p in (B/'results/revtrace/ces_v6_abcd_20261025').glob('*FREEZE.json'):
 d=json.loads(p.read_text());print(json.dumps({'path':str(p),'manifests':sorted({c['manifest'] for c in d.get('cells',[])})}))
PY
