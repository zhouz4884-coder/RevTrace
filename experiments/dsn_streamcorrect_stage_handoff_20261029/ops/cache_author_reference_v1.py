import pathlib,urllib.request,hashlib,json
T=pathlib.Path(__file__).resolve().parents[1];out=T/'author_reference';out.mkdir(exist_ok=True);commit='bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3';rows=[]
for name in ['simul_whisper/simul_whisper.py','whisper_streaming/vac_online_processor.py','runs/run_single_eval_aishell.sh','README.md']:
 url='https://raw.githubusercontent.com/vu-duy-tung/StreamCorrect/'+commit+'/'+name;data=urllib.request.urlopen(url,timeout=30).read();p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
 rows.append(dict(path=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
assert rows[0]['sha256']=='9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7'
(out/'MANIFEST.json').write_text(json.dumps(dict(author_commit=commit,files=rows),indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
