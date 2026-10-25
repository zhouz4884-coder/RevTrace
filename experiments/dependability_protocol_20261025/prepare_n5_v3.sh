set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');p=B/'projects/revtrace_dependability_20261025/n5_v3';o=B/'results/revtrace/dependability_20261025/n5_v3'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
q=B/'results/revtrace/dependability_20261025/n5_v2/DEVELOPMENT_ASSET_REPLAY_v1.json'
if q.exists():print('DEVELOPMENT_ASSET',q.read_text()[:600])
else:raise RuntimeError('development asset audit not completed')
p.mkdir(exist_ok=False);o.mkdir(exist_ok=False)
for name in ['DEVELOPMENT_MANIFEST.json','INDEPENDENT_MANIFEST_v1.json']:
 (p/name).write_bytes((p.parent/'n5_v2'/name).read_bytes())
print('PREPARED',p)
PY
