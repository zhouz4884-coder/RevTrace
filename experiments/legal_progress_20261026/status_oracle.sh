set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
import pathlib,json,sys
o=pathlib.Path(sys.argv[1]);d=o/'x_service_oracle_v1'
for n in ['SUMMARY.json','STOP.json']:
 if (d/n).exists():
  x=json.loads((d/n).read_text());print(n,{k:v for k,v in x.items() if k not in ['rows','completed']})
print('log_tail',(o/'x_service_oracle_v1_owner.log').read_text()[-1800:])
PY
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
