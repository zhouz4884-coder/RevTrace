from pathlib import Path
import argparse,json,time
from remote import Remote,E
p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args()
h=json.loads((E/'history'/(a.tag+'_HANDLE.json')).read_bytes())
script='H='+repr(h)+'\n'+r'''
from pathlib import Path
import hashlib,json
p=Path('/proc')/str(H['pid']);alive=p.exists();same=False;state=None
if alive:
 stat=(p/'stat').read_text().split();state=stat[2]
 same=int(stat[21])==H['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==H['cmdline_sha256']
out=Path(H['out']);result=dict(alive=alive,same_identity=same,state=state)
for name in ['PROGRESS.json','SUMMARY.json','GATE.json']:
 f=out/name
 if f.exists():
  try:
   j=json.loads(f.read_bytes());result[name]={k:v for k,v in j.items() if k not in {'runs','failures','run_summaries','attempts','repeats_data'} and (not isinstance(v,list) or len(v)<=4)}
  except Exception as e:result[name]=repr(e)
log=Path(H['log']);result['log_tail']=log.read_text(errors='replace')[-2500:] if log.exists() else ''
print(json.dumps(result))
'''
with Remote() as c:
 raw=c.python(script);j=json.loads(raw)
 target=E/'history'/(a.tag+'_POLL_'+str(time.time_ns())+'.json');target.write_bytes(raw)
 if 'SUMMARY.json' in j:
  dest=E/'history'/('RESULTS_'+a.tag);dest.mkdir(exist_ok=True)
  for name in ['SUMMARY.json','GATE.json','RUN_RECORD.json']:
   try:c.get(h['out']+'/'+name,dest/name)
   except FileNotFoundError:pass
 print(raw.decode())
