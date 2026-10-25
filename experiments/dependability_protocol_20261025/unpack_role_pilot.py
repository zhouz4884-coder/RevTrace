from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;p=W/'role_pilot_evidence_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='6ef95fb39aee244ffd8490c57ec33a6353a76eb7cf9b3b6f7bb23181a76b7a45'
O=W/'role_pilot_collected_v1';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isdir() or m.isfile();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
index=json.loads((O/'PILOT_RAW_INDEX_v1.json').read_text())
for r in index['files']:
 q=O/r['path'];assert q.stat().st_size==r['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
print('PASS_ROLE_PILOT_RAW_BYTES',len(index['files']))
