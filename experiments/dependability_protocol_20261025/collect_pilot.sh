set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,sys,tarfile
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025';O=B/'results/revtrace/dependability_20261025'
sys.path.insert(0,str(P/'runtime/scripts'))
from audit_tc_live_qwen import audit
s=json.loads((O/'pilot/SUMMARY.json').read_text());assert s['cells']==2
for name in s['completed']:
 C=O/'pilot'/name;print(json.dumps({'cell':name,'history_audit':audit(C)}))
 ev=[json.loads(v) for v in (C/'events.jsonl').read_text().splitlines()]
 print(json.dumps({'cell':name,'captured':[e for e in ev if e['kind']=='ipc-complete-captured'],
   'delivered':[e for e in ev if e['kind']=='ipc-complete-delivered']}))
target=O/'pilot_evidence_v1.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz') as t:
 t.add(O/'pilot',arcname='pilot')
 for name in ['CPU_N1_LINUX_v1.xml','MANIFEST.json']:
  t.add(P/name,arcname=name)
 t.add(O/'PILOT_LAUNCH.json',arcname='PILOT_LAUNCH.json')
print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
PY
