set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/x_execution_v1"
test ! -e "$O/x_gpu_v1"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
mkdir "$P/x_execution_v1"
tar -xzf "$P/x_execution_v1.tar.gz" -C "$P/x_execution_v1"
nohup "$B/envs/revtrace-er1-20261026/bin/python" "$P/x_execution_v1/x_gpu_probe.py" --out "$O/x_gpu_v1" --profiles "$P/x_execution_v1/X_PROFILES_v1.json" > "$O/x_gpu_v1_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"stage":"x_gpu_v1","identity":"x_execution_v1/x_gpu_probe.py"}\n' "$pid" > "$O/X_OWNER_v1.json"
cat "$O/X_OWNER_v1.json"
