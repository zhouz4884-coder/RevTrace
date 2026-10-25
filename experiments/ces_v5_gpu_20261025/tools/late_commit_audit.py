"""Actual late transitions: when was their deadline already missed?"""
from pathlib import Path
from collections import defaultdict
import csv,json,statistics
from local_review import csvrows,sha
W=Path(__file__).resolve().parent;A=W/'local_review'
paths=csvrows(A/'AUTHORITY_CRITICAL_PATHS.csv');forecasts=csvrows(A/'SELECTED_ROW_FORECASTS.csv')
defer=csvrows(A/'TARGET_DEFERRALS.csv');dd={(d['cell'],d['job_id']):d for d in defer}
ff={(f['cell'],f['session'],f['window']):f for f in forecasts}
rows=[];groups=defaultdict(list)
for r in paths:
    if not r['commit_8s_missed']:continue
    p=ff.get((r['cell'],r['session'],r['window']));d=dd.get((r['cell'],r['job_id']))
    enqueue_latency=r['release_to_parent_eligible_s']+r['eligible_to_enqueue_s']
    x=dict(r,already_late_at_enqueue=enqueue_latency>8,release_to_enqueue_s=enqueue_latency,
        observed_passovers=d['first_batch_deferrals'] if d else None,
        predicted_commit_met_probability_at_selected_decision=p['predicted_commit_probability'] if p else None)
    rows.append(x);groups[r['cell'].split('-')[1],r['method']].append(x)
summary=[]
for (arrival,method),rr in sorted(groups.items()):
    summary.append({'arrival':arrival,'method':method,'late_frontier_observations':len(rr),
        'already_late_before_enqueue':sum(r['already_late_at_enqueue'] for r in rr),
        'observed_passed_over_at_least_once':sum((r['observed_passovers'] or 0)>0 for r in rr),
        'selected_forecast_commit_success_zero':sum(r['predicted_commit_met_probability_at_selected_decision']==0 for r in rr),
        'late_generate_rows':sum(r['operation']=='generate' for r in rr),
        'late_verify_rows':sum(r['operation']=='verify' for r in rr),
        'mean_selected_prediction_commit_success':statistics.mean(r['predicted_commit_met_probability_at_selected_decision'] for r in rr)})
assert len(rows)==97
p=A/'LATE_COMMIT_WITNESSES.csv';assert not p.exists()
with p.open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
out={'status':'PASS_ACTUAL_LATE_COMMIT_CLASSIFICATION','groups':summary,'GPU_calls':0,
    'scope':'Timing and chosen-action diagnosis, not unchosen-action regret; observations repeat shared sources',
    'script_sha256':sha(Path(__file__))}
(A/'LATE_COMMIT_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
