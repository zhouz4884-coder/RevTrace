import pathlib,json,hashlib
T=pathlib.Path(__file__).resolve().parents[1];p=T/'packages/SOURCE_v4.json';x=json.loads(p.read_text());x['code_commit']=x['source_commit']
q=T/'packages/SOURCE_v4_LOCAL_PREFLIGHT.json';assert not q.exists();q.write_text(json.dumps(x,indent=2))
print(json.dumps(dict(manifest=str(q),sha256=hashlib.sha256(q.read_bytes()).hexdigest(),code_commit=x['code_commit']),indent=2))
