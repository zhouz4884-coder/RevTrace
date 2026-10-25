"""Actual chosen-batch calibration and released-successor opportunity audit.

No model is executed and unchosen outcomes are never filled in. Future audio
readiness is reconstructed only for already released logical frontiers.
"""
from pathlib import Path
from collections import defaultdict
import bisect,csv,hashlib,json,math,statistics,sys
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime'
O=B/'results/revtrace/ces_v5_20261025';D=O/'diagnosis_v1'
sys.path[:0]=[str(S/'src')]
from revtrace.ces_policy import Target,cost,verify_cost
from revtrace.ces_v5_policy import V5Target,predict_batch,_weighted_quantile

def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def writecsv(p,rows):
 with p.open('w',newline='') as f:
  if rows:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert read(O/'SUMMARY.json')['online_cells']==48
assert not D.exists();D.mkdir()
batches=[];debts=[];cells=[]
for C in sorted((O/'pilot_v1').iterdir()):
 if not (C/'result.json').exists():continue
 cfg=read(C/'config.json');result=read(C/'result.json');method=cfg['ces_study']['method'];cal=cfg['ces_study']['calibration']
 label=C.name.rsplit('-r',1)[0].split('-',3)[-1]
 es=lines(C/'events.jsonl');vs=lines(C/'consumer.jsonl');rs=lines(C/'worker_records.jsonl');ac=lines(C/'worker_batch_accounting.jsonl')
 byid={r['job']['job_id']:r for r in rs};specs={r['session_id']:r for r in read(C/'sessions.json')}
 t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
 decisions=[e for e in es if e['kind']=='ces-decision' and e['operation'] is not None]
 views=defaultdict(list)
 for v in vs:views[v['session_id']].append(v)
 first={}
 for sid,spec in specs.items():
  for q in range(1,math.ceil(spec['duration']/2)+1):
   frontier=round(min(q*2,spec['duration'])*16000)
   hits=[v['observed_perf'] for v in views[sid] if v['valid_visible_frontier']>=frontier]
   first[sid,q]=min(hits) if hits else math.inf
 owned={}
 for r in rs:
  j=r['job']
  if j['role']!='authority':continue
  applicable=[d for d in decisions if d['time']<=j['enqueue_perf']-t0 and j['session_id'] in d['sids'] and
    any(f['sid']==j['session_id'] and f['window']==j['end_window'] for f in d['features'])]
  if applicable:owned[j['job_id']]=applicable[-1]
 for a in ac:
  rr=[byid[j] for j in a['job_ids']]
  if rr[0]['job']['role']!='authority':continue
  op=rr[0]['job']['ces_operation'];d=owned.get(rr[0]['job']['job_id']);mean=q90=None
  if d:
   ids={r['job']['session_id'] for r in rr};constructor=V5Target if method in ['risk_cost','progress','progress_joint'] else Target
   ts=[constructor(**f) for f in d['features'] if f['sid'] in ids]
   assert len(ts)==len(rr)
   if method in ['risk_cost','progress','progress_joint']:
    outcomes=predict_batch(cal,op,ts);mean=sum(o.weight*o.lease for o in outcomes);q90=_weighted_quantile([(o.lease,o.weight) for o in outcomes],.9)
   elif method in ['cost','cost_gate','ces','causal_only']:
    mean=verify_cost(cal,ts,method in ['ces','causal_only']) if op=='verify' else cost(cal,'generate',len(ts),ts)
  actual=a['batch_drained_perf']-a['worker_started_perf']
  batches.append({'cell':C.name,'method':label,'operation':op,'batch_id':a['batch_id'],'rows':len(rr),
   'predicted_mean_lease_s':mean,'predicted_q90_lease_s':q90,'actual_lease_s':actual,
   'actual_minus_mean_s':None if mean is None else actual-mean,
   'covered_by_predicted_q90':None if q90 is None else actual<=q90,
   'actual_model_calls':len(a['phases']),'actual_fallback_calls':sum(p['phase']=='fresh-FP32-fallback' for p in a['phases']),
   'actual_fallback_rows':sum(r['result'].get('online_verification',{}).get('fallback_used',False) for r in rr)})
 unique=set();dcount=0
 for d in decisions:
  now=d['observed_perf']
  for f in d['features']:
   sid,q=f['sid'],f['window'];spec=specs[sid];nxt=q+1
   if nxt>math.ceil(spec['duration']/2):continue
   release=t0+spec['offset']+min(nxt*2,spec['duration']);deadline=release+2
   if not (release<=now<=deadline):continue
   if first[sid,nxt]<=now:continue
   own_release=t0+spec['offset']+min(q*2,spec['duration'])
   if first[sid,q]<=own_release+2:continue
   key=(sid,q,nxt);unique.add(key);dcount+=1
   debts.append({'cell':C.name,'method':label,'session':sid,'parent_window':q,'released_successor_window':nxt,
    'decision_perf':now,'successor_remaining_display_slack_s':deadline-now,'parent_selected_now':sid in d['sids'],
    'selected_operation':d['operation'],'actual_successor_display_latency_s':None if math.isinf(first[sid,nxt]) else first[sid,nxt]-release,
    'actual_successor_display_missed':first[sid,nxt]>deadline,
    'scope':'observed candidate Canonical-dependency opportunity; no counterfactual speedup or proof Private path required certification'})
 cells.append({'cell':C.name,'method':label,'decision_observations_with_live_released_successor':dcount,
  'unique_session_parent_successor_opportunities':len(unique),'planner_wall_s':result['CES_host_cost']['planner_wall_seconds'],
  'feature_wall_s':result['CES_host_cost']['feature_wall_seconds'],
  'ack_wall_s':result.get('CES_consumer_ack',{}).get('owner_ack_wall_seconds'),
  'source_reused_diagnostic_not_independent_confirmation':True})
writecsv(D/'CHOSEN_BATCH_PREDICTION_VS_ACTUAL.csv',batches)
writecsv(D/'RELEASED_SUCCESSOR_OPPORTUNITIES.csv',debts)
writecsv(D/'CELL_DIAGNOSIS.csv',cells)
assert len(cells)==48
(D/'SUMMARY.json').write_text(json.dumps({'status':'PASS_ACTUAL_CHOICE_AND_SUCCESSOR_DIAGNOSIS','online_cells':48,
 'GPU_calls':0,'unchosen_model_outcomes_not_inferred':True,'opportunities_are_not_independent_samples':True,
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'cells':len(cells),'chosen_batches':len(batches),'successor_decision_observations':len(debts)}))
