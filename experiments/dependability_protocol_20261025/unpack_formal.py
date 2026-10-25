from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;p=W/'formal_evidence_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c5ee313a7d32949d4e1d44cd83640eec7241738973c69731a58375af765f6913'
O=W/'formal_collected';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    for m in t.getmembers():
        assert m.isdir() or m.isfile()
        (O/m.name).resolve().relative_to(O.resolve())
    t.extractall(O,filter='data')
idx=json.loads((O/'FORMAL_RAW_INDEX_v1.json').read_text())
for r in idx['files']:
    f=O/r['path'];assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
print(json.dumps({'bytes_verified_files':len(idx['files']),'cells':idx['cells']}))
