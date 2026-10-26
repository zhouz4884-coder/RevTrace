from pathlib import Path
import argparse,hashlib,json,tarfile
ap=argparse.ArgumentParser();ap.add_argument('--sha256',required=True);a=ap.parse_args()
W=Path(__file__).resolve().parent;p=W/'role_formal_evidence_v2.tar.gz';O=W/'role_formal_collected_v2'
assert hashlib.sha256(p.read_bytes()).hexdigest()==a.sha256
O.mkdir(exist_ok=False)
with tarfile.open(p) as t:
 for m in t:
  assert m.isfile() or m.isdir();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
idx=json.loads((O/'FORMAL_RAW_INDEX_v1.json').read_text())
for r in idx['files']:
 p=O/r['path'];assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
assert json.loads((O/'formal/SUMMARY.json').read_text())['cells']==64
print(json.dumps(dict(verified_files=len(idx['files']),archive_sha256=a.sha256)))
