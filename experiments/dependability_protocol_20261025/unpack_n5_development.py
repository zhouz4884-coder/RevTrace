from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;p=W/'n5_development_evidence_v2.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c272a6536b49f13731d76fea3c6f40e1b61076ec3d0f615d56d4d306aba6969b'
O=W/'n5_development_collected_v2';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isdir() or m.isfile();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
for r in json.loads((O/'DEVELOPMENT_RAW_INDEX_v1.json').read_text())['files']:
 q=O/r['path'];assert q.stat().st_size==r['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
print('PASS_RAW_BYTES_12_DEVELOPMENT_CELLS')
