set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" "$B/projects/revtrace_dependability_20261025/n5_v3/aggregate_n5_fault_v2.py" --root "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2" --output "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2/fault_aggregation_v1"
