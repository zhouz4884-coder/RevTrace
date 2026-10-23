set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O=$B/results/revtrace/ces_20261023
ps -p 2731451 -o pid,ppid,stat,etime,args || true
find "$O" -maxdepth 3 -type f -printf '%p %s\n' | head -n 45
if test -d /proc/2731451; then tr '\0' ' ' </proc/2731451/cmdline; printf '\n'; fi
ls -l "$B/projects/revtrace_ces_20261023/run_pilot.py"
