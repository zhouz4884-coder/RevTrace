set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_ces_v6_abcd_20261025"
O="$B/results/revtrace/ces_v6_abcd_20261025"
"$B/envs/revbatch-cu128/bin/python" "$P/summarize_v6.py" --root "$O" --stage A
"$B/envs/revbatch-cu128/bin/python" "$P/analyze_C.py" --root "$O"
"$B/envs/revbatch-cu128/bin/python" "$P/summarize_v6.py" --root "$O" --stage C
"$B/envs/revbatch-cu128/bin/python" "$P/analyze_B.py" --root "$O"
