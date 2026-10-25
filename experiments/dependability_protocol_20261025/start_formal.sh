set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025"
O="$B/results/revtrace/dependability_20261025"
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025')
assert json.loads((O/'pilot/SUMMARY.json').read_text())['cells']==2
assert json.loads((O/'PILOT_ASSET_AUDIT_v2.json').read_text())['status']=='PASS_CPU_ASSET_RENDER_AND_FULL_BATCH_REPROCESS'
assert json.loads((O/'PILOT_LOCAL_AUDIT_v1.json').read_text())['status']=='PASS_BOUNDED_INDEPENDENT_N1_AUDIT'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert not (O/'formal').exists() and not (O/'FORMAL_LAUNCH.json').exists()
PY
nohup "$B/envs/revbatch-cu128/bin/python" -u "$P/run_n1.py" --stage formal > "$O/formal_controller.log" 2>&1 < /dev/null &
PID=$!
"$B/envs/revbatch-cu128/bin/python" - "$PID" <<'PY'
from pathlib import Path
import json,sys,time
p=Path('/proc')/sys.argv[1]
d={'pid':int(sys.argv[1]),'start_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
   'cmdline':p.joinpath('cmdline').read_bytes().decode().replace('\0',' '),'launched_unix':time.time(),
   'cells':54,'no_new_source_selection_after_pilot':True}
Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/FORMAL_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d))
PY
