import pathlib,json,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';plan=json.loads((P/'NATIVE_CAMPAIGN_v8_FROZEN.json').read_text());out=[]
for arm in ('sequential','joint'):
 cell=next(c for c in plan['cells'] if c['stage']=='formal' and c['cohort']=='A' and c['arm']==arm and c['repeat']==0);p=pathlib.Path(cell['out'])/'READY.json';rows=json.loads(p.read_text())
 out.append(dict(arm=arm,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ready=rows))
print(json.dumps(out,ensure_ascii=False,indent=2))
