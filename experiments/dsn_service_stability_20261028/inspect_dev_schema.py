import json,collections
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/physical_retirement_20261028';P=B/'projects/revtrace_physical_retirement_20261028'
p=json.loads((P/'CONFIRMATION_DEV_PLAN_v3_FROZEN.json').read_text())
for c in p['cells']:
 if c['adapter']!='qwen':continue
 d=Path(c['output']);s=json.loads((d/'INDEPENDENT_SUMMARY.json').read_text())['service']
 print('SUMMARY',c['cell_id'],json.dumps({k:s[k] for k in ['whole_run_dual_P99_pass','display_P99','commit_view_P99','input_fsync_seconds','controller_host_seconds','GPU_joules','all_offered_audio_goodput_2_8','all_offered_WER_percent']}))
 f=json.loads((d/'audit/FRONTIERS.json').read_text());print('FRONTIER',f[:1]);print('WORST',sorted(f,key=lambda x:x['display_latency_seconds'],reverse=True)[:3] if f and 'display_latency_seconds' in f[0] else f[-1:])
 e=[json.loads(x) for x in (d/'attempt0/events.jsonl').read_text().splitlines()];cnt=collections.Counter(x['kind'] for x in e);print('KINDS',dict(cnt))
 for kind in cnt:
  if any(z in kind for z in ['enqueue','publish','canonical','input','dispatch']):print('EVENT',kind,next(x for x in e if x['kind']==kind))
 r=json.loads((d/'attempt0/worker_records.jsonl').read_text().splitlines()[0]);print('RESULT_KEYS',list(r['result']));print('RECEIPT',r['result'].get('_row_receipt'))
