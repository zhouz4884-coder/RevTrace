"""Read-only AISHELL cache/legacy-location prerequisite probe, no corpus scan."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
helper=ROOT/'experiments/dsn_continuity_cost_20261102/ops/remote.py'
spec=importlib.util.spec_from_file_location('approved_selection_locator3',helper);remote=importlib.util.module_from_spec(spec);spec.loader.exec_module(remote)
SCRIPT=r'''
import datetime,json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
targets=[B/'datasets/modelscope-cache/datasets/modelscope',B/'revtrace',B/'RevTrace',B/'projects/revtrace',B/'projects/RevTrace']
out=[]
for p in targets:
 item=dict(path=str(p),exists=p.exists())
 if p.is_dir():
  rows=sorted(p.iterdir(),key=lambda x:x.name);item.update(total_entries=len(rows),entries=[dict(name=q.name,directory=q.is_dir()) for q in rows[:100]])
  if 'modelscope-cache' in str(p):
   item['children']=[]
   for q in rows[:20]:
    if q.is_dir():
     sub=sorted(q.iterdir(),key=lambda x:x.name);item['children'].append(dict(path=str(q),entries=[dict(name=x.name,directory=x.is_dir()) for x in sub[:50]],total_entries=len(sub)))
 out.append(item)
print(json.dumps(dict(scope='Bounded named-directory availability only, not source selection/formal census',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),locations=out)))
'''
if __name__=='__main__':
 with remote.Remote() as client:result=json.loads(client.python(SCRIPT,timeout=60))
 result['local_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();out=HERE/'REMOTE_METADATA_LOCATORS_v3.json'
 if out.exists():raise RuntimeError('Observation already exists')
 out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result,indent=2))
