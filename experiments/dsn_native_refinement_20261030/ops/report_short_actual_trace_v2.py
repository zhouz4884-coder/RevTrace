"""Assemble exact six-trial structural-check facts without changing any gate."""
import hashlib,json,pathlib,sys
F=pathlib.Path(__file__).resolve().parents[1];N=F.parent/'dsn_native_resilience_20261030';O=F/'SHORT_ACTUAL_TRACE_RESULTS_v2'
sys.path.insert(0,str(F/'trace_source_v2'));from refinement_trace import read_frames,lines
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
batch=read(O/'GATE.json');assert batch['status']=='PASS_ALL_SIX_ACTUAL_TRACE_REFINEMENT'
plan=read(N/'SHORT_PILOT_v1_FROZEN.json');rows=[];totals={k:0 for k in ('durable_original_transitions','unique_original_C_U_jobs_used','actual_Consumer_rows','verified_complete_Private_path_links')}
for cell in plan['cells']:
 cid=cell['cell_id'];s=read(O/cid/'SUMMARY.json');raw=N/'SHORT_PILOT_RESULTS_v1/cells'/cid
 frames,_=read_frames(raw/'facts.wal')
 buffered=[]
 for obj,_ in frames[1:]:
  j=obj['body']['job']
  if j.get('started_on_canonical') is False and j.get('promoted_to_canonical') is False:
   buffered.append(dict(job_id=j['job_id'],worker=j['worker'],worker_incarnation=j['worker_incarnation'],owner_epoch=obj['body']['owner_epoch'],frontier=obj['body']['next_state']['frontier']))
 reject_rows=list(lines(raw/'consumer_rejections.jsonl'))
 row=dict(cell_id=cid,fault_kind=cell['fault_kind'],original_raw_result_location=cell['out'],
  gate_sha256=sha(O/cid/'GATE.json'),canonical_transitions=s['durable_original_transitions'],
  actual_Consumer_rows=s['actual_Consumer_rows'],Private_path_links=s['verified_complete_Private_path_links'],
  counts=s['counts'],physical=s['worker_only_physical_replacement_audit'],rejections=s['local_rejection_audit'],
  original_clock=s['original_ingress'],dispatch_arrivals=s['dispatch_original_arrivals'],
  completed_conditional_buffer_installs=buffered,
  raw_consumer_local_rejections=reject_rows,
  consumer_local_rejection_independent_snapshot_hash_audit='NOT_IN_C4_CHECKER; raw rows reported separately')
 rows.append(row)
 for k in totals:totals[k]+=s[k]
facts=dict(status='COMPLETE_SIX_ACTUAL_TRACE_STRUCTURAL_CHECKS_V2',checker_source_commit='c4dde9ea9c7abf80fae084bc2293e193262c71e6',
 actual_neural_source_commit=plan['source_commit'],operator_source_commit='dd4d16a51320eca0899ad6cccc1d61a0f3fbdc1a',
 cases=6,source_tier='six development failure-coverage trials on one acoustic source, not formal28 or six independent acoustic sources',
 canonical_binding='Every new durable Canonical fact uniquely binds its immutable actual dispatch and original full C/U start/end/selected-C/token-IDs receipt; not a fixed GPU replay equality theorem',
 total=totals,batch_gate_sha256=sha(O/'GATE.json'),rows=rows,new_neural_calls_by_analysis=0,
 caveats=['Current-owned policy-local rejection observations are zero here; wrong-rejection0 with zero events does not test duplicate/late ability.',
          'Compatible-ahead actual applications are zero in these six; current conditional S control and earlier natural witnesses remain separate.',
          'Per-Owner worker-only exit/CUDA release bound; Supervisor whole-group termination proof is separate.',
          'Consumer old-Owner local rejection raw events are not yet in c4 independent snapshot-hash scope.'])
p=F/'SHORT_ACTUAL_TRACE_FACTS_v2.json';assert not p.exists();p.write_bytes((json.dumps(facts,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(total=totals,buffered_installs=[dict(cell_id=r['cell_id'],jobs=r['completed_conditional_buffer_installs']) for r in rows],
 consumer_rejections=[dict(cell_id=r['cell_id'],rows=r['raw_consumer_local_rejections']) for r in rows if r['raw_consumer_local_rejections']],
 facts_sha256=sha(p)),ensure_ascii=False,indent=2))

