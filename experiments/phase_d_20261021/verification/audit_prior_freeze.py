"""Verify old immutable raw evidence; no new GPU result or incidence claim."""
import json,hashlib,sys
from pathlib import Path
B=Path(sys.argv[1]);N=B/'results/revtrace/phaseN_20261021';O=B/'results/revtrace/phaseD_20261021'
idx=json.loads((N/'RAW_EVIDENCE_INDEX.json').read_text());bad=[]
for r in idx['files']:
 p=N/r['path']
 if not p.exists():bad.append({'path':r['path'],'reason':'missing'});continue
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 if h!=r['sha256'] or p.stat().st_size!=r['bytes']:bad.append({'path':r['path'],'reason':'changed bytes'})
record={'status':'PASS_PRIOR_RAW_HASH_FREEZE' if not bad else 'FAIL_PRIOR_RAW_CHANGE','files_checked':len(idx['files']),'failures':bad,'scope':'old frozen Phase N artifacts, not additional trials'}
(O/'PRIOR_FREEZE_RECHECK.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));assert not bad
