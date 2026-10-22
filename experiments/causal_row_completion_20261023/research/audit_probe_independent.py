"""Independent P1 read-only checks, no model calls and no timing extrapolation."""
from pathlib import Path
import hashlib,json,statistics,sys,csv

B=Path(sys.argv[1]);P=B/'projects/revtrace_row_completion_20261023';O=B/'results/revtrace/row_completion_20261023'
D=O/'probe_v1';A=O/'probe_v1_independent_audit_v2';A.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
summary=read(D/'SUMMARY.json')
assert summary['status']=='COMPLETE_BOUNDED_ROW_GPU_PROBE' and not (D/'STOP.json').exists()
plan=read(O/'p0_v1/GPU_PROBE_PLAN.json');expected=[p for p in plan['operations'] if p['status']=='FROZEN_BEFORE_NEW_GPU']
extension=read(O/'probe_identity_v2/SUMMARY.json')
assert extension['status']=='PASS_ALL6_VERIFIER_POSTCAST_INPUT_CONTROLS' and extension['completed_invocations']==12
covered=set()
for rec in extension['operations']:
 oi=rec['operation'];E=O/'probe_identity_v2'
 a=read(E/f'op{oi}-reference.json');p=read(E/f'op{oi}-probe.json')
 hashes=lambda d:[{k:v for k,v in e.items() if k!='job_ids'} for e in d['results'][0]['diagnostic_row_probe'] if e['kind'].startswith('actual-postcast')]
 assert hashes(a)==hashes(p) and any(e['kind']=='actual-postcast-verifier-inputs' and e['tensors'] for e in hashes(a))
 for x,y in zip(a['results'],p['results']):
  assert all(x[k]==y[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit'])
  assert x['online_verification']['candidate_accepted']==y['online_verification']['candidate_accepted']
 covered.add(oi)
assert len(covered)==6
rows=[];ops=[]
def elapsed(x):return x['results'][0]['completed_perf']-x['results'][0]['started_perf']
for oi,operation in enumerate(expected):
 effects=[];leads=[]
 for cycle in range(2):
  data=[read(D/f'op{oi}-c{cycle}-{s}.json') for s in ['before','probe','after']]
  a,p,z=data;assert not a['probe'] and p['probe'] and not z['probe']
  assert all(not x['postcast_identity_capture'] for x in data)
  baseline=statistics.mean([elapsed(a),elapsed(z)]);effect=elapsed(p)/baseline-1;effects.append(effect)
  byid={r['job_id']:r for r in p['results']}
  content=lambda r:{k:r[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']}
  assert [content(r) for r in a['results']]==[content(r) for r in p['results']]==[content(r) for r in z['results']]
  for rr in zip(*[x['results'] for x in data]):
   assert rr[0]['model_input_audit']['batch_tensors']==rr[1]['model_input_audit']['batch_tensors']==rr[2]['model_input_audit']['batch_tensors']
  es=p['results'][0]['diagnostic_row_probe'];finals=[e for e in es if e['kind'] in ['probe-row-final','probe-verified-row-final']]
  assert len(finals)==operation['rows'] and len({e['job_id'] for e in finals})==len(finals)
  batch_end=p['results'][0]['completed_perf']
  for e in finals:
   r=byid[e['job_id']]
   assert (e['Z'],e['P'],e['text'])==(r['token_ids'],r['state_tokens'],r['text'])
   assert e['terminal_observed_perf']<=e['complete_render_perf']<=batch_end and not e['worker_reusable']
   lead=batch_end-e['complete_render_perf'];leads.append((e['kind'],lead))
   rows.append({'operation':oi,'cell':operation['cell'],'role':operation['role'],'criterion':operation['criterion'],
    'cycle':cycle,'job_id':e['job_id'],'kind':e['kind'],'render_complete_lead_s':lead,
    'observer_render_s':e['observer_render_s'],'terminal_to_render_s':e['complete_render_perf']-e['terminal_observed_perf'],
    'row_output_equal_all_references':True,'not_a_repaired_old_serving_deadline':True})
 a=read(D/f'op{oi}-identity-before.json');p=read(D/f'op{oi}-identity-probe.json')
 extract=lambda d:[{k:v for k,v in e.items() if k!='job_ids'} for e in d['results'][0]['diagnostic_row_probe'] if e['kind']=='actual-postcast-inputs']
 assert extract(a)==extract(p)
 if expected[oi]['has_verification']:assert oi in covered
 else:assert extract(a)
 qualified=any(v>=(.05 if k=='probe-verified-row-final' else .1) for k,v in leads)
 ops.append({'operation':oi,'cell':operation['cell'],'role':operation['role'],
    'median_incremental_observer_overhead':statistics.median(effects),'cycle_effects':effects,
    'median_complete_row_lead_s':statistics.median(v for k,v in leads),'maximum_complete_row_lead_s':max(v for k,v in leads),
    'lead_qualified':qualified,'all_reference_input_and_output_controls_equal':True})
with (A/'ROW_LEADS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (A/'OPERATION_OVERHEAD.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(ops[0]));w.writeheader();w.writerows(ops)
gate=sum(r['lead_qualified'] for r in ops)>=2 and statistics.median(r['median_incremental_observer_overhead'] for r in ops)<=.05
assert gate==summary['GO_minimal_interface']
out={'status':'PASS_INDEPENDENT_ROW_PROBE_AUDIT','operations':len(ops),'row_measurements':len(rows),
 'lead_qualified_operations':sum(r['lead_qualified'] for r in ops),
 'median_operation_overhead':statistics.median(r['median_incremental_observer_overhead'] for r in ops),
 'GO_minimal_interface':gate,'original_old_row_clocks_not_filled':True,
 'verification_actual_tensor_coverage_repaired_by_separate12_controls':sorted(covered),
 'original96_timing_data_not_rerun_or_rewritten':True,
 'no_claim_new_system_performance_or_independent_algorithm_yet':True,'new_model_calls':0,
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
