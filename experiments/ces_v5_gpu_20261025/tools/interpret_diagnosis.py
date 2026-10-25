"""Derived actual-path diagnosis; does not construct missing GPU outcomes."""
from pathlib import Path
from collections import defaultdict
import json,statistics
from local_review import csvrows,sha
W=Path(__file__).resolve().parent;A=W/'local_review';R=W/'collected'
critical=csvrows(A/'AUTHORITY_CRITICAL_PATHS.csv');defer=csvrows(A/'TARGET_DEFERRALS.csv')
rows=csvrows(R/'pilot_v1_audit_corrected/SERVICE_CELLS.csv');groups=defaultdict(list)
for r in critical:groups[r['cell'].split('-')[1],r['method']].append(r)
parts=['release_to_parent_eligible_s','eligible_to_enqueue_s','enqueue_to_worker_start_s','worker_start_to_complete_row_s',
    'row_to_trusted_render_s','render_to_emit_s','emit_to_owner_receive_s','owner_receive_to_install_s']
result=[]
for (arrival,method),rr in sorted(groups.items()):
    late=[r for r in rr if r['commit_8s_missed']]
    dd=[d for d in defer if d['cell'].split('-')[1]==arrival and d['method']==method]
    summary={'arrival':arrival,'method':method,'frontier_observations':len(rr),'commit_8s_misses':len(late),
        'non_IID_frontiers':True,'actual_eligible_first_batch_deferrals':sum(d['first_batch_deferrals'] for d in dd),
        'targets_observed_passed_over':sum(d['first_batch_deferrals']>0 for d in dd),
        'max_observed_passovers_one_target':max([d['first_batch_deferrals'] for d in dd] or [0]),
        'deferral_telemetry_available':bool(dd),
        'all_targets_mean_path_s':{k:statistics.mean(r[k] for r in rr) for k in parts},
        'late_targets_mean_path_s':{k:statistics.mean(r[k] for r in late) for k in parts} if late else None,
        'late_targets_mean_occupied_queue_s':statistics.mean(r['eligible_queue_overlap_other_authority_lease_s'] for r in late) if late else None,
        'late_targets_mean_nonlease_queue_s':statistics.mean(r['eligible_queue_nonlease_host_and_scheduler_s'] for r in late) if late else None}
    result.append(summary)
    print('PATH',arrival,method,json.dumps({k:v for k,v in summary.items() if k not in ['all_targets_mean_path_s']}))
byjob={(r['cell'],r['job_id']):r for r in critical}
examples=[]
for d in sorted(defer,key=lambda r:(r['first_batch_deferrals'],r['first_observed_to_enqueue_s']),reverse=True)[:12]:
    c=byjob[d['cell'],d['job_id']];examples.append(dict(d,path=c))
    print('DEFERRED_EXAMPLE',d['cell'],d['job_id'],json.dumps({'passovers':d['first_batch_deferrals'],
        'first_observed_to_enqueue_s':d['first_observed_to_enqueue_s'],'commit_latency_s':c['commit_latency_s'],
        'parent_wait_s':c['release_to_parent_eligible_s'],'eligible_wait_s':c['eligible_to_enqueue_s'],
        'own_worker_row_s':c['worker_start_to_complete_row_s']}))
behave=csvrows(A/'V5_DECISION_BEHAVIOR.csv');bg=defaultdict(list)
for r in behave:bg[r['cell'].split('-')[1],r['method']].append(r)
bs=[]
for (arrival,method),rr in sorted(bg.items()):
    x={'arrival':arrival,'method':method,'actual_decisions':len(rr),
        'same_operation_split_plans':sum(r['same_operation_split'] for r in rr),
        'first_batch_smaller_than_cut':sum(r['first_rows']<r['current_cut'] for r in rr),
        'zero_credit_decisions':sum(r['zero_residual_credit'] for r in rr),
        'max_planner_wall_s':max(r['planner_wall_s'] for r in rr)}
    bs.append(x);print('DECISION_BEHAVIOR',json.dumps(x))
head=csvrows(A/'ARRIVAL_HEADROOM_BOUNDS.csv')
for arrival in ['sync','staggered']:
    rr=[r for r in head if r['cell'].split('-')[1]==arrival and r['method']=='fine']
    print('ARRIVAL_HEADROOM_FINE',arrival,json.dumps({'upper_bound_goodput':statistics.median(r['arrival_only_goodput_upper_bound'] for r in rr),
        'max_relative_goodput_headroom_median':statistics.median(r['max_relative_goodput_headroom'] for r in rr),
        'max_relative_throughput_headroom_median':statistics.median(r['max_relative_throughput_headroom'] for r in rr)}))
rowstats=csvrows(A/'SELECTED_ROW_FORECAST_GROUPS.csv')
for r in rowstats:print('ROW_FORECAST',json.dumps(r))
out={'scope':'Actual selected decisions and event paths only; no unchosen-action counterfactual or future gain estimate',
    'critical_path_groups':result,'deferred_examples':examples,'decision_behavior':bs,'selected_row_forecast_groups':rowstats,
    'audit_script_sha256':sha(Path(__file__))}
target=A/'DIAGNOSIS_SUMMARY.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n')
