set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O=$B/results/revtrace/ces_20261023
for n in PILOT_PID_v1.json pilot_v1/PROGRESS.json pilot_v1/STOP.json pilot_v1/SUMMARY.json; do
 if test -f "$O/$n"; then printf '%s\n' "$n"; head -c 1800 "$O/$n"; printf '\n'; fi
done
tail -n 9 "$O/PILOT_CONTROLLER_v1.log" </dev/null
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
for p in "$O"/pilot_v1/*.log; do tail -n 3 "$p"; done
