"""Bounded actual two-arm interval extraction, with each arm's own ready clock.

This does not estimate a same-interleaving counterfactual or change the original
48-run endpoints. It reports whatever the actual Joint rows contain.
"""
from copy import deepcopy
import hashlib,json,math
from interaction_opportunities_v1 import complete_chain

F=224000;START=192000;SID=7;RATE=16000
def need(x,msg):
 if not x:raise ValueError(msg)
def ready_clock(episode,session,F=F):return episode['origin_perf']+session['offset']+F/RATE
def first_cover(rows,field,F=F):
 need(all(rows[i]['observed_perf']<=rows[i+1]['observed_perf'] for i in range(len(rows)-1)),'Consumer order regressed')
 return next(i for i,r in enumerate(rows) if r[field]>=F)
def whole_text_equal(a,b):return a['visible_text']==b['visible_text']
def relative_trace(rows,ready):
 return [dict(t=r['observed_perf']-ready,visible_F=r['valid_visible_frontier']/RATE,
   certified_F=r['certified_frontier']/RATE,kind=r['source_kind'],input_row=i,
   visible_text_sha256=hashlib.sha256(r['visible_text'].encode()).hexdigest()) for i,r in enumerate(rows)]
def checked_chain(jid,F,P,records,published,fine):
 value,reason,route=complete_chain(jid,F,P,records,published,fine)
 for key in route:
  rec=records.get(key)
  if rec is None:return None,'missing_complete_actual_ancestor',route
  actual=rec['result'].get('execution_context_audit',{}).get('executed_prompt_tokens')
  if actual is None:return None,'missing_executed_input_audit',route
  if actual!=rec['job']['prompt_tokens']:return False,'actual_conditioning_differs_from_declared_prompt',route
 return value,reason,route

def arm_extract(data,arm):
 rows=data['CONSUMER'];events=data['EVENTS'];session=data['SESSION'];episode=data['EPISODE']
 identity=episode['identity']
 need(identity['source_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf','Wrong original neural source')
 need(identity['manifest_sha256']=='69560358173834f45fa284c472bdfab8f284f82ff13034efcc4408a7f492ea04','Wrong original stream manifest')
 need(session['session_id']==SID and session['source_id']=='3570-5694-0003','Wrong source/session')
 need(session['audio_sha256']==data['MANIFEST_ROW']['audio_sha256'] and session['source_id']==data['MANIFEST_ROW']['source_id'],'Frozen audio manifest mismatch')
 need(F<round(session['duration']*RATE),'Target must be original non-EOS')
 need(all(r['session_id']==SID for r in rows),'Mixed session rows')
 need(all(math.isfinite(r['observed_perf']) and math.isfinite(r['server_time']) for r in rows),'Nonfinite actual Consumer clock')
 ready=ready_clock(episode,session);first=first_cover(rows,'valid_visible_frontier');cert=first_cover(rows,'certified_frontier')
 need(rows[first]['visible_text'],'Internal empty tip is not visible content')
 records={r['job']['job_id']:r for r in data['WORKER_RECORDS']}
 need(len(records)==len(data['WORKER_RECORDS']),'Duplicate complete records')
 starts=[e['t0_perf'] for e in events if e['kind']=='run-start'];need(len(starts)==1,'Need one original run origin')
 owner_origin=starts[0]
 lookup={}
 for ev in events:
  if ev['kind'] in ('display','canonical-display','view-mode'):
   lookup.setdefault((ev['kind'],ev['displayed']),[]).append(ev)
 current_job=None;windows=[];active=None;previous=None;applications=[]
 for i,row in enumerate(rows):
  found=lookup.get((row['source_kind'],row['server_time']),[])
  need(len(found)==1,'Actual Consumer row lacks unique publication event')
  ev=found[0];need(ev.get('session_id')==SID,'Wrong event session')
  need(math.isfinite(ev['displayed']) and owner_origin+ev['displayed']<=row['observed_perf'],'Actual use precedes publication')
  if row['source_kind']=='display':
   need(ev['text']==row['visible_text'] and ev['audio_end_sample']==row['valid_visible_frontier'],'Private publication differs from actual whole view')
   current_job=ev['job_id'];rec=records.get(current_job);need(rec is not None,'Missing complete actual result')
   need(rec['job']['audio_end_sample']==ev['audio_end_sample'] and rec['job']['session_id']==SID and rec['job']['source_id']==session['source_id'],'Private original job target/source mismatch')
   need(rec['result']['text']==ev['text'],'Result text binding differs')
   executed=rec['result'].get('execution_context_audit',{}).get('executed_prompt_tokens')
   need(executed is not None and executed==rec['job']['prompt_tokens'],'Actual executed input missing or differs')
  classification=None;route=[];reason=None
  if row['source_kind']=='canonical-display':
   commits=[x for x in events if x['kind']=='commit' and x['version']==row['canonical_version']]
   need(len(commits)==1,'Selected version must bind one original commit')
   commit=commits[0];need(commit['audio_end_sample']==row['certified_frontier'],'Certified frontier mismatch')
   rec=records.get(commit['job_id']);need(rec is not None,'Selected complete result missing')
   need(rec['job']['audio_end_sample']==commit['audio_end_sample'] and rec['job']['session_id']==SID and rec['job']['source_id']==session['source_id'],'Selected original job target/source mismatch')
   need(rec['result']['token_ids']==commit['segment_tokens'] and rec['result']['state_tokens']==commit['next_prompt_tokens'],'Selected original result mismatch')
   need(ev['text']==row['certified_text']==rec['result']['text'],'Selected actual text binding mismatch')
   if previous is not None and previous['valid_visible_frontier']>row['certified_frontier']:
    published={x['job_id'] for x in events if x['kind']=='display' and owner_origin+x['displayed']<=row['observed_perf']}
    value,reason,route=checked_chain(current_job,row['certified_frontier'],commit['next_prompt_tokens'],records,published,32000)
    classification='compatible' if value is True else 'incompatible' if value is False else 'unknown'
    applications.append(dict(row=i,relative_time=row['observed_perf']-ready,
     before_visible_F=previous['valid_visible_frontier'],after_visible_F=row['valid_visible_frontier'],
     selected_F=row['certified_frontier'],classification=classification,reason=reason,chain=route,
     whole_view_unchanged=whole_text_equal(previous,row) and previous['valid_visible_frontier']==row['valid_visible_frontier']))
   if row['valid_visible_frontier']==row['certified_frontier'] and row['visible_text']==row['certified_text']:current_job=None
  if i>=first:
   covered=row['valid_visible_frontier']>=F
   if not covered and active is None:
    active=dict(start=row['observed_perf']-ready,start_row=i,classification=classification,
     reason=reason,chain=route)
   if covered and active is not None:
    active.update(end=row['observed_perf']-ready,end_row=i,right_censored=False,
      gap_seconds=row['observed_perf']-ready-active['start']);windows.append(active);active=None
  previous=row
 if active is not None:
  active.update(end=rows[-1]['observed_perf']-ready,end_row=len(rows)-1,right_censored=True,
    gap_seconds=rows[-1]['observed_perf']-ready-active['start']);windows.append(active)
 firstrow=rows[first];certrow=rows[cert]
 same_G=[r for r in rows if r['source_kind']=='canonical-display' and r['certified_frontier']==firstrow['valid_visible_frontier']]
 need(len(same_G)<=1,'Ambiguous later selected text at actual first-view frontier')
 posterior=None if not same_G else firstrow['visible_text']==same_G[0]['certified_text']
 return dict(arm=arm,source_id=session['source_id'],session_id=SID,audio_sha256=session['audio_sha256'],
  offered_F=F,offered_interval=[START,F],ready_perf=ready,origin_perf=episode['origin_perf'],session_offset=session['offset'],
  original_neural_identity=identity,first_visible=firstrow['observed_perf']-ready,first_certified=certrow['observed_perf']-ready,
  first_visible_row=first,first_certified_row=cert,first_visible_F=firstrow['valid_visible_frontier'],
  first_certified_F=certrow['certified_frontier'],
  first_visible_source_kind=firstrow['source_kind'],first_visible_whole_text=firstrow['visible_text'],
  first_certified_whole_text=certrow['certified_text'],first_and_certified_whole_text_equal=firstrow['visible_text']==certrow['certified_text'],
  posterior_same_actual_G_text_support=posterior,posterior_comparison_actual_G=firstrow['valid_visible_frontier'],
  first_D2_pass=firstrow['observed_perf']-ready<=2,first_C8_pass=certrow['observed_perf']-ready<=8,
  complete_trace=relative_trace(rows,ready),observed_target_loss_windows=windows,
  canonical_ahead_applications=applications,last_observation=rows[-1]['observed_perf']-ready)

def extract_comparison(j):
 result={arm:arm_extract(j[arm],arm) for arm in ('R1_S0','R1_S1')}
 a=result['R1_S0'];z=result['R1_S1']
 need((a['source_id'],a['session_id'],a['audio_sha256'],a['offered_interval'])==(z['source_id'],z['session_id'],z['audio_sha256'],z['offered_interval']),'Arms must share actual input interval')
 need(a['original_neural_identity']['manifest_sha256']==z['original_neural_identity']['manifest_sha256'],'Arms changed stream manifest')
 need(math.isclose(a['first_visible'],1.4439057689160109,abs_tol=1e-9),'Original first-view time did not reproduce')
 need(math.isclose(a['first_certified'],3.7196051217615604,abs_tol=1e-9),'Original certified return did not reproduce')
 old=next(w for w in a['observed_target_loss_windows'] if math.isclose(w['start'],1.543663284741342,abs_tol=1e-9))
 need(old['classification']=='compatible' and math.isclose(old['gap_seconds'],2.1759418370202184,abs_tol=1e-9),'Original compatible gap did not reproduce')
 need(a['first_and_certified_whole_text_equal'],'Original whole-text return not reproduced')
 return dict(status='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS',same_input_interval=True,
  same_execution_interleaving=False,paired_counterfactual=False,new_model_calls=0,arms=result,
  first_visible_whole_text_equal_across_arms=a['first_visible_whole_text']==z['first_visible_whole_text'],
  first_visible_frontiers_equal_across_arms=a['first_visible_F']==z['first_visible_F'],
  first_certified_whole_text_equal_across_arms=a['first_certified_whole_text']==z['first_certified_whole_text'],
  first_certified_frontiers_equal_across_arms=a['first_certified_F']==z['first_certified_F'],
  interpretation='Actual policies on the same original input interval. Each uses its own original ready clock; event schedules and visible objects can differ.')

def controls():
 rows=[]
 def test(name,f):
  f();rows.append(dict(name=name,pass_=True))
 def check(v):need(v,'Control mismatch')
 test('distinct_per_arm_ready_origins',lambda:check(ready_clock(dict(origin_perf=100),dict(offset=1.75))==115.75 and ready_clock(dict(origin_perf=200),dict(offset=1.75))==215.75))
 test('common_origin_misuse_changes_latency',lambda:check(217.25-ready_clock(dict(origin_perf=200),dict(offset=1.75))==1.5 and 217.25-ready_clock(dict(origin_perf=100),dict(offset=1.75))==101.5))
 test('first_cover_uses_actual_consumer',lambda:check(first_cover([dict(observed_perf=1,valid_visible_frontier=START),dict(observed_perf=2,valid_visible_frontier=F)],'valid_visible_frontier')==1))
 def order():
  try:first_cover([dict(observed_perf=2,valid_visible_frontier=F),dict(observed_perf=1,valid_visible_frontier=F)],'valid_visible_frontier')
  except ValueError:return
  raise AssertionError('Order reversal accepted')
 test('Consumer_order_regression_rejected',order)
 test('same_frontier_not_same_whole_text',lambda:check(not whole_text_equal(dict(visible_text='alpha',F=F),dict(visible_text='beta',F=F))))
 test('same_whole_text_exact',lambda:check(whole_text_equal(dict(visible_text='alpha'),dict(visible_text='alpha'))))
 job=dict(role='proposal',session_id=SID,source_id='s',contract_epoch=0,contract_digest='x',branch_generation=0,chunk_id=6,audio_end_sample=F,prompt_tokens=[1])
 result=dict(state_tokens=[3],token_ids=[2],text='x',execution_context_audit=dict(executed_prompt_tokens=[1]))
 records={'j':dict(job=job,result=result)}
 test('complete_actual_input_match',lambda:check(checked_chain('j',START,[1],records,{'j'},32000)[0] is True))
 bad=deepcopy(records);bad['j']['result']['execution_context_audit']['executed_prompt_tokens']=[9]
 test('executed_input_mismatch_is_refuted',lambda:check(checked_chain('j',START,[1],bad,{'j'},32000)[0] is False))
 test('missing_evidence_remains_unknown',lambda:check(checked_chain('j',START,[1],records,set(),32000)[0] is None))
 no_audit=deepcopy(records);del no_audit['j']['result']['execution_context_audit']
 test('missing_actual_execution_audit_is_unknown',lambda:check(checked_chain('j',START,[1],no_audit,{'j'},32000)[0] is None))
 return dict(status='PASS_RAM_COMPARISON_CLOCK_AND_BINDING_CONTROLS',tests=rows,passed=len(rows),new_model_calls=0)
