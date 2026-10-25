from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;p=W/'n5_recovery_development_evidence_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='ddceb778c21eb3b4b12afe9f9049df5b498f62aa02f6b369818212275cbfb6a7'
O=W/'n5_recovery_development_collected_v1';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() or m.isdir();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
index=json.loads((O/'RECOVERY_RAW_INDEX_v1.json').read_text())
for r in index['files']:
 q=O/r['path'];assert q.stat().st_size==r['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
print('PASS_RECOVERY_RAW_BYTES',len(index['files']))
