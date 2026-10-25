"""Count emergent tails and real context clocks without calling them natural faults."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();O=a.root;A=a.output;A.mkdir()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
cells=[];tails=[];batches={}
for stage in ['A_pilot','A','C','D_development','D_heldout']:
 for name in read(O/(stage+'_SUMMARY.json'))['completed']:
  C=O/stage/name;cfg=read(C/'config.json');es=lines(C/'events.jsonl');rs=lines(C/'worker_records.jsonl');ss=read(C/'sessions.json');t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');acs=lines(C/'worker_batch_accounting.jsonl');byid={r['job']['job_id']:r for r in rs};bybatch={j:b for b in acs for j in b['job_ids']};commits=[e for e in es if e['kind']=='commit'];n=0;tokens=0
  for rec in rs:
   j,r=rec['job'],rec['result']
   if j['role']!='proposal':continue
   n+=1;tokens+=len(r['token_ids'])
   if not r['hit_token_limit']:continue
   sid=j['session_id'];prior=[e for e in commits if e['session_id']==sid and t0+e['installed']<=j['enqueue_perf']]
   latest=max(prior,key=lambda e:e['version']) if prior else None
   auth=[x for x in rs if x['job']['role']=='authority' and x['job']['session_id']==sid and x['job']['end_window']==j['end_window']]
   assert len(auth)==1
   target=auth[0];b=bybatch[j['job_id']];lease=b['batch_result_complete_perf']-b['worker_started_perf'];key=stage,name,b['batch_id']
   batches[key]={'stage':stage,'cell':name,'batch_id':b['batch_id'],'physical_lease_s':lease,'rows':len(b['job_ids'])}
   tails.append({'stage':stage,'cell':name,'traffic':cfg['ces_study']['traffic'],'method':name.rsplit('-r',1)[0].split('-',3)[-1],
    'source':j['source_id'],'sid':sid,'window':j['end_window'],'birth_parent':j['parent'],'latest_canonical_before_issue':0 if latest is None else latest['version'],
    'audio_ready':j['audio_ready_perf']-t0,'enqueued':j['enqueue_perf']-t0,'row_returned':r['received_perf']-t0,'cap_tokens':len(r['token_ids']),
    'same_actual_conditioning_tokens_as_Authority':r['execution_context_audit']['executed_prompt_tokens']==target['result']['execution_context_audit']['executed_prompt_tokens'],
    'same_actual_target_audio_as_Authority':r['execution_context_audit']['actual_audio_sha256']==target['result']['execution_context_audit']['actual_audio_sha256'],
    'direct_injected_input_override':'fault_actual_prompt_tokens' in j,'associated_batch_id':b['batch_id'],'associated_batch_lease_not_exclusive_s':lease,
    'declared_hold_seconds':cfg['ces_study'].get('v6',{}).get('authority_hold_seconds',0.),'scope':'Emergent generation during declared clean/F2 laboratory workload, not production fault prevalence'})
  cells.append({'stage':stage,'cell':name,'traffic':cfg['ces_study']['traffic'],'method':name.rsplit('-r',1)[0].split('-',3)[-1],'proposal_rows':n,'proposal_tokens':tokens,'cap_rows':sum(x['stage']==stage and x['cell']==name for x in tails),'associated_unique_batches':sum(x[0]==stage and x[1]==name for x in batches)})
for file,rows in [('PRIVATE_TAIL_CELLS.csv',cells),('PRIVATE_CAP_ROWS.csv',tails),('PRIVATE_CAP_ASSOCIATED_BATCHES.csv',list(batches.values()))]:
 with (A/file).open('w',newline='') as f:
  if rows:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  else:f.write('no_observed_rows\n')
summary={'status':'COMPLETE_ACTUAL_PRIVATE_TAIL_CENSUS','serving_cells':len(cells),'cap_row_observations':len(tails),'unique_cap_sources':sorted({r['source'] for r in tails}),'cap_associated_unique_batches':len(batches),'non_C_intervention_cap_rows':sum(r['stage']!='C' for r in tails),'heldout_cap_rows':sum(r['stage']=='D_heldout' for r in tails),'new_GPU_calls':0,'birth_mismatch_not_automatically_illegal':True,'no_row_exclusive_GPU_cost_claim':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
