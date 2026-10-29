"""Metadata-only public HF fallback; no weights or user secrets."""
import pathlib,urllib.request,urllib.error,json,hashlib,datetime
O=pathlib.Path(__file__).resolve().parents[1]/'public_asset_metadata_v2';O.mkdir(exist_ok=False)
urls=[
 'https://huggingface.co/api/datasets?author=playwithmino&limit=100',
 'https://huggingface.co/api/models?author=playwithmino&limit=100',
 'https://huggingface.co/api/datasets/playwithmino/qwen3asr_0p6b_correctors_20260525_hf_clean',
 'https://huggingface.co/api/datasets/playwithmino/StreamCorrect',
 'https://huggingface.co/api/datasets/playwithmino/StreamCorrect_internal',
]
rows=[]
for i,url in enumerate(urls):
 row={'url':url}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RevTrace-public-metadata-research'}),timeout=20) as r:
   data=r.read(4_000_001);assert len(data)<4_000_001
   (O/f'response_{i}.json').write_bytes(data);body=json.loads(data)
   row.update(status=r.status,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
   if isinstance(body,list):row['entries']=[x.get('id') for x in body]
   else:row['identity']={k:body.get(k) for k in ('id','sha','private','gated','cardData','siblings')}
 except Exception as e:row['error']=type(e).__name__+': '+str(e)
 rows.append(row)
summary={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpu_launched':False,'weights_downloaded':False,'requests':rows}
(O/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
