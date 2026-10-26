set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/s_execution_v1"
mkdir "$P/s_execution_v1"
tar -xzf "$P/s_execution_v1.tar.gz" -C "$P/s_execution_v1"
nohup "$B/envs/revbatch-cu128/bin/python" "$P/s_execution_v1/s_independent_audit.py" > "$O/s_independent_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"stage":"s_independent_CPU","identity":"s_execution_v1/s_independent_audit.py"}\n' "$pid" > "$O/S_INDEPENDENT_OWNER.json"
cat "$O/S_INDEPENDENT_OWNER.json"
