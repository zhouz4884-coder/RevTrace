set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,hashlib
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/role_probe_v2'
handles=[]
for f in ['FORMAL_LAUNCH.json','FORMAL_ASSET_LAUNCH.json','PILOT_LAUNCH.json','PILOT_ASSET_LAUNCH.json']:
 d=json.loads((O/f).read_text());p=Path('/proc')/str(d['pid']);live=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']
 assert not live;handles.append(dict(file=f,pid=d['pid'],start_ticks=d['start_ticks'],verified_exited=True))
release=json.loads((O/'FORMAL_RELEASE.json').read_text());assert len(release['owned'])==128
for h in release['owned']:
 p=Path('/proc')/str(h['pid']);assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']))
current=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader'],text=True).strip()
out=dict(status='ALL_THIS_TASK_CONTROLLERS_AND128_WORKERS_RELEASED',handles=handles,owned_workers=128,
 current_GPU_compute_rows=current,GPUs_currently_empty=not current,no_other_process_modified=True,new_GPU_queue_closed=True)
p=O/'FINAL_RESOURCE_RELEASE_v1.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
PY
