set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
"$B/envs/revbatch-cu128/bin/python" -u "$P/audit_ces_v3.py" "$B" pilot_v2 9 "$P/runtime_v2"
"$B/envs/revbatch-cu128/bin/python" "$P/bound_conditional_cost.py" "$B"
