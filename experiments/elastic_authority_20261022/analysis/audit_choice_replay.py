"""Independent choice-rule replay and two-plane physical costs, CPU-only."""
from pathlib import Path
from collections import defaultdict
import csv,json,math,statistics,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/elastic_20261022';rows=[];pred_errors=[];checked=0
for stage in ['fixed_scout','stress_scout','formal']:
 for c in sorted((O/stage).iterdir()):
  if not (c/'result.json').exists():continue
  cfg=json.loads((c/'config.json').read_text());es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');plans={};kind=cfg['granularity_policy']['kind']
  if stage=='formal':
   rule=cfg['granularity_policy']
   for e in es:
    if e['kind']!='granularity-plan':continue
    plans[e['session_id'],e['parent']]=e
    if kind.startswith('fixed'):expected=int(kind[-1])
    else:
     obs=e['observation'];vs=obs['predictions'];assert [v['rho'] for v in vs]==[1,2,3]
     for v in vs:assert abs(v['lateness']-max(0,v['eta']-obs['earliest_frontier_deadline']))<1e-7
     if kind=='backlog':
      a,b=rule['backlog_cutoffs'];n=obs['released_uncommitted_fine_windows'];expected=1 if n<=a else 2 if n<=b else 3
     else:
      feasible=[v for v in vs if v['lateness']<=1e-9 and (kind=='deadline' or v['demand_estimate']<=rule['capacity_target'])]
      expected=(max(v['rho'] for v in feasible) if kind=='deadline' else min(v['rho'] for v in feasible)) if feasible else min(vs,key=lambda v:(v['lateness'],v['work_per_audio_estimate'],v['rho']))['rho']
    assert e['selected_rho']==expected;checked+=1
   for e in es:
    if e['kind']=='commit' and not kind.startswith('fixed'):
     p=plans[e['session_id'],e['parent']];prediction=next(v for v in p['observation']['predictions'] if v['rho']==p['selected_rho'])
     pred_errors.append({'cell':c.name,'kind':kind,'session_id':e['session_id'],'parent':e['parent'],'rho':p['selected_rho'],'predicted_install_perf':prediction['eta'],'actual_install_perf':t0+e['installed'],'error_seconds':t0+e['installed']-prediction['eta'],'includes_Render_WAL_after_model':True})
  for role in ['proposal','authority']:
   spans=set((e['gpu_model_started'],e['gpu_model_completed']) for e in es if e['kind']=='executor-complete' and e['role']==role)
   service=set((e['started'],e['completed']) for e in es if e['kind']=='executor-complete' and e['role']==role)
   rows.append({'stage':stage,'cell':c.name,'kind':kind,'role':role,'distinct_model_calls':len(spans),'dedup_worker_seconds':sum(b-a for a,b in service),'dedup_model_seconds':sum(b-a for a,b in spans),'model_overlap_high_10_42_seconds':sum(max(0,min(b,42)-max(a,10)) for a,b in spans),'high_window_model_interval_fraction':sum(max(0,min(b,42)-max(a,10)) for a,b in spans)/32,'not_kernel_busy_utilization':True})
A=O/'mechanism_analysis';A.mkdir(exist_ok=True)
for n,rs in [('ROLE_DEMAND.csv',rows),('PREDICTION_ERRORS.csv',pred_errors)]:
 with (A/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
(A/'RULE_REPLAY.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_DECLARED_CHOICE_RULE_REPLAY','formal_choices_checked':checked,'completed_cells':len(rows)//2,'source_tiers':'real GPU logs, CPU read-only analysis; no model rerun','model_prediction_not_a_deadline_guarantee':True},indent=2)+'\n');print('choice replay passed',checked,'two-plane costs',len(rows))
