"""Hash-check bounded archive parts and stream-extract only safe regular files."""
from pathlib import Path
import hashlib,json,tarfile
from make_delivery import ConcatenatedReader
W=Path(__file__).resolve().parent;index=json.loads((W/'BOUNDED_INDEX.json').read_text());out=W/'collected'
assert index['status']=='COMPLETE_BOUNDED_72_FORMAL_COLLECTION_NO_NEW_GPU' and not out.exists()
paths=[];full=hashlib.sha256();total=0
for r in index['publish_files']:
 p=W/'artifact_parts'/Path(r['path']).name;h=hashlib.sha256()
 assert p.stat().st_size==r['bytes']
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b);full.update(b);total+=len(b)
 assert h.hexdigest()==r['sha256'];paths.append(p)
assert total==index['full_archive_bytes'] and full.hexdigest()==index['full_archive_sha256']
out.mkdir();n=0
with ConcatenatedReader(paths) as stream,tarfile.open(fileobj=stream,mode='r|gz') as tf:
 for m in tf:
  target=(out/m.name).resolve();target.relative_to(out.resolve())
  assert m.isfile() and m.size<40_000_000 and not target.exists(),m.name
  tf.extract(m,path=out,filter='data');n+=1
manifest=json.loads((out/'MANIFEST.json').read_text());listed={r['path'] for r in manifest['files']}|{'MANIFEST.json'}
assert {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}==listed
for r in manifest['files']:
 p=out/r['path'];assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
assert hashlib.sha256((out/'MANIFEST.json').read_bytes()).hexdigest()==index['manifest_sha256']
assert hashlib.sha256((out/'RAW_INDEX.json').read_bytes()).hexdigest()==index['raw_index_sha256']
record={'status':'PASS_ARCHIVE_PARTS_AND_ALL_BOUNDED_FILE_HASHES','archive_sha256':full.hexdigest(),'files':n,
 'raw_index_sha256':index['raw_index_sha256'],'scope':'No model/audio download; immutable bounded evidence only'}
(W/'LOCAL_COLLECTION_VERIFIED.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
