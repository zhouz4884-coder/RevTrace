set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/x_audit_execution_v3"
test ! -e "$O/X_ORACLE_OWNER.json"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
mkdir "$P/x_audit_execution_v3"
tar -xzf "$P/x_audit_execution_v3.tar.gz" -C "$P/x_audit_execution_v3"
"$B/envs/revbatch-cu128/bin/python" "$P/x_audit_execution_v3/x_service_audit.py" > "$O/x_service_audit_v3_owner.log" 2>&1
nohup "$B/envs/revtrace-er1-20261026/bin/python" "$P/x_audit_execution_v3/x_service_oracle.py" > "$O/x_service_oracle_v1_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"identity":"x_audit_execution_v3/x_service_oracle.py","scope":"16actualparent controls,48 logical target calls,not serving"}\n' "$pid" > "$O/X_ORACLE_OWNER.json"
cat "$O/X_ORACLE_OWNER.json"
