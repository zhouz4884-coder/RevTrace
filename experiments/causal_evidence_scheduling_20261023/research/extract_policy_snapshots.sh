set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
from pathlib import Path
import json,sys
O=Path(sys.argv[1])/'results/revtrace/ces_20261023';D=O/'policy_equivalence_v4';D.mkdir(exist_ok=False)
rows=[]
for c in ['ces-mixed','ces-mixed-repeat','oracle-ces-mixed']:
 C=O/'pilot_v3'/c;cfg=json.loads((C/'config.json').read_text())
 for l in (C/'events.jsonl').read_text().splitlines():
  e=json.loads(l)
  if e['kind']=='ces-decision':rows.append({'cell':c,'config':{'microbatch':cfg['microbatch'],'ces_study':{k:cfg['ces_study'][k] for k in ['display_slo','commit_slo','wait_cap']}},'event':e})
(D/'SNAPSHOTS.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows))
PY
