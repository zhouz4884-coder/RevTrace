"""Tiny non-secret acquisition status, never temporary download URLs."""
import json
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
out={}
if (O/'ACTIVE_DOWNLOAD_HANDLE.json').exists():
 h=json.loads((O/'ACTIVE_DOWNLOAD_HANDLE.json').read_text());p=Path('/proc',str(h['pid']))
 try:alive=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==h['start_ticks']
 except FileNotFoundError:alive=False
 out.update(handle=h,exact_process_live=alive)
for n in ['GATE.json','PROGRESS.json','ASSET_MANIFEST.json']:
 if (O/n).exists():
  d=json.loads((O/n).read_text());out[n]={k:v for k,v in d.items() if k not in ['files','frames']}
  if 'files' in d:out[n]['completed_files']=len(d['files'])
if (O/'PUBLIC_PLAN.json').exists():
 plan=json.loads((O/'PUBLIC_PLAN.json').read_text());active=[]
 for r in plan['files']:
  p=Path(r['path']);partial=p.with_name(p.name+'.partial')
  if partial.exists():active.append(dict(file=p.name,partial_bytes=partial.stat().st_size,total_bytes=r['bytes']))
 out['partials']=active
out['old_failure_gate_is_not_worker_death']=True
print(json.dumps(out))
