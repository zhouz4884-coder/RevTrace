set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
O=$B/results/revtrace/ces_20261023
test -f "$O/pilot_v1/SUMMARY.json"
"$B/envs/revbatch-cu128/bin/python" "$P/audit_ces.py" "$B" pilot_v1 9 "$P/runtime_v1"
