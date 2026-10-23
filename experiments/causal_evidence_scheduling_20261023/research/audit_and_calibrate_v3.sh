set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
"$B/envs/revbatch-cu128/bin/python" "$P/audit_ces_v2.py" "$B" pilot_v1 9 "$P/runtime_v1"
"$B/envs/revbatch-cu128/bin/python" "$P/diagnose_pilot.py" "$B"
"$B/envs/revbatch-cu128/bin/python" "$P/calibrate_v3.py" "$B"
