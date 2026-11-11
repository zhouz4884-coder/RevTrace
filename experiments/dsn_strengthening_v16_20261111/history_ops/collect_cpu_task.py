from pathlib import Path
import argparse,hashlib,importlib.util,json,time
p=argparse.ArgumentParser();p.add_argument('--launch',required=True);p.add_argument('--name',required=True);a=p.parse_args()
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
record=json.loads((H/a.launch).read_bytes())
with m.Remote() as c:
 script='L='+repr(record)+'\n'+r'''
from pathlib import Path
import hashlib,json
O=Path(L['raw_result_location']);g=O/'GATE.json';proc=Path('/proc/'+str(L['pid'])+'/stat')
if not g.exists():
 print(json.dumps(dict(ready=False,same_process_identity=proc.exists() and proc.read_text().split()[21]==L['start_ticks'],log_tail=Path(L['log']).read_text()[-4000:])));raise SystemExit()
files=list(O.glob('*.json'))+list(O.glob('*.log'))+list(O.glob('*.csv'))
print(json.dumps(dict(ready=True,gate=json.loads(g.read_bytes()),files=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])))
'''
 raw=c.python(script,timeout=60);j=json.loads(raw)
 if not j['ready']:print(raw.decode());raise SystemExit()
 assert sum(x['bytes'] for x in j['files'])<20000000
 target=H/'results'/a.name;target.mkdir(parents=True,exist_ok=True)
 for r in j['files']:
  blob=c.get(r['path'],target/Path(r['path']).name,maximum=20000000)
  assert len(blob)==r['bytes'] and hashlib.sha256(blob).hexdigest()==r['sha256']
 receipt=target/'DOWNLOAD_VERIFICATION.json'
 if not receipt.exists():receipt.write_text(json.dumps(j['files'],indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(local=str(target),files=len(j['files']),bytes=sum(x['bytes'] for x in j['files']),gate=j['gate'])))
