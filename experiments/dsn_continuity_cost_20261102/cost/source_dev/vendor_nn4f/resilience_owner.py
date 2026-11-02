"""Restartable Owner. The original full model program is unchanged."""
from __future__ import annotations
import hashlib,json,multiprocessing as mp,os,pathlib,queue,time,traceback
from feedback_contract import FeedbackCut
from native_service import Journal
from resilience_policy import ResilientFullSpecCoordinator
from resilience_storage import FactStore,canonical
from resilience_transport import start_worker,stop_worker,wait_cuda_release
from resilience_inbound import audit_value,IntegrityError,WritesFrozenError
from resilience_channel_close import drain_closed_worker_channel
def owner_main(config,manifest,out,epoch,control,publication,accepted,origin,initials_hint):
 if hasattr(os,'setsid'):os.setsid()
 out=pathlib.Path(out);attempt=out/f'owner_e{epoch}';attempt.mkdir()
 events=Journal(attempt/'owner_events.jsonl');dispatchlog=Journal(attempt/'dispatch.jsonl');resultslog=Journal(attempt/'worker_results.jsonl');auditlog=Journal(attempt/'policy_audit.jsonl');sizes=Journal(attempt/'state_sizes.jsonl')
 def emit(kind,**body):publication.send(dict(kind=kind,owner_epoch=epoch,observed=time.perf_counter(),**body))
 def log(kind,**body):events.write(dict(kind=kind,owner_epoch=epoch,observed=time.perf_counter(),**body))
 emit('owner_group_started',pid=os.getpid(),pgid=os.getpgrp())
 settings=config['settings'];fault=config.get('fault',{'kind':'none'});sidlist=[s['source_id'] for s in settings['sources']];sources={s['source_id']:s for s in settings['sources']}
 import soundfile as sf
 audio={sid:sf.read(s['path'],dtype='float32')[0] for sid,s in sources.items()}
 ctx=mp.get_context('spawn');inbox=queue.Queue();workers={};ready={};busy={};inc={slot:0 for slot in ('full0','full1')};sent_hints=set();pubseq=0;serial=0;pending={};consumer_pins=set();fault_claim=ctx.Event();fault_lock=ctx.Lock();fault_after={};injected=False;late_event=None;deferred=[];store=None;policy=None;last_stats=0.;stopping=False
 metadata=dict(config_sha256=hashlib.sha256(canonical(config)).hexdigest(),actual_source_commit=settings['source_commit'],sources=[dict(source_id=sid,frames=s['frames'],audio_sha256=s['audio_sha256']) for sid,s in sources.items()])
 def launch(slot):
  gpu=settings['primary_gpu'] if slot=='full0' else 1-settings['primary_gpu']
  w=start_worker(ctx,slot,gpu,settings,inc[slot],inbox,fault if epoch==0 else {'kind':'none'},fault_claim,fault_lock);workers[slot]=w;busy[slot]=None
  log('worker_started',slot=slot,incarnation=inc[slot],pid=w['pid'],start_ticks=w['start_ticks'],gpu=gpu);emit('worker_started',slot=slot,incarnation=inc[slot],pid=w['pid'],gpu=gpu)
 def publish(event):
  nonlocal pubseq
  pubseq+=1;event=dict(event,publication_id=pubseq);pending[pubseq]=[s['job_id'] for s in event.get('steps',[])]
  if len(pending)>64:raise RuntimeError('bounded publication window exhausted; writes require recovery')
  emit('publication',event=event)
 def view(sid):publish(policy.view_event(sid))
 def commit(tx):
  body=dict(tx);body['record']=body.pop('full_record')
  target=fault.get('target')
  match=(epoch==0 and tx['source_id']==fault.get('source_id') and tx['next_state']['frontier']==target)
  if match and fault.get('kind')=='owner_before_durable':
   emit('owner_fault_ready',site='after_original_C_before_durable',source_id=tx['source_id'],target=target,job_id=tx['job']['job_id']);time.sleep(60);raise RuntimeError('scheduled Owner kill was not delivered')
  receipt=store.commit(body);receipt['synced_perf']=time.perf_counter();log('durable_sync',receipt=receipt,job_id=tx['job']['job_id'],source_id=tx['source_id'])
  if match and fault.get('kind')=='owner_after_durable':
   emit('owner_fault_ready',site='after_durable_before_install_and_consume',source_id=tx['source_id'],target=target,job_id=tx['job']['job_id'],receipt=receipt);time.sleep(60);raise RuntimeError('scheduled Owner kill was not delivered')
  return receipt
 def outcome(result):
  kind=result['kind'];job=result.get('job',{});sid=job.get('source_id')
  if kind=='canonical':
   receipt=result['durable_receipt'];log('canonical_install',source_id=sid,job_id=job['job_id'],receipt=receipt,parent_state_sha=job['start'].sha256,next_state_sha=result['cut'].sha256)
   publish(dict(kind='canonical',source_id=sid,state=result['cut'].state,durable_receipt=receipt))
   publish(result['view_event_snapshot'])
  elif kind in ('buffered_full','producer_completed'):view(sid)
  elif kind not in ('discarded','abandoned_full','fenced_terminal'):raise RuntimeError('unknown owned outcome')
 def admit_packet(e,closed=False):
  nonlocal injected,late_event
  slot=e['slot'];physical=e['incarnation'];event=e['payload'];kind=event['kind']
  resultslog.write(dict(physical_slot=slot,physical_incarnation=physical,event=event))
  before=dict(canon={sid:policy.canonical(sid).sha256 for sid in sidlist},busy=dict(busy),session_epochs=dict(policy.epochs),physical_incarnations=dict(inc),inbound_seen={jid:dict(v['seen']) for jid,v in policy.inbound.active.items()})
  r=policy.receive_event(slot,physical,event,received_perf=e['received_perf'])
  if r['disposition']!='accept':
   if r['physical_terminal']:
    if busy[slot]!=event['job_id']:raise RuntimeError('fenced terminal cannot retire a different busy lease')
    busy[slot]=None
   log('local_message_disposition',result=audit_value(r),before=before,after=dict(canon={sid:policy.canonical(sid).sha256 for sid in sidlist},busy=dict(busy),session_epochs=dict(policy.epochs),physical_incarnations=dict(inc),inbound_seen={jid:dict(v['seen']) for jid,v in policy.inbound.active.items()}));return r
  if kind=='asr_early':
   if r['outcome']['eligible_view']:view(event['source_id'])
  else:
   if not r['physical_terminal'] or busy[slot]!=event['job_id']:raise RuntimeError('terminal event cannot release this busy slot')
   busy[slot]=None;outcome(r['outcome'])
  if not closed and fault.get('kind')=='duplicate_late' and event.get('end_frontier',event.get('record',{}).get('end'))==fault.get('target'):
   duplicate=dict(e);duplicate['received_perf']=time.perf_counter()
   if not injected:
    injected=True;deferred.append((time.perf_counter()+.05,duplicate));emit('fault_triggered',site='actual_message_duplicate_and_late',job_id=event['job_id'])
   if late_event is None and kind=='completed':late_event=duplicate;deferred.append((time.perf_counter()+.65,duplicate))
  return r
 def lose(slot,reason,planned=False):
  w=workers[slot];old=inc[slot];proof=stop_worker(w,force=True);proof.update(slot=slot,incarnation=old,reason=reason)
  if proof['partial_frame_thread_blocked']:raise RuntimeError('retired channel receiver is blocked')
  release=wait_cuda_release(w['gpu'],w['pid']);proof['cuda_release']=release
  def control_tail(e):
   c=e['payload']
   if c.get('kind')=='state_telemetry':auditlog.write(dict(kind='native_state',owner_epoch=epoch,physical_slot=slot,physical_incarnation=old,**c['row']))
  drained=drain_closed_worker_channel(inbox,slot=slot,incarnation=old,death_proof=proof,on_message=lambda e:admit_packet(e,True),on_control=control_tail,audit_packet=lambda e:log('sealed_old_channel_receipt',packet=e))
  log('old_channel_validated_before_incarnation_fence',slot=slot,incarnation=old,drain=drained)
  policy.worker_lost(slot,old,proof);busy[slot]=None;ready.pop(slot,None);log('worker_death_confirmed',proof=proof,planned=planned);emit('worker_death_confirmed',proof=proof,planned=planned)
  inc[slot]+=1;policy.replace_worker(slot,inc[slot]);launch(slot)
 def controls():
  nonlocal consumer_pins,stopping
  while control.poll():
   c=control.recv()
   if c['kind']=='consumer_ack':
    pending.pop(c['publication_id'],None);consumer_pins=set(c['visible_job_ids'])
   elif c['kind']=='stop':stopping=True
   else:raise RuntimeError('unknown Supervisor command')
 def stats():
  nonlocal last_stats
  now=time.perf_counter()
  if now-last_stats<1:return
  last_stats=now
  rss=int(pathlib.Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE') if pathlib.Path('/proc/self/statm').exists() else None
  row=dict(observed=now,owner_epoch=epoch,history=policy.history_stats(),pending_publications=len(pending),consumer_pins=len(consumer_pins),current_cut_bytes=sum(len(canonical(policy.canonical(sid).state)) for sid in sidlist),current_text_bytes=sum(len(policy.canonical(sid).transcript.encode()) for sid in sidlist),immutable_audio_bytes=sum(a.nbytes for a in audio.values()),owner_RSS_bytes=rss)
  sizes.write(row)
 try:
  if initials_hint is not None:store=FactStore(out/'facts.wal',initials_hint,metadata,repair_tail=True)
  for slot in inc:launch(slot)
  while len(ready)<2:
   e=inbox.get(timeout=300)
   if e['type']!='message' or e['payload']['kind']!='ready':raise RuntimeError('worker startup failed: '+repr(e))
   slot=e['slot'];ready[slot]=e['payload'];resultslog.write(dict(physical_slot=slot,physical_incarnation=e['incarnation'],event=e['payload']))
  ids=[r['runtime_identity'] for r in ready.values()]
  if ids[0]!=ids[1]:raise RuntimeError('protected replicas have different contracts')
  initials={sid:ready['full0']['initials'][sid] for sid in sidlist}
  if any(r['initials'][sid]!=initials[sid] for r in ready.values() for sid in sidlist):raise RuntimeError('native genesis differs')
  if store is None:store=FactStore(out/'facts.wal',initials,metadata)
  elif initials!=initials_hint:raise RuntimeError('recovery changed the original full-state genesis')
  policy=ResilientFullSpecCoordinator(initials={sid:c.state for sid,c in store.roots.items()},audio=audio,runtime_identity=ids[0],source_frames={sid:s['frames'] for sid,s in sources.items()},producer_worker=None,authority_workers=('full0','full1'),owner_epoch=epoch,before_commit=commit,worker_incarnations=inc,audit_sink=lambda k,v:auditlog.write(dict(kind=k,observed=time.perf_counter(),body=v)),history_limit=64)
  emit('owner_ready',initials=initials,runtime_identity=ids[0],workers=ready,recovered_frontiers={sid:c.frontier for sid,c in store.roots.items()})
  while origin.value==0:controls();time.sleep(.002)
  while not stopping:
   controls()
   if time.perf_counter()-origin.value>config['maximum_service_seconds']:raise TimeoutError('original-clock service bound exceeded')
   for _ in range(16):
    try:e=inbox.get_nowait()
    except queue.Empty:break
    slot=e['slot'];physical=e['incarnation']
    if physical!=inc.get(slot):
     log('retired_physical_channel_drop',slot=slot,incarnation=physical,message_type=e['type']);continue
    if e['type']=='control':
     c=e['payload']
     if c['kind']=='state_telemetry':
      auditlog.write(dict(kind='native_state',owner_epoch=epoch,physical_slot=slot,physical_incarnation=physical,**c['row']));continue
     fault_after[slot]=c
     if c['kind']=='fault_partial_frame_ready':emit('fault_triggered',site='worker_partial_logical_frame',slot=slot,incarnation=physical,job_id=c['job_id']);lose(slot,'controlled_partial_frame',True);fault_after.pop(slot,None)
     continue
    if e['type'] in ('channel_exit','channel_integrity_failure'):
     if slot in ready:lose(slot,e['type']);continue
     raise RuntimeError('startup channel failed')
    event=e['payload'];kind=event['kind']
    if kind=='ready':
     ready[slot]=event;resultslog.write(dict(physical_slot=slot,physical_incarnation=physical,event=event));log('replacement_neural_ready',slot=slot,incarnation=physical,pid=event['pid']);emit('replacement_neural_ready',slot=slot,incarnation=physical,pid=event['pid']);continue
    if kind=='failed':raise RuntimeError(event['traceback'])
    if kind=='drained':raise RuntimeError('unscheduled worker drain')
    admit_packet(e)
   now=time.perf_counter()
   due=[p for p in deferred if p[0]<=now];deferred[:]=[p for p in deferred if p[0]>now]
   for _,e in due:inbox.put(e)
   for slot,w in list(workers.items()):
    if not w['process'].is_alive() and slot in ready:
     if w['process'].exitcode==0:raise RuntimeError('unannounced clean worker exit; original worker failed before its declared drain')
     lose(slot,'observed_worker_fail_stop')
   for slot,c in list(fault_after.items()):
    if c['kind']=='fault_after_asr_ready' and c['job_id'] in consumer_pins:
     emit('fault_triggered',site='worker_after_actual_ASR_consumption',slot=slot,incarnation=c['incarnation'],job_id=c['job_id']);lose(slot,'controlled_after_actual_ASR',True);fault_after.pop(slot,None)
   for result in policy.pop_ready_commits():outcome(result)
   for jobid,proof in policy.invalidations().items():
    if jobid in sent_hints:continue
    job=policy.jobs[jobid];workers[job['worker']]['hints'].send(dict(job_id=jobid,source_id=job['source_id'],dispatch_epoch=job['dispatch_epoch'],proof=proof));sent_hints.add(jobid)
   pending_ids=set(consumer_pins)
   for refs in pending.values():pending_ids.update(refs)
   policy.collect_history(pending_job_ids=pending_ids);sent_hints.intersection_update(policy.jobs);stats()
   complete=all(policy.canonical(sid).frontier==sources[sid]['frames'] for sid in sidlist)
   if complete and all(v is None for v in busy.values()) and not deferred and inbox.empty():
    emit('owner_all_canonical_complete',canonical_frontiers={sid:policy.canonical(sid).frontier for sid in sidlist});break
   for slot in ('full0','full1'):
    if slot not in ready or busy[slot] is not None:continue
    for sid in sidlist:
     accepted_F=accepted[sid].value
     if config['arm']=='fullcall':start=policy.next_full_start(sid,accepted_F,settings['max_ahead_frames'])
     else:start=policy.canonical(sid) if sid not in policy.active_authority else None
     if start is None:continue
     end=min(sources[sid]['frames'],start.frontier+8000)
     if end<=start.frontier or end>accepted_F:continue
     serial+=1;jid=f'e{epoch}-j{serial:09d}';job=policy.register(job_id=jid,worker=slot,worker_incarnation=inc[slot],kind='full',source_id=sid,start=start,end=end,dispatched_perf=time.perf_counter())
     dispatchlog.write(dict(owner_epoch=epoch,physical_slot=slot,physical_incarnation=inc[slot],pid=workers[slot]['pid'],job=audit_value(job)))
     busy[slot]=jid;workers[slot]['commands'].send(dict(kind='full',job_id=jid,dispatch_epoch=job['dispatch_epoch'],source_id=sid,start=start.state,end=end,early_view=True,capture_packet=False));break
   time.sleep(.002)
  for slot,w in list(workers.items()):
   proof=stop_worker(w,force=slot not in ready);proof['cuda_release']=wait_cuda_release(w['gpu'],w['pid']);log('worker_final_exit',proof=proof)
  # Both receiver threads have now joined. Preserve late telemetry and reject
  # terminal duplicates rather than silently omitting the last channel tail.
  while not inbox.empty():
   e=inbox.get_nowait();slot=e['slot'];physical=e['incarnation']
   if e['type']=='control' and e['payload'].get('kind')=='state_telemetry':auditlog.write(dict(kind='native_state',owner_epoch=epoch,physical_slot=slot,physical_incarnation=physical,**e['payload']['row']));continue
   if e['type']!='message':log('closed_channel_tail',slot=slot,incarnation=physical,event=e);continue
   event=e['payload']
   if event['kind']=='failed':raise RuntimeError(event['traceback'])
   resultslog.write(dict(physical_slot=slot,physical_incarnation=physical,event=event))
   if event['kind'] in ('ready','drained'):continue
   r=policy.receive_event(slot,physical,event,received_perf=e['received_perf'])
   if r['disposition']=='accept' or r['physical_terminal']:raise RuntimeError('new owned work appeared after complete physical shutdown')
   log('shutdown_message_disposition',result=audit_value(r))
  emit('owner_finished',history=policy.history_stats())
 except BaseException as exc:
  emit('owner_error',traceback=traceback.format_exc(),recoverable_owner_failure=isinstance(exc,(IntegrityError,WritesFrozenError)));raise
 finally:
  for w in workers.values():
   if w['process'].is_alive():stop_worker(w,force=True)
  if store is not None:store.close()
  for j in (events,dispatchlog,resultslog,auditlog,sizes):j.close()

