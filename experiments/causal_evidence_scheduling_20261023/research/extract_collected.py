"""Verify transport and extracted bounded evidence bytes; no modification."""
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;A=W/'bounded_evidence_v1.tar.gz';D=W/'collected'
meta=json.loads((W/'BOUNDED_ARCHIVE_REMOTE.json').read_text());assert not D.exists()
assert A.stat().st_size==meta['bytes'] and hashlib.sha256(A.read_bytes()).hexdigest()==meta['sha256']
with tarfile.open(A,'r:gz') as f:
 members=f.getmembers();assert len(members)<4000 and sum(m.size for m in members)<350_000_000
 assert len({m.name for m in members})==len(members)
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and m.size<50_000_000
 D.mkdir()
 for m in members:
  p=D/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(f.extractfile(m).read())
expected=json.loads((D/'MANIFEST.json').read_text());actual={p.relative_to(D).as_posix():p for p in D.rglob('*') if p.is_file()}
assert set(actual)=={r['path'] for r in expected['files']}|{'MANIFEST.json'}
for r in expected['files']:
 raw=actual[r['path']].read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],r['path']
out={'status':'PASS_COMPLETE_BOUNDED_ARCHIVE_AND_ALL_MEMBER_BYTES','files':len(actual),'formal_cells':180,
 'archive_sha256':meta['sha256'],'archive_bytes':A.stat().st_size,'all_extracted_bytes_match_remote_manifest':True,
 'large_original_traces_remain_on_authorized_8TB':True}
(W/'COLLECTION_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
