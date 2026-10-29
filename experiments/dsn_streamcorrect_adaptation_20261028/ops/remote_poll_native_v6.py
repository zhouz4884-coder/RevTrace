import pathlib,json,hashlib,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';out=O/'native_campaign_v6_controller'
def read(p):return json.loads(p.read_text())
h=read(O/'NATIVE_v6_HANDLE.json');proc=pathlib.Path('/proc')/str(h['pid']);r=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),handle=h,controller_proc_exists=proc.exists())
if proc.exists():
 stat=(proc/'stat').read_text().rsplit(')',1)[1].split();r['controller_identity_matches']=int(stat[19])==h['start_ticks'] and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'];r['controller_state']=stat[0]
for name in ['GATE.json','WITNESS_GATE.json','ACTIVE_CHILD.json']:
 p=out/name
 if p.exists():r[name]=read(p)
progress=out/'PROGRESS.json'
if progress.exists():
 v=read(progress);r['progress']=dict(completed=len(v['completed']),remaining=v['remaining'])
active=r.get('ACTIVE_CHILD.json')
if active:
 cfg=next(x for x in read(P/'NATIVE_CAMPAIGN_v6_FROZEN.json')['cells'] if x['cell_id']==active['cell_id']);cell=pathlib.Path(cfg['out'])
 r['active_cell']=dict(cell_id=cfg['cell_id'],ready=(cell/'READY.json').exists(),native_jobs_bytes=(cell/'native_jobs.jsonl').stat().st_size if (cell/'native_jobs.jsonl').exists() else 0)
 for name in ['GATE.json','failure.txt']:
  q=cell/name
  if q.exists():r['active_cell'][name]=read(q) if name.endswith('.json') else q.read_text()[-5000:]
 log=out/(cfg['cell_id']+'.log')
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-6000));r['active_cell_log_tail']=f.read().decode(errors='replace')
failure=out/'failure.txt'
if failure.exists():r['controller_failure']=failure.read_text()[-5000:]
print(json.dumps(r,indent=2))
