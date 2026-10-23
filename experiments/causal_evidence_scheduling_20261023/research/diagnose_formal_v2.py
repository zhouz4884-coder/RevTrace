"""Actual opportunities/paid costs; unchosen verification labels stay unknown."""
from pathlib import Path
import collections,csv,hashlib,json,statistics,sys
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime_v4'
sys.path.insert(0,str(S/'src'))
from revtrace.ces_policy import Target,cost,verify_cost,rejection
O=B/'results/revtrace/ces_20261023';D=O/'formal_diagnosis_v1';D.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(l) for l in p.read_text().splitlines()]
def csvsave(p,rows):
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
targets=[];batches=[];cells=[];counterexamples=[]
for C in sorted((O/'formal_v1').iterdir()):
 if not C.is_dir() or not (C/'result.json').exists():continue
 cfg=read(C/'config.json');method=cfg['ces_study']['method'];cal=cfg['ces_study']['calibration']
 rs=lines(C/'worker_records.jsonl');es=lines(C/'events.jsonl');ac=lines(C/'worker_batch_accounting.jsonl')
 byid={r['job']['job_id']:r for r in rs};props={(r['job']['session_id'],r['job']['end_window']):r for r in rs if r['job']['role']=='proposal'}
 decisions=[e for e in es if e['kind']=='ces-decision' and e['operation'] is not None]
 origin={}
 for e in es:
  if e['kind']=='ces-operation-bound':
   ds=[d for d in decisions if d['time']<=e['time']+1e-9 and e['session_id'] in d['sids']]
   if ds:origin[e['job_id']]=ds[-1]
 selected=[]
 for r in rs:
  j=r['job'];z=r['result']
  if j['role']!='authority':continue
  candidate=props.get((j['session_id'],j['end_window']))
  ready=bool(candidate and candidate['result']['received_perf']<=j['enqueue_perf'])
  same=bool(ready and candidate['job']['parent']==j['parent'] and candidate['job']['prompt_tokens']==j['prompt_tokens'])
  proof=z.get('online_verification');reject=not proof['candidate_accepted'] if proof else None
  d=origin.get(j['job_id']);feature=next((f for f in d['features'] if f['sid']==j['session_id']),None) if d else None
  p=rejection(cal,Target(**feature),causal=method in ['ces','causal_only']) if feature and method in ['ces','causal_only','cost','cost_gate'] else None
  row={'cell':C.name,'method':method,'session':j['session_id'],'window':j['end_window'],'operation':j['ces_operation'],
    'candidate_owner_ready_at_dispatch':ready,'same_declared_parent_and_prompt':same,
    'verification_rejected_observed':reject,'unchosen_verification_label_unknown':proof is None,
    'predicted_reject_if_observed_feature':p,'candidate_tokens':len(candidate['result']['token_ids']) if ready else None,
    'enqueue_after_audio_s':j['enqueue_perf']-j['audio_ready_perf'],'worker_queue_s':z['started_perf']-j['enqueue_perf'],
    'row_result_after_start_s':z['completed_perf']-z['started_perf'],'actual_F2_candidate':bool(ready and 'fault_actual_prompt_tokens' in candidate['job'])}
  targets.append(row);selected.append(row)
  if proof and feature and feature['previous_reject'] and proof['candidate_accepted']:
   counterexamples.append({'cell':C.name,'job_id':j['job_id'],'case':'previous rejection did not imply this candidate rejection','predicted_probability':p})
 for a in ac:
  rr=[byid[j] for j in a['job_ids']]
  if rr[0]['job']['role']!='authority':continue
  op=rr[0]['job']['ces_operation'];d=origin.get(rr[0]['job']['job_id']);pred=None
  if d and d['features']:
   ids={r['job']['session_id'] for r in rr};ts=[Target(**f) for f in d['features'] if f['sid'] in ids]
   assert len(ts)==len(rr)
   pred=verify_cost(cal,ts,method in ['ces','causal_only']) if op=='verify' else cost(cal,'generate',len(ts),ts)
  actual=a['batch_drained_perf']-a['worker_started_perf']
  batches.append({'cell':C.name,'method':method,'operation':op,'batch_id':a['batch_id'],'rows':len(rr),
   'predicted_selected_batch_occupancy_s':pred,'actual_batch_occupancy_s':actual,
   'error_actual_minus_prediction_s':None if pred is None else actual-pred,
   'actual_model_calls':len(a['phases']),'actual_model_seconds':sum(p['completed_perf']-p['started_perf'] for p in a['phases']),
   'actual_fallback_calls':sum(p['phase']=='fresh-FP32-fallback' for p in a['phases'])})
 cells.append({'cell':C.name,'method':method,'targets':len(selected),
  'candidate_ready_targets':sum(r['candidate_owner_ready_at_dispatch'] for r in selected),
  'same_birth_targets':sum(r['same_declared_parent_and_prompt'] for r in selected),
  'verified_targets':sum(r['operation']=='verify' for r in selected),
  'observed_rejections':sum(r['verification_rejected_observed'] is True for r in selected),
  'unknown_unchosen_verification_outcomes':sum(r['unchosen_verification_label_unknown'] for r in selected)})
assert len(cells)==180
for n,rs in [('TARGETS.csv',targets),('BATCH_PREDICTION_VS_ACTUAL.csv',batches),('CELL_OPPORTUNITIES.csv',cells)]:csvsave(D/n,rs)
(D/'COUNTEREXAMPLES.json').write_text(json.dumps(counterexamples,indent=2)+'\n')
(D/'SUMMARY.json').write_text(json.dumps({'status':'PASS_ACTUAL_OPPORTUNITY_AND_COST_DIAGNOSIS','cells':180,
 'unchosen_outcomes_not_fabricated':True,'F2_labels_used_only_in_posthoc_diagnostic_not_policy':True,
 'actual_clock_and_work_not_counterfactual_speedups':True,'new_GPU_calls':0,
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
