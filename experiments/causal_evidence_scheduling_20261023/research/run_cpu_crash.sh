set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
"$B/envs/revbatch-cu128/bin/python" "$P/ces_wal_crash_cpu.py" "$P/runtime_v2" "$B/results/revtrace/ces_20261023/CPU_SIGKILL_v2"
