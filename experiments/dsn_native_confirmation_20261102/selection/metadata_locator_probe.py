"""Read-only bounded directory/stat prerequisite probe; no corpus census/model."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
helper=ROOT/'experiments/dsn_continuity_cost_20261102/ops/remote.py'
spec=importlib.util.spec_from_file_location('approved_revtrace_remote_metadata_probe',helper)
remote=importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)

SCRIPT=r'''
import datetime,json,pathlib,sys
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
def directory(path,limit=100):
 if not path.exists():return dict(path=str(path),exists=False)
 entries=sorted(path.iterdir(),key=lambda p:p.name)
 return dict(path=str(path),exists=True,total_entries=len(entries),entries=[dict(name=p.name,directory=p.is_dir(),bytes=p.stat().st_size if p.is_file() else None) for p in entries[:limit]])
roots=[B/'datasets',B/'datasets/revtrace']
result=dict(scope='Read-only prerequisite location/stat probe, NOT a corpus census, source selection, formal analysis or model experiment',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,roots=[directory(p) for p in roots])
result['named_catalog_locations']=[]
for base in [B/'datasets',B/'datasets/revtrace']:
 if base.exists():
  for path in sorted(base.iterdir()):
   if path.is_dir() and any(word in path.name.lower() for word in ['aishell','streamcorrect','speech','source']):
    result['named_catalog_locations'].append(directory(path,80))
print(json.dumps(result))
'''

if __name__=='__main__':
    with remote.Remote() as client:
        raw=client.python(SCRIPT,timeout=60)
    result=json.loads(raw)
    result['local_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['approved_transport_helper_sha256']=hashlib.sha256(helper.read_bytes()).hexdigest()
    target=HERE/'REMOTE_METADATA_LOCATORS_v1.json'
    if target.exists():
        raise RuntimeError('Refusing to overwrite prerequisite observation')
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
