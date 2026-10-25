"""Reassemble bounded evidence exactly; fail closed on archive or logical hashes."""
from pathlib import Path,PurePosixPath
import argparse,gzip,hashlib,json,tarfile
p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();D=a.collection;out=a.output
assert not out.exists();out.mkdir();parts=out/'_compressed';parts.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=json.loads((D/'COLLECTION.json').read_text())
for r in index['archives']:
 path=D/r['path'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
 with tarfile.open(path) as tf:
  for m in tf.getmembers():
   rel=PurePosixPath(m.name);assert not rel.is_absolute() and '..' not in rel.parts and m.isfile()
   target=parts.joinpath(*rel.parts);target.resolve().relative_to(parts.resolve());assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:f.write(tf.extractfile(m).read())
assert sha(parts/'PAYLOADS.json')==index['PAYLOADS_sha256'] and sha(parts/'RAW_INDEX.json')==index['RAW_INDEX_sha256']
payloads=json.loads((parts/'PAYLOADS.json').read_text())['logical_files'];verified=[]
for r in payloads:
 rel=PurePosixPath(r['logical_path']);assert not rel.is_absolute() and '..' not in rel.parts
 path=out.joinpath(*rel.parts);path.resolve().relative_to(out.resolve());path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists()
 h=hashlib.sha256();size=0
 with path.open('xb') as f:
  for part in r['parts']:
   src=parts/part['path'];assert src.stat().st_size==part['bytes'] and sha(src)==part['sha256']
   data=gzip.decompress(src.read_bytes());assert len(data)==part['uncompressed_bytes'];h.update(data);size+=len(data);f.write(data)
 assert size==r['raw_bytes'] and h.hexdigest()==r['raw_sha256'];verified.append({'path':r['logical_path'],'sha256':h.hexdigest(),'bytes':size})
report={'status':'PASS_COMPLETE_BYTE_REASSEMBLY','logical_files':len(verified),'raw_bytes':sum(r['bytes'] for r in verified),'collection_sha256':sha(D/'COLLECTION.json'),'new_GPU_calls':0,'files':verified}
(out/'LOCAL_BYTES_VERIFIED.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'}))
