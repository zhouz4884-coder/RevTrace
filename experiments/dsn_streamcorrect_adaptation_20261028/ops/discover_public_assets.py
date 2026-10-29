"""Read public author release metadata; no GPU/model download and no credentials."""
import hashlib,json,pathlib,subprocess,urllib.request,urllib.error,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_streamcorrect_20261028'
O=B/'results/revtrace/dsn_streamcorrect_20261028/public_asset_discovery_v1'
O.mkdir(parents=True,exist_ok=False);P.mkdir(parents=True,exist_ok=True)
record={'experiment_id':'SC_PUBLIC_ASSET_DISCOVERY_V1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpu_launched':False,'requests':[]}
urls=[
 'https://api.github.com/repos/vu-duy-tung/StreamCorrect/commits/main',
 'https://api.github.com/users/vu-duy-tung',
 'https://huggingface.co/api/datasets?author=playwithmino&limit=100',
 'https://huggingface.co/api/models?author=playwithmino&limit=100',
 'https://huggingface.co/api/datasets?search=StreamCorrect&limit=100',
 'https://huggingface.co/api/models?search=StreamCorrect&limit=100',
]
for i,url in enumerate(urls):
 row={'url':url}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RevTrace-research-public-asset-check'}),timeout=25) as r:
   data=r.read(3_000_001);assert len(data)<3_000_001
   (O/f'response_{i}.json').write_bytes(data)
   body=json.loads(data);row.update(status=r.status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
   if isinstance(body,list):row['entries']=[x.get('id',x.get('name')) for x in body]
   elif 'commit' in body:row['commit']=body.get('sha')
   else:row['metadata']={k:body.get(k) for k in ['login','name','blog','bio']}
 except Exception as e:row.update(error=type(e).__name__+': '+str(e))
 record['requests'].append(row)
repo=P/'author_StreamCorrect_bbb9f7f'
assert not repo.exists()
subprocess.run(['git','clone','--no-checkout','https://github.com/vu-duy-tung/StreamCorrect.git',str(repo)],check=True,capture_output=True)
subprocess.run(['git','-C',str(repo),'checkout','--detach','bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3'],check=True,capture_output=True)
record['author_commit']=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
record['author_status']=subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=all'],text=True)
record['code_path']=str(repo)
record['source_files']=[dict(path=str(x.relative_to(repo)),bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in repo.rglob('*') if x.is_file() and '.git' not in x.relative_to(repo).parts]
(O/'SUMMARY.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(record,ensure_ascii=False,indent=2))
