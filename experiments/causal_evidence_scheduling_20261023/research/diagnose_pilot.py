"""Read-only actual choice/cost/opportunity diagnostics, not counterfactual speedup."""
from pathlib import Path
import collections,csv,hashlib,json,statistics,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';D=O/'pilot_diagnosis_v1';assert not D.exists();D.mkdir()
cal=json.loads((O/'calibration_v2/CALIBRATION.json').read_text());rows=[];choice=[]
for C in sorted((O/'pilot_v1').iterdir()):
 if not C.is_dir() or not (C/'result.json').exists():continue
 records=[json.loads(l) for l in (C/'worker_records.jsonl').read_text().splitlines()]
 events=[json.loads(l) for l in (C/'events.jsonl').read_text().splitlines()];byid={r['job']['job_id']:r for r in records}
 decisions=[e for e in events if e['kind']=='ces-decision'];groups=collections.defaultdict(list)
 for r in records:
  if r['job']['role']=='authority':groups[r['result']['physical_batch_id']].append(r)
 accounts=[json.loads(l) for l in (C/'worker_batch_accounting.jsonl').read_text().splitlines()]
 acc={a['batch_id']:a for a in accounts}
 for bid,rr in groups.items():
  a=acc[bid];phases=a['phases'];first=rr[0];mode=first['job']['ces_operation']
  row={'cell':C.name,'operation':mode,'batch_rows':len(rr),'worker_service_s':a['batch_drained_perf']-a['worker_started_perf'],
    'physical_model_s':sum(p['completed_perf']-p['started_perf'] for p in phases),
    'physical_calls':len(phases),'fallback_rows':sum(t['result'].get('online_verification',{}).get('fallback_used',False) for t in rr),
    'accepted_rows':sum(t['result'].get('online_verification',{}).get('candidate_accepted',False) for t in rr)}
  rows.append(row)
 for e in decisions:
  fs=e['features'];choice.append({'cell':C.name,'event_time':e['time'],'operation':str(e['operation']),
    'reason':e['reason'],'targets':len(fs),'selected':len(e['sids']),
    'ready_candidates':sum(f['candidate_ready'] for f in fs),'same_birth':sum(f['same_birth'] for f in fs),
    'prior_reject':sum(f['previous_reject'] for f in fs),'issued_descendants':sum(f['descendant_count'] for f in fs),
    'predicted_plan_s':e.get('planned_seconds'),'score':e.get('score')})
for n,rs in [('ACTUAL_BATCH_COSTS.csv',rows),('OBSERVED_CHOICES.csv',choice)]:
 with (D/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
summary={}
for c in sorted({r['cell'] for r in rows}):
 cs=[r for r in choice if r['cell']==c];rs=[r for r in rows if r['cell']==c]
 summary[c]={'physical_batches':len(rs),'model_seconds':sum(r['physical_model_s'] for r in rs),
   'choice_operations':dict(collections.Counter(r['operation'] for r in cs)),
   'decisions_with_candidate':sum(r['ready_candidates']>0 for r in cs),'decision_count':len(cs),
   'ready_candidate_occurrences':sum(r['ready_candidates'] for r in cs),'target_occurrences':sum(r['targets'] for r in cs),
   'fallback_rows':sum(r['fallback_rows'] for r in rs),'accepted_rows':sum(r['accepted_rows'] for r in rs)}
(D/'SUMMARY.json').write_text(json.dumps({'status':'READ_ONLY_PILOT_DIAGNOSIS','cells':summary,
 'not_unrun_counterfactual_cost_or_speedup':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps(summary,indent=2))
