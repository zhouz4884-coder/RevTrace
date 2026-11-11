"""Read-only CPU preregistration inventory; no model imports or launches."""
from pathlib import Path
import importlib.util, json, hashlib
E=Path(__file__).resolve().parents[1]; R=E.parents[1]
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
old=json.loads((R/'experiments/dsn_native_content_20261029/CONFIG_v1.json').read_bytes())
h3=json.loads((R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/aggregate/COVERAGE.json').read_bytes())
cells=[]
for c in old['cells']:
 cells.append(dict(cell_id=c['cell_id'],bank='native_old14',stage=c['stage'],arm=c['arm'],cohort=c['cohort'],repeat=c['repeat'],
  consumer_path=c['path']+'/consumer.jsonl',consumer_expected_sha256=c['expected']['consumer_sha256'],schema='native',
  original_final_lcp_path=None))
for c in h3:
 if c['phase']=='primary' and c['adapter']=='qwen' and c['rho']==1 and c['arrival']=='staggered':
  cells.append(dict(cell_id=c['cell_id'],bank='H3_primary24_qwen_staggered',stage='primary',arm=c['arm'],cohort=c['cohort'],repeat=c['repeat'],
   consumer_path=c['path']+'/attempt0/consumer.jsonl',schema='core'))
script="CELLS="+repr(cells)+"\n"+r'''
from pathlib import Path
import datetime,hashlib,json,platform,sys
rows=[]
for c in CELLS:
 p=Path(c['consumer_path']);r=dict(c,exists=p.is_file())
 if p.is_file():
  raw=p.read_bytes();r.update(bytes=len(raw),consumer_sha256=hashlib.sha256(raw).hexdigest())
  if c.get('consumer_expected_sha256'):assert r['consumer_sha256']==c['consumer_expected_sha256']
  first=json.loads(next(line for line in raw.decode('utf8').splitlines() if line.strip()))
  r['first_row_keys']=sorted(first)
 rows.append(r)
print(json.dumps(dict(record_type='READ_ONLY_PRELAUNCH_INPUT_INVENTORY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform()),cells=rows,new_model_calls=0)))
'''
with m.Remote() as c:raw=c.python(script,timeout=60)
p=E/'history_ops/INPUT_AVAILABILITY.json';assert not p.exists();p.write_bytes(raw+b'\n')
j=json.loads(raw)
print(json.dumps(dict(path=str(p),cells=len(j['cells']),available=sum(x['exists'] for x in j['cells']),
 schemas={k:next((x['first_row_keys'] for x in j['cells'] if x['schema']==k and x['exists']),None) for k in ('native','core')},
 total_bytes=sum(x.get('bytes',0) for x in j['cells']),environment=j['environment'],new_model_calls=0)))
