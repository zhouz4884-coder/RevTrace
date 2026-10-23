"""Development-only historical fit: no held-out source outcome enters parameters."""
from pathlib import Path
import collections,csv,hashlib,json,statistics,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';D=O/'calibration_v3';assert not D.exists();D.mkdir()
roots=[B/'results/revtrace/online_admission_20261022/formal_v1',B/'results/revtrace/row_completion_20261023/formal_row_v1']
samples=[];files=[];reject=collections.defaultdict(list);cost=collections.defaultdict(list)
def bucket(n):return min([1,2,4,8,16],key=lambda b:abs(b-n))
for root in roots:
 for cell in sorted(root.iterdir()):
  p=cell/'worker_records.jsonl'
  if not p.is_file():continue
  files.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  records=[json.loads(l) for l in p.read_text().splitlines()];prev={}
  for x in sorted(records,key=lambda x:x['result'].get('received_perf',x['result']['completed_perf'])):
   j=x['job'];r=x['result'];proof=r.get('online_verification')
   if j['role']=='proposal':
    cost[('proposal',bucket(r.get('model_input_audit',{}).get('batch_rows',1)))].append(r['completed_perf']-r['started_perf']);continue
   if proof:
    if proof['mode']!='strict':continue
    same=j['candidate_origin_parent']==j['parent'] and j['candidate_origin_prompt_tokens']==j['prompt_tokens']
    key=('same' if same else 'mismatch')+('-prev-reject' if prev.get(j['session_id'],False) else '-prev-ok')
    bad=not proof['candidate_accepted'];reject[key].append(bad);prev[j['session_id']]=bad
    cost[('verify',bucket(proof['physical_batch_rows']))].append(proof['verify_batch_seconds'])
    if proof['fallback_used']:cost[('fallback',bucket(proof.get('fallback_batch_rows') or len(proof.get('fallback_executed_job_ids',[])) or 1))].append(proof.get('fallback_batch_seconds') or proof.get('fallback_row_compute_seconds_so_far',0))
    samples.append({'cell':cell.name,'session':j['session_id'],'window':j['end_window'],'features':key,'reject':bad,'candidate_tokens':len(j['candidate_token_ids'])})
   else:
    phase=(r.get('model_completed_perf') or r['completed_perf'])-(r.get('model_started_perf') or r['started_perf'])
    cost[('generate',bucket(r.get('model_input_audit',{}).get('batch_rows',1)))].append(phase)
# Row records can precede final physical cost: use full physical phase journals
# when available, deduplicated by batch identity. Do not sum per-row costs.
physical=collections.defaultdict(list);rowfractions=collections.defaultdict(list)
for root in roots:
 for p in sorted(root.glob('*/worker_batch_accounting.jsonl')):
  files.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  recs={x['job']['job_id']:x for x in [json.loads(l) for l in (p.parent/'worker_records.jsonl').read_text().splitlines()]}
  for l in p.read_text().splitlines():
   x=json.loads(l)
   for q in x.get('phases',[]):
    name=q['phase'];k='verify' if name=='correct-context-strict' else 'fallback' if name=='fresh-FP32-fallback' else 'generate' if name=='independent-generate' else None
    if k=='generate' and x.get('worker','').startswith('proposal'):k='proposal'
    if k is not None:physical[(k,bucket(q['physical_batch_rows']))].append(q['completed_perf']-q['started_perf'])
    if k=='generate':
     for jid in q['executed_job_ids']:
      r=recs[jid]['result']
      if r.get('row_terminal_perf') is not None:rowfractions[bucket(q['physical_batch_rows'])].append(min(1.,max(0.,(r['row_terminal_perf']-q['started_perf'])/(q['completed_perf']-q['started_perf']))))
allreject=[v for values in reject.values() for v in values]
out={'schema':'CES-calibration-v1','fitting_sources':'development16 only, old72 plus new120; no validation30',
 'record_files':len(files),'strict_rows':len(samples),'global_reject':(sum(allreject)+1)/(len(allreject)+2),
 'causal_reject':{k:{'n':len(v),'rejects':sum(v),'p':(sum(v)+1)/(len(v)+2)} for k,v in sorted(reject.items())},
 'cost_seconds':{},'generation_row_fraction':{str(b):statistics.median(v) for b,v in rowfractions.items()},
 'physical_phase_samples':{str(k):len(v) for k,v in physical.items()},'input_files':files,
 'frozen_before_new_GPU_pilot':True,'not_a_deployed_performance_result':True}
for mode in ['generate','verify','fallback','proposal']:
 vals={b:physical.get((mode,b),[]) or cost.get((mode,b),[]) for b in [1,2,4,8,16]}
 available={b:statistics.median(v) for b,v in vals.items() if v}
 assert available,mode
 out['cost_seconds'][mode]={str(b):available[min(available,key=lambda n:abs(n-b))] for b in [1,2,4,8,16]}
(D/'CALIBRATION.json').write_text(json.dumps(out,indent=2)+'\n')
with (D/'STRICT_CAUSAL_ROWS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
print(json.dumps({k:v for k,v in out.items() if k!='input_files'}))
