"""Read small authored config/card entries; no pickle loading or GPU."""
import pathlib,json,urllib.request,hashlib,struct,zlib
T=pathlib.Path(__file__).resolve().parents[1]
rows=json.loads((T/'public_asset_metadata_v3/ARCHIVE_ENTRIES_0.json').read_text())
O=T/'author_checkpoint_metadata_v1';O.mkdir(exist_ok=False)
url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/StreamCorrect.zip'
records=[]
for row in rows:
 if row['path'] not in ('StreamCorrect/error_corrector_ckpt/README.md','StreamCorrect/error_corrector_ckpt/adapter_config.json'):continue
 start=row['local_offset'];stop=start+row['compressed']+4095
 req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{stop}','User-Agent':'RevTrace-public-metadata-research'})
 with urllib.request.urlopen(req,timeout=35) as r:
  assert r.status==206
  blob=r.read(row['compressed']+4097);assert len(blob)<=row['compressed']+4096
 v=struct.unpack_from('<4s5H3L2H',blob,0);assert v[0]==b'PK\x03\x04'
 pos=30+v[-2]+v[-1];payload=blob[pos:pos+row['compressed']]
 b=zlib.decompress(payload,-15) if row['method']==8 else payload
 assert len(b)==row['bytes'] and zlib.crc32(b)==row['crc32']
 (O/pathlib.PurePosixPath(row['path']).name).write_bytes(b)
 records.append(dict(**row,sha256=hashlib.sha256(b).hexdigest()))
(O/'MANIFEST.json').write_text(json.dumps(records,indent=2))
for p in O.iterdir():
 if p.name!='MANIFEST.json':print(p.name+'\n'+p.read_text())
