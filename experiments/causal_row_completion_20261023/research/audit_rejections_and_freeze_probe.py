"""P0: rejection associations, not an assumed causal rejection cascade."""
from collections import Counter,defaultdict
from pathlib import Path
import csv,hashlib,json,sys

B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023'
OLD=B/'results/revtrace/online_admission_20261022';D=O/'p0_v1';D.mkdir(exist_ok=False)
index={r['path']:r for r in json.loads((OLD/'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())['files']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p,lines=False):
 raw=p.read_bytes();r=index[p.relative_to(OLD).as_posix()]
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return [json.loads(x) for x in raw.splitlines()] if lines else json.loads(raw)
def write(name,rs):
 with (D/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def state_digest(tokens):return hashlib.sha256(','.join(map(str,tokens)).encode()).hexdigest()
out=[];plans=[];physical=[];cell_summaries=[];unknown=[]
try:
 for C in sorted((OLD/'formal_v1').iterdir()):
  if not C.is_dir() or not (C/'config.json').is_file():continue
  cfg=read(C/'config.json');method=cfg['online_study']['method']
  if method not in ['score','strict','fine','dgft','standard']:continue
  rs=read(C/'worker_records.jsonl',True);byid={r['job']['job_id']:r for r in rs}
  es=read(C/'events.jsonl',True);commits={(e['session_id'],e['version']):e for e in es if e['kind']=='commit'}
  t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
  ancestry={};unresolved={}
  props=sorted([r for r in rs if r['job']['role']=='proposal'],key=lambda r:r['job']['end_window'])
  for r in props:
   j,z=r['job'],r['result'];jid=j['job_id']
   if 'fault_actual_prompt_tokens' in j:
    ancestry[jid]={jid};unresolved[jid]=False;continue
   prev=[p for p in props if p['job']['session_id']==j['session_id']
         and p['job'].get('branch_generation')==j.get('branch_generation')
         and p['job']['end_window']==j['chunk_id']
         and p['job']['end_window']<j['end_window']
         and p['result']['state_tokens']==j['prompt_tokens']]
   if len(prev)==1:
    pid=prev[0]['job']['job_id'];ancestry[jid]=set(ancestry.get(pid,set()));unresolved[jid]=unresolved.get(pid,True)
   elif not j['prompt_tokens'] or j['prompt_tokens']==(commits.get((j['session_id'],j['parent']),{}).get('next_prompt_tokens',[])):
    ancestry[jid]=set();unresolved[jid]=False
   else:ancestry[jid]=set();unresolved[jid]=True
  batches=defaultdict(list)
  for r in rs:batches[r['job']['role'],r['result']['started_perf'],r['result']['completed_perf']].append(r)
  ordered=sorted(batches.items(),key=lambda kv:kv[0][1])
  for bi,(key,group) in enumerate(ordered):
   group.sort(key=lambda r:r['job']['enqueue_perf'])
   accepts=[r['result'].get('online_verification',{}).get('candidate_accepted') for r in group]
   lens=[len(r['result']['token_ids']) for r in group]
   physical.append({'cell':C.name,'method':method,'role':key[0],'physical_batch_index':bi,
      'job_ids':[r['job']['job_id'] for r in group],'rows':len(group),'min_tokens':min(lens),'max_tokens':max(lens),
      'direct_F2_rows':sum('fault_actual_prompt_tokens' in r['job'] for r in group),
      'descendant_exposure_rows':sum(bool(ancestry.get(r['job']['job_id'],set())) for r in group),
      'accepts':sum(x is True for x in accepts),'rejects':sum(x is False for x in accepts),
      'has_verification':method in ['score','strict'] and key[0]=='authority',
      'started_perf':key[1],'completed_perf':key[2]})
  if method not in ['score','strict']:continue
  targets=sorted([r for r in rs if r['job']['role']=='authority'],key=lambda r:(r['job']['session_id'],r['job']['end_window']))
  previous={};counter=Counter()
  for r in targets:
   j,z=r['job'],r['result'];proof=z['online_verification'];candidate=byid[j['candidate_origin_job_id']]
   cj,cz=candidate['job'],candidate['result'];direct='fault_actual_prompt_tokens' in cj
   roots=ancestry[cj['job_id']];desc=bool(roots) and not direct
   accepted=proof['candidate_accepted'];assert proof['fallback_used']!=accepted
   reject=proof['reason'];shape=reject in ['invalid-length','tokens-after-stop','early-nonterminal-prefix','incomplete-prediction']
   oldparent=cj['parent']!=j['parent'];oldprompt=cj['prompt_tokens']!=j['prompt_tokens']
   ci,ti=cz['model_input_audit'],z['model_input_audit']
   input_same=ci['unpadded_input_ids']==ti['unpadded_input_ids']
   prefix_same=ci['rollback_prefix']==ti['rollback_prefix']
   features_same=ci['row_features']==ti['row_features']
   parent_incompatible=oldparent or oldprompt or not input_same or not prefix_same
   primary=('accepted' if accepted else 'termination_or_structure' if shape else
      'direct_F2' if direct else 'private_F2_ancestry_association' if desc else
      'candidate_birth_target_context_incompatible' if parent_incompatible else
      'unresolved_ancestry' if unresolved[cj['job_id']] else 'unlinked_content_or_numeric_difference')
   prev=previous.get(j['session_id']);online_signal=bool(prev and prev['result']['online_verification']['fallback_used']
       and cj['enqueue_perf']<t0+commits[j['session_id'],j['parent']]['installed'])
   vp=[p for p in proof['phases'] if p['phase'].startswith('correct-context')]
   fb=[p for p in proof['phases'] if 'fallback' in p['phase']]
   p={'cell':C.name,'method':method,'load':C.name.split('-')[1],'traffic':cfg['online_study']['traffic'],
    'source_id':j['source_id'],'target_job_id':j['job_id'],'origin_job_id':cj['job_id'],
    'target_window':j['end_window'],'accepted':accepted,'fallback':proof['fallback_used'],'checker_reason':reject,
    'primary_reporting_class_not_unique_causal_claim':primary,'direct_consumed_F2':direct,
    'private_F2_ancestry_association':desc,'ancestry_roots':sorted(roots),'ancestry_unresolved':unresolved[cj['job_id']],
    'origin_parent_differs_target':oldparent,'origin_logical_prompt_differs':oldprompt,
    'realized_unpadded_IDs_equal':input_same,'realized_decoder_prefix_equal':prefix_same,
    'row_feature_hashes_equal':features_same,
    'online_prev_fallback_and_preissued_child_signal':online_signal,
    'old_ancestry_or_parent_not_a_guaranteed_rejection':bool(accepted and (desc or parent_incompatible)),
    'verification_completed_perf':vp[-1]['completed_perf'] if vp else None,
    'fallback_started_perf':fb[0]['started_perf'] if fb else None,
    'fallback_completed_perf':fb[-1]['completed_perf'] if fb else None,
    'original_row_final_perf_UNKNOWN':None,'original_batch_return_perf':z['completed_perf'],
    'original_Render_of_verified_success_not_built_until_after_fallback':bool(accepted and fb),
    'numerical_vs_model_cause_not_identified_by_this_CPU_audit':True}
   out.append(p);counter[primary]+=1;previous[j['session_id']]=r
  cell_summaries.append({'cell':C.name,'method':method,'load':C.name.split('-')[1],
   'traffic':cfg['online_study']['traffic'],'targets':len(targets),'accepted':sum(r['result']['online_verification']['candidate_accepted'] for r in targets),
   'fallback':sum(r['result']['online_verification']['fallback_used'] for r in targets),
   'direct_F2_jobs':sum('fault_actual_prompt_tokens' in r['job'] for r in props),
   'primary_counts':dict(counter)})
 assert len(out)==3912 and len(cell_summaries)==24
 # Frozen diagnostic selection, not an unbiased serving source sample.
 requests=[
  ('fine-sync16-clean-r0','authority','heterogeneous'),
  ('dgft-sync16-clean-r0','authority','heterogeneous'),
  ('dgft-sync16-F2-r0','proposal','direct_F2'),
  ('dgft-sync16-F2-r0','proposal','post_F2'),
  ('dgft-sync16-F2-r0','authority','heterogeneous'),
  ('standard-sync16-F2-r0','authority','heterogeneous'),
  ('strict-sync16-F2-r0','authority','mixed_verify'),
  ('strict-cohort8-F2-r0','authority','mixed_verify'),
  ('score-sync16-F2-r0','authority','mixed_verify'),
  ('score-cohort8-F2-r0','authority','mixed_verify'),
  ('strict-sync16-clean-r0','authority','all_pass'),
  ('score-sync16-clean-r0','authority','all_pass')]
 used=set()
 for cell,role,criterion in requests:
  candidates=[r for r in physical if r['cell']==cell and r['role']==role and r['rows']>=2]
  if criterion=='heterogeneous':candidates=[r for r in candidates if r['max_tokens']>r['min_tokens']]
  elif criterion=='direct_F2':candidates=[r for r in candidates if r['direct_F2_rows']]
  elif criterion=='post_F2':candidates=[r for r in candidates if r['descendant_exposure_rows'] and not r['direct_F2_rows']]
  elif criterion=='mixed_verify':candidates=[r for r in candidates if r['accepts'] and r['rejects']]
  elif criterion=='all_pass':candidates=[r for r in candidates if r['accepts']==r['rows']]
  candidates=[r for r in candidates if (r['cell'],r['physical_batch_index']) not in used]
  if not candidates:
   plans.append({'cell':cell,'role':role,'criterion':criterion,'status':'NO_MATCH_NOT_REPLACED'});continue
  chosen=min(candidates,key=lambda r:r['started_perf']);used.add((cell,chosen['physical_batch_index']))
  plans.append({**chosen,'criterion':criterion,'status':'FROZEN_BEFORE_NEW_GPU'})
 write('REJECTION_ASSOCIATIONS.csv',out)
 write('REJECTION_CELLS.csv',cell_summaries)
 (D/'PHYSICAL_BATCH_INVENTORY.json').write_text(json.dumps(physical,indent=2)+'\n')
 (D/'GPU_PROBE_PLAN.json').write_text(json.dumps({'operations':plans,'two_ABA_cycles':True,
   'selection':'deterministic old-log diagnostic fixtures, not a new serving population',
   'original_row_final_times_unknown':True,'no_new_GPU_yet':True},indent=2)+'\n')
 stats=[]
 for method in ['score','strict']:
  for load in ['cohort8','sync16']:
   for traffic in ['clean','F2']:
    a=[r for r in out if r['method']==method and r['load']==load and r['traffic']==traffic]
    sig=[r for r in a if r['online_prev_fallback_and_preissued_child_signal']]
    stats.append({'method':method,'load':load,'traffic':traffic,'targets':len(a),
     'fallback':sum(r['fallback'] for r in a),'direct_F2':sum(r['direct_consumed_F2'] for r in a),
     'rejected_classes':dict(Counter(r['primary_reporting_class_not_unique_causal_claim'] for r in a if r['fallback'])),
     'signal_targets':len(sig),'signal_rejected':sum(r['fallback'] for r in sig),
     'signal_accepted_counterexamples':sum(r['accepted'] for r in sig),
     'accepted_context_or_old_ancestry_counterexamples':sum(r['old_ancestry_or_parent_not_a_guaranteed_rejection'] for r in a)})
 summary={'status':'PASS_OLD72_REJECTION_ASSOCIATION_AND_PROBE_FREEZE','rows':len(out),
  'physical_batches':len(physical),'frozen_probe_operations':sum(r['status']=='FROZEN_BEFORE_NEW_GPU' for r in plans),
  'groups':stats,'no_claim_lag1_or_ancestry_implies_rejection':True,
  'new_GPU_calls':0,'script_sha256':sha(Path(__file__))}
 (D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
except BaseException as e:
 (D/'STOP.json').write_text(json.dumps({'error':repr(e),'old_raw_untouched':True})+'\n');raise
