set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
tail -c 5000 "$O/x_service_audit_v3_owner.log"
cat "$O/CHAIN_COMPLETE.json"
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
