"""Validate exact archive bytes and extract only regular bounded evidence."""
from pathlib import Path, PurePosixPath
import json,tarfile,hashlib
W=Path(__file__).resolve().parent
meta=json.loads((W/'BOUNDED_METADATA_v1.json').read_text())
archive=W/'BOUNDED_EVIDENCE_v1.tar.gz'
assert archive.stat().st_size==meta['archive_bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['archive_sha256']
dest=W/'collected_v6';assert not dest.exists()
with tarfile.open(archive,'r:gz') as t:
    members=t.getmembers();assert len(members)==meta['bounded_files']
    assert len({m.name for m in members})==len(members)
    for m in members:
        p=PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts
        assert ':' not in m.name and '\\' not in m.name
        assert m.size<100_000_000
    dest.mkdir()
    t.extractall(dest,filter='data')
index=json.loads((dest/'RAW_INDEX_v1.json').read_text())
lookup={r['path']:r for r in index['files']}
matched=0
for f in dest.rglob('*'):
    if not f.is_file():continue
    rel=f.relative_to(dest).as_posix()
    if rel=='RAW_INDEX_v1.json':continue
    r=lookup[rel]
    assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
    matched+=1
record=dict(status='PASS_ARCHIVE_AND_ALL_INCLUDED_FILE_HASHES',archive_sha256=meta['archive_sha256'],
            included_files_verified_against_raw_index=matched,bounded_files=meta['bounded_files'])
(W/'LOCAL_EVIDENCE_IDENTITY_v1.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
