"""Inspect public archive central directories with bounded official HTTP ranges."""
import pathlib,json,urllib.request,urllib.error,hashlib,struct,datetime
O=pathlib.Path(__file__).resolve().parents[1]/'public_asset_metadata_v3';O.mkdir(exist_ok=False)
releases=[('playwithmino/StreamCorrect','16f6fd1e17418f1c4111a18fdd39543813206d96'),('playwithmino/qwen3asr_0p6b_correctors_20260525_hf_clean','80ec90cd2032c9f5f95b98db3f6a2a7a94a168d5')]
records=[]
def get(url,headers=None,limit=5_000_000):
 req=urllib.request.Request(url,headers={'User-Agent':'RevTrace-public-release-inspection',**(headers or {})})
 with urllib.request.urlopen(req,timeout=35) as r:
  b=r.read(limit+1)
  if len(b)>limit:raise ValueError('bounded metadata response exceeded')
  return b,dict(r.headers),r.status
for idx,(repo,rev) in enumerate(releases):
 row={'repo':repo,'revision':rev}
 try:
  b,h,s=get(f'https://huggingface.co/api/datasets/{repo}/tree/{rev}?recursive=true&expand=false')
  (O/f'tree_{idx}.json').write_bytes(b);tree=json.loads(b);row['files']=tree
  z=next(x for x in tree if x['path'].endswith('.zip') and not x['path'].startswith('large-'))
  url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/{z["path"]}'
  size=z['size'];start=max(0,size-65577)
  tail,headers,status=get(url,{'Range':f'bytes={start}-{size-1}'},limit=70000)
  assert status==206 and len(tail)==size-start,(status,len(tail))
  (O/f'zip_tail_{idx}.bin').write_bytes(tail)
  off=tail.rfind(b'PK\x05\x06');assert off>=0
  eocd=struct.unpack_from('<4s4H2LH',tail,off);cdsize=eocd[5];cdstart=eocd[6]
  row['zip_range']={'bytes':len(tail),'status':status,'content_range':headers.get('Content-Range'),'size':size,'directory_size':cdsize,'directory_start':cdstart}
  if cdsize==0xffffffff or cdstart==0xffffffff:
   z64=tail.rfind(b'PK\x06\x06');assert z64>=0
   r=struct.unpack_from('<4sQ2H2L4Q',tail,z64);cdsize=r[-2];cdstart=r[-1]
   row['zip_range'].update(directory_size=cdsize,directory_start=cdstart,zip64=True)
  if cdsize>4_000_000:raise ValueError('central directory exceeds metadata budget')
  data,_,stat=get(url,{'Range':f'bytes={cdstart}-{cdstart+cdsize-1}'},limit=4_000_000)
  assert stat==206 and len(data)==cdsize
  (O/f'zip_directory_{idx}.bin').write_bytes(data)
  pos=0;entries=[]
  while pos<len(data):
   v=struct.unpack_from('<4s6H3L5H2L',data,pos);assert v[0]==b'PK\x01\x02'
   n,e,c=v[10:13];name=data[pos+46:pos+46+n].decode('utf-8');extra=data[pos+46+n:pos+46+n+e]
   item=dict(path=name,method=v[4],compressed=v[8],bytes=v[9],local_offset=v[-1],crc32=v[7],extra=extra.hex())
   entries.append(item);pos+=46+n+e+c
  (O/f'ARCHIVE_ENTRIES_{idx}.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
  row['entries_count']=len(entries);row['relevant_entries']=[x for x in entries if any(k in x['path'].lower() for k in ['adapter','corrector','config','readme','license','testset'])][:160]
 except Exception as e:row['error']=type(e).__name__+': '+str(e)
 records.append(row)
summary=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu_launched=False,weights_downloaded=False,archives=records)
(O/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
