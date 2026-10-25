"""Same-input/native-output check across measurement-only source repair."""
from pathlib import Path
import json,hashlib
W=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
rows=[]
for name in read(W/'role_pilot_collected_v2/pilot/SUMMARY.json')['completed']:
 a=read(W/'role_pilot_collected_v1/pilot'/name/'PHYSICAL_CALLS.json')['calls']
 b=read(W/'role_pilot_collected_v2/pilot'/name/'PHYSICAL_CALLS.json')['calls']
 assert len(a)==len(b)
 mismatches=[]
 for x,y in zip(a,b):
  for field in ['role','prompt_tokens','audio_start_sample','audio_end_sample','prefix_audio_sha256']:
   if x['job'][field]!=y['job'][field]:mismatches.append([x['purpose'],'job',field])
  for field in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']:
   if x['result'][field]!=y['result'][field]:mismatches.append([x['purpose'],'result',field])
 rows.append(dict(case=name,actual_jobs=len(a),mismatches=mismatches))
out=W/'ROLE_MEASUREMENT_REPAIR_SAME_INPUT_v1.json';assert not out.exists()
out.write_text(json.dumps(dict(status='PASS' if not any(x['mismatches'] for x in rows) else 'MISMATCH_RETAINED',cases=rows,
 scope='actual model inputs and full Z/P/Y/Stop across measurement-only repair; clocks and declared source digests intentionally differ',
 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print(out.read_text())
