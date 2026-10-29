"""Public licensed alternative-source metadata search; no model weights."""
import pathlib,json,urllib.request,urllib.error,hashlib,datetime
O=pathlib.Path(__file__).resolve().parents[1]/'modelscope_metadata_v1';O.mkdir(exist_ok=False)
urls=[
 'https://huggingface.co/api/models/meta-llama/Llama-3.2-1B-Instruct',
 'https://huggingface.co/api/models/meta-llama/Llama-3.2-1B-Instruct/tree/main?recursive=true&expand=false',
 'https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct',
 'https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo/files?Revision=master&Recursive=true',
 'https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo?Revision=master&FilePath=config.json',
 'https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo?Revision=master&FilePath=LICENSE.txt',
]
rows=[]
for i,url in enumerate(urls):
 row=dict(url=url)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RevTrace-public-research-metadata'}),timeout=25) as r:
   b=r.read(3_000_001);assert len(b)<=3_000_000
   (O/f'response_{i}.json').write_bytes(b)
   row.update(status=r.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
   if i in (0,1,3,4):
    x=json.loads(b)
    if i==0:row['summary']={k:x.get(k) for k in ('id','sha','gated','private','siblings')}
    elif i==1:row['summary']=x
    elif i==3:row['summary']=x
    elif i==4:row['summary']={k:x.get(k) for k in ('model_type','architectures','hidden_size','num_hidden_layers','num_attention_heads','num_key_value_heads','vocab_size')}
 except urllib.error.HTTPError as e:row.update(status=e.code,error='HTTPError')
 except Exception as e:row.update(status='ERROR',error=type(e).__name__)
 rows.append(row)
summary=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='ACTIVE_ALTERNATE_AUTHORIZED_SOURCE_SEARCH',model_weights_downloaded=False,gpu_launched=False,requests=rows)
(O/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
