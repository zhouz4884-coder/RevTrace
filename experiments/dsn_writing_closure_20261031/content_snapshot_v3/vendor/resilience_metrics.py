"""Offline trial aggregation, never an online control-memory implementation.

Original all-offered D2/C8 quantiles and text-occurrence endpoints are reused.
Archived trace/history allocation here is explicitly outside the serving path.
Semantic admissibility/refinement is a separate checker; unknown evidence is
reported as unknown, not silently converted into a zero-error result.
"""
from __future__ import annotations
import copy,hashlib,json,math,pathlib,re
from collections import Counter,defaultdict
from feedback_contract import FeedbackCut,canonical_bytes
from original_primary_quantiles import cell_metrics,quantile,finite
from content_endpoints import analyze_cell,normalize
from resilience_storage import scan

BDFA='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
class MetricsIntegrityError(RuntimeError):pass
def need(ok,message):
 if not ok:raise MetricsIntegrityError(message)
def load(path):return json.loads(pathlib.Path(path).read_bytes())
def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8'))
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def lines(path):
 p=pathlib.Path(path)
 return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()] if p.exists() else []
def event_time(row):
 for key in ('observed','observed_perf','confirmed_perf','received_perf','synced_perf'):
  value=row.get(key)
  if isinstance(value,(int,float)) and math.isfinite(value):return float(value)
 return None
def logs(root,name):
 rows=[]
 for p in sorted(pathlib.Path(root).rglob(name)):
  need(p.resolve().is_relative_to(pathlib.Path(root).resolve()),'trace path escapes trial')
  for row in lines(p):rows.append((p,row))
 return rows
def epoch_for(path,row):
 if isinstance(row.get('owner_epoch'),int):return row['owner_epoch']
 m=re.search(r'owner_e(\d+)',str(path));return int(m[1]) if m else None
def levenshtein(a,b):
 previous=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  current=[i]
  for j,y in enumerate(b,1):current.append(min(previous[j]+1,current[-1]+1,previous[j-1]+(x!=y)))
  previous=current
 return previous[-1]

def static_reference_state(state,kind,actual_commit):
 s=copy.deepcopy(state)
 if kind=='short_bdfa_static_source_mapping':
  need(isinstance(actual_commit,str) and re.fullmatch('[0-9a-f]{40}',actual_commit),'missing actual runtime commit for static map')
  marker=s['contract']['stage_execution']['source_commit']
  need(marker in (BDFA,actual_commit),'unexpected source marker cannot be projected')
  s['contract']['stage_execution']['source_commit']=BDFA
 elif kind not in ('strict','continuous_original'):raise MetricsIntegrityError('unknown reference comparison kind')
 return s

def fact_audit(path,sources):
 roots={};facts=[];processed={sid:0 for sid in sources};ids=set();sequences=set()
 for obj,receipt in scan(path,repair_tail=False):
  if obj['kind']=='genesis':
   need(not roots,'duplicate genesis');roots={sid:FeedbackCut(v) for sid,v in obj['body']['initials'].items()};need(set(roots)==set(sources),'genesis source set differs')
   for sid,cut in roots.items():need(cut.frontier==0 and cut.transcript=='' and cut.state['contract']['source_sha']==sources[sid]['audio_sha256'],'genesis input differs')
   continue
  need(obj['kind']=='canonical','unknown durable record');body=obj['body'];sid=body['source_id'];parent=FeedbackCut(body['parent_state']);end=FeedbackCut(body['next_state']);record=body['record'];job=body['job']
  need(sid in roots and parent.same(roots[sid]),'durable parent does not follow current source root')
  need(end.frontier==min(sources[sid]['frames'],parent.frontier+8000),'durable transition changed original500ms/EOS cadence')
  need(end.state['contract']==parent.state['contract'],'durable input contract changed')
  need(record['start_state']==parent.sha256 and record['end_state']==end.sha256 and record['start']==parent.frontier and record['end']==end.frontier,'durable original record cut binding differs')
  need(record['role']=='authority' and record['candidate_handoff'] is False and type(record['native_model_evaluated']) is bool,'durable record is not protected original complete C/U')
  need(job['start']==parent.state and job['end']==end.frontier and job['source_id']==sid and job['dispatch_epoch']==body['session_epoch'],'durable owned input identity changed')
  tid=body['transition_id'];need(tid not in ids and obj['sequence'] not in sequences,'duplicate durable transition identity');ids.add(tid);sequences.add(obj['sequence'])
  roots[sid]=end
  if record['native_model_evaluated']:processed[sid]=end.frontier
  facts.append(dict(sequence=obj['sequence'],receipt=receipt,body=body,processed_frontier=processed[sid]))
 need(bool(roots),'no durable genesis');return roots,facts,processed

def reference_audit(config,facts,actual_commit):
 path=config.get('reference_details');kind=config.get('reference_kind','strict')
 if not path:return dict(status='NOT_REQUESTED',checked_steps=0,scope='No fixed-reference empirical equality claimed.')
 p=pathlib.Path(path);need(p.is_file(),'frozen original reference missing')
 if config.get('reference_details_sha256'):need(sha(p)==config['reference_details_sha256'],'frozen original reference bytes differ')
 reference=load(p);need(isinstance(reference,list),'reference must be raw original DETAILS array')
 refs={(r['source_id'],r['end']):r for r in reference};need(len(refs)==len(reference),'duplicate original reference frontier')
 failures=[]
 for fact in facts:
  body=fact['body'];key=(body['source_id'],body['next_state']['frontier']);need(key in refs,'durable frontier lacks original reference');ref=refs[key];record=body['record']
  expected=static_reference_state(ref['original_full_cut'],kind,actual_commit);actual=static_reference_state(body['next_state'],kind,actual_commit)
  ok=expected==actual and ref['original_full_result']['token_ids']==record['token_ids'] and ref['original_full_result']['selected_correction']==record['selected_correction']
  if 'original_full_start_cut' in ref:ok=ok and static_reference_state(ref['original_full_start_cut'],kind,actual_commit)==static_reference_state(body['parent_state'],kind,actual_commit)
  if not ok:failures.append(dict(source_id=key[0],end=key[1],sequence=fact['sequence']))
 return dict(status='PASS_COMPLETE_ORIGINAL_REFERENCE' if not failures else 'FAIL_COMPLETE_ORIGINAL_REFERENCE',checked_steps=len(facts),mismatches=len(failures),first_mismatches=failures[:8],reference_kind=kind,projection='only contract.stage_execution.source_commit maps BDFA/current to BDFA' if kind=='short_bdfa_static_source_mapping' else 'none; entire state/C/IDs compared',reference_sha256=sha(p))

def consumer_audit(rows,facts):
 byseq={f['sequence']:f for f in facts};seen=set();failures=[]
 for row in rows:
  if row['kind']!='canonical':continue
  seq=row.get('journal_sequence');need(seq in byseq,'actual Consumer canonical application lacks its durable fact')
  fact=byseq[seq];body=fact['body'];need(seq not in seen,'same durable transition actually applied twice');seen.add(seq)
  need(row['source_id']==body['source_id'] and row['canonical_sha']==FeedbackCut(body['next_state']).sha256 and row['certified_frontier']==fact['processed_frontier'],'Consumer certified state differs from durable fact')
 return dict(status='PASS_DURABLE_CONSUMER_BINDING',applied_durable_facts=len(seen),durable_facts_not_yet_consumed=len(facts)-len(seen),duplicate_actual_durable_applications=0,scope='Whole provisional text can remain ahead; this does not require Consumer visible text to equal Canonical text.')

def posterior_support(rows,frontiers,facts):
 canon={(f['body']['source_id'],f['body']['next_state']['frontier']):f['body']['next_state']['transcript'] for f in facts};result={}
 for label,transform in [('raw',lambda x:x),('whitespace_stripped',normalize)]:
  weights=Counter();counts=Counter()
  for f in frontiers:
   index=f['first_visible_row'];row=rows[index] if index is not None else None;expected=canon.get((f['source_id'],row['visible_frontier'])) if row else None
   state='unknown' if expected is None else 'supported' if transform(row['text'])==transform(expected) else 'mismatching'
   counts[state]+=1
   if f['original_dual_credit']:weights[state]+=f['audio_seconds']
  result[label]=dict(original_credit_supported_seconds=weights['supported'],original_credit_mismatching_seconds=weights['mismatching'],original_credit_unknown_seconds=weights['unknown'],all_offered_frontier_counts=dict(counts))
 return dict(**result,scope='Posterior whole first-view agreement at its actual G, not online certification, human correctness or newly transcribed character volume.')

def power_metrics(root,origin,end):
 path=pathlib.Path(root)/'power.jsonl'
 if not path.exists() or end is None:return dict(status='UNAVAILABLE',reason='Need actual power trace and explicit service_end_perf; no surrogate end time used.')
 from native_service import Power
 obj=Power.__new__(Power);obj.rows=[dict(time=r['time'],watts={int(k):v for k,v in r['watts'].items()}) for r in lines(path)]
 value=Power.energy(obj,origin,end)
 return dict(status='PASS_ACTUAL_BOTH_BOARD_SERVICE_INTERVAL',service=value,origin_perf=origin,service_end_perf=end,includes_fault_and_recovery_after_origin=True,initial_cold_load_excluded=True,scope='Original Power.energy linear interpolation, both physical boards; no CPU-energy claim.')

def history_metrics(root):
 samples=[row for _,row in logs(root,'state_sizes.jsonl')];control_names=('live_jobs','completed_full','branch_steps','canonical_witnesses','nodes','projections','issued_proofs','issued_id_memory_entries','pending_job_refs')
 maxima={name:max((r.get('history',{}).get(name,0) for r in samples),default=0) for name in control_names}
 for name in ('pending_publications','consumer_pins'):maxima[name]=max((r.get(name,0) for r in samples),default=0)
 separate={name:dict(min=min((r[name] for r in samples if isinstance(r.get(name),(int,float))),default=None),max=max((r[name] for r in samples if isinstance(r.get(name),(int,float))),default=None),last=next((r[name] for r in reversed(samples) if r.get(name) is not None),None)) for name in ('owner_RSS_bytes','current_cut_bytes','current_text_bytes','immutable_audio_bytes')}
 return dict(samples=len(samples),coordination_entry_maxima=maxima,application_and_process_data=separate,scope='Observed finite-run coordination-entry counts; RSS/current cuts/output/immutable audio are separate. Offline analysis allocation and cumulative application output do not establish constant online total memory.')

def state_metrics(root,facts):
 rows=[row for _,row in logs(root,'policy_audit.jsonl') if row.get('kind')=='native_state'];inserts=[r for r in rows if r.get('boundary')=='audio_insert'];trims=[r for r in rows if r.get('boundary')=='context_trim']
 shifts=sum(r.get('buffer_shift',False) for r in inserts);changed=sum(r.get('context_changed',False) for r in trims)
 canonical_shifts=sum(b['next_state']['frontier']-sum(s['samples'] for s in b['next_state']['audio_segments'])>b['parent_state']['frontier']-sum(s['samples'] for s in b['parent_state']['audio_segments']) for b in (f['body'] for f in facts))
 projections={}
 for path,row in logs(root,'worker_results.jsonl'):
  event=row.get('event',row)
  if event.get('kind')=='asr_early':projections[(epoch_for(path,row),event['job_id'])]=event['projection']['end']
 values=defaultdict(list)
 for f in facts:
  b=f['body'];prediction=projections.get((b['owner_epoch'],b['job']['job_id']));values[b['source_id']].append(None if prediction is None else prediction!=b['next_state'])
 clusters={}
 for sid,sequence in values.items():
  longest=current=0
  for v in sequence:current=current+1 if v is True else 0;longest=max(longest,current)
  clusters[sid]=dict(selected_edges=len(sequence),observed_predictions=sum(v is not None for v in sequence),own_prediction_changed=sum(v is True for v in sequence),longest_consecutive_changed=longest,unknown_prediction_edges=sum(v is None for v in sequence))
 return dict(actual_worker_audio_insert_observations=len(inserts),actual_worker_buffer_shifts=shifts,actual_worker_context_trim_changes=changed,actual_worker_context_bound_still_exceeded=sum(r.get('bound_still_exceeded',False) for r in trims),selected_canonical_buffer_shift_edges=canonical_shifts,selected_edge_prediction_clusters=clusters,scope='All worker observations include recomputation; selected-edge clusters are separate and unknown edges break a known streak. These are observed coverage, not natural-prevalence or universal-state-sufficiency claims.')

def recovery_clocks(root,rows,facts,sources,origin,end):
 events=[];direct_faults=[]
 for filename in ('supervisor.jsonl','owner_events.jsonl'):
  for _,raw in logs(root,filename):
   if filename=='supervisor.jsonl' and raw.get('kind')=='fault_triggered':direct_faults.append(dict(raw,_t=event_time(raw)))
   row=raw.get('event',raw);t=event_time(row)
   if t is not None:events.append(dict(row,_t=t))
 events.sort(key=lambda r:r['_t']);faults=direct_faults or [r for r in events if r.get('kind') in ('fault_triggered','owner_fault_ready','fault_injected','owner_sigkill','worker_sigkill')]
 # Supervisor may relay an Owner trigger with the same site. Keep one actual
 # trigger timestamp, rather than count mirror log entries as extra failures.
 unique=[]
 for r in faults:
  if not any((r.get('site'),r.get('job_id'),r.get('owner_epoch'))==(p.get('site'),p.get('job_id'),p.get('owner_epoch')) for p in unique):unique.append(r)
 result=[];fact_by_seq={f['sequence']:f for f in facts};syncs=[r for r in events if r.get('kind')=='durable_sync']
 for fault in unique:
  t=fault['_t'];before_sequences=[r['receipt']['sequence'] for r in syncs if r['_t']<=t and 'receipt' in r]
  if fault.get('receipt'):before_sequences.append(fault['receipt']['sequence'])
  durable_before=max(before_sequences,default=1)
  death=next((r for r in events if r['_t']>=t and r.get('kind') in ('worker_death_confirmed','owner_death_confirmed','owner_group_death_confirmed','owner_exited')),None)
  ready=next((r for r in events if r['_t']>=t and r.get('kind') in ('replacement_neural_ready','recovered_owner_neural_ready','owner_ready') and (r.get('kind')!='owner_ready' or r.get('owner_epoch',0)>fault.get('owner_epoch',-1))),None)
  replay=next((r for r in rows if r['observed']>=t and r.get('recovery_replay') is True),None)
  fresh=[];new_facts=[]
  for r in rows:
   if r['kind']!='canonical' or r['observed']<t:continue
   f=fact_by_seq.get(r.get('journal_sequence'))
   if f and f['sequence']>durable_before:new_facts.append(r)
   if f and f['sequence']>durable_before and not r.get('recovery_replay') and f['body']['record']['model_end']>=t:fresh.append(r)
  first_new=fresh[0] if fresh else None;first_new_fact=new_facts[0] if new_facts else None
  accepted={sid:0 for sid in sources}
  for r in lines(pathlib.Path(root)/'ingress.jsonl'):
   rt=event_time(r)
   if rt is not None and rt<=t and r.get('source_id') in accepted:accepted[r['source_id']]=max(accepted[r['source_id']],r.get('accepted',r.get('frontier',0)))
  pre_roots={sid:0 for sid in sources}
  for f in facts:
   if f['sequence']<=durable_before:pre_roots[f['body']['source_id']]=f['processed_frontier']
  debt={sid:max(0,accepted[sid]-pre_roots[sid]) for sid in sources};coverage={sid:0 for sid in sources};clear=None
  for row in rows:
   coverage[row['source_id']]=max(coverage[row['source_id']],row['certified_frontier'])
   if row['observed']>=t and all(coverage[sid]>=accepted[sid] for sid in sources):clear=row;break
  delta=lambda value:None if value is None else value-t
  availability={}
  if end is not None:
   for sid in sources:
    own=[r for r in rows if r['source_id']==sid];prior=next((r for r in reversed(own) if r['observed']<=t),None);baseline=prior['visible_frontier'] if prior else 0;visible=baseline;cursor=t;gap=total=longest=0.
    for row in [r for r in own if t<r['observed']<=end]+[dict(observed=end,visible_frontier=visible)]:
     duration=max(0.,row['observed']-cursor)
     if visible<baseline:total+=duration;gap+=duration;longest=max(longest,gap)
     else:gap=0.
     visible=row['visible_frontier'];cursor=row['observed']
    availability[sid]=dict(pre_fault_visible_frontier=baseline,observed_deficit_seconds=total,longest_observed_deficit_seconds=longest,scope='Below pre-fault visible frontier; necessary selected revisions are not automatically attributed to failure.')
  result.append(dict(fault_kind=fault.get('site',fault.get('kind')),fault_perf=t,physical_death_confirmed_perf=death['_t'] if death else None,replacement_ready_perf=ready['_t'] if ready else None,first_actual_old_fact_replay_perf=replay['observed'] if replay else None,first_new_durable_fact_actual_consume_perf=first_new_fact['observed'] if first_new_fact else None,first_new_model_completed_after_fault_and_certified_consume_perf=first_new['observed'] if first_new else None,accepted_before_fault_samples=accepted,pre_fault_durable_sequence=durable_before,uncertified_debt_before_fault_samples=debt,debt_clear_actual_certified_consume_perf=clear['observed'] if clear and any(debt.values()) else None,fault_to_death=delta(death['_t'] if death else None),fault_to_replacement_ready=delta(ready['_t'] if ready else None),fault_to_old_fact_replay=delta(replay['observed'] if replay else None),fault_to_new_durable_fact=delta(first_new_fact['observed'] if first_new_fact else None),fault_to_new_certified_result=delta(first_new['observed'] if first_new else None),fault_to_debt_clear=delta(clear['observed'] if clear and any(debt.values()) else None),pre_fault_view_availability=availability,scope='Old durable replay is not new inference. New durable fact and actual model completion after fault are separate clocks. Debt target is accepted before fault, not all future offered audio.'))
 return dict(observed_fault_records=len(result),events=result,scope='Component clocks may overlap; replay may precede cold model readiness. Missing markers remain unknown, never zero-duration recovery.')

def analyze_trial(root):
 root=pathlib.Path(root).resolve();result=dict(schema='revtrace-resilience-offline-metrics-v1',analysis_phase='offline_after_trial',new_model_calls=0)
 try:
  config=load(root/'CONFIG.json');origin_record=load(root/'ORIGIN.json');origin=origin_record['origin_perf'];sources={s['source_id']:s for s in config['settings']['sources']};rows=lines(root/'consumer.jsonl')
  need(origin_record.get('original_D',2.)==2. and origin_record.get('original_C',8.)==8.,'original D2/C8 changed')
  need(rows and set(r['source_id'] for r in rows)==set(sources),'actual Consumer evidence missing; no synthetic observations substituted')
  meta={k:config.get(k,{'cell_id':config.get('experiment_id','trial'),'stage':'resilience','cohort':'frozen','repeat':0}.get(k)) for k in ('cell_id','stage','cohort','arm','repeat')}
  primary=cell_metrics(dict(meta,out=str(root)));content,events,spans,frontiers=analyze_cell(meta,rows,sources,origin)
  need(abs(primary['dual_deadline_audio_credit_seconds']-content['original_dual_credit_audio_seconds'])<1e-8,'original endpoint recounts disagree')
  primary['primary_linear_all_offered_C50']=finite(quantile([f['C'] if f['C'] is not None else math.inf for f in frontiers],.5));primary['primary_linear_all_offered_D50']=finite(quantile([f['D'] if f['D'] is not None else math.inf for f in frontiers],.5))
  primary['EOS_D2_misses']=sum(f['frontier']==sources[f['source_id']]['frames'] and (f['D'] is None or f['D']>2.) for f in frontiers);primary['nonEOS_D2_misses']=primary['D2_misses_all_offered']-primary['EOS_D2_misses']
  roots,facts,processed=fact_audit(root/'facts.wal',sources);consumer=consumer_audit(rows,facts)
  reference=reference_audit(config,facts,config.get('source_commit',config['settings'].get('source_commit')))
  expected=sum((s['frames']+7999)//8000 for s in sources.values());complete=all(roots[sid].frontier==s['frames'] and processed[sid]==s['frames'] for sid,s in sources.items()) and len(facts)==expected and consumer['durable_facts_not_yet_consumed']==0
  quality=[]
  for sid,source in sources.items():
   target=normalize(source['reference']);actual=normalize(roots[sid].transcript);edits=levenshtein(target,actual);quality.append(dict(source_id=sid,reference_characters=len(target),character_edits=edits,CER=edits/len(target) if target else None,final_text=roots[sid].transcript,scope='Fixed whitespace-only original native CER; final task quality, not provisional correctness.'))
  end_record=load(root/'SERVICE_END.json') if (root/'SERVICE_END.json').exists() else {};end=end_record.get('service_end_perf')
  reject_rows=[r for _,r in logs(root,'owner_events.jsonl') if r.get('kind')=='local_message_disposition'];reject_mutations=sum(r.get('before',{}).get('canon')!=r.get('after',{}).get('canon') for r in reject_rows)
  input_clock_checks=[]
  for r in lines(root/'ingress.jsonl'):
   F=r.get('accepted',r.get('frontier'));stamp=r.get('original_offer',r.get('original_ready_perf'))
   if F is not None and stamp is not None:input_clock_checks.append(abs(stamp-(origin+F/16000))<1e-6)
  need(all(input_clock_checks),'an accepted original input clock was changed')
  accepted={sid:0 for sid in sources}
  for r in lines(root/'ingress.jsonl'):
   if r.get('source_id') in accepted:accepted[r['source_id']]=max(accepted[r['source_id']],r.get('accepted',r.get('frontier',0)))
  owner_errors=[r for _,r in logs(root,'supervisor.jsonl') if r.get('kind')=='writes_frozen_owner_error'];allowed=set(config.get('expected_owner_error_types',[]));error_types=Counter()
  for row in owner_errors:
   last=next((line for line in reversed(row.get('traceback','').splitlines()) if line.strip()),'UNKNOWN');error_types[last.split(':',1)[0].rsplit('.',1)[-1]]+=1
  unexpected=sum(n for kind,n in error_types.items() if kind not in allowed)
  result.update(experiment_id=config.get('experiment_id',meta['cell_id']),cell_id=meta['cell_id'],arm=config['arm'],source_commit=config.get('source_commit',config['settings'].get('source_commit')),primary=primary,content=content,posterior_whole_text_support=posterior_support(rows,frontiers,facts),quality=quality,energy=power_metrics(root,origin,end),integrity=dict(durable_frames_verified=True,complete_original_parent_cadence_records_verified=True,durable_canonical_steps=len(facts),expected_canonical_steps=expected,all_original_obligations_eventually_processed=complete,accepted_frontiers=accepted,pending_accepted_uncertified_samples={sid:max(0,accepted[sid]-processed[sid]) for sid in sources},unprocessed_all_offered_samples={sid:max(0,s['frames']-processed[sid]) for sid,s in sources.items()},observed_acknowledged_input_loss_samples={sid:0 for sid in sources} if complete and input_clock_checks else None,input_loss_scope='Completed fixed accepted obligations are checked by the full durable source chain; incomplete debt is pending work, not automatically lost input.',consumer_binding=consumer,original_reference=reference,local_reject_records=len(reject_rows),local_reject_canonical_mutations=reject_mutations,legal_progress_wrong_rejections=None,legal_progress_wrong_rejections_status='REQUIRES_SEPARATE_SEMANTIC_WITNESS_CHECK',accepted_original_clock_notifications_checked=len(input_clock_checks)),history=history_metrics(root),state_boundaries=state_metrics(root,facts),recovery=recovery_clocks(root,rows,facts,sources,origin,end))
  result['integrity'].update(owner_error_records=len(owner_errors),owner_error_types=dict(error_types),explicit_expected_owner_error_types=sorted(allowed),unexpected_owner_error_records=unexpected)
  task_ok=complete and reject_mutations==0 and unexpected==0 and reference['status'] in ('PASS_COMPLETE_ORIGINAL_REFERENCE','NOT_REQUESTED')
  result['gate']='PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT' if task_ok else 'FAIL_OR_INCOMPLETE_TRIAL_TASK_PRESERVED'
  result['scope']='Offline aggregation only. Complete-task/refinement/physical-owner admissibility evidence roles remain distinct. Cold-fault P99 failure is an endpoint outcome, not automatic evidence that safe recovery failed.'
 except BaseException as exc:
  result.update(gate='FAIL_OFFLINE_TRIAL_RECOUNT_PRESERVED',error_type=type(exc).__name__,reason=str(exc))
 put(root/'METRICS_SUMMARY.json',result);put(root/'METRICS_GATE.json',dict(gate=result['gate'],analysis_phase='offline_after_trial',new_model_calls=0))
 return result
