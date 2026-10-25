set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025"
O="$B/results/revtrace/dependability_20261025"
test -e "$O/FORMAL_CERTIFICATE_AND_RELEASE_v1.json"
test ! -e "$O/FORMAL_ASSET_AUDIT_v2.json"
test ! -e "$O/FORMAL_ASSET_AUDIT_LAUNCH.json"
nohup "$B/envs/revbatch-cu128/bin/python" -u "$P/audit_assets_n1_v2.py" --stage "$O/formal" --manifest "$P/MANIFEST.json" --model "$B/models/Qwen3-ASR-1.7B" --output "$O/FORMAL_ASSET_AUDIT_v2.json" > "$O/formal_asset_audit_v2.log" 2>&1 < /dev/null &
PID=$!
"$B/envs/revbatch-cu128/bin/python" - "$PID" <<'PY'
from pathlib import Path
import hashlib,json,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'
p=Path('/proc')/sys.argv[1]
d={'pid':int(sys.argv[1]),'start_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
 'cmdline':p.joinpath('cmdline').read_bytes().decode().replace('\0',' '),'new_neural_GPU_calls':0,'time_unix':time.time()}
(O/'FORMAL_ASSET_AUDIT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
