set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v3"
O="$B/results/revtrace/dependability_20261025/ck5_v3"
test -f "$O/pilot/SUMMARY.json"
test ! -e "$O/pilot/STOP.json"
test ! -e "$O/RECOVERY_PILOT_OWNER.json"
cd "$P"
"$B/envs/revbatch-cu128/bin/python" audit_ck5.py --stage pilot > "$O/PILOT_AUDIT.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" regression.py > "$O/CPU_FULL_v3.log" 2>&1
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
nohup "$B/envs/revbatch-cu128/bin/python" -u gpu_controller_next.py --stage recovery_pilot > "$O/RECOVERY_PILOT_CONTROLLER.log" 2>&1 < /dev/null &
CPID=$!
"$B/envs/revbatch-cu128/bin/python" -c 'import json,pathlib,sys; p=int(sys.argv[1]); s=pathlib.Path("/proc")/str(p)/"stat"; pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(pid=p,start_ticks=s.read_text().rsplit(")",1)[1].split()[19])))' "$CPID" "$O/RECOVERY_PILOT_OWNER.json"
cat "$O/RECOVERY_PILOT_OWNER.json"
