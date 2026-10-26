set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/ck5_v6')
def rows(p):
 out=[]
 if not p.exists():return out
 raw=p.read_bytes().splitlines(keepends=True)
 for i,s in enumerate(raw):
  try:out.append(json.loads(s))
  except (ValueError,UnicodeDecodeError):assert i==len(raw)-1 and not s.endswith(b'\n')
 return out
report=[]
for name in json.loads((O/'fault/SUMMARY.json').read_text())['completed']:
 D=O/'fault'/name/'attempt0';submitted={};completed=set()
 for f in D.glob('*.submissions'):
  for r in rows(f):
   for j in r['jobs']:submitted[j['job_id']]=j
 for f in D.glob('worker-*-receipts.jsonl'):
  for r in rows(f):
   if r['kind']=='row-complete':completed.add(r['message']['binding']['job_id'])
 for e in rows(D/'events.jsonl'):
  if e['kind']=='enqueue' and e['job_id'] not in submitted:
   assert e['job_id'] not in completed
   report.append(dict(episode=name,logical_enqueue_without_pre_submit_record={k:e.get(k) for k in ['job_id','role','session_id','audio_start_sample','audio_end_sample','enqueue_perf','audio_ready_perf']},actual_result_exists=False))
p=O/'LOGICAL_ENQUEUE_GAP_DIAGNOSIS_v1.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
PY
