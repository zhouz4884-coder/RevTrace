set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
hostname
date -Iseconds
df -h "$B"
nvidia-smi --query-gpu=index,name,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
test -x "$B/envs/revbatch-cu128/bin/python"
test -f "$B/results/revtrace/row_completion_20261023/FORMAL_ROW_SUMMARY_v1.json"
head -c 800 "$B/results/revtrace/row_completion_20261023/formal_row_v1/strict-row-sync16-F2-r0/worker_records.jsonl" || true
printf '\n'
find "$B/results/revtrace/row_completion_20261023/formal_row_v1/strict-row-sync16-F2-r0" -maxdepth 1 -type f -printf '%f %s\n'
mkdir -p "$B/projects/revtrace_ces_20261023" "$B/results/revtrace/ces_20261023"
