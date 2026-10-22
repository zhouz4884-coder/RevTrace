"""Minimal surviving-supervisor feasibility harness. NOT a full serving runtime."""
from pathlib import Path
import copy,hashlib,json,multiprocessing as mp,os,queue,subprocess,sys,threading,time,uuid
from adoption_core import digest,semantic,inspect_adoption,install_result

def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def call(c,op,**args):
 c.send((op,args));ans=c.recv()
 if 'error' in ans:raise RuntimeError(ans['error'])
 return ans
def expected(state,template,jid):
 from revtrace.dgft import digest_tokens
 j=copy.deepcopy(template);j.update(job_id=jid,parent=state.checkpoint_id,parent_prompt_digest=digest_tokens(state.prompt_tokens),prompt_tokens=list(state.prompt_tokens),audio_start_sample=state.audio_frontier_window,chunk_id=state.audio_frontier_window//32000,chunk_advance=template['end_window']-state.audio_frontier_window//32000)
 return j
def publish_certified(out,config,state,event,result,recovered):
 from revtrace.certified_display import RealtimeConsumer,text_sha
 from revtrace.dgft import digest_tokens
 t0=time.perf_counter();consumer=RealtimeConsumer(Path(out)/'consumer.jsonl','snapshot',strict_bound=True)
 consumer.put({'kind':'run-start','time':0.,'t0_perf':t0,'contract_digest':config['contract_digest']})
 if not recovered:
  consumer.put({'kind':'commit','time':time.perf_counter()-t0,'session_id':0,'version':state.checkpoint_id,'segment_id':event['segment_id'],'audio_end_sample':state.audio_frontier_window,'next_prompt_tokens':list(state.prompt_tokens),'certificate':event['certificate']})
 stamp=time.perf_counter()-t0
 consumer.put({'kind':'canonical-display','time':stamp,'session_id':0,'version':state.checkpoint_id,'canonical_version':state.checkpoint_id,'display_revision':1,'displayed':stamp,'text':result['text'],'audio_end_sample':state.audio_frontier_window,'transaction_id':event['segment_id'],'contract_digest':config['contract_digest'],'contract_epoch':state.contract_epoch,'canonical_projection_sha256':digest_tokens(state.prompt_tokens),'canonical_Z_sha256':digest_tokens(result['token_ids']),'text_sha256':text_sha(result['text']),'recovered':recovered})
 consumer.close();views=[json.loads(l) for l in (Path(out)/'consumer.jsonl').read_text().splitlines()];assert views and views[-1]['certified_text']==result['text'];return views
def coordinator(conn,config,out,method,old):
 sys.path[:0]=[config['sdk']+'/src',config['sdk']+'/scripts']
 from revtrace.dgft import FeedbackTransactionState,digest_tokens
 from revtrace.durable_journal import DurableCommitJournal
 from revtrace.certified_display import RealtimeConsumer,replay_bound_text,text_sha
 from dataclasses import asdict
 out=Path(out);started=time.perf_counter();initial=FeedbackTransactionState(0,1,'coarse',contract_digest=config['contract_digest'],canonical_runtime_digest=config['runtime_digest'])
 t=time.perf_counter();journal=DurableCommitJournal(out/'ledger.wal',[initial]);ledger=time.perf_counter()-t;state=journal.states()[0]
 call(conn,'owner',epoch=state.contract_epoch,pid=os.getpid())
 if state.audio_frontier_window>=config['template']['audio_end_sample']:
  event=[e for e in journal.events() if e.get('event')=='canonical-segment-committed'][-1]
  call(conn,'replay_validate',event=event)
  result={'token_ids':state.stable_token_segments[-1],'state_tokens':state.prompt_tokens,'text':event['committed_text']};adopted=False;recovered=True
 else:
  j=expected(state,config['template'],('old' if old else 'new')+'-e'+str(state.contract_epoch))
  if old or method!='adopt':
   handle=call(conn,'dispatch',job=j,epoch=state.contract_epoch)['handle']
  else:
   handle=call(conn,'old_handle')['handle']
  record=call(conn,'wait',handle=handle)['record']
  if not old and method=='adopt':
   reason=inspect_adoption(state,j,record,manifest_digest=config['manifest_sha256'],worker_live=record['worker_live'],supervisor_id=config['supervisor_id'],worker_incarnation=record['current_worker_incarnation'],owner_epoch=state.contract_epoch)
   if reason!='eligible-for-new-epoch-authorization':raise ValueError('adoption refused '+reason)
  else:
   assert record['dispatch_epoch']==state.contract_epoch and semantic(record['job'])==semantic(j)
   assert digest(record['job'])==record['job_sha256'] and digest(record['result'])==record['result_sha256'] and record['worker_live']
  result=record['result'];binding=call(conn,'render',job=j,handle=handle)['binding']
  state,event,sequence,sync=install_result(journal,state,j,result,binding)
  adopted=not old and method=='adopt';recovered=False
  if old:
   save(out/'WAL_DURABLE_BEFORE_PUBLICATION.json',{'time':time.perf_counter(),'pid':os.getpid(),'epoch':state.contract_epoch,'version':state.checkpoint_id})
   while True:time.sleep(.02)
 views=publish_certified(out,config,state,event,result,recovered);journal.close()
 save(out/'new_coordinator.json',{'state':asdict(state),'Z':list(result['token_ids']),'P':list(result['state_tokens']),'text':result['text'],'ledger_recovery_seconds':ledger,'coordinator_started':started,'first_certified_consumer_perf':views[0]['observed_perf'],'adopted':adopted,'recovered_without_generation':recovered,'completed':time.perf_counter()})
 conn.send({'done':True})

class Power:
 def __init__(self):self.rows=[];self.stopflag=threading.Event();self.thread=None
 def start(self):
  def loop():
   while not self.stopflag.is_set():
    s=subprocess.check_output(['nvidia-smi','--id=1','--query-gpu=power.draw,memory.used','--format=csv,noheader,nounits'],text=True);p,m=map(float,s.strip().split(','));self.rows.append({'time':time.perf_counter(),'watts':p,'MiB':m});self.stopflag.wait(.1)
  self.thread=threading.Thread(target=loop,daemon=True);self.thread.start()
 def close(self):self.stopflag.set();self.thread.join()
 def integral(self,a,b):
  e=0.
  for x,y in zip(self.rows,self.rows[1:]):
   l=max(a,x['time']);r=min(b,y['time'])
   if r<=l:continue
   def w(t):return x['watts']+(y['watts']-x['watts'])*(t-x['time'])/(y['time']-x['time'])
   e+=(w(l)+w(r))*.5*(r-l)
  return e

def trial(B,P,O,base,method,phase,repeat):
 sys.path[:0]=[base['sdk']+'/src',base['sdk']+'/scripts']
 from tc_live_worker import GPUExecutor
 from revtrace.certified_display import TrustedQwenRender,validate_bound_text,replay_bound_text
 from transformers import AutoProcessor,GenerationConfig
 from qwen_asr import parse_asr_output
 config=copy.deepcopy(base);config['supervisor_id']=uuid.uuid4().hex
 out=O/f'{phase}-{method}-r{repeat}';out.mkdir();save(out/'config.json',config|{'method':method,'phase':phase,'repeat':repeat})
 processor=AutoProcessor.from_pretrained(config['model'],local_files_only=True);eos=GenerationConfig.from_pretrained(config['model'],local_files_only=True).eos_token_id
 renderer=TrustedQwenRender(processor.tokenizer,parse_asr_output,[eos] if isinstance(eos,int) else eos,256)
 worker=None;children=[];conn=None;old_handle=None;current=None;records={};pending=[];waiting=[];tele=[];incarnation=uuid.uuid4().hex;fault=None;new=None;old=None;new_started=False
 power=Power();power.start();initialized=time.perf_counter();cold_init=0.
 def start_worker():
  nonlocal worker,incarnation,cold_init
  t=time.perf_counter();worker=GPUExecutor('audit-authority-1',config['worker_config']);worker.wait_ready();incarnation=uuid.uuid4().hex;return time.perf_counter()-t
 def spawn(is_old):
  a,b=mp.get_context('spawn').Pipe();p=mp.get_context('spawn').Process(target=coordinator,args=(b,config,str(out),method,is_old),name='audit-coordinator-only');p.start();b.close();children.append(p);return p,a
 initial_init=start_worker();lease=1
 if config.get('nonempty_parent'):
  from revtrace.dgft import FeedbackTransactionState
  from revtrace.durable_journal import DurableCommitJournal
  initial=FeedbackTransactionState(0,1,'coarse',contract_digest=config['contract_digest'],canonical_runtime_digest=config['runtime_digest'])
  seed=expected(initial,config['seed_template'],'seed-parent');worker.submit([seed]);seedresult=None
  while seedresult is None:
   got=worker.poll();worker.drain_telemetry()
   if got is not None:assert len(got)==1;seedresult=got[0]
   time.sleep(.001)
  binding=validate_bound_text(renderer,seed,seedresult)
  with DurableCommitJournal(out/'ledger.wal',[initial]) as wal:
   seeded,event,seq,sync=install_result(wal,initial,seed,seedresult,binding)
  save(out/'SEED_PARENT.json',{'job':seed,'result':seedresult,'state_checkpoint':seeded.checkpoint_id,'state_P':list(seeded.prompt_tokens),'state_F':seeded.audio_frontier_window})
  lease=2 # old coordinator opens a nonempty WAL and appends its restart epoch
 old,conn=spawn(True);old_pid=old.pid;deadline=time.perf_counter()+180
 try:
  while True:
   if time.perf_counter()>deadline:raise TimeoutError('bounded trial timeout')
   if worker is not None:
    result=worker.poll()
    for t in worker.drain_telemetry():tele.append(t)
    if result is not None:
     assert current is not None and len(result)==1
     records[current]['result']=copy.deepcopy(result[0]);records[current]['result_sha256']=digest(result[0]);records[current]['completed_received']=time.perf_counter();current=None
    if current is None and pending:
     handle=pending.pop(0);current=handle;worker.submit([records[handle]['job']])
   if conn.poll():
    try:message=conn.recv()
    except EOFError:
     if not new_started:raise RuntimeError('old coordinator exited before planned fault')
     message=None
    if message and isinstance(message,dict) and message.get('done'):
     new.join(timeout=5);assert new.exitcode==0;break
    if message:
     op,args=message
     if op=='owner':assert args['epoch']==lease and args['pid']==(new.pid if new_started else old.pid);conn.send({'ok':True})
     elif op=='dispatch':
      assert args['epoch']==lease;handle=uuid.uuid4().hex;j=copy.deepcopy(args['job']);records[handle]={'job':j,'job_sha256':digest(j),'result':None,'dispatch_epoch':lease,'supervisor_id':config['supervisor_id'],'worker_incarnation':incarnation,'manifest_digest':config['manifest_sha256'],'source_role':'authority'};pending.append(handle)
      if old_handle is None:old_handle=handle
      conn.send({'handle':handle})
     elif op=='old_handle':conn.send({'handle':old_handle})
     elif op=='wait':waiting.append((conn,args['handle']))
     elif op=='render':
      r=records[args['handle']];assert r['result'] is not None and semantic(r['job'])==semantic(args['job']);binding=validate_bound_text(renderer,args['job'],r['result']);conn.send({'binding':binding})
     elif op=='replay_validate':replay_bound_text(renderer,args['event']);conn.send({'ok':True})
     else:raise ValueError(op)
   # Supervisor retains source records while only its coordinator is killed.
   should_kill=not new_started and old_handle is not None and (
     (phase=='running' and any(t['kind']=='model-started' for t in tele)) or
     (phase=='completed' and records[old_handle]['result'] is not None) or
     (phase=='wal' and (out/'WAL_DURABLE_BEFORE_PUBLICATION.json').exists()))
   if should_kill:
    assert old.pid==old_pid and old.is_alive();fault=time.perf_counter();old.kill();old.join(timeout=5);assert old.exitcode==-9
    conn.close();waiting=[];lease+=1
    if method=='cold':
     worker.process.terminate();worker.process.join(timeout=10);assert not worker.process.is_alive();worker=None;current=None;pending=[]
     if phase!='wal':cold_init=start_worker()
    new,conn=spawn(False);new_started=True
   keep=[]
   for channel,handle in waiting:
    # Leave old pre-commit result unread in the completed-fault condition.
    if not new_started and phase=='completed':keep.append((channel,handle));continue
    if records[handle]['result'] is None:keep.append((channel,handle));continue
    r=copy.deepcopy(records[handle]);r['worker_live']=worker is not None and worker.process.is_alive();r['current_worker_incarnation']=incarnation
    channel.send({'record':r})
   waiting=keep
   if new_started and not new.is_alive() and not (out/'new_coordinator.json').exists():raise RuntimeError('recovery coordinator failed')
   time.sleep(.001)
  finished=json.loads((out/'new_coordinator.json').read_text());assert fault is not None and finished['first_certified_consumer_perf']>=fault
  oldrec=records[old_handle];oldresult=oldrec.get('result');model_completed=None if oldresult is None else oldresult.get('model_completed_perf')
  result={'status':'COMPLETE_BOUNDED_GPU_FEASIBILITY','method':method,'phase':phase,'repeat':repeat,'fault_perf':fault,'old_coordinator_pid':old_pid,'worker_pid_after':None if worker is None else worker.process.pid,'initial_worker_init_seconds':initial_init,'recovery_worker_init_seconds':cold_init,'ledger_recovery_seconds':finished['ledger_recovery_seconds'],'first_certified_consumer_RTO':finished['first_certified_consumer_perf']-fault,'old_job_remaining_GPU_model_seconds':None if model_completed is None else max(0,model_completed-fault),'old_job_remaining_scope':'CENSORED if cold killed before completion; not inferred from another run','dispatches':len(records),'completed_GPU_generations':sum(r['result'] is not None for r in records.values()),'adopted':finished['adopted'],'restored_WAL_without_generation':finished['recovered_without_generation'],'Z':finished['Z'],'P':finished['P'],'text':finished['text'],'recovery_GPU_energy_J':power.integral(fault,finished['first_certified_consumer_perf']),'GPU_peak_MiB':max(r['MiB'] for r in power.rows),'supervisor_id':config['supervisor_id'],'source_trust':'local trusted supervisor and actual worker queues, not GPU attestation','normal_registered_job_bytes':len(json.dumps(oldrec['job']).encode())}
  save(out/'result.json',result);save(out/'SUPERVISOR_RECORDS.json',{'records':records,'telemetry':tele});return result
 finally:
  power.close();save(out/'power.json',power.rows)
  for p in children:
   if p.is_alive():p.terminate();p.join(timeout=5)
  if worker is not None:worker.close()

def main():
 B=Path(sys.argv[1]);P=B/'projects/revtrace_opportunity_20261022';nonempty=len(sys.argv)>2 and sys.argv[2]=='nonempty';O=B/'results/revtrace/opportunity_20261022'/('B_gpu_nonempty' if nonempty else 'B_gpu_v3');O.mkdir(exist_ok=True)
 if nonempty:assert json.loads((B/'results/revtrace/opportunity_20261022/B_gpu_v2/SUMMARY.json').read_text())['all_Z_P_text_same_input_oracles_equal']
 assert not list(O.glob('*/result.json')),'Refuse duplicate matrix'
 sys.path[:0]=[str(B/'projects/revtrace_phaseD_20261021/continuity_v6/src'),str(B/'projects/revtrace_phaseD_20261021/continuity_v6/scripts')]
 import qwen_asr,numpy as np,soundfile as sf,torch,transformers
 from revtrace.dgft import digest_tokens
 prior=json.loads((B/'results/revtrace/phaseD_20261021/R2_transfer/coarse-keep1-two_lane-c4-staggered-r0/config.json').read_text());rt=copy.deepcopy(prior['authority_runtime']);rt['microbatch']=1
 mf=B/'datasets/revtrace/phaseD_20261021/manifest.json';manifest=json.loads(mf.read_text());row=manifest['sessions'][0];audio,rate=sf.read(row['path'],dtype='float32');assert rate==16000;audio=np.asarray(audio,dtype='<f4');assert hashlib.sha256(audio.tobytes()).hexdigest()==row['audio_sha256']
 C={'study':'RESEARCH_OPPORTUNITY_B_ONLY','policy':'coarse','authority_runtime':rt,'fine_seconds':2,'rho':3,'sample_rate':16000,'manifest_sha256':hashlib.sha256(mf.read_bytes()).hexdigest(),'scope':'single Authority job, not complete service'};Csha=digest(C);Rsha=digest(rt);now=time.perf_counter();a=hashlib.sha256(audio[:96000].tobytes()).hexdigest()
 worker={**rt,'model':str(B/'models/Qwen3-ASR-1.7B'),'manifest':str(mf),'gpu':1,'dtype':'float32','runtime_digest':Rsha,'capture_model_inputs':True,'lifecycle_instrumentation':True}
 base={'sdk':str(B/'projects/revtrace_phaseD_20261021/continuity_v6'),'model':str(B/'models/Qwen3-ASR-1.7B'),'contract':C,'contract_digest':Csha,'runtime_digest':Rsha,'manifest_sha256':C['manifest_sha256'],'worker_config':worker,'template':{'session_id':0,'role':'authority','source_id':row['source_id'],'language':row['language'],'audio_start_sample':0,'audio_end_sample':96000,'parent':0,'parent_prompt_digest':digest_tokens([]),'prompt_tokens':[],'chunk_id':0,'chunk_advance':3,'end_window':3,'prefix_audio_sha256':a,'interval_audio_sha256':a,'contract_digest':Csha,'runtime_digest':Rsha,'audio_ready_perf':now,'enqueue_perf':now}}
 if nonempty:
  base['nonempty_parent']=True;base['seed_template']=copy.deepcopy(base['template']);base['template'].update(audio_end_sample=192000,end_window=6,prefix_audio_sha256=hashlib.sha256(audio[:192000].tobytes()).hexdigest(),interval_audio_sha256=hashlib.sha256(audio[96000:192000].tobytes()).hexdigest())
 save(O/'FROZEN_CONFIG.json',base);save(O/'ENVIRONMENT.json',{'torch':torch.__version__,'transformers':transformers.__version__,'python':sys.version,'hardware':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.total','--format=csv,noheader'],text=True),'code_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),P/'adoption_core.py']}})
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 rows=[]
 try:
  for repeat in range(2):
   for phase in (['completed'] if nonempty else ['running','completed','wal']):
    methods=['strict','adopt'] if repeat==0 else ['adopt','strict']
    if not nonempty:methods=['cold','strict','adopt'] if repeat==0 else ['adopt','strict','cold']
    for method in methods:
     r=trial(B,P,O,base,method,phase,repeat);rows.append(r);save(O/'PROGRESS.json',{'completed':len(rows),'expected':4 if nonempty else 18,'last':f'{phase}-{method}-r{repeat}'});print(json.dumps({k:r[k] for k in ['phase','method','repeat','first_certified_consumer_RTO','dispatches','adopted']}),flush=True)
  assert len({digest({k:r[k] for k in ['Z','P','text']}) for r in rows})==1,'same-input legal oracle changed'
  save(O/'SUMMARY.json',{'status':'COMPLETE_4_NONEMPTY_PARENT_GPU_TRIALS' if nonempty else 'COMPLETE_18_GPU_FEASIBILITY_TRIALS','rows':rows,'all_Z_P_text_same_input_oracles_equal':True,'not_complete_system':True})
 except BaseException as e:save(O/'STOP.json',{'error':repr(e),'completed':len(rows)});raise
if __name__=='__main__':main()
