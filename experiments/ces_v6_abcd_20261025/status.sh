set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,time
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025')
r={'time_unix':time.time()}
for n in ['SOURCE_EXPOSURE_AUDIT.json','B_GPU_STARTED.json','B_SUMMARY.json','B_STOP.json','B_sorted_GPU_STARTED.json','B_SORTED_SUMMARY.json','B_sorted_STOP.json','ABC_STARTED.json','ABC_SUMMARY.json','ABC_STOP.json','A_pilot_PROGRESS.json','A_pilot_SUMMARY.json','A_pilot_STOP.json','A_PROGRESS.json','A_SUMMARY.json','A_STOP.json','C_PROGRESS.json','C_SUMMARY.json','C_STOP.json','NEXT_STAGES_STARTED.json','NEXT_STAGES_SUMMARY.json','NEXT_STAGES_STOP.json','D_development_PROGRESS.json','D_development_SUMMARY.json','D_development_STOP.json','D_heldout_PROGRESS.json','D_heldout_SUMMARY.json','D_heldout_STOP.json','D_SEQUENCE_SUMMARY.json','D_SEQUENCE_STOP.json']:
 p=O/n
 if p.exists():
  d=json.loads(p.read_text());d.pop('scanned_manifests',None);d.pop('input_files',None)
  if 'completed' in d:d['completed_count']=len(d['completed']);d['last_completed']=d['completed'][-2:];del d['completed']
  r[n]=d
r['processes']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True)
for name in ['ABC_CONTROLLER.log','C_CONTROLLER.log','B_sorted_CONTROLLER.log','POST_ABC.log','D_SEQUENCE_CONTROLLER.log','D_development_CONTROLLER.log','D_heldout_CONTROLLER.log']:
 p=O/name
 if p.exists():r[name+'_tail']=p.read_text(errors='replace')[-2200:]
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except (OSError,ProcessLookupError):continue
 if 'revtrace_ces_v6_abcd_20261025/prepare_sources.py' in cmd:active.append({'pid':int(p.name),'command':'prepare_sources.py'})
r['source_preparation_processes']=active
print(json.dumps(r))
PY
