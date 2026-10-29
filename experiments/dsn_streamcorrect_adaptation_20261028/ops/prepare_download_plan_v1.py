"""Freeze only metadata-selected sources and exact public asset identities."""
import pathlib,json,urllib.request,urllib.parse,struct,zlib,io,wave,hashlib,datetime
T=pathlib.Path(__file__).resolve().parents[1];O=T/'download_plan_v1';O.mkdir(exist_ok=False)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
M=B+'/models/revtrace_streamcorrect_20261028';D=B+'/datasets/revtrace/streamcorrect_adaptation_20261028'
base_url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/StreamCorrect.zip'
entries=json.loads((T/'public_asset_metadata_v3/ARCHIVE_ENTRIES_0.json').read_text())
rows=sorted([x for x in entries if '/aishell1_testset/' in x['path'] and x['path'].endswith('.wav') and 8*32000+44<=x['bytes']<=15*32000+78],key=lambda x:x['path'])
selected=[];speakers=set();probes=[]
for row in rows:
 speaker=pathlib.PurePosixPath(row['path']).stem[6:11]
 if speaker in speakers:continue
 start=row['local_offset'];stop=start+4095
 req=urllib.request.Request(base_url,headers={'Range':f'bytes={start}-{stop}'})
 with urllib.request.urlopen(req,timeout=30) as r:b=r.read(4097);assert r.status==206 and len(b)==4096
 v=struct.unpack_from('<4s5H3L2H',b);assert v[0]==b'PK\x03\x04';pos=30+v[-2]+v[-1]
 raw=zlib.decompressobj(-15).decompress(b[pos:]) if row['method']==8 else b[pos:]
 with wave.open(io.BytesIO(raw)) as w:
  meta=dict(channels=w.getnchannels(),sample_width=w.getsampwidth(),sample_rate=w.getframerate(),frames=w.getnframes())
 duration=meta['frames']/meta['sample_rate'];probes.append(dict(path=row['path'],speaker=speaker,duration=duration,**meta))
 if meta['channels']!=1 or meta['sample_width']!=2 or meta['sample_rate']!=16000 or not 8<=duration<=15:continue
 selected.append(dict(source_id=pathlib.PurePosixPath(row['path']).stem,speaker_id=speaker,duration=duration,
   path=D+'/audio/'+pathlib.PurePosixPath(row['path']).name,archive_entry=row,**meta));speakers.add(speaker)
 if len(selected)==4:break
assert len(selected)==4
files=[]
base_tree=json.loads((T/'asset_inventory_v2/BASE_TREE.json').read_text())
for x in base_tree:
 if x['path'].startswith('.'):continue
 files.append(dict(path=M+'/ultravox_b95bec8/'+x['path'],bytes=x['size'],
   url='https://huggingface.co/fixie-ai/ultravox-v0_5-llama-3_2-1b/resolve/b95bec8ab291eeb04b5cd600dd473377f6b79026/'+x['path'],
   sha256=x.get('lfs',{}).get('oid'),git_blob_sha1=x.get('oid') if 'lfs' not in x else None))
ms=json.loads((T/'modelscope_metadata_v1/response_3.json').read_text())['Data']['Files']
for x in ms:
 if x['Type']!='blob' or '/' in x['Path'] or x['Path'].startswith('.') or x['Path']=='configuration.json':continue
 files.append(dict(path=M+'/llama32_1b_instruct_f8e6b/'+x['Path'],bytes=x['Size'],sha256=x['Sha256'],
   url='https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo?'+urllib.parse.urlencode({'Revision':x['Revision'],'FilePath':x['Path']})))
files.append(dict(path=B+'/cache/revtrace_streamcorrect_20261028/large-v2-zh.pt.zip',bytes=5728245750,
 sha256='ab30ddd181d1ab323711ea29d991f1d68ab9b6f0e43f5b8612f2dad6a65d07a4',
 url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/large-v2-zh.pt.zip'))
range_files=[]
for name,target in [('StreamCorrect/error_corrector_ckpt/adapter_model.safetensors',M+'/adapter/adapter_model.safetensors'),('StreamCorrect/error_corrector_ckpt/adapter_config.json',M+'/adapter/adapter_config.json'),('StreamCorrect/reference.json',D+'/reference.json')]:
 row=next(x for x in entries if x['path']==name);range_files.append(dict(path=target,url=base_url,entry=row))
for x in selected:range_files.append(dict(path=x['path'],url=base_url,entry=x['archive_entry']))
plan=dict(experiment_id='SC_NATIVE_ASSET_ACQUISITION_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 scope='public exact model acquisition and metadata-only source selection; no neural calls',
 model_root=M,dataset_root=D,files=files,range_files=range_files,selected_sources=selected,header_probes=probes,
 native_author_commit='bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3',
 original_meta_weight_pointer_proof=json.loads((T/'modelscope_metadata_v1/EXACT_WEIGHT_IDENTITY_PROOF.json').read_text()),
 io_policy='start only after explicit root idle-window message; models/data/cache/raw on designated disk')
(O/'PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
print(json.dumps(dict(selected_sources=[{k:v for k,v in x.items() if k!='archive_entry'} for x in selected],full_download_bytes=sum(x['bytes'] for x in files),range_compressed_bytes=sum(x['entry']['compressed'] for x in range_files),plan_sha256=hashlib.sha256((O/'PLAN.json').read_bytes()).hexdigest()),indent=2))
