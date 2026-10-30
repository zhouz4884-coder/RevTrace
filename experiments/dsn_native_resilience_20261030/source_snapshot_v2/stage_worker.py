"""Isolated original full replica or protected ASR stage, fixed native assets."""
import os,pathlib,hashlib,json,time,traceback,collections,sys,importlib.metadata

def worker_main(name,gpu,mode,settings,commands,results,invalidations=None):
 try:
  cache=pathlib.Path(settings['cache_root'])
  for key,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
   p=cache/rel;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
  (cache/'xdg/torch/kernels').mkdir(parents=True,exist_ok=True)
  os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')
  import torch,numpy as np,soundfile as sf,random
  torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
  from candidate_bridge import CandidateBridge,KnownInvalidASRPrefix
  from feedback_contract import FeedbackCut
  from stage_packet import CandidatePacket
  begun=time.perf_counter();model=CandidateBridge(**settings['backend'],stage_role=mode,source_commit=settings['source_commit'],corrector_dtype=settings.get('corrector_dtype','float32'));loaded=time.perf_counter();audio={}
  for s in settings.get('model_sources',settings['sources']):
   p=pathlib.Path(s['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['audio_sha256'];a,sr=sf.read(p,dtype='float32');assert sr==16000 and a.ndim==1 and len(a)==s['frames'];audio[s['source_id']]=(a,s['audio_sha256'])
  warm=settings['warmup'];ws=next(s for s in settings.get('model_sources',settings['sources']) if s['source_id']==warm['source_id']);a,source_sha=audio[ws['source_id']];warm_start=model.rebind_warm_cut(warm['original_reference_start_state'],source_sha);warm_record=model.warm_neural_ready(audio=a,start=warm_start,end=32000)
  def dtypes(module):
   counts=collections.Counter()
   if module is not None and hasattr(module,'parameters'):
    for p in module.parameters():counts[str(p.dtype)]+=p.numel()
   return dict(counts)
  results.put(dict(kind='ready',worker=name,mode=mode,gpu=gpu,pid=os.getpid(),runtime_identity=model.runtime_identity,initials={sid:model.initial_for(h).state for sid,(_,h) in audio.items()},model_load_seconds=loaded-begun,full_load_warmup_seconds=time.perf_counter()-begun,neural_ready_warmup=warm_record,asr_parameter_dtypes=dtypes(model.engine.model),corrector_parameter_dtypes=dtypes(model.corrector_model),environment=dict(python=sys.version,executable=sys.executable,packages={k:importlib.metadata.version(k) for k in ('torch','transformers','peft','triton','numpy','soundfile')},autocast_enabled=torch.is_autocast_enabled(),TF32=False,CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'],PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),PYTORCH_ALLOC_CONF=os.environ.get('PYTORCH_ALLOC_CONF')),sent_perf=time.perf_counter()))
  invalid_hints={}
  observer=None
  if settings.get('record_state_telemetry',False):
   from state_telemetry import NativeStateObserver
   observer=NativeStateObserver(model.engine,emit=lambda row:results.control.send(dict(kind='state_telemetry',row=row)))
  while True:
   cmd=commands.get()
   if cmd is None:break
   job_begin=time.perf_counter()
   sid=cmd['source_id'];a,h=audio[sid];start=FeedbackCut(cmd['start']);assert start.state['contract']['source_sha']==h;kind=cmd['kind']
   invalid_hints.clear()
   if observer is not None:observer.bind(source_id=sid,job_id=cmd['job_id'],start_frontier=start.frontier,end_frontier=cmd['end'])
   def emit(event):event.update(worker=name,job_id=cmd['job_id'],source_id=sid,dispatch_epoch=cmd.get('dispatch_epoch'),wire_complete_perf=time.perf_counter(),sent_perf=time.perf_counter());results.put(event)
   def drain_known_hints():
    if invalidations is None:return
    import queue
    while True:
     try:hint=invalidations.get_nowait()
     except queue.Empty:break
     # This physical worker owns one call. Old hints cannot grant a later
     # call cancellation authority or accumulate for the stream's lifetime.
     if hint['job_id']==cmd['job_id']:invalid_hints[hint['job_id']]=hint
   def check_known_invalid():
    drain_known_hints()
    hint=invalid_hints.get(cmd['job_id'])
    if hint is not None:
     assert hint['source_id']==sid and hint['dispatch_epoch']==cmd['dispatch_epoch'] and hint['proof']
     raise KnownInvalidASRPrefix(hint['proof'])
   drain_known_hints()
   if kind=='full':
    try:cut,record=model.full_step(audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a),on_asr=emit if cmd.get('early_view',False) or cmd.get('capture_packet',False) else None,capture_required=cmd.get('capture_packet',False),before_corrector=check_known_invalid if invalidations is not None else None)
    except KnownInvalidASRPrefix as stopped:
     torch.cuda.synchronize();model.engine._clean_cache();torch.cuda.synchronize();invalid_hints.pop(cmd['job_id'],None);results.put(dict(kind='abandoned',worker=name,mode=mode,gpu=gpu,job_id=cmd['job_id'],dispatch_epoch=cmd.get('dispatch_epoch'),source_id=sid,start=start.state,target_end=cmd['end'],proof=stopped.proof,asr_prefix_executed=True,learned_C_executed=False,C_U_completed=False,feedback_cut_emitted=False,actual_cache_decoder_cleared=True,worker_job_begin_perf=job_begin,worker_job_end_perf=time.perf_counter(),sent_perf=time.perf_counter()));continue
   elif kind=='consume':cut,record=model.consume(packet=cmd['packet_wire'],audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a))
   elif kind=='project':
    projection=model.project_packet(packet=cmd['packet_wire'],audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a));cut=FeedbackCut(projection['end']);record=dict(projection,stage_execution='identity_tail_projection_only',native_model_evaluated=False)
   else:raise ValueError('unknown stage command')
   record.update(worker_job_begin_perf=job_begin,worker_job_end_perf=time.perf_counter(),worker_job_wall_seconds=time.perf_counter()-job_begin,learned_C_model_loaded=mode=='authority',stage_projection_is_not_learned_C=True)
   results.put(dict(kind='completed',worker=name,mode=mode,gpu=gpu,job_id=cmd['job_id'],dispatch_epoch=cmd.get('dispatch_epoch'),source_id=sid,start=start.state,end=cut.state,record=record,sent_perf=time.perf_counter()))
   invalid_hints.pop(cmd['job_id'],None)
  if observer is not None:observer.close()
  torch.cuda.synchronize();results.put(dict(kind='drained',worker=name,pid=os.getpid()))
 except BaseException:results.put(dict(kind='failed',worker=name,pid=os.getpid(),traceback=traceback.format_exc(),sent_perf=time.perf_counter()))
