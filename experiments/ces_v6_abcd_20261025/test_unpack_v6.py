"""CPU-only transport fixtures; never counted as serving or GPU evidence."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fixture(tmp):
 spec=importlib.util.spec_from_file_location('collector',HERE/'collect_v6_v2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 root=tmp/'collection';root.mkdir();raw=tmp/'raw';raw.write_bytes(b'crlf\r\nlf\n\x00\xffend')
 rec=m.compress_file(raw,root,'results/one/raw.bin')
 (root/'PAYLOADS.json').write_text(json.dumps({'logical_files':[rec]}));(root/'RAW_INDEX.json').write_text('{}')
 tar=root/'evidence-000.tar'
 with tarfile.open(tar,'w') as tf:
  for f in [root/r['path'] for r in rec['parts']]+[root/'PAYLOADS.json',root/'RAW_INDEX.json']:tf.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
 index={'archives':[{'path':tar.name,'bytes':tar.stat().st_size,'sha256':sha(tar)}],'PAYLOADS_sha256':sha(root/'PAYLOADS.json'),'RAW_INDEX_sha256':sha(root/'RAW_INDEX.json')}
 (root/'COLLECTION.json').write_text(json.dumps(index));return root,raw
def test_reassembly_roundtrip_is_byte_exact(tmp_path):
 root,raw=fixture(tmp_path);out=tmp_path/'out'
 r=subprocess.run([sys.executable,str(HERE/'unpack_v6.py'),'--collection',str(root),'--output',str(out)],capture_output=True,text=True)
 assert r.returncode==0,r.stderr
 assert (out/'results/one/raw.bin').read_bytes()==raw.read_bytes()
 assert json.loads((out/'LOCAL_BYTES_VERIFIED.json').read_text())['logical_files']==1
def test_tampered_archive_fails_without_complete_receipt(tmp_path):
 root,_=fixture(tmp_path);path=root/'evidence-000.tar';data=bytearray(path.read_bytes());data[600]^=1;path.write_bytes(data);out=tmp_path/'out'
 r=subprocess.run([sys.executable,str(HERE/'unpack_v6.py'),'--collection',str(root),'--output',str(out)],capture_output=True,text=True)
 assert r.returncode!=0 and not (out/'LOCAL_BYTES_VERIFIED.json').exists()
