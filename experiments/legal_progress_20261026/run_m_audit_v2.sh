set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/audit_execution_v2"
mkdir "$P/audit_execution_v2"
tar -xzf "$P/audit_execution_v2.tar.gz" -C "$P/audit_execution_v2"
"$B/envs/revtrace-er1-20261026/bin/python" "$P/audit_execution_v2/m_independent_audit.py" > "$O/m_independent_audit_v2_owner.log" 2>&1
tail -c 1800 "$O/m_independent_audit_v2_owner.log"
