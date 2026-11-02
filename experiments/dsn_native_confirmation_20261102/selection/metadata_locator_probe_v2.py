"""Bounded read-only metadata-location probe; never opens audio/model/results."""
from pathlib import Path
import hashlib
import importlib.util
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
helper=ROOT/'experiments/dsn_continuity_cost_20261102/ops/remote.py'
spec=importlib.util.spec_from_file_location('approved_selection_location_transport',helper)
remote=importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)
SCRIPT=r'''
import datetime,json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
relative=['datasets/modelscope-cache','datasets/hf_cache','datasets/repos','datasets/revtrace/final_quality',
'datasets/revtrace/phaseD_20261021','datasets/revtrace/dsn_whisper_20261006','datasets/revtrace/dsn_feedback_20261005',
'datasets/revtrace/native_sustained_20261030','datasets/revtrace/streamcorrect_adaptation_20261028/audio',
'datasets/tc_live_20260906']
out=[]
for name in relative:
 p=B/name
 if not p.exists():out.append(dict(path=str(p),exists=False));continue
 rows=sorted(p.iterdir(),key=lambda x:x.name)
 item=dict(path=str(p),exists=True,total_entries=len(rows),entries=[dict(name=x.name,directory=x.is_dir(),bytes=x.stat().st_size if x.is_file() else None) for x in rows[:100]])
 if name in ['datasets/modelscope-cache','datasets/hf_cache','datasets/repos','datasets/revtrace/final_quality']:
  item['subdirectories']=[]
  for q in rows[:30]:
   if q.is_dir():
    sub=sorted(q.iterdir(),key=lambda x:x.name)
    item['subdirectories'].append(dict(path=str(q),total_entries=len(sub),entries=[dict(name=x.name,directory=x.is_dir(),bytes=x.stat().st_size if x.is_file() else None) for x in sub[:60]]))
 out.append(item)
print(json.dumps(dict(scope='Read-only bounded directory/stat prerequisite locator only; no formal census, audio/model access or selection',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),locations=out)))
'''
if __name__=='__main__':
    with remote.Remote() as client:
        result=json.loads(client.python(SCRIPT,timeout=60))
    result['local_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=HERE/'REMOTE_METADATA_LOCATORS_v2.json'
    if out.exists():raise RuntimeError('Refusing to overwrite observation')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(scope=result['scope'],locations=len(result['locations']),output=str(out))))
