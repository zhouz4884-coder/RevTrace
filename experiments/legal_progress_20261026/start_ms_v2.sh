set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$O/m_gpu_v2"
test ! -e "$O/s_independent_v2"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
for stage in m_execution_v2 s_execution_v2; do
 test ! -e "$P/$stage"
 mkdir "$P/$stage"
 tar -xzf "$P/$stage.tar.gz" -C "$P/$stage"
done
nohup "$B/envs/revbatch-cu128/bin/python" "$P/s_execution_v2/s_independent_audit.py" > "$O/s_independent_v2_owner.log" 2>&1 < /dev/null &
spid=$!
nohup "$B/envs/revtrace-er1-20261026/bin/python" "$P/m_execution_v2/m_orthogonal.py" --out "$O/m_gpu_v2" > "$O/m_gpu_v2_owner.log" 2>&1 < /dev/null &
mpid=$!
printf '{"S_cpu_pid":%s,"M_gpu_pid":%s,"S_identity":"s_execution_v2/s_independent_audit.py","M_identity":"m_execution_v2/m_orthogonal.py"}\n' "$spid" "$mpid" > "$O/OWNER_MS_v2.json"
cat "$O/OWNER_MS_v2.json"
