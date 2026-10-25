set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025"
O="$B/results/revtrace/dependability_20261025"
date -u
df -h "$B"
findmnt -T "$B" -no FSTYPE,SOURCE
nvidia-smi --query-gpu=index,name,uuid,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,gpu_uuid,process_name,used_memory --format=csv,noheader
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dependability_20261025/n5_v1';O=B/'results/revtrace/dependability_20261025/n5_v1'
P.mkdir(exist_ok=False);O.mkdir(exist_ok=False)
d=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text())
assert len(d['sessions'])==16
(P/'DEVELOPMENT_MANIFEST.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'project':str(P),'results':str(O),'development_sources':len(d['sessions']),'model_exists':(B/'models/Qwen3-ASR-1.7B/config.json').is_file()}))
PY
