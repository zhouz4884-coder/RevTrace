set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/role_probe_v2';O=B/'results/revtrace/dependability_20261025/role_probe_v2'
d=json.loads((O/'FORMAL_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert json.loads((O/'formal/SUMMARY.json').read_text())['cells']==64
assert len(json.loads((O/'FORMAL_RELEASE.json').read_text())['owned'])==128
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
checker_sha=hashlib.sha256((P/'audit_role_assets_v2.py').read_bytes()).hexdigest()
assert checker_sha=='1f4be1ab8830eeeaa1eaea20891879cb0193b13f6bed90772a52b0b740d62f7f'
cmd=[str(B/'envs/revbatch-cu128/bin/python'),str(P/'audit_role_assets_v2.py'),'--stage',str(O/'formal'),
 '--manifest',str(P.parent/'n5_v3/DEVELOPMENT_MANIFEST.json'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(O/'FORMAL_ASSET_REPLAY_v2.json')]
with (O/'formal_asset_audit.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],new_neural_GPU_calls=0,checker_sha256=checker_sha)
 (O/'FORMAL_ASSET_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
