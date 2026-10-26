set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
import sys,json,pathlib
o=pathlib.Path(sys.argv[1])
for s in ['s_independent_v2','m_gpu_v2','m_old_truth_controls_v1','x_service_v2']:
 for n in ['PROGRESS.json','SUMMARY.json','STOP.json']:
  p=o/s/n
  if p.exists():
   x=json.loads(p.read_text());print(s,n,{k:v for k,v in x.items() if k not in ['rows','quarantine_owner_reaudit','completed_rows','selfchecks']})
for n in ['CHAIN_PROGRESS.json','CHAIN_COMPLETE.json','CHAIN_STOP.json']:
 if (o/n).exists():print(n,(o/n).read_text()[:1400])
for n in ['m_independent_audit_v2_owner.log','x_service_v2_owner.log','chain_v2_owner.log']:
 if (o/n).exists():print(n,(o/n).read_text()[-2000:])
PY
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
