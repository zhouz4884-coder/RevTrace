from pathlib import Path
import argparse,json,time
from remote import Remote,E
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['cpu','nn'],required=True);a=p.parse_args()
tag='COST_'+a.phase.upper()+'_V1';h=json.loads((E/'cost'/(tag+'_HANDLE.json')).read_bytes())
script='H='+repr(h)+'\n'+r'''
from pathlib import Path
import hashlib,json
p=Path('/proc')/str(H['pid']);r=dict(alive=p.exists())
if p.exists():
 s=(p/'stat').read_text().split();r.update(state=s[2],same_identity=int(s[21])==H['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==H['cmdline_sha256'])
out=Path(H['out'])
for name in ['PROGRESS.json','SUMMARY.json','GATE.json','STOP.json']:
 f=out/name
 if f.exists():
  try:
   j=json.loads(f.read_bytes());r[name]={k:v for k,v in j.items() if k not in {'cells','results','traceback'}}
  except Exception as e:r[name]=repr(e)
logs=sorted(out.glob('logs/*')) if out.exists() else []
if logs:r['last_cell_log']=dict(path=str(logs[-1]),tail=logs[-1].read_text(errors='replace')[-1200:])
f=Path(H['log']);r['campaign_tail']=f.read_text(errors='replace')[-3000:] if f.exists() else ''
print(json.dumps(r))
'''
with Remote() as c:
 raw=c.python(script);j=json.loads(raw);(E/'cost'/(tag+'_POLL_'+str(time.time_ns())+'.json')).write_bytes(raw)
 if not j['alive'] or 'SUMMARY.json' in j or 'GATE.json' in j:
  d=E/'cost'/('RESULTS_'+tag);d.mkdir(exist_ok=True)
  for n in ['SUMMARY.json','GATE.json','RUN_RECORD.json','ENVIRONMENT.json','DRIVER_CONFIG.json','STOP.json']:
   try:c.get(h['out']+'/'+n,d/n)
   except FileNotFoundError:pass
 print(raw.decode())
