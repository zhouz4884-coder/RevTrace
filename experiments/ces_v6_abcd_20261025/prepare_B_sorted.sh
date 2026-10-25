set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/ces_v6_abcd_20261025';old=B/'results/revtrace/ces_v5_closed_loop_20261025/formal'
out=O/'B_CASES_SORTED_v2.json';assert not out.exists()
cases=json.loads((O/'B_CASES.json').read_text())['cases'];changes=[]
for i,c in enumerate(cases):
 records=[json.loads(x) for x in (old/c['source_cell']/'worker_batch_accounting.jsonl').read_text().splitlines()]
 matched=[r for r in records if r.get('batch_id')==c['batch_id']];assert len(matched)==1,(i,c['batch_id'])
 order=matched[0]['job_ids'];assert set(order)=={j['job_id'] for j in c['jobs']}
 indices=[next(i for i,j in enumerate(c['jobs']) if j['job_id']==jid) for jid in order]
 changes.append({'case':i,'old_arrival_order_indices_to_physical_order':indices,'changed':indices!=list(range(len(order)))})
 for key in ['jobs','old_input_audits','old_Z']:c[key]=[c[key][i] for i in indices]
 c['failed_indices']=[indices.index(i) for i in c['failed_indices']];c['historical_physical_job_order']=order
out.write_text(json.dumps({'selection':'Same six frozen historical targets, corrected physical Batch row order from original worker_batch_accounting; no selection on new output','original_cases_sha256':hashlib.sha256((O/'B_CASES.json').read_bytes()).hexdigest(),'corrections':changes,'cases':cases},indent=2)+'\n')
print(json.dumps({'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'corrections':changes}))
PY
