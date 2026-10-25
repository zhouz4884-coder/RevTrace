set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025')
cases=json.loads((O/'B_CASES.json').read_text())['cases'];rows=[]
for f in sorted((O/'B_operator_v1').glob('case*-r*.json')):
 d=json.loads(f.read_text());c=cases[d['case']]
 rows.append({'case':d['case'],'repeat':d['repeat'],'historical_batch_tensors_equal':c['old_input_audits'][0]['batch_tensors']==d['rows'][0]['model_input_audit']['batch_tensors']})
print(json.dumps({'rows':rows,'all_historical_batch_inputs_equal':all(r['historical_batch_tensors_equal'] for r in rows)}))
PY
