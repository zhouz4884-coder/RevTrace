set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/role_probe_v2';O=B/'results/revtrace/dependability_20261025/role_probe_v2'
d=json.loads((O/'PILOT_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert json.loads((O/'pilot/SUMMARY.json').read_text())['cells']==8
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),str(P/'audit_role_assets_v2.py'),'--stage',str(O/'pilot'),
 '--manifest',str(P.parent/'n5_v3/DEVELOPMENT_MANIFEST.json'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(O/'PILOT_ASSET_REPLAY_v2.json')]
with (O/'pilot_asset_audit.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],new_neural_GPU_calls=0)
 (O/'PILOT_ASSET_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
