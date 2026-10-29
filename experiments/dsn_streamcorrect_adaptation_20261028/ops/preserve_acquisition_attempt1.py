import pathlib,shutil,hashlib,json
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
records=[]
for old,new in [('GATE.json','GATE_attempt1_python38.json'),('ACTIVE_DOWNLOAD_HANDLE.json','HANDLE_attempt1_python38.json')]:
 source=O/old;target=O/new;assert source.exists() and not target.exists()
 b=source.read_bytes();target.write_bytes(b);records.append(dict(path=str(target),sha256=hashlib.sha256(b).hexdigest()))
print(json.dumps(records,indent=2))
