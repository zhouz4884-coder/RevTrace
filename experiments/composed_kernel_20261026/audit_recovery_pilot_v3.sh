set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v3"
O="$B/results/revtrace/dependability_20261025/ck5_v3"
cd "$P"
"$B/envs/revbatch-cu128/bin/python" audit_ck5.py --stage recovery_pilot > "$O/RECOVERY_PILOT_AUDIT.log" 2>&1
cat "$O/RECOVERY_PILOT_AUDIT.log"
