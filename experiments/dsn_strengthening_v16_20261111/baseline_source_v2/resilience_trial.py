"""Actual trial supervisor; survives the declared Owner/worker failure domain."""
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
def process_group_members(group):
 rows=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split()
   if int(s[2])==group:rows.append(dict(pid=int(p.name),state=s[0],start_ticks=int(s[19])))
  except (OSError,ValueError,IndexError):continue
 return rows
def kill_owner_group(owner,group_registered):
 pid=owner.pid
 if not group_registered:raise RuntimeError('cannot kill an unregistered Owner group')
 members=process_group_members(pid)
 if any(r['state'] not in ('Z','X') for r in members):os.killpg(pid,signal.SIGKILL)
 owner.join(10)
 deadline=time.perf_counter()+30
 while True:
  members=process_group_members(pid);active=[r for r in members if r['state'] not in ('Z','X')]
  gpu_pids=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
  if not active and not gpu_pids:return dict(owner_pid=pid,owner_exitcode=owner.exitcode,confirmed_no_executing_members=True,retired_process_members=members,all_CUDA_owners_released=True,observed=time.perf_counter())
  if time.perf_counter()>deadline:raise RuntimeError('old Owner group still owns execution or CUDA')
  time.sleep(.05)
def run_trial(config_path,manifest,out):
 config_path=pathlib.Path(config_path);config=json.loads(config_path.read_bytes());settings=config['settings'];source=verify_source(pathlib.Path(manifest))
 if settings['source_commit']!=source['source_commit']:raise RuntimeError('wrong actual execution source')
 out=pathlib.Path(out);out.mkdir(exist_ok=False);put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=os.sys.version,executable=os.sys.executable,source=source,platform=os.sys.platform,precision='original FP32; TF32/autocast disabled in original workers',failure_domain='Owner+model workers; Supervisor/ingress/actualConsumer/power/storage survive',PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),PYTORCH_ALLOC_CONF=os.environ.get('PYTORCH_ALLOC_CONF')))
 put(out/'RUN_RECORD.json',dict(experiment_id=config['cell_id'],code_commit=source['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
 for s in settings['sources']:
  if hashlib.sha256(pathlib.Path(s['path']).read_bytes()).hexdigest()!=s['audio_sha256']:raise RuntimeError('accepted immutable input changed')
 ctx=mp.get_context('spawn');accepted={s['source_id']:ctx.Value('q',0) for s in settings['sources']};origin=ctx.Value('d',0.)
 supervisor=Journal(out/'supervisor.jsonl',True);ingress=Journal(out/'ingress.jsonl',True);publications=Journal(out/'publications.jsonl',True);power=BoundedPower(out/'power.jsonl');consumer=None;epoch=0;owner=None;owner_group=False;initials=None;inbox=queue.Queue();ctrl=None;old_publication=None;injection_used=False;finished=False;owner_restarts=0;all_canonical=False;initial_ready=None
 power_start_deadline=time.perf_counter()+20
 while not power.recent:
  if power.error or time.perf_counter()>power_start_deadline:
   power.close()
   for j in (supervisor,ingress,publications):j.close()
   put(out/'GATE.json',dict(status='FAIL_INITIAL_POWER_MEASUREMENT_NO_NEURAL_LAUNCH',failure=power.error or 'initial power sample timeout'))
   raise RuntimeError(power.error or 'initial power sample timeout')
  time.sleep(.02)
 started=time.perf_counter()
 def note(kind,**body):supervisor.write(dict(kind=kind,observed=time.perf_counter(),**body))
 ingress_stop=threading.Event();ingress_errors=[]
 def ingest():
  try:
   while not ingress_stop.is_set():
    if not origin.value:ingress_stop.wait(.002);continue
    now=time.perf_counter()
    for s in settings['sources']:
     sid=s['source_id'];n=s['frames'];due=min(n,int((now-origin.value)/.5)*8000) if now-origin.value<n/16000 else n;past=accepted[sid].value
     while past<due:
      F=min(n,past+8000);offer=origin.value+F/16000
      ingress.write(dict(kind='accepted_input',source_id=sid,frontier=F,original_offer=offer,observed=time.perf_counter(),audio_sha256=s['audio_sha256']))
      accepted[sid].value=F;past=F
    if all(accepted[s['source_id']].value==s['frames'] for s in settings['sources']):return
    ingress_stop.wait(.002)
  except BaseException:ingress_errors.append(traceback.format_exc())
 ingress_thread=threading.Thread(target=ingest,daemon=True);ingress_thread.start()
 def start():
  nonlocal owner,ctrl,owner_group
  rx,tx=ctx.Pipe(duplex=False);pubrx,pubtx=ctx.Pipe(duplex=False)
  owner=ctx.Process(target=owner_main,args=(config,str(manifest),str(out),epoch,rx,pubtx,accepted,origin,initials));owner.start();rx.close();pubtx.close();ctrl=tx;owner_group=False
  FramedReader(pubrx,'owner',epoch,inbox,'control')
  note('owner_started',owner_epoch=epoch,pid=owner.pid,start_ticks=start_ticks(owner.pid))
 def recover(reason):
  nonlocal epoch,owner_restarts,owner_group
  proof=kill_owner_group(owner,owner_group);note('owner_group_death_confirmed',owner_epoch=epoch,reason=reason,proof=proof);owner_restarts+=1
  if owner_restarts>config.get('maximum_owner_restarts',2):raise RuntimeError('supported Owner recovery budget exhausted')
  epoch+=1;consumer.begin_owner(epoch);count=0
  for obj,receipt in scan(out/'facts.wal',repair_tail=True):
   if obj['kind']=='canonical':
    result=consumer.replay_fact(receipt)
    if result['applied']:count+=1;note('durable_fact_replayed',owner_epoch=epoch,transition_id=obj['body']['transition_id'],original_fact_owner_epoch=obj['body']['owner_epoch'],row=result['row'])
  note('recovery_durable_prefix_ready',owner_epoch=epoch,newly_applied_facts=count)
  if old_publication is not None:
   rejected=consumer.apply(old_publication,epoch-1)
   if rejected['applied']:raise RuntimeError('retired Owner publication acquired new authority')
   note('actual_old_owner_publication_fenced',old_epoch=epoch-1,new_epoch=epoch)
  ctrl.close();start()
 try:
  start()
  while not finished:
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
    if e['pid']!=owner.pid or e['pgid']!=owner.pid or os.getpgid(owner.pid)!=owner.pid:raise RuntimeError('Owner physical group registration changed')
    owner_group=True
   elif kind=='owner_ready':
    if consumer is None:
     initials=e['initials'];consumer=SurvivorConsumer(initials,out/'consumer.jsonl',out/'consumer_rejections.jsonl',out/'facts.wal');consumer.begin_owner(0)
     initial_ready=time.perf_counter();origin.value=initial_ready;put(out/'ORIGIN.json',dict(origin_perf=origin.value,cadence_seconds=.5,original_D=2.,original_C=8.,admission_scope='immutable source identity fixed before trial; each released obligation syncs in surviving ingress before Owner may dispatch'))
     put(out/'GENESIS.json',initials);note('initial_neural_ready_and_origin',origin_perf=origin.value,initial_load_and_warmup_seconds=initial_ready-started)
    else:note('recovered_owner_neural_ready',owner_epoch=epoch,recovered_frontiers=e['recovered_frontiers'])
   elif kind=='publication':
    event=e['event'];publications.write(dict(bound_owner_epoch=epoch,received_perf=packet['received_perf'],event=event))
    result=consumer.apply(event,epoch);old_publication=event
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
  from resilience_metrics import analyze_trial
  summary=analyze_trial(out)
  if summary['gate']!='PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT':raise RuntimeError('complete original trial recount did not pass')
  if config.get('require_reference',True) and summary['integrity']['original_reference']['status']!='PASS_COMPLETE_ORIGINAL_REFERENCE':raise RuntimeError('formal trial lacks complete original-task reference')
  put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK',source_commit=source['source_commit'],cell_id=config['cell_id'],scope='Actual task and original endpoint recount complete; separate actual trace refinement remains required.'))
  return summary
 except BaseException:
  put(out/'GATE.json',dict(status='FAIL_RESILIENT_NATIVE_TRIAL_PRESERVED',source_commit=source['source_commit'],failure=traceback.format_exc()));(out/'failure.txt').write_text(traceback.format_exc());raise
 finally:
  ingress_stop.set();ingress_thread.join(10)
  if owner is not None and owner.is_alive():
   try:kill_owner_group(owner,owner_group)
   except BaseException:owner.kill();owner.join(10)
  if power.t.is_alive():power.close()
  for j in (supervisor,ingress,publications):
   if not j.f.closed:j.close()
  if consumer is not None and not consumer.log.f.closed:consumer.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();run_trial(a.config,a.manifest,a.out)

