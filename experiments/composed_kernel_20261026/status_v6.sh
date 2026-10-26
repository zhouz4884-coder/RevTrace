set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v6"
for F in "$O/CAMPAIGN_PROGRESS.json" "$O/CAMPAIGN_STOP.json" "$O/CAMPAIGN_COMPLETE.json" "$O"/*/STOP.json; do
 if test -f "$F"; then echo "$F"; cat "$F"; fi
done
tail -n 6 "$O/CAMPAIGN.log"
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
