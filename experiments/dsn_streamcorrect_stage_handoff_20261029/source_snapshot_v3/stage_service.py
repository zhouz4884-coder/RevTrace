"""Actual one-owner service: two full early-view replicas or ready-only handoff."""
import pathlib,json,hashlib,sys,os,time,queue,multiprocessing as mp,traceback,platform,collections,math
from native_service import Journal,Power,verify_source,Consumer
from feedback_contract import FeedbackCut,BranchStep,Reconciler
from stage_policy import StageCoordinator
from original_primary_quantiles import cell_metrics,quantile,finite
from content_endpoints import analyze_cell
from native_audit import distance
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

class StageConsumer(Consumer):
 def __init__(self,*args,**kwargs):self.node_info={};super().__init__(*args,**kwargs)
 def run(self):
  try:
   while True:
    e=self.q.get()
    if e is None:return
    sid=e['source_id'];r=self.states[sid]
    if e['kind']=='canonical':r.install(FeedbackCut(e['state']));self.processed[sid]=max(self.processed[sid],e['processed_frontier'])
    elif e['kind']=='private':
     if r.canonical.sha256!=e['canonical_sha']:raise ValueError('Consumer rejected foreign Canonical clock')
     previous=r.canonical;steps=[]
     for s in e['steps']:
      start=FeedbackCut(s['start']);end=FeedbackCut(s['end'])
      if not start.same(previous):raise ValueError('Consumer rejected stage projection chain')
      steps.append(BranchStep(s['job_id'],start.sha256,start,end));previous=end;self.node_info[s['job_id']]={k:s.get(k) for k in ('kind','actual_identity_full_step_completed','actual_full_C_U_completed')}
     if previous.frontier>=r.tail.frontier:r.steps=steps
    else:raise ValueError('unknown Consumer publication')
    view=r.visible();view['certified_frontier']=self.processed[sid]
    if not view['text']:view['visible_frontier']=0
    row=dict(kind=e['kind'],source_id=sid,observed=time.perf_counter(),publication_id=e['publication_id'],view_node=self.node_info.get(view['private_job'],{'kind':'canonical_original_C_U'}),**view);self.rows.append(row);self.log.write(row)
  except BaseException:self.error=traceback.format_exc()

def run(config_path,manifest_path,out):
 config=json.loads(pathlib.Path(config_path).read_text());settings=config['settings'];source_gate=verify_source(pathlib.Path(manifest_path));assert settings['source_commit']==source_gate['source_commit'];assert settings['corrector_dtype']=='float32'
 out=pathlib.Path(out);out.mkdir(exist_ok=False);put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),source=source_gate,actual_packages='worker READY records',GPU_boundary='dedicated root allocated window',precision='public FP32 default; TF32/autocast disabled'))
 put(out/'RUN_RECORD.json',dict(experiment_id=config['cell_id'],code_commit=source_gate['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
 arm=config['arm'];assert arm in ('two_full_early','two_full_spec_early','ready_handoff');sources={s['source_id']:s for s in settings['sources']};source_ids=list(sources);assert 1<=len(sources)<=2
 import soundfile as sf
 audio={}
 for sid,s in sources.items():
  assert sha(s['path'])==s['audio_sha256'];a,sr=sf.read(s['path'],dtype='float32');assert sr==16000 and len(a)==s['frames'];audio[sid]=a
 from stage_worker import worker_main
 primary=settings['primary_gpu'];assert primary in (0,1)
 specs=[('full0',primary,'authority'),('full1',1-primary,'authority')] if arm.startswith('two_full') else [('authority',primary,'authority'),('producer',1-primary,'protected_asr_stage')]
 ctx=mp.get_context('spawn');workers={};commands={};results={};invalidations={};sent_invalidations=set();abandoned=[];busy={name:None for name,_,_ in specs};ready={};consumer=None;power=Power(out/'power.jsonl');logs=Journal(out/'native_jobs.jsonl');events=Journal(out/'events.jsonl');canon=Journal(out/'canonical_wal.jsonl',True);ingress=Journal(out/'accepted_input_wal.jsonl',True);out.joinpath('packets').mkdir();sequence=0;publication=0;histories={sid:[] for sid in sources};processed={sid:0 for sid in sources};dispatches=[];admissions=[];controller_begin=time.perf_counter()
 while not power.rows:time.sleep(.02)
 load_begin=time.perf_counter()
 def receive(name,block=False):
  r=results[name].get(timeout=180) if block else results[name].get_nowait();received=time.perf_counter();r['received_perf']=received;r['physical_channel_worker']=name
  if r.get('worker')!=name:raise ValueError('physical worker-channel message mismatch')
  if r['kind']=='failed':raise RuntimeError(r['traceback'])
  return r,received
 try:
  for name,gpu,mode in specs:
   c=ctx.Queue();q=ctx.Queue();inv=ctx.Queue() if arm=='two_full_spec_early' else None;w=ctx.Process(target=worker_main,args=(name,gpu,mode,settings,c,q,inv));w.start();workers[name]=w;commands[name]=c;results[name]=q;invalidations[name]=inv
  for name,_,mode in specs:
   r,_=receive(name,True);assert r['kind']=='ready' and r['mode']==mode
   if mode=='authority':assert r['neural_ready_warmup']['neural_C_confirmed'] is True
   assert r['neural_ready_warmup']['reset_to_genesis'] and not r['neural_ready_warmup']['warmup_packet_admitted'];ready[name]=r
  load_end=time.perf_counter();put(out/'READY.json',ready);identities=[r['runtime_identity'] for r in ready.values()];assert all(x==identities[0] for x in identities)
  initials={sid:next(iter(ready.values()))['initials'][sid] for sid in sources}
  for r in ready.values():assert all(r['initials'][sid]==initials[sid] for sid in sources)
  from fullspec_policy import FullSpecCoordinator
  policy_class=FullSpecCoordinator if arm=='two_full_spec_early' else StageCoordinator
  policy=policy_class(initials=initials,audio=audio,runtime_identity=identities[0],source_frames={sid:s['frames'] for sid,s in sources.items()},producer_worker='producer' if arm=='ready_handoff' else None,authority_workers=tuple(name for name,_,m in specs if m=='authority'))
  origin=time.perf_counter();consumer=StageConsumer({sid:FeedbackCut(s) for sid,s in initials.items()},out/'consumer.jsonl',origin);put(out/'ORIGIN.json',dict(origin_perf=origin,cadence_seconds=.5,original_D=2.,original_C=8.));accepted={sid:0 for sid in sources};source_rr=0;producer_rr=0;authority_rr=0
  def publish(e):
   nonlocal publication
   publication+=1;e=dict(e,publication_id=publication);consumer.publish(e)
  def publish_view(sid):publish(policy.view_event(sid))
  def next_end(sid,start):return min(sources[sid]['frames'],start.frontier+8000)
  def dispatch(name,sid,start,end,kind,receipt=None,matching_inflight=None):
   nonlocal sequence
   sequence+=1;job_id=f'j{sequence:06d}';stamp=time.perf_counter();job=policy.register(job_id=job_id,worker=name,kind=kind,source_id=sid,start=start,end=end,dispatched_perf=stamp,receipt=receipt);busy[name]=job_id
   header=dict(kind='dispatch',job_id=job_id,worker=name,source_id=sid,execution=kind,start=start.frontier,end=end,start_sha=start.sha256,birth_canonical_sha=job['birth_canonical_sha'],dispatch_epoch=job['dispatch_epoch'],dispatched_perf=stamp,cache_hit=receipt is not None,producer_job=receipt.producer_job_id if receipt else None,producer_birth_canonical_sha=receipt.birth_canonical_sha if receipt else None,producer_birth_epoch=receipt.birth_epoch if receipt else None,receipt_ready_perf=receipt.ready_perf if receipt else None,matching_inflight_producer_job=matching_inflight['job_id'] if matching_inflight else None,matching_inflight_producer_dispatched_perf=matching_inflight['dispatched_perf'] if matching_inflight else None,matching_inflight_full_input_and_epoch=matching_inflight is not None);events.write(header);dispatches.append(header)
   cmd=dict(kind=kind,job_id=job_id,dispatch_epoch=job['dispatch_epoch'],source_id=sid,start=start.state,end=end,early_view=kind=='full',capture_packet=name=='producer')
   if receipt is not None:cmd['packet_wire']=receipt.packet.wire()
   commands[name].put(cmd)
  def apply_outcome(outcome,fallback_event=None):
   r=outcome.get('event',fallback_event);sid=outcome['job']['source_id']
   if outcome['kind']=='canonical':
    cut=outcome['cut'];canon.write(dict(source_id=sid,state=cut.state,state_sha256=cut.sha256,selected=r['record']['selected_correction'],dispatch_epoch=outcome['job']['dispatch_epoch']))
    if r['record']['native_model_evaluated']:processed[sid]=cut.frontier
    histories[sid].append(dict(F=cut.frontier,state=cut.state,state_sha256=cut.sha256,token_ids=r['record']['token_ids']));events.write(dict(kind='canonical_install',source_id=sid,job_id=r['job_id'],observed=time.perf_counter(),reconciliation=outcome['reconciliation'],completed_buffer_reuse=outcome.get('completed_buffer_reuse',False),fullspec_promoted=outcome['job'].get('promoted_to_canonical',False)));publish(dict(kind='canonical',source_id=sid,state=cut.state,processed_frontier=processed[sid]));publish(outcome['view_event_snapshot']) if 'view_event_snapshot' in outcome else publish_view(sid)
   elif outcome['kind'] in ('producer_completed','buffered_full'):publish_view(sid)
   elif outcome['kind'] not in ('discarded','abandoned_full'):raise ValueError('unrecognized full result disposition')
  while True:
   now=time.perf_counter()
   if now-origin>config['maximum_service_seconds']:raise TimeoutError('bounded original service exceeded frozen limit')
   for sid,s in sources.items():
    n=s['frames'];elapsed=max(0.,now-origin);F=n if elapsed>=n/16000 else min(n,int(elapsed/.5)*8000)
    if F>accepted[sid]:accepted[sid]=F;ingress.write(dict(source_id=sid,accepted=F,observed=time.perf_counter(),original_offer=origin+F/16000,audio_sha256=s['audio_sha256']))
   for name,_,_ in specs:
    while True:
     try:r,received=receive(name)
     except queue.Empty:break
     if r['kind'] in ('candidate','asr_early'):
      wire=r.get('candidate_wire');header={k:v for k,v in r.items() if k!='candidate_wire'}
      if wire is not None:
       p=out/'packets'/(r['job_id']+'.json');assert not p.exists();p.write_bytes(wire);header.update(candidate_wire_bytes=len(wire),candidate_wire_sha256=hashlib.sha256(wire).hexdigest())
      accepted_asr=policy.admit_asr(name,r,received_perf=received);header.update(admitted_perf=time.perf_counter(),eligible_view=accepted_asr['eligible_view']);events.write(header);admissions.append({k:header.get(k) for k in ('worker','job_id','source_id','produced_perf','wire_complete_perf','received_perf','admitted_perf','candidate_wire_bytes','candidate_wire_sha256','eligible_view','packet_capture_seconds','identity_projection_seconds','wire_serialization_seconds')})
      if accepted_asr['eligible_view']:publish_view(r['source_id'])
     elif r['kind']=='completed':
      if busy[name]!=r['job_id']:raise ValueError('completion from non-owned in-flight job')
      outcome=policy.complete(name,r,received_perf=received);busy[name]=None;logs.write(r);sid=r['source_id']
      apply_outcome(outcome,r)
     elif r['kind']=='abandoned':
      if arm!='two_full_spec_early' or busy[name]!=r['job_id'] or r['C_U_completed'] or r['feedback_cut_emitted']:raise ValueError('invalid full-call abandonment')
      outcome=policy.abandon(name,r['job_id'],r['proof']);busy[name]=None;events.write(r);abandoned.append(r);apply_outcome(outcome,r)
     else:raise ValueError('unexpected live service worker response')
   if arm=='two_full_spec_early':
    for outcome in policy.pop_ready_commits():outcome['completed_buffer_reuse']=True;apply_outcome(outcome)
    for job_id,proof in policy.invalidations().items():
     if job_id not in sent_invalidations:
      job=policy.jobs[job_id];invalidations[job['worker']].put(dict(job_id=job_id,source_id=job['source_id'],dispatch_epoch=job['dispatch_epoch'],proof=proof));sent_invalidations.add(job_id);events.write(dict(kind='known_invalid_C_skip_hint',job_id=job_id,proof=proof,observed=time.perf_counter()))
   if all(policy.canonical(sid).frontier==sources[sid]['frames'] for sid in sources) and all(v is None for v in busy.values()):break
   authority_names=[name for name,_,mode in specs if mode=='authority'];ordered=authority_names[authority_rr:]+authority_names[:authority_rr]
   for name in ordered:
    if busy[name] is not None:continue
    for i in range(len(source_ids)):
     sid=source_ids[(source_rr+i)%len(source_ids)]
     if arm=='two_full_spec_early':
      start=policy.next_full_start(sid,accepted[sid],settings['max_ahead_frames'])
      if start is None:continue
     else:
      start=policy.canonical(sid)
      if sid in policy.active_authority:continue
     end=next_end(sid,start)
     if end<=start.frontier or end>accepted[sid]:continue
     decision=time.perf_counter();receipt=policy.take_ready(sid,end,decision) if arm=='ready_handoff' else None
     if receipt is not None and policy.publish_ready_projection(receipt):publish_view(sid)
     pj=policy.jobs.get(busy.get('producer')) if arm=='ready_handoff' and receipt is None else None;matching=pj if pj and pj['key']==policy.key(sid,start,end) and pj['dispatch_epoch']==policy.epochs[sid] else None
     dispatch(name,sid,start,end,'consume' if receipt else 'full',receipt,matching);source_rr=(source_rr+i+1)%len(source_ids);authority_rr=(authority_names.index(name)+1)%len(authority_names);break
   if arm=='ready_handoff' and busy['producer'] is None:
    for i in range(len(source_ids)):
     sid=source_ids[(producer_rr+i)%len(source_ids)];start=policy.tail(sid);end=next_end(sid,start)
     if policy.canonical(sid).frontier==sources[sid]['frames'] or end<=start.frontier or end>accepted[sid] or end>policy.canonical(sid).frontier+settings['max_ahead_frames']:continue
     dispatch('producer',sid,start,end,'full');producer_rr=(producer_rr+i+1)%len(source_ids);break
   time.sleep(.002)
  consumer.close();ended=time.perf_counter();put(out/'CANONICAL_HISTORIES.json',histories);put(out/'CONSUMPTIONS.json',policy.consumptions);put(out/'STAGE_ADMISSIONS.json',admissions);put(out/'DISPATCHES.json',dispatches)
  if arm=='two_full_spec_early':
   put(out/'FULLSPEC_LEDGER.json',dict(promotions=policy.promotions,discarded=[dict(job_id=x['job']['job_id'],proof=x['proof']) for x in policy.discarded_full],abandoned=abandoned))
  for c in commands.values():c.put(None)
  for name,_,_ in specs:
   r,_=receive(name,True);assert r['kind']=='drained';workers[name].join(30);assert workers[name].exitcode==0
  while power.rows[-1]['time']<ended:time.sleep(.02)
  power.close();energy=dict(service=power.energy(origin,ended),load_and_neural_warmup=power.energy(load_begin,load_end),service_scope='both GPUs from actual origin through Consumer drain; cold load and fixed neural warmup separate');put(out/'ENERGY.json',energy)
  primary=cell_metrics(dict(config,out=str(out)));content,content_events,spans,frontiers=analyze_cell({k:config[k] for k in ('cell_id','arm','stage','cohort','repeat')},consumer.rows,sources,origin);assert abs(content['original_dual_credit_audio_seconds']-primary['dual_deadline_audio_credit_seconds'])<1e-7;primary.update(primary_linear_all_offered_C50=finite(quantile([x['C'] if x['C'] is not None else math.inf for x in frontiers],.5)),primary_linear_all_offered_D50=finite(quantile([x['D'] if x['D'] is not None else math.inf for x in frontiers],.5)));put(out/'PRIMARY_METRICS.json',primary);put(out/'CONTENT.json',content);put(out/'CONTENT_EVENTS.json',content_events);put(out/'CONTENT_SPANS.json',spans);put(out/'CONTENT_FRONTIERS.json',frontiers)
  quality=[]
  for sid,s in sources.items():
   text=policy.canonical(sid).transcript;ref=''.join(s['reference'].split());hyp=''.join(text.split());quality.append(dict(source_id=sid,text=text,reference_characters=len(ref),character_edits=distance(hyp,ref)))
  auth=[j for j in dispatches if j['worker']!='producer'];hits=[j for j in auth if j['cache_hit']];by_job={r['job_id']:r for r in admissions};inflight=[]
  for j in auth:
   p=by_job.get(j['matching_inflight_producer_job']);a=by_job.get(j['job_id'])
   if j['matching_inflight_producer_job'] is not None:inflight.append(dict(authority_job=j['job_id'],producer_job=j['matching_inflight_producer_job'],same_full_input_and_epoch=True,dispatch_perf=j['dispatched_perf'],producer_ready_perf=p['admitted_perf'] if p else None,producer_ready_after_dispatch_seconds=p['admitted_perf']-j['dispatched_perf'] if p else None,new_authority_ASR_ready_perf=a['produced_perf'] if a else None,producer_ready_before_new_authority_ASR=(p['admitted_perf']<a['produced_perf']) if p and a else None))
  put(out/'MATCHING_INFLIGHT_OPPORTUNITIES.json',inflight)
  summary=dict(status='PASS_ACTUAL_NATIVE_SERVICE_EXECUTION',cell_id=config['cell_id'],arm=arm,source_commit=settings['source_commit'],primary=primary,quality=quality,energy=energy,source_count=len(sources),all_authority_steps=sum(len(v) for v in histories.values()),authority_dispatches=len(auth),actual_ready_hits=len(hits),actual_ready_hit_rate=len(hits)/len(auth) if auth else 0.,matching_inflight_fallbacks=len(inflight),fullspec_inflight_promotions=len(policy.promotions) if arm=='two_full_spec_early' else 0,fullspec_known_invalid_C_skips=len(abandoned),fullspec_discarded_full_results=len(policy.discarded_full) if arm=='two_full_spec_early' else 0,producer_dispatches=sum(j['worker']=='producer' for j in dispatches),packet_admissions=len([r for r in admissions if r['candidate_wire_bytes'] is not None]),wire_total_bytes=sum(r['candidate_wire_bytes'] or 0 for r in admissions),wall_seconds=ended-origin,load_neural_ready_wall_seconds=load_end-load_begin,all_actual_roots_and_epochs_checked=True,component_timer_scopes=dict(full='native model timer excludes pre-model restore; worker_job_wall includes restore/export',consume='matching/restore plus original C/U and export is in worker_job_wall; not only C',receipt='fresh physical-queue get followed by complete validation, actual admission and decision times'),original_D2_C8_unchanged=True,scope='actual deployed controlled adaptation; original selected quality/history must still pass independent paired audit')
  put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],source_count=len(sources),actual_ready_hits=len(hits),neural_ready_all_C_models=True,semantic_history_comparison='required independent paired audit; not inferred from source identity'));print(json.dumps({k:v for k,v in summary.items() if k not in ('quality','energy')},indent=2));return summary
 except BaseException:
  (out/'failure.txt').write_text(traceback.format_exc());put(out/'GATE.json',dict(status='FAIL_READY_ONLY_NATIVE_SERVICE_PRESERVED',actual_dispatches=len(dispatches)));raise
 finally:
  for c in commands.values():c.put(None)
  for w in workers.values():
   w.join(10)
   if w.is_alive():w.terminate();w.join(10)
  if consumer is not None and consumer.t.is_alive():consumer.close()
  if power.t.is_alive():power.close()
  for j in (logs,events,canon,ingress):j.close()

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.config,a.manifest,a.out)
