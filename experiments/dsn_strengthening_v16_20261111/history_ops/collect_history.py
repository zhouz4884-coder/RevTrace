"""Download only bounded audited CPU results; retain full text/event raw on8TB."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
launch=json.loads((H/'PROCESS_LAUNCH_v1.json').read_bytes())
audit=H/'AUDIT_PROCESS_LAUNCH_v1.json';second=json.loads(audit.read_bytes()) if audit.exists() else None
with m.Remote() as c:
 for name,record in [('PRIMARY_v1',launch),('INDEPENDENT_v1',second)]:
  if record is None:continue
  remote=record['raw_result_location']
  raw=c.python('O='+repr(remote)+'\n'+r'''
from pathlib import Path
import hashlib,json
O=Path(O);g=O/'GATE.json'
assert g.exists(),'CPU gate pending'
paths=list(O.glob('*.json'))+list(O.glob('*.log'))
print(json.dumps([dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]))
''',timeout=60)
  manifest=json.loads(raw);assert sum(x['bytes'] for x in manifest)<20000000
  target=H/'results'/name;target.mkdir(parents=True,exist_ok=True)
  for r in manifest:
   p=target/Path(r['path']).name;blob=c.get(r['path'],p,maximum=20000000)
   assert len(blob)==r['bytes'] and hashlib.sha256(blob).hexdigest()==r['sha256']
  receipt=target/'DOWNLOAD_VERIFICATION.json'
  if not receipt.exists():receipt.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
  print(json.dumps(dict(role=name,local=str(target),files=len(manifest),bytes=sum(x['bytes'] for x in manifest),gate=json.loads((target/'GATE.json').read_bytes()))))
