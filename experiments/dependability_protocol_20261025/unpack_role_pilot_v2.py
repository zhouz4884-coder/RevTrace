from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent
p=W/'role_pilot_evidence_v2.tar.gz';O=W/'role_pilot_collected_v2'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='9320ca37584c558ca2e41ac7c82984859664e4fd730ae4187b67cfa916802ec3'
O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
 for m in t:
  assert m.isfile() or m.isdir()
  (O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
idx=json.loads((O/'PILOT_RAW_INDEX_v1.json').read_text())
for r in idx['files']:
 p=O/r['path'];assert p.stat().st_size==r['bytes']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
print(json.dumps(dict(verified_files=len(idx['files']),archive_sha256='9320ca37584c558ca2e41ac7c82984859664e4fd730ae4187b67cfa916802ec3')))
