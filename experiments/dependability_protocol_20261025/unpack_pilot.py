from pathlib import Path
import hashlib,tarfile
W=Path(__file__).resolve().parent;p=W/'pilot_evidence_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='a397ea51e073d01b07e950ad764592e6d002b5f0782baefc6bda31073b0688a6'
O=W/'pilot_collected';O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    for m in t.getmembers():
        assert m.isdir() or m.isfile()
        (O/m.name).resolve().relative_to(O.resolve())
    t.extractall(O,filter='data')
print(O)
