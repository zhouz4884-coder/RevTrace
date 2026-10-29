import pathlib,json,sys,shutil
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
x=dict(python=sys.version,free_bytes=shutil.disk_usage(B).free)
for name in ('ACTIVE_DOWNLOAD_HANDLE.json','GATE.json','PROGRESS.json'):
 p=O/name
 if p.exists():
  v=json.loads(p.read_text());x[name]=v if name!='PROGRESS.json' else dict(files=len(v['files']),last_file=v['files'][-1] if v['files'] else None)
print(json.dumps(x,indent=2))
