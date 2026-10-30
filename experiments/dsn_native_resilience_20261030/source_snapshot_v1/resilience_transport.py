"""Incarnation-bound Pipes; a partial worker frame cannot block the Owner loop."""
from __future__ import annotations
import hashlib,json,multiprocessing as mp,os,pathlib,pickle,queue,signal,subprocess,threading,time
MAX_WIRE=32*1024*1024
class ChannelIntegrityError(RuntimeError):pass
class FramedSender:
 def __init__(self,connection,control=None,slot=None,incarnation=None,fault=None,fired=None,lock=None,record_resources=False):
  self.c=connection;self.control=control;self.slot=slot;self.inc=incarnation;self.fault=fault or {};self.fired=fired;self.lock=lock;self.record_resources=record_resources
 def put(self,event):
  event=dict(event,worker_incarnation=self.inc)
  if self.record_resources and event.get('kind') in ('completed','abandoned'):
   import torch
   rss=int(pathlib.Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE') if pathlib.Path('/proc/self/statm').exists() else None
   event['resource_snapshot']=dict(RSS_bytes=rss,cuda_allocated_bytes=torch.cuda.memory_allocated(),cuda_reserved_bytes=torch.cuda.memory_reserved(),cuda_peak_allocated_since_worker_start=torch.cuda.max_memory_allocated(),cuda_peak_reserved_since_worker_start=torch.cuda.max_memory_reserved())
  payload=pickle.dumps(event,protocol=5)
  if len(payload)>MAX_WIRE:raise ChannelIntegrityError('oversize protocol frame')
  self.c.send_bytes(json.dumps(dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())).encode())
  eligible=(self.fault.get('kind')=='worker_partial_frame' and event.get('kind')=='asr_early' and event.get('source_id')==self.fault.get('source_id') and event.get('end_frontier')==self.fault.get('target'))
  if eligible:
   with self.lock:
    first=not self.fired.is_set()
    if first:self.fired.set()
   if first:
    self.control.send(dict(kind='fault_partial_frame_ready',slot=self.slot,incarnation=self.inc,job_id=event['job_id'],source_id=event['source_id'],target=event['end_frontier'],pid=os.getpid(),observed=time.perf_counter()))
    # A controlled pause makes the actual SIGKILL land after header/before
    # body. This is an IPC fault site, not added model computation.
    time.sleep(30)
    raise RuntimeError('scheduled physical IPC fail-stop was not delivered')
  self.c.send_bytes(payload)
  eligible_after=(self.fault.get('kind')=='worker_after_asr' and event.get('kind')=='asr_early' and event.get('source_id')==self.fault.get('source_id') and event.get('end_frontier')==self.fault.get('target'))
  if eligible_after:
   with self.lock:
    first=not self.fired.is_set()
    if first:self.fired.set()
   if first:
    self.control.send(dict(kind='fault_after_asr_ready',slot=self.slot,incarnation=self.inc,job_id=event['job_id'],source_id=event['source_id'],target=event['end_frontier'],pid=os.getpid(),observed=time.perf_counter()))
    time.sleep(30)
    raise RuntimeError('scheduled after-ASR physical fail-stop was not delivered')
class CommandReceiver:
 def __init__(self,c):self.c=c
 def get(self):return self.c.recv()
class HintReceiver:
 def __init__(self,c):self.c=c
 def get_nowait(self):
  if not self.c.poll():raise queue.Empty()
  return self.c.recv()
class FramedReader:
 def __init__(self,c,slot,incarnation,inbox,channel_kind='result'):
  self.c=c;self.slot=slot;self.inc=incarnation;self.inbox=inbox;self.channel_kind=channel_kind;self.closed=False
  self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
 def run(self):
  partial=False
  try:
   while True:
    if self.channel_kind=='control':
     event=self.c.recv();self.inbox.put(dict(type='control',slot=self.slot,incarnation=self.inc,payload=event,received_perf=time.perf_counter()));continue
    h=json.loads(self.c.recv_bytes(2048));partial=True
    if not isinstance(h.get('bytes'),int) or not 0<=h['bytes']<=MAX_WIRE:raise ChannelIntegrityError('invalid bounded frame header')
    raw=self.c.recv_bytes(MAX_WIRE)
    if len(raw)!=h['bytes'] or hashlib.sha256(raw).hexdigest()!=h['sha256']:raise ChannelIntegrityError('partial/corrupt framed message')
    event=pickle.loads(raw);partial=False
    if not isinstance(event,dict):raise ChannelIntegrityError('worker frame is not an event')
    self.inbox.put(dict(type='message',slot=self.slot,incarnation=self.inc,payload=event,received_perf=time.perf_counter()))
  except (EOFError,OSError) as e:self.inbox.put(dict(type='channel_exit',slot=self.slot,incarnation=self.inc,partial_frame=partial,error=type(e).__name__,received_perf=time.perf_counter()))
  except BaseException as e:self.inbox.put(dict(type='channel_integrity_failure',slot=self.slot,incarnation=self.inc,error=repr(e),received_perf=time.perf_counter()))
  finally:self.closed=True;self.c.close()
def worker_entry(slot,gpu,settings,commands,results,hints,control,incarnation,fault,fired,lock):
 from stage_worker import worker_main
 worker_main(slot,gpu,'authority',settings,CommandReceiver(commands),FramedSender(results,control,slot,incarnation,fault,fired,lock,record_resources=settings.get('record_resources',False)),HintReceiver(hints))
def start_worker(ctx,slot,gpu,settings,incarnation,inbox,fault,fired,lock):
 cmd_rx,cmd_tx=ctx.Pipe(duplex=False);res_rx,res_tx=ctx.Pipe(duplex=False);hint_rx,hint_tx=ctx.Pipe(duplex=False);control_rx,control_tx=ctx.Pipe(duplex=False)
 p=ctx.Process(target=worker_entry,args=(slot,gpu,settings,cmd_rx,res_tx,hint_rx,control_tx,incarnation,fault,fired,lock));p.start()
 for c in (cmd_rx,res_tx,hint_rx,control_tx):c.close()
 r=FramedReader(res_rx,slot,incarnation,inbox);control_reader=FramedReader(control_rx,slot,incarnation,inbox,'control')
 return dict(slot=slot,process=p,commands=cmd_tx,hints=hint_tx,result_reader=r,control_reader=control_reader,incarnation=incarnation,gpu=gpu,pid=p.pid,start_ticks=start_ticks(p.pid))
def start_ticks(pid):
 path=pathlib.Path('/proc')/str(pid)/'stat'
 return int(path.read_text().rsplit(')',1)[1].split()[19]) if path.exists() else None
def stop_worker(w,*,force=False):
 p=w['process'];requested=time.perf_counter()
 if p.is_alive():
  if force:
   if w['start_ticks'] is not None and start_ticks(p.pid)!=w['start_ticks']:raise RuntimeError('PID identity changed before fail-stop')
   os.kill(p.pid,signal.SIGKILL) if hasattr(signal,'SIGKILL') else p.kill()
  else:
   try:w['commands'].send(None)
   except (EOFError,OSError):pass
 p.join(10)
 if p.is_alive():p.kill();p.join(10)
 if p.is_alive() or p.exitcode is None:raise RuntimeError('worker ownership not physically terminated')
 for k in ('commands','hints'):
  try:w[k].close()
  except OSError:pass
 for k in ('result_reader','control_reader'):w[k].thread.join(5)
 return dict(slot=w['slot'],pid=p.pid,start_ticks=w['start_ticks'],exitcode=p.exitcode,confirmed_dead=True,confirmed_exit=True,requested_perf=requested,confirmed_perf=time.perf_counter(),incarnation=w['incarnation'],result_channel_closed=w['result_reader'].closed,control_channel_closed=w['control_reader'].closed,partial_frame_thread_blocked=w['result_reader'].thread.is_alive())
def wait_cuda_release(gpu,old_pid,timeout=20):
 begun=time.perf_counter()
 while True:
  pids=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True)
  used=subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip()
  if str(old_pid) not in [r.strip() for r in pids.splitlines()] and float(used)<128:return dict(gpu=gpu,old_pid=old_pid,gpu_context_released=True,observed_perf=time.perf_counter(),memory_used_MiB=float(used))
  if time.perf_counter()-begun>timeout:raise RuntimeError('old CUDA owner not released; slot cannot be reused')
  time.sleep(.05)

