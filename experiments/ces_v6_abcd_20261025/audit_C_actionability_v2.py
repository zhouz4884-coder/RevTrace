"""Post-randomization actionability audit, not a simulated policy speedup."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,json,hashlib,statistics
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();O=a.root;A=a.output;A.mkdir()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
rows=[]
for C in [O/'C'/name for name in sorted(read(O/'C_SUMMARY.json')['completed'])]:
 cfg=read(C/'config.json');es=lines(C/'events.jsonl');rs=lines(C/'worker_records.jsonl');spec={s['session_id']:s for s in read(C/'sessions.json')};commits={r['job_id']:r for r in es if r['kind']=='commit'};t0=next(r['t0_perf'] for r in es if r['kind']=='run-start')
 for r in rs:
  j,v=r['job'],r['result']
  if j['role']!='authority' or j['end_window']!=5:continue
  sid=j['session_id'];offered=[x for x in rs if x['job']['role']=='proposal' and x['job']['session_id']==sid and x['job']['end_window']==5 and x['result']['received_perf']<=j['enqueue_perf']]
  all5=[x for x in rs if x['job']['role']=='proposal' and x['job']['session_id']==sid and x['job']['end_window']==5]
  cand5=min((x['result']['received_perf'] for x in all5),default=None)
  pending=[x for x in rs if x['job']['role']=='proposal' and x['job']['session_id']==sid and x['job']['enqueue_perf']<=j['enqueue_perf']<x['result']['received_perf']]
  future=[x for x in rs if x['job']['role']=='proposal' and x['job']['session_id']==sid and x['job']['end_window']>5 and x['job']['enqueue_perf']>=v['received_perf']]
  release=t0+spec[sid]['offset']+min(12.,spec[sid]['duration']);installed=t0+commits[j['job_id']]['installed'];hold=cfg['ces_study']['v6']['authority_hold_seconds']
  rows.append({'cell':C.name,'traffic':cfg['ces_study']['traffic'],'repeat':int(C.name.rsplit('-r',1)[1]),'hold':hold,'sid':sid,'source':j['source_id'],
   'ready_candidate5_at_actual_authority_dispatch':bool(offered),'same_birth_ready_candidates':sum(x['job']['parent']==j['parent'] and x['job']['prompt_tokens']==j['prompt_tokens'] for x in offered),
   'pending_private_rows_at_dispatch':len(pending),'observed_dispatch_to_result_receipt_s':v['received_perf']-j['enqueue_perf'],'receipt_to_next_audio_release_s':release-v['received_perf'],
   'actual_candidate5_delay_from_auth_dispatch_s':None if cand5 is None else cand5-j['enqueue_perf'],
   'observed_zero_cost_verify_headroom_s_not_counterfactual_gain':0. if cand5 is None else max(0.,v['received_perf']-cand5),
   'receipt_plus_assigned_hold_crosses_next_release':v['received_perf']+hold>=release,'actual_install_crosses_next_release':installed>=release,
   'future_new_jobs':len(future),'future_new_tokens':sum(len(x['result']['token_ids']) for x in future),'future_new_caps':sum(x['result']['hit_token_limit'] for x in future)})
with (A/'C_DECISION_ACTIONABILITY.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
groups=[]
for traffic in ['clean','mixed']:
 for hold in [0.,.75,1.5]:
  rs=[r for r in rows if r['traffic']==traffic and r['hold']==hold]
  groups.append({'traffic':traffic,'hold':hold,'actual_decisions':len(rs),'ready_candidates':sum(r['ready_candidate5_at_actual_authority_dispatch'] for r in rs),'pending_private_at_dispatch':sum(r['pending_private_rows_at_dispatch']>0 for r in rs),'assigned_hold_crosses_next_release':sum(r['receipt_plus_assigned_hold_crosses_next_release'] for r in rs),'actual_install_crosses_next_release':sum(r['actual_install_crosses_next_release'] for r in rs),'future_new_caps':sum(r['future_new_caps'] for r in rs),'median_nohold_receipt_slack_to_next_release_s':statistics.median(r['receipt_to_next_audio_release_s'] for r in rs),'positive_observed_zero_cost_verify_headroom':sum(r['observed_zero_cost_verify_headroom_s_not_counterfactual_gain']>0 for r in rs),'median_observed_zero_cost_verify_headroom_s':statistics.median(r['observed_zero_cost_verify_headroom_s_not_counterfactual_gain'] for r in rs)})
report={'status':'COMPLETE_ACTUAL_ACTION_OPPORTUNITY_AUDIT','groups':groups,'not_a_counterfactual_schedule':'Observed readiness is evaluated at each real Fine dispatch. Waiting could create another feasible action with its own paid delay; no such action is executed by this audit.','causal_intervention_scope':'Large artificial installation holds do not identify the effect of a small Verify-vs-Generate compute-time change. Future cost is threshold-dependent on lawful audio/Parent release.','no_policy_uses_fault_labels':True,'new_GPU_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
