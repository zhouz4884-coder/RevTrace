set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,time
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025');handles=[];live=[]
for stage in ['A_pilot','A','C','D_development','D_heldout']:
 s=json.loads((O/(stage+'_SUMMARY.json')).read_text());assert s['GPU_queue_closed']
 for cell in s['completed']:handles+=json.loads((O/stage/cell/'OWNED_WORKER_HANDLES.json').read_text())
for folder in ['B_operator_v1','B_operator_sorted_v2']:handles+=json.loads((O/folder/'OWNED_WORKER_HANDLES.json').read_text())
for h in handles:
 p=Path('/proc',str(h['pid']),'stat')
 if p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']):live.append(h)
assert not live
print(json.dumps({'status':'PASS_ALL_OWNED_GPU_WORKERS_RELEASED','time_unix':time.time(),'worker_handle_observations':len(handles),'live_original_workers':live,'current_GPU_processes':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True),'D_complete':json.loads((O/'D_SEQUENCE_SUMMARY.json').read_text())['status'],'new_GPU_jobs_after_D':False}))
PY
