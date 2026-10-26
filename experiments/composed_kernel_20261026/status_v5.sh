set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v5"
for F in "$O"/*/PROGRESS.json "$O"/*/SUMMARY.json "$O"/*/STOP.json; do
 if test -f "$F"; then echo "$F"; cat "$F"; fi
done
for F in "$O"/*CONTROLLER.log; do
 if test -f "$F"; then tail -n 7 "$F"; fi
done
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
