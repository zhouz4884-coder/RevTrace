set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v6"
tail -n 25 "$O/boundary_pilot_CPU_ASSETS.log"
cat "$O/boundary_pilot_INDEPENDENT.log"
