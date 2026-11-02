"""Verify the declared model assets before allocating the normal NN cost window."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,B
R=E.parents[1];f=json.loads((R/'experiments/dsn_native_resilience_20261030/FROZEN_ENVIRONMENT_v2.json').read_bytes())
script='C='+repr(dict(base=B,manifest=f['assets_manifest_path'],sha=f['assets_manifest_sha256']))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess,time
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
manifest=Path(C['manifest']);assert hashlib.sha256(manifest.read_bytes()).hexdigest()==C['sha']
m=json.loads(manifest.read_bytes());checked=[];begin=time.perf_counter()
for r in m['files']:
 p=Path(r['path']);assert p.resolve().is_relative_to(Path(C['base']).resolve()) and p.is_file() and p.stat().st_size==r['bytes']
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 assert h.hexdigest()==r['sha256'],str(p)
 checked.append(dict(path=str(p),bytes=r['bytes'],sha256=r['sha256']))
print(json.dumps(dict(gate='PASS_DECLARED_MODEL_ASSET_BYTES',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest=str(manifest),manifest_sha256=C['sha'],files=len(checked),bytes=sum(r['bytes'] for r in checked),verification_wall_seconds=time.perf_counter()-begin,rows=checked,new_model_calls=0)))
'''
with Remote() as c:
 raw=c.python(script,timeout=120);result=json.loads(raw)
 p=E/'cost/ASSET_BYTE_GATE_v1.json';assert not p.exists();p.write_bytes(raw)
 print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
