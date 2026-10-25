"""Separate installation randomization, exact target matching and paid future work."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();O=a.root
assert json.loads((O/'C_SUMMARY.json').read_text())['status']=='COMPLETE_GPU_MATRIX_AND_SAFETY_AUDIT'
A=O/'C_independent_analysis_v2';A.mkdir()
def load(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def csvsave(name,rows):
 with (A/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
cells=[];targets=[];caps=[];batches=[];private=[];target_map={}
for C in [O/'C'/name for name in sorted(json.loads((O/'C_SUMMARY.json').read_text())['completed'])]:
 cfg=load(C/'config.json');records=lines(C/'worker_records.jsonl');es=lines(C/'events.jsonl');byid={r['job']['job_id']:r for r in records}
 arm=cfg['ces_study']['v6']['authority_hold_seconds'];traffic=cfg['ces_study']['traffic'];repeat=int(C.name.rsplit('-r',1)[1])
 t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
 window5={r['job']['session_id']:r for r in records if r['job']['role']=='authority' and r['job']['end_window']==5}
 assert len(window5)==16
 post=[];inflight=[];raw_post_tokens=0
 for sid,r in window5.items():
  j,v=r['job'],r['result'];audit=v['model_input_audit']
  identity={'sid':sid,'source':j['source_id'],'parent':j['parent'],'prompt':j['prompt_tokens'],'audio_start':j['audio_start_sample'],'audio_end':j['audio_end_sample'],'audio_sha':j['prefix_audio_sha256'],'effective_context':v['execution_context_audit']['executed_prompt_tokens'],'individual_tensors':{k:x for k,x in audit.items() if k not in ['batch_tensors','row_index','physical_batch_rows']}}
  # Batch tensor identity is separately compared, not folded into logical identity.
  check={'cell':C.name,'traffic':traffic,'repeat':repeat,'hold':arm,'sid':sid,'source':j['source_id'],'logical_target_sha':digest({k:x for k,x in identity.items() if k!='individual_tensors'}),'individual_input_sha':digest(identity['individual_tensors']),'batch_input_sha':digest(audit['batch_tensors']),'Z_sha':digest(v['token_ids']),'P_sha':digest(v['state_tokens']),'text_sha':digest(v['text']),'cap':v['hit_token_limit']}
  targets.append(check);target_map[traffic,repeat,arm,sid]=check
 for r in records:
  j,v=r['job'],r['result']
  if j['role']!='proposal':continue
  receipt=window5[j['session_id']]['result']['received_perf'];future=j['end_window']>5
  new=future and j['enqueue_perf']>=receipt
  if future and not new:inflight.append(j['job_id'])
  if new:post.append(j['job_id']);raw_post_tokens+=len(v['token_ids'])
  if v['hit_token_limit']:caps.append({'cell':C.name,'traffic':traffic,'repeat':repeat,'hold':arm,'source':j['source_id'],'sid':j['session_id'],'window':j['end_window'],'parent':j['parent'],'direct_F2_override':'fault_actual_prompt_tokens' in j,'new_after_target_receipt':new,'input_sha':digest(v['model_input_audit']),'tokens':len(v['token_ids'])})
  private.append({'cell':C.name,'traffic':traffic,'repeat':repeat,'hold':arm,'source':j['source_id'],'sid':j['session_id'],'window':j['end_window'],'parent':j['parent'],'new_after_window5_receipt':new,'inflight_at_window5_receipt':future and not new,'tokens':len(v['token_ids']),'cap':v['hit_token_limit'],'batch_id':v['physical_batch_id']})
 accts=lines(C/'worker_batch_accounting.jsonl');total=exclusive=mixed=remaining=0.;calls=exclusive_calls=mixed_calls=0
 first_receipt=min(r['result']['received_perf'] for r in window5.values())
 for b in accts:
  if byid[b['job_ids'][0]]['job']['role']!='proposal':continue
  ids=b['job_ids'];duration=b['batch_result_complete_perf']-b['worker_started_perf'];total+=duration;calls+=len(b['phases'])
  selected=[i for i in ids if i in post];kind='no_future_new'
  if selected:
   kind='exclusively_future_new' if len(selected)==len(ids) else 'overlapping_mixed'
   if len(selected)==len(ids):exclusive+=duration;exclusive_calls+=len(b['phases'])
   else:mixed+=duration;mixed_calls+=len(b['phases'])
  if b['worker_started_perf']<first_receipt<b['batch_result_complete_perf']:remaining+=b['batch_result_complete_perf']-first_receipt
  batches.append({'cell':C.name,'traffic':traffic,'repeat':repeat,'hold':arm,'batch_id':b['batch_id'],'classification':kind,'rows':len(ids),'future_new_rows':len(selected),'physical_lease_s':duration,'max_tokens':max(len(byid[i]['result']['token_ids']) for i in ids)})
 cells.append({'cell':C.name,'traffic':traffic,'repeat':repeat,'hold':arm,'GPU0_paid_lease_s':total,'GPU0_physical_calls':calls,'exclusively_future_new_lease_s':exclusive,'exclusively_future_new_calls':exclusive_calls,'mixed_overlap_lease_s_not_exclusive':mixed,'mixed_overlap_calls':mixed_calls,'future_new_rows':len(post),'future_new_tokens':raw_post_tokens,'inflight_future_rows':len(inflight),'inflight_residual_at_first_receipt_s_not_reclaimable':remaining,'proposal_caps':sum(x['cell']==C.name for x in caps),'max_GPU0_lease_s':max(b['physical_lease_s'] for b in batches if b['cell']==C.name),'obsolete_rows':sum(e['kind']=='proposal-obsolete' for e in es),'commits':sum(e['kind']=='commit' for e in es)})
matches=[];contrasts=[]
for traffic in ['clean','mixed']:
 for repeat in range(3):
  base=next(r for r in cells if r['traffic']==traffic and r['repeat']==repeat and r['hold']==0)
  for hold in [.75,1.5]:
   new=next(r for r in cells if r['traffic']==traffic and r['repeat']==repeat and r['hold']==hold)
   counters={k:0 for k in ['logical','individual','batch','Z','P','text','all_exact']}
   for sid in range(16):
    x,y=target_map[traffic,repeat,0.,sid],target_map[traffic,repeat,hold,sid]
    eq={key:x[field]==y[field] for key,field in [('logical','logical_target_sha'),('individual','individual_input_sha'),('batch','batch_input_sha'),('Z','Z_sha'),('P','P_sha'),('text','text_sha')]};eq['all_exact']=all(eq.values())
    matches.append({'traffic':traffic,'repeat':repeat,'hold':hold,'sid':sid,**eq})
    for k,v in eq.items():counters[k]+=v
   contrasts.append({'traffic':traffic,'repeat':repeat,'hold':hold,**{k+'_matched':v for k,v in counters.items()},'target_count':16,**{k+'_delta':new[k]-base[k] for k in ['GPU0_paid_lease_s','exclusively_future_new_lease_s','future_new_rows','future_new_tokens','proposal_caps','max_GPU0_lease_s','obsolete_rows']}})
primary=[r for r in contrasts if r['traffic']=='mixed' and r['hold']==1.5]
gate=all(r['GPU0_paid_lease_s_delta']>0 and r['exclusively_future_new_lease_s_delta']>0 and r['all_exact_matched']/16>=.9 for r in primary)
# Exact matching alone cannot learn the supported observable risk stratum.
decision={'status':'COMPLETE_RANDOMIZED_HOLD_ANALYSIS','cells':len(cells),'causal_numeric_gate_pass':gate,'causal_risk_integration_GO':False,'reason':'NO_GO_INSUFFICIENT_EXACT_MATCH_OR_FUTURE_WORK' if not gate else 'NUMERIC_GATE_ONLY_REQUIRES_SEPARATE_OBSERVABLE_STRATUM_VALIDATION_NOT_AUTOMATIC_GO','all_primary_pairs':primary,'natural_prevalence_claim':False,'GPU_new_calls':0,'physical_batches_not_row_latency_sums':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
for n,rs in [('C_RUNS.csv',cells),('C_TARGETS.csv',targets),('C_TARGET_MATCH.csv',matches),('C_CONTRASTS.csv',contrasts),('C_CAP_ROWS.csv',caps),('C_PRIVATE_ROWS.csv',private),('C_PHYSICAL_BATCHES.csv',batches)]:
 if rs:csvsave(n,rs)
 else:(A/n).write_text('no_observed_rows\n')
save(A/'SUMMARY.json',decision);print(json.dumps(decision))
