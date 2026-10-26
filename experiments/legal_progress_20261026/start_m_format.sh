set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/m_format_execution_v1"
test ! -e "$O/m_format_v1"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
mkdir "$P/m_format_execution_v1"
tar -xzf "$P/m_format_execution_v1.tar.gz" -C "$P/m_format_execution_v1"
nohup "$B/envs/revtrace-er1-20261026/bin/python" "$P/m_format_execution_v1/m_format_control.py" > "$O/m_format_v1_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"identity":"m_format_execution_v1/m_format_control.py","expected":64,"scope":"content-only formatting control; old320 untouched"}\n' "$pid" > "$O/M_FORMAT_OWNER.json"
cat "$O/M_FORMAT_OWNER.json"
"$B/envs/revbatch-cu128/bin/python" "$P/reserve_next_sources_v1.py"
