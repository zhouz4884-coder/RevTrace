set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
test -f "$B/results/revtrace/ces_20261023/pilot_v3/SUMMARY.json"
"$B/envs/revbatch-cu128/bin/python" -u "$P/audit_ces_final.py" "$B" pilot_v3 9 "$P/runtime_v3"
