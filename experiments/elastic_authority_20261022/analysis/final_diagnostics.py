"""Read-only descriptive summaries of frozen GPU evidence; never tune policies."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, json, statistics
W=Path(__file__).resolve().parent; C=W/'collected'
def rows(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def q(xs,p):
    xs=sorted(xs);k=(len(xs)-1)*p;a=int(k);b=min(a+1,len(xs)-1)
    return xs[a]+(xs[b]-xs[a])*(k-a)
roles=rows(C/'mechanism_analysis/ROLE_DEMAND.csv')
cost=[]
for kind in ['fixed1','fixed2','fixed3','backlog','deadline','joint']:
    for role in ['proposal','authority']:
        rs=[r for r in roles if r['stage']=='formal' and r['kind']==kind and r['role']==role];assert len(rs)==4
        cost.append({'method':kind,'role':role,'n_runs':4,**{k:statistics.mean(float(r[k]) for r in rs) for k in ['distinct_model_calls','dedup_worker_seconds','dedup_model_seconds','high_window_model_interval_fraction']}})
errs=rows(C/'mechanism_analysis/PREDICTION_ERRORS.csv');pred=[]
for kind in ['backlog','deadline','joint']:
    xs=[float(r['error_seconds']) for r in errs if r['kind']==kind]
    pred.append({'method':kind,'transitions':len(xs),'install_minus_forecast_mean_s':statistics.mean(xs),'install_minus_forecast_median_s':q(xs,.5),'install_minus_forecast_p95_s':q(xs,.95),'positive_error_fraction':sum(x>0 for x in xs)/len(xs),'absolute_error_p95_s':q([abs(x) for x in xs],.95)})
cells=rows(C/'formal_audit/SERVICE_CELLS.csv');choices=[]
for kind in ['fixed1','fixed2','fixed3','backlog','deadline','joint']:
    rs=[r for r in cells if r['granularity_kind']==kind];assert len(rs)==4
    hist=Counter()
    for r in rs:hist.update(json.loads(r['selected_rho_counts']))
    choices.append({'method':kind,'total_planned_intervals_4_runs':sum(int(r['planned_intervals_independently_checked']) for r in rs),'selected_rho_counts':dict(hist),'selector_host_wall_mean_s':statistics.mean(float(r['selector_decision_host_wall_seconds']) for r in rs),'canonical_commits_mean':statistics.mean(int(r['canonical_publications']) for r in rs),'consumer_display_P99_all_runs_fail_2s':all(float(r['display_P99_consumer'])>2 for r in rs),'commit_P99_all_runs_fail_8s':all(float(r['commit_P99'])>8 for r in rs)})
assert sum(x['total_planned_intervals_4_runs'] for x in choices)==4224
points=rows(C/'formal_audit/COMMON_FRONTIER_POINTS.csv');phase=[]
for kind in ['fixed1','fixed2','fixed3','backlog','deadline','joint']:
    for ph in ['low_initial','high','low_final']:
        rs=[r for r in points if r['cell'].startswith(kind+'-') and r['phase_by_release']==ph]
        phase.append({'method':kind,'phase_by_frontier_release':ph,'observed_frontiers_4_repeats':len(rs),'mean_audio_seconds_meeting_both_deadlines_per_run':sum(float(r['audio_seconds']) for r in rs if float(r['display'])<=2 and float(r['commit'])<=8)/4,'conditional_pooled_display_p99_s':q([float(r['display']) for r in rs],.99),'conditional_pooled_commit_p99_s':q([float(r['commit']) for r in rs],.99),'not_additional_independent_audio':True})
out={'two_plane_costs':cost,'forecast_errors':pred,'choices_and_overhead':choices,'phase_frontier_diagnostics':phase,'scope':'descriptive after formal; no policy tuning; no causal claim; model-call elapsed intervals are not CUDA kernel busy utilization; install minus ETA includes Render/WAL and waiting; phase is by release clock, not instantaneous occupancy'}
(W/'FINAL_DIAGNOSTICS.json').write_text(json.dumps(out,indent=2)+'\n')
for n,rs in [('TWO_PLANE_COSTS.csv',cost),('FORECAST_ERRORS.csv',pred),('PHASE_FRONTIER_DIAGNOSTICS.csv',phase)]:
    with (W/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
print(json.dumps({k:v for k,v in out.items() if k!='phase_frontier_diagnostics'},indent=2))
