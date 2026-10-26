set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v6"
for F in "$O/CAMPAIGN_PROGRESS_v2.json" "$O/CAMPAIGN_STOP_v2.json" "$O/CAMPAIGN_COMPLETE_v2.json" "$O"/*/STOP.json; do
 if test -f "$F"; then echo "$F"; cat "$F"; fi
done
tail -n 8 "$O/CAMPAIGN_v2.log"
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
