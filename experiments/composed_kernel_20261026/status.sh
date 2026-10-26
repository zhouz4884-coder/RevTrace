set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v1"
for F in "$O"/*/PROGRESS.json "$O"/*/SUMMARY.json "$O"/*/STOP.json; do
 if test -f "$F"; then echo "$F"; cat "$F"; fi
done
tail -n 12 "$O/PILOT_CONTROLLER.log"
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
