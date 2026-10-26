set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revtrace-er1-20261026/bin/python" "$P/m_format_audit_v1.py" > "$O/m_format_audit_v1_owner.log" 2>&1
tail -c 3000 "$O/m_format_audit_v1_owner.log"
