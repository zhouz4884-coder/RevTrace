"""Bounded public release/model metadata and native ASR ZIP directory."""
import pathlib,json,urllib.request,struct,hashlib
T=pathlib.Path(__file__).resolve().parents[1];O=T/'asset_inventory_v2';O.mkdir(exist_ok=False)
def get(url,headers=None,limit=2_000_000):
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers or {}),timeout=35) as r:
  b=r.read(limit+1);assert len(b)<=limit;return b,r.status
repo='fixie-ai/ultravox-v0_5-llama-3_2-1b';rev='b95bec8ab291eeb04b5cd600dd473377f6b79026'
b,_=get(f'https://huggingface.co/api/models/{repo}/tree/{rev}?recursive=true&expand=false')
(O/'BASE_TREE.json').write_bytes(b);x=json.loads(b)
for row in x:
 if row['path'].endswith(('.py','.json','.md')) and not row['path'].startswith('.') and row['size']<=300000:
  a,_=get(f'https://huggingface.co/{repo}/resolve/{rev}/{row["path"]}',limit=300000)
  (O/row['path']).write_bytes(a)
size=5728245750;url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/large-v2-zh.pt.zip'
tail,status=get(url,{'Range':f'bytes={size-65577}-{size-1}'},limit=65577);assert status==206
off=tail.rfind(b'PK\x05\x06');v=struct.unpack_from('<4s4H2LH',tail,off);n=v[5];start=v[6]
if n==0xffffffff or start==0xffffffff:
 off=tail.rfind(b'PK\x06\x06');v=struct.unpack_from('<4sQ2H2L4Q',tail,off);n=v[-2];start=v[-1]
b,status=get(url,{'Range':f'bytes={start}-{start+n-1}'},limit=2_000_000);assert status==206
(O/'ASR_ZIP_DIRECTORY.bin').write_bytes(b);entries=[];i=0
while i<len(b):
 v=struct.unpack_from('<4s6H3L5H2L',b,i);assert v[0]==b'PK\x01\x02';na,ne,nc=v[10:13]
 extra=b[i+46+na:i+46+na+ne];name=b[i+46:i+46+na].decode('utf-8')
 row=dict(path=name,method=v[4],compressed=v[8],bytes=v[9],local_offset=v[-1],crc32=v[7],extra=extra.hex())
 if row['compressed']==0xffffffff or row['bytes']==0xffffffff or row['local_offset']==0xffffffff:
  j=0
  while j<len(extra):
   typ,ln=struct.unpack_from('<HH',extra,j);payload=extra[j+4:j+4+ln];j+=4+ln
   if typ!=1:continue
   pos=0
   for key in ('bytes','compressed','local_offset'):
    if row[key]==0xffffffff:row[key]=struct.unpack_from('<Q',payload,pos)[0];pos+=8
 entries.append(row);i+=46+na+ne+nc
(O/'ASR_ENTRIES.json').write_text(json.dumps(entries,indent=2))
print(json.dumps(dict(base_files=[dict(path=r['path'],bytes=r['size'],lfs=r.get('lfs')) for r in x],asr_entries=entries),indent=2))
