set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,time
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025');r={'time_unix':time.time(),'stages':{}}
for name in ['A_pilot','A','C','D_development','D_heldout']:
 for tag in ['SUMMARY','STOP','PROGRESS']:
  p=O/(name+'_'+tag+'.json')
  if p.exists():
   d=json.loads(p.read_text());done=d.pop('completed',[]);d['completed_count']=len(done);d['last_completed']=done[-2:];r['stages'][name]=d;break
for name in ['B_independent_analysis/SUMMARY.json','C_independent_analysis_v2/SUMMARY.json','RESUME_D_v2_STOP.json','RESUME_D_v2_SUMMARY.json','D_SEQUENCE_SUMMARY.json','D_SEQUENCE_STOP.json']:
 p=O/name
 if p.exists():
  d=json.loads(p.read_text());d.pop('all_primary_pairs',None);r[name]=d
for name in ['RESUME_D_v2_CONTROLLER.log','D_SEQUENCE_CONTROLLER.log','D_development_CONTROLLER.log','D_heldout_CONTROLLER.log']:
 p=O/name
 if p.exists():r[name+'_tail']=p.read_text(errors='replace')[-2000:]
r['GPU']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True)
print(json.dumps(r))
PY
