"""Closed-loop finite preregistered requests; unchanged final NN/Owner dependency.

Derived Supervisor orchestration only. The base 59-file checkout remains external,
clean and byte matched. This harness and its request-clock analysis have their
own execution identity. No core C/U, admission, fencing, or commit logic is edited.
"""
from __future__ import annotations
import datetime,hashlib,json,multiprocessing as mp,os,pathlib,queue,signal,subprocess,threading,time,traceback,collections
from native_service import Journal,verify_source
from resilience_owner import owner_main
from resilience_transport import FramedReader,start_ticks
from resilience_storage import scan,canonical
from resilience_consumer import SurvivorConsumer
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
class BoundedPower:
 def __init__(self,path):
  self.stop=threading.Event();self.recent=collections.deque(maxlen=2);self.error=None;self.path=path;self.t=threading.Thread(target=self.run,daemon=True);self.t.start()
 def run(self):
  try:
   with open(self.path,'x',encoding='utf8') as f:
    while not self.stop.is_set():
     a=time.perf_counter();rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,power.draw,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10).splitlines();b=time.perf_counter()
     values={int(r.split(',')[0]):[float(v.strip()) for v in r.split(',')[1:]] for r in rows}
     row=dict(time=(a+b)/2,watts={g:v[0] for g,v in values.items()},gpu_memory_MiB={g:v[1] for g,v in values.items()},utilization_percent={g:v[2] for g,v in values.items()});self.recent.append(row);f.write(json.dumps(row)+'\n');f.flush();self.stop.wait(.1)
  except BaseException:self.error=traceback.format_exc()
 def close(self):self.stop.set();self.t.join(20)
from process_cleanup import (process_identity,process_group_members,owned_worker_identities,refresh_proof,terminate_group,cleanup_owner,CleanupError)

def kill_owner_group(owner,group_registered):
 return terminate_group(owner,group_registered)

def run_resident(config_path,manifest,out,*,owner_target=None,observer=None):
 config_path=pathlib.Path(config_path);config=json.loads(config_path.read_bytes());settings=config['settings'];source=verify_source(pathlib.Path(manifest))
 from common import verify_checkout,need,sha
 harness=config['harness_source'];need(pathlib.Path(harness['source_root']).resolve()==pathlib.Path(__file__).resolve().parent,'wrong harness source root');need(sha(harness['source_manifest'])==harness['source_manifest_sha256'],'harness manifest bytes differ');harness_gate=verify_checkout(harness['source_root'],harness['source_manifest'],harness['source_commit'])
 dependency_gates=[]
 for dependency in config.get('execution_dependencies',[]):
  need(sha(dependency['source_manifest'])==dependency['source_manifest_sha256'],'execution dependency manifest differs');dependency_gates.append(verify_checkout(dependency['source_root'],dependency['source_manifest'],dependency['source_commit']))
 target=owner_main if owner_target is None else owner_target
 request_order=config['request_order'];need(config['request_contract']=='closed_loop_single_outstanding_independent_EOS_v1','unknown request contract');need(len(request_order)==len(set(request_order)) and set(request_order)=={s['source_id'] for s in settings['sources']},'resident v1 requires each preregistered sid exactly once')
 if settings['source_commit']!=source['source_commit']:raise RuntimeError('wrong actual execution source')
 out=pathlib.Path(out);out.mkdir(exist_ok=False);put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=os.sys.version,executable=os.sys.executable,source=source,platform=os.sys.platform,precision='original FP32; TF32/autocast disabled in original workers',failure_domain='Owner+model workers; Supervisor/ingress/actualConsumer/power/storage survive',PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),PYTORCH_ALLOC_CONF=os.environ.get('PYTORCH_ALLOC_CONF'),harness_source=harness_gate,actual_NN_source=source,execution_dependencies=dependency_gates,request_contract=config['request_contract']))
 put(out/'RUN_RECORD.json',dict(experiment_id=config['cell_id'],code_commit=harness_gate['source_commit'],harness_source=harness_gate,actual_NN_source_commit=source['source_commit'],execution_dependencies=dependency_gates,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
 for s in settings['sources']:
  if hashlib.sha256(pathlib.Path(s['path']).read_bytes()).hexdigest()!=s['audio_sha256']:raise RuntimeError('accepted immutable input changed')
 ctx=mp.get_context('spawn');accepted={s['source_id']:ctx.Value('q',0) for s in settings['sources']};origin=ctx.Value('d',0.)
 supervisor=Journal(out/'supervisor.jsonl',True);ingress=Journal(out/'ingress.jsonl',True);publications=Journal(out/'publications.jsonl',True);power=BoundedPower(out/'power.jsonl');consumer=None;epoch=0;owner=None;owner_group=False;owner_launch_ticks=None;initials=None;inbox=queue.Queue();ctrl=None;old_publication=None;injection_used=False;finished=False;owner_restarts=0;all_canonical=False;initial_ready=None
 power_start_deadline=time.perf_counter()+20
 while not power.recent:
  if power.error or time.perf_counter()>power_start_deadline:
   power.close()
   for j in (supervisor,ingress,publications):j.close()
   put(out/'GATE.json',dict(status='FAIL_INITIAL_POWER_MEASUREMENT_NO_NEURAL_LAUNCH',failure=power.error or 'initial power sample timeout'))
   raise RuntimeError(power.error or 'initial power sample timeout')
  time.sleep(.02)
 started=time.perf_counter();request_ledger=Journal(out/'request_ledger.jsonl',True);request_origins={};request_completed={};request_index=0
 def admit_request():
  sid=request_order[len(request_origins)];stamp=time.perf_counter();previous=request_order[len(request_origins)-1] if request_origins else None
  if previous is not None:need(previous in request_completed,'next request released before actual prior Consumer EOS')
  request_origins[sid]=stamp;request_ledger.write(dict(kind='request_admitted',source_id=sid,request_index=len(request_origins)-1,observed=stamp,request_origin_perf=stamp,previous_source_id=previous,previous_complete_perf=request_completed.get(previous)))
  return sid
 def complete_request(result):
  if not result.get('applied'):return
  row=result['row'];sid=row['source_id'];source_config=next(s for s in settings['sources'] if s['source_id']==sid)
  if sid not in request_completed and row['certified_frontier']==source_config['frames']:
   need(sid in request_origins,'unadmitted request acquired certified output');observed=row['observed'];request_completed[sid]=observed
   request_ledger.write(dict(kind='request_complete',source_id=sid,request_index=request_order.index(sid),observed=observed,request_origin_perf=request_origins[sid],EOS_frontier=source_config['frames'],certified_frontier=row['certified_frontier'],consumer_observed_perf=observed))
   if len(request_origins)<len(request_order):admit_request()
 def note(kind,**body):supervisor.write(dict(kind=kind,observed=time.perf_counter(),**body))
 ingress_stop=threading.Event();ingress_errors=[]
 def ingest():
  try:
   while not ingress_stop.is_set():
    if not origin.value:ingress_stop.wait(.002);continue
    now=time.perf_counter()
    for s in settings['sources']:
     sid=s['source_id']
     if sid not in request_origins:continue
     request_origin=request_origins[sid];n=s['frames'];elapsed=max(0.,now-request_origin);due=min(n,int(elapsed/.5)*8000) if elapsed<n/16000 else n;past=accepted[sid].value
     while past<due:
      F=min(n,past+8000);offer=request_origin+F/16000
      ingress.write(dict(kind='accepted_input',source_id=sid,frontier=F,original_offer=offer,observed=time.perf_counter(),audio_sha256=s['audio_sha256']))
      accepted[sid].value=F;past=F
    if all(accepted[s['source_id']].value==s['frames'] for s in settings['sources']):return
    ingress_stop.wait(.002)
  except BaseException:ingress_errors.append(traceback.format_exc())
 ingress_thread=threading.Thread(target=ingest,daemon=True);ingress_thread.start()
 def start():
  nonlocal owner,ctrl,owner_group,owner_launch_ticks
  rx,tx=ctx.Pipe(duplex=False);pubrx,pubtx=ctx.Pipe(duplex=False)
  owner=ctx.Process(target=target,args=(config,str(manifest),str(out),epoch,rx,pubtx,accepted,origin,initials));owner.start();rx.close();pubtx.close();ctrl=tx;owner_group=False
  FramedReader(pubrx,'owner',epoch,inbox,'control')
  owner_launch_ticks=start_ticks(owner.pid);note('owner_started',owner_epoch=epoch,pid=owner.pid,start_ticks=owner_launch_ticks)
 def recover(reason):
  nonlocal epoch,owner_restarts,owner_group
  proof=kill_owner_group(owner,dict(owner_group,known_members=[*owner_group.get('known_members',[]),*owned_worker_identities(out,epoch)]));note('owner_group_death_confirmed',owner_epoch=epoch,reason=reason,proof=proof);owner_restarts+=1
  if owner_restarts>config.get('maximum_owner_restarts',2):raise RuntimeError('supported Owner recovery budget exhausted')
  epoch+=1;consumer.begin_owner(epoch);count=0
  for obj,receipt in scan(out/'facts.wal',repair_tail=True):
   if obj['kind']=='canonical':
    result=consumer.replay_fact(receipt)
    if result['applied']:count+=1;note('durable_fact_replayed',owner_epoch=epoch,transition_id=obj['body']['transition_id'],original_fact_owner_epoch=obj['body']['owner_epoch'],row=result['row']);complete_request(result)
  note('recovery_durable_prefix_ready',owner_epoch=epoch,newly_applied_facts=count)
  if old_publication is not None:
   rejected=consumer.apply(old_publication,epoch-1)
   if rejected['applied']:raise RuntimeError('retired Owner publication acquired new authority')
   note('actual_old_owner_publication_fenced',old_epoch=epoch-1,new_epoch=epoch)
  ctrl.close();start()
 try:
  if observer is not None:observer.start()
  start()
  while not finished:
   if observer is not None:observer.poll()
   now=time.perf_counter()
   if origin.value:
    if now-origin.value>config['maximum_service_seconds']:raise TimeoutError('fixed original service clock bound exceeded')
   if ingress_errors:raise RuntimeError('surviving ingress failure: '+ingress_errors[0])
   try:packet=inbox.get(timeout=.01)
   except queue.Empty:
    if owner.exitcode is not None and not finished:
     if consumer is None:raise RuntimeError('Owner failed before initial neural readiness')
     recover('observed_owner_exit')
    continue
   if packet['incarnation']!=epoch:
    note('retired_owner_channel_drop',old_owner_epoch=packet['incarnation'],current_owner_epoch=epoch);continue
   if packet['type'] in ('channel_exit','channel_integrity_failure'):
    owner.join(.05)
    if all_canonical and owner.exitcode==0:finished=True;continue
    if consumer is None:raise RuntimeError('initial Owner channel ended')
    recover(packet['type']);continue
   e=packet['payload'];kind=e['kind'];note('owner_event',event=e)
   if e['owner_epoch']!=epoch:raise RuntimeError('physical Owner namespace disagrees with its publication')
   if kind=='owner_group_started':
    if e['pid']!=owner.pid or e['pgid']!=owner.pid or not isinstance(owner_launch_ticks,int):raise RuntimeError('Owner physical group registration changed')
    current=process_identity(owner.pid)
    if current is not None and (current['start_ticks']!=owner_launch_ticks or current['pgid']!=owner.pid or current['session']!=owner.pid):raise RuntimeError('Owner registered PID generation/session changed')
    owner_group=dict(pid=owner.pid,pgid=owner.pid,session=owner.pid,start_ticks=owner_launch_ticks,bound_Owner_registration=True,known_members=[dict(pid=owner.pid,start_ticks=owner_launch_ticks)])
   elif kind=='owner_ready':
    if consumer is None:
     initials=e['initials'];consumer=SurvivorConsumer(initials,out/'consumer.jsonl',out/'consumer_rejections.jsonl',out/'facts.wal');consumer.begin_owner(0)
     initial_ready=time.perf_counter();origin.value=initial_ready;admit_request();put(out/'ORIGIN.json',dict(origin_perf=origin.value,cadence_seconds=.5,original_D=2.,original_C=8.,admission_scope='closed-loop per-request origins in request_ledger/REQUEST_ORIGINS; future preregistered sid accepted=0; every original obligation syncs before Owner dispatch'))
     put(out/'GENESIS.json',initials);note('initial_neural_ready_and_origin',origin_perf=origin.value,initial_load_and_warmup_seconds=initial_ready-started)
    else:note('recovered_owner_neural_ready',owner_epoch=epoch,recovered_frontiers=e['recovered_frontiers'])
   elif kind=='publication':
    event=e['event'];publications.write(dict(bound_owner_epoch=epoch,received_perf=packet['received_perf'],event=event))
    result=consumer.apply(event,epoch);old_publication=event
    complete_request(result)
    ctrl.send(dict(kind='consumer_ack',publication_id=event['publication_id'],visible_job_ids=result.get('visible_job_ids',[s.job_id for r in consumer.states.values() for s in r.steps])))
   elif kind=='owner_fault_ready':
    if injection_used:raise RuntimeError('Owner crash injection repeated')
    injection_used=True;note('fault_triggered',site=e['site'],target=e['target'],job_id=e['job_id'],owner_epoch=epoch,receipt=e.get('receipt'));recover(e['site'])
   elif kind=='fault_triggered':
    injection_used=True;note('fault_triggered',site=e['site'],owner_epoch=epoch,job_id=e.get('job_id'),slot=e.get('slot'))
   elif kind=='owner_all_canonical_complete':all_canonical=True
   elif kind=='owner_finished':
    owner.join(20)
    if owner.exitcode!=0:raise RuntimeError('Owner did not exit after physical drain')
    finished=True
   elif kind=='owner_error':
    note('writes_frozen_owner_error',traceback=e['traceback'])
    if consumer is None or not e.get('recoverable_owner_failure',False):raise RuntimeError(e['traceback'])
    recover('owner_integrity_or_uncertain_write')
   elif kind not in ('worker_started','replacement_neural_ready','worker_death_confirmed'):raise RuntimeError('unknown Supervisor Owner event')
   if power.error:raise RuntimeError(power.error)
  if not all_canonical:raise RuntimeError('Owner finished before completing every input obligation')
  if config.get('fault',{}).get('kind','none')!='none' and not injection_used:raise RuntimeError('frozen fault site was not exercised')
  if any(accepted[s['source_id']].value!=s['frames'] for s in settings['sources']):raise RuntimeError('original accepted input obligations missing')
  end=time.perf_counter();put(out/'SERVICE_END.json',dict(service_end_perf=end,initial_load_begin_perf=started,initial_neural_ready_perf=initial_ready,scope='original origin through final model physical drain and actual Consumer FIFO applications; fault/reload/recomputation costs included'))
  power_deadline=time.perf_counter()+20
  while not power.recent or power.recent[-1]['time']<end:
   if power.error or not power.t.is_alive() or time.perf_counter()>power_deadline:raise RuntimeError('missing actual final power sample: '+str(power.error))
   time.sleep(.02)
  ingress_thread.join(10)
  if ingress_thread.is_alive() or ingress_errors:raise RuntimeError('surviving ingress did not finish actual accepted input')
  power.close();consumer.close();note('trial_all_input_and_physical_completion',owner_restarts=owner_restarts,owner_epoch=epoch)
  for j in (supervisor,ingress,publications):j.close()
  put(out/'REQUEST_ORIGINS.json',request_origins);request_ledger.close()
  if observer is not None:observer.finish()
  from resident_analysis import analyze_resident
  summary=analyze_resident(out)
  if summary['gate']!='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE':raise RuntimeError('complete resident task/request-clock/reference recount did not pass')
  put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['gate'],harness_source_commit=harness_gate['source_commit'],actual_NN_source_commit=source['source_commit'],cell_id=config['cell_id'],scope='Finite preregistered closed-loop requests; original500ms/EOS, exact C/U and actual Consumer; no arbitrary dynamic registration/capacity claim.'))
  return summary
 except BaseException:
  put(out/'GATE.json',dict(status='FAIL_RESILIENT_NATIVE_TRIAL_PRESERVED',source_commit=source['source_commit'],failure=traceback.format_exc()));(out/'failure.txt').write_text(traceback.format_exc());raise
 finally:
  ingress_stop.set();ingress_thread.join(10)
  cleanup_error=None
  if owner is not None and not (finished and owner.exitcode==0):
   try:
    if owner_group:
     proof=dict(owner_group,known_members=[*owner_group.get('known_members',[]),*owned_worker_identities(out,epoch)]);release=kill_owner_group(owner,proof)
    else:release=cleanup_owner(owner,None,owner_launch_ticks,out,epoch)
    put(out/'OWNER_CLEANUP.json',dict(status='PASS_ACTUAL_FAILED_TRIAL_GROUP_AND_CUDA_RELEASE',proof=release,scope='Failure cleanup only; does not turn the trial into a task/performance PASS'))
   except BaseException as exc:
    cleanup_error=exc;detail=traceback.format_exc();put(out/'OWNER_CLEANUP.json',dict(status='FAIL_OWNER_CLEANUP_RELEASE_UNVERIFIED',failure=detail,confirmed_physical_release=False))
    put(out/'GATE.json',dict(status='FAIL_RESIDENT_OWNER_CLEANUP_RELEASE_UNVERIFIED',source_commit=source['source_commit'],failure=detail,confirmed_physical_release=False))
    with (out/'failure.txt').open('a',encoding='utf8') as failure_log:failure_log.write('\nOWNER CLEANUP FAILURE (release unverified):\n'+detail)
  if power.t.is_alive():power.close()
  for j in (supervisor,ingress,publications):
   if not j.f.closed:j.close()
  if consumer is not None and not consumer.log.f.closed:consumer.close()
  if not request_ledger.f.closed:request_ledger.close()
  if observer is not None and hasattr(observer,'close'):observer.close()
  if cleanup_error is not None:raise CleanupError('Owner group/CUDA cleanup failed; trial and resource release remain FAIL') from cleanup_error
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();run_resident(a.config,a.manifest,a.out)

