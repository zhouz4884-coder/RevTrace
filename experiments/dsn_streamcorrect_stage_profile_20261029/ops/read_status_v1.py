import pathlib,json,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_stage_profile_20261029';h=json.loads((O/'HANDLE_v1.json').read_text());p=pathlib.Path('/proc')/str(h['pid']);alive=False
if p.exists():alive=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==h['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256']
r=dict(controller_alive_exact=alive,handle=h,files={})
for name in ['GATE.json','PROGRESS.json','ACTIVE_CHILD.json','SUMMARY.json','failure.txt']:
 f=O/'campaign_v1'/name
 if f.exists():
  r['files'][name]=dict(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,value=json.loads(f.read_text()) if f.suffix=='.json' and name!='SUMMARY.json' else f.read_text()[-5000:] if name=='failure.txt' else {'status':json.loads(f.read_text())['status']})
active=r['files'].get('ACTIVE_CHILD.json',{}).get('value',{});current=active.get('run_id')
if current:
 base=O/'campaign_v1'/current
 r['current']=dict(run_id=current,trace_steps=len(list((base/'trace').glob('step_*.json'))),warmup=(base/'WARMUP.json').exists(),summary=(base/'SUMMARY.json').exists())
 log=O/'campaign_v1'/(current+'.log')
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-4000));r['current']['log_tail']=f.read().decode('utf-8',errors='replace')
print(json.dumps(r,ensure_ascii=False,indent=2))
