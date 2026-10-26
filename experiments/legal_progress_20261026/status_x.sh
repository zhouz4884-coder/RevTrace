set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
import sys,json,pathlib
o=pathlib.Path(sys.argv[1]);d=o/'x_gpu_v1'
for n in ['FREEZE.json','PILOT_PROGRESS.json','FORMAL_PROGRESS.json','SUMMARY.json','STOP.json']:
 p=d/n
 if p.exists():
  x=json.loads(p.read_text());print(n,{k:v for k,v in x.items() if k not in ['rows','spec','source','completed_rows']})
print('owner_tail',(o/'x_gpu_v1_owner.log').read_text()[-2600:])
PY
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
