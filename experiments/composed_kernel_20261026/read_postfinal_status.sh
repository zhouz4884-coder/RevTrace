set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v6"
cat "$O/CAMPAIGN_COMPLETE_v3.json"
for f in CPU_SUPPORTED_FINAL.log CPU_EXTERNAL_FINAL.log FORMAL_LINUX.log FORMAL_TWO_SESSION_LINUX.log HISTORY_COMPARISON.log RECOVERY_CLOCKS.log PHYSICAL_COSTS.log BOUNDARY_ACTUAL_OUTCOMES.log FINAL_RESOURCE.log BOUNDED_COLLECTION.log; do
  if test -f "$O/$f"; then printf '\n%s\n' "$f"; tail -c 6000 "$O/$f"; fi
done
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
