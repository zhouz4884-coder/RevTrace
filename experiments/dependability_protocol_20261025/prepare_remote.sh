set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
for part in ['projects/revtrace_dependability_20261025','results/revtrace/dependability_20261025']:
 p=B/part;p.mkdir(exist_ok=True)
for p in (B/'datasets/revtrace/phaseD_20261021').iterdir():
 if p.is_file() and p.suffix=='.json':
  try:d=json.loads(p.read_text())
  except Exception:continue
  print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'keys':list(d)[:8],
   'sessions':[ {k:r[k] for k in ['source_id','path','duration','text','reference'] if k in r} for r in d.get('sessions',[])[:6]]}))
p=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
d=json.loads(p.read_text());print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sessions':d['sessions'][:4]}))
PY
