set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
hostname
date -u
df -h "$B"
nvidia-smi --query-gpu=index,name,uuid,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,gpu_uuid,process_name,used_memory --format=csv,noheader
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
for pattern in ['projects/revtrace_phase_d*/**/*manifest*.json',
                'projects/revtrace_online*/**/*manifest*.json',
                'projects/revtrace_row*/**/*manifest*.json',
                'projects/revtrace_ces_v6_abcd_20261025/**/*manifest*.json']:
    paths=list(B.glob(pattern))
    print(json.dumps({'pattern':pattern,'paths':[str(p) for p in paths[:30]]}))
print(json.dumps({'model_exists':(B/'models/Qwen3-ASR-1.7B/config.json').is_file()}))
PY
