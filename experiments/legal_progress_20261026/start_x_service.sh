set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P/x_service_execution_v1"
test ! -e "$O/x_service_v1"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
mkdir "$P/x_service_execution_v1"
tar -xzf "$P/x_service_execution_v1.tar.gz" -C "$P/x_service_execution_v1"
nohup "$B/envs/revbatch-cu128/bin/python" "$P/x_service_execution_v1/x_service_controller.py" > "$O/x_service_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"stage":"x_service_v1","identity":"x_service_execution_v1/x_service_controller.py"}\n' "$pid" > "$O/X_SERVICE_OWNER.json"
cat "$O/X_SERVICE_OWNER.json"
