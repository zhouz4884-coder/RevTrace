import json
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');D=B/'results/revtrace/physical_retirement_20261028/confirmation_dev_v3/dev-qwen-rho1-staggered-two_lane-r0'
for name in ['consumer.jsonl','events.jsonl']:
 rows=[json.loads(x) for x in (D/'attempt0'/name).read_text().splitlines()]
 if name=='consumer.jsonl':
  for k in ['display','canonical-display']:
   print('CONSUMER',k,next((r for r in rows if r.get('source_kind')==k),None))
 else:
  for k in ['display','executor-complete','commit','wal-physical-timing','install-ack']:
   print('EVENT',k,next((r for r in rows if r['kind']==k),None))
f=json.loads((D/'audit/FRONTIERS.json').read_text());print('WORST',sorted(f,key=lambda x:x['display_latency'],reverse=True)[:4])
