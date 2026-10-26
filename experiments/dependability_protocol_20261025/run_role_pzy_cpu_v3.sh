set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/role_probe_v2';P=B/'projects/revtrace_dependability_20261025/role_probe_v2'
assert json.loads((O/'FORMAL_ASSET_REPLAY_v2.json').read_text())['cases']==64
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
subprocess.run([str(B/'envs/revbatch-cu128/bin/python'),str(P/'decode_role_pzy_v3.py'),'--root',str(O),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(O/'FORMAL_PZY_DECODE_v3.json')],check=True)
PY
