set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/n5_v1"
O="$B/results/revtrace/dependability_20261025/n5_v1"
test -e "$P/CPU_N5_LINUX_v1.xml"
test ! -e "$O/pilot"
nohup "$B/envs/revbatch-cu128/bin/python" -u "$P/run_n5_pilot.py" --base "$B" > "$O/pilot_controller.log" 2>&1 < /dev/null &
PID=$!
"$B/envs/revbatch-cu128/bin/python" - "$PID" <<'PY'
from pathlib import Path
import json,sys,time
p=Path('/proc')/sys.argv[1]
d=dict(pid=int(sys.argv[1]),start_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
    cmdline=p.joinpath('cmdline').read_bytes().decode().replace('\0',' '),launch_unix=time.time(),expected_cells=4)
Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v1/PILOT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d))
PY
