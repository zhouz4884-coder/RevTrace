import json
from pathlib import Path
p=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/assets_v1/GATE.json')
d=json.loads(p.read_text());print(json.dumps({k:d.get(k) for k in ['status','error','http_status','frames']}))
