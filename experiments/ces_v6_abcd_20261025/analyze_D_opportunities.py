"""Observed action/cost opportunities, not an unexecuted policy oracle."""
from pathlib import Path
from collections import Counter
import argparse,csv,json,statistics,hashlib
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();O=a.root;A=a.output;A.mkdir()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
rows=[];plans=[];reasons=[]
for stage in ['D_development','D_heldout']:
 for C in [O/stage/name for name in sorted(read(O/(stage+'_SUMMARY.json'))['completed'])]:
  cfg=read(C/'config.json');events=lines(C/'events.jsonl');rs=lines(C/'worker_records.jsonl');acs=lines(C/'worker_batch_accounting.jsonl');byid={r['job']['job_id']:r for r in rs}
  decisions=[e for e in events if e['kind']=='ces-decision'];anchor=cfg['ces_study']['v6']['policy']=='anchor_cost';reason=Counter(e['reason'] for e in decisions)
  for why,n in reason.items():reasons.append({'stage':stage,'cell':C.name,'reason':why,'count':n})
  authority=[r for r in rs if r['job']['role']=='authority'];verify=[r for r in authority if r['job']['ces_operation']=='verify'];proposal=[r for r in rs if r['job']['role']=='proposal']
  observed=[]
  for rec in authority:
   j=rec['job'];cand=[r for r in proposal if r['job']['session_id']==j['session_id'] and r['job']['audio_end_sample']==j['audio_end_sample'] and r['result']['received_perf']<=j['enqueue_perf']]
   observed.append(bool(cand))
  actual_credit=[e.get('v6_observed_credit_rate',0.) for e in decisions]
  rows.append({'stage':stage,'cell':C.name,'method':C.name.rsplit('-r',1)[0].split('-',3)[-1],'authority_targets':len(authority),'targets_with_existing_candidate_at_actual_dispatch':sum(observed),'actual_verify_rows':len(verify),'actual_fallback_rows':sum(r['result']['online_verification']['fallback_used'] for r in verify),'same_birth_verified_rows':sum(byid[r['job']['candidate_origin_job_id']]['job']['parent']==r['job']['parent'] and byid[r['job']['candidate_origin_job_id']]['job']['prompt_tokens']==r['job']['prompt_tokens'] for r in verify),'decision_count':len(decisions),'supported_deviations':sum(e.get('chosen_index',0)>0 for e in decisions),'planning_overrun_defaults':reason['anchor-planning-age-overrun-default'],'planning_wall_s':sum(e['planner_wall_seconds'] for e in decisions),'max_single_plan_wall_s':max(e['planner_wall_seconds'] for e in decisions),'nonzero_credit_decisions':sum(x>0 for x in actual_credit),'proposal_caps':sum(r['result']['hit_token_limit'] for r in proposal),'proposal_physical_batches':sum(byid[b['job_ids'][0]]['job']['role']=='proposal' for b in acs),'anchor':anchor})
  for e in decisions:
   for s in e.get('anchor_scores',[]):
    if s['index']==0:continue
    plans.append({'stage':stage,'cell':C.name,'observed_perf':e['observed_perf'],'plan_index':s['index'],'chosen':e.get('chosen_index')==s['index'],'viable':s['viable'],'all_supported':s['all_supported'],'conservative_credit_gain':s['conservative_credit_gain'],'predicted_work_saving':s['predicted_work_saving'],'mean_work':s['mean_work'],'upper_wall':s['upper_wall'],'late_audio_risk':s['late_audio_risk'],'future_unissued_risk':s['future_unissued_risk'],'scope':'Only observable predictions; not measured unchosen costs'})
for name,rs in [('D_OPPORTUNITIES.csv',rows),('D_PLAN_GATES.csv',plans),('D_DECISION_REASONS.csv',reasons)]:
 with (A/name).open('w',newline='') as f:
  if rs:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
  else:f.write('no_observed_rows\n')
report={'status':'COMPLETE_OBSERVED_D_OPPORTUNITY_AND_OVERHEAD_AUDIT','serving_cells':len(rows),'verified_rows':sum(r['actual_verify_rows'] for r in rows),'fallback_rows':sum(r['actual_fallback_rows'] for r in rows),'ready_candidate_targets_at_actual_dispatch':sum(r['targets_with_existing_candidate_at_actual_dispatch'] for r in rows),'authority_target_observations':sum(r['authority_targets'] for r in rows),'preconditions_not_IID_or_counterfactual':'Readiness at different policies dispatch times is selection-dependent; no reassembled or oracle speedup is claimed.','all_causal_risk_terms_disabled':all(r['future_unissued_risk']==0 for r in plans),'new_GPU_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
