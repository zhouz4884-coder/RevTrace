import pathlib,json,hashlib,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1';D=O/'attempts/attempt02_python312_stdout_brokenpipe';D.mkdir(parents=True,exist_ok=False)
handle=json.loads((O/'ACTIVE_DOWNLOAD_HANDLE.json').read_text());proc=pathlib.Path('/proc')/str(handle['pid'])
if proc.exists() and int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])==handle['start_ticks']:raise RuntimeError('prior exact acquisition PID still active; no preservation/relaunch')
rows=[]
for name in ('GATE.json','PROGRESS.json','ACTIVE_DOWNLOAD_HANDLE.json','PUBLIC_PLAN.json'):
 p=O/name
 if p.exists():
  b=p.read_bytes();(D/name).write_bytes(b);rows.append(dict(path=str(D/name),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
record=dict(preserved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),failure_cause='confirmed stdout print BrokenPipeError after SSH-owned stream closed; not a network/model-identity failure',files=rows,original_partial_retained=True)
(D/'PRESERVATION.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
