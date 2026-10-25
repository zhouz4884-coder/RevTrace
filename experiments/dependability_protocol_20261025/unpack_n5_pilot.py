from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;p=W/'n5_pilot_evidence_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='0daa05bbf0e473580a4f52663da27e2843c359896726b1e10778e0a60a09019b'
O=W/'n5_pilot_collected_v1';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    for m in t.getmembers():
        assert m.isdir() or m.isfile();(O/m.name).resolve().relative_to(O.resolve())
    t.extractall(O,filter='data')
index=json.loads((O/'PILOT_RAW_INDEX_v1.json').read_text())
for r in index['files']:
    q=O/r['path'];assert q.stat().st_size==r['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
print(json.dumps({'status':'PASS_RAW_BYTES','files':len(index['files'])}))
