"""Isolated original full replica or protected ASR stage, fixed native assets."""
import os,pathlib,hashlib,json,time,traceback,collections,sys,importlib.metadata

def worker_main(name,gpu,mode,settings,commands,results):
 try:
  cache=pathlib.Path(settings['cache_root'])
  for key,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
   p=cache/rel;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
  (cache/'xdg/torch/kernels').mkdir(parents=True,exist_ok=True)
  os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')
  import torch,numpy as np,soundfile as sf,random
  torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
  from candidate_bridge import CandidateBridge
  from feedback_contract import FeedbackCut
  from stage_packet import CandidatePacket
  begun=time.perf_counter();model=CandidateBridge(**settings['backend'],stage_role=mode,source_commit=settings['source_commit'],corrector_dtype=settings.get('corrector_dtype','float32'));loaded=time.perf_counter();audio={}
  for s in settings['sources']:
   p=pathlib.Path(s['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['audio_sha256'];a,sr=sf.read(p,dtype='float32');assert sr==16000 and a.ndim==1 and len(a)==s['frames'];audio[s['source_id']]=(a,s['audio_sha256'])
  warm=settings['warmup'];ws=next(s for s in settings['sources'] if s['source_id']==warm['source_id']);a,source_sha=audio[ws['source_id']];warm_start=model.rebind_warm_cut(warm['original_reference_start_state'],source_sha);warm_record=model.warm_neural_ready(audio=a,start=warm_start,end=32000)
  def dtypes(module):
   counts=collections.Counter()
   if module is not None and hasattr(module,'parameters'):
    for p in module.parameters():counts[str(p.dtype)]+=p.numel()
   return dict(counts)
  results.put(dict(kind='ready',worker=name,mode=mode,gpu=gpu,pid=os.getpid(),runtime_identity=model.runtime_identity,initials={sid:model.initial_for(h).state for sid,(_,h) in audio.items()},model_load_seconds=loaded-begun,full_load_warmup_seconds=time.perf_counter()-begun,neural_ready_warmup=warm_record,asr_parameter_dtypes=dtypes(model.engine.model),corrector_parameter_dtypes=dtypes(model.corrector_model),environment=dict(python=sys.version,executable=sys.executable,packages={k:importlib.metadata.version(k) for k in ('torch','transformers','peft','triton','numpy','soundfile')},autocast_enabled=torch.is_autocast_enabled(),TF32=False,CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES']),sent_perf=time.perf_counter()))
  while True:
   cmd=commands.get()
   if cmd is None:break
   sid=cmd['source_id'];a,h=audio[sid];start=FeedbackCut(cmd['start']);assert start.state['contract']['source_sha']==h;kind=cmd['kind']
   def emit(event):event.update(worker=name,job_id=cmd['job_id'],source_id=sid,sent_perf=time.perf_counter());results.put(event)
   if kind=='full':cut,record=model.full_step(audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a),on_asr=emit if cmd.get('early_view',False) or cmd.get('capture_packet',False) else None,capture_required=cmd.get('capture_packet',False))
   elif kind=='consume':cut,record=model.consume(packet=cmd['packet_wire'],audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a))
   elif kind=='project':
    projection=model.project_packet(packet=cmd['packet_wire'],audio=a,start=start,end=cmd['end'],is_last=cmd['end']==len(a));cut=FeedbackCut(projection['end']);record=dict(projection,stage_execution='identity_tail_projection_only',native_model_evaluated=False)
   else:raise ValueError('unknown stage command')
   results.put(dict(kind='completed',worker=name,mode=mode,gpu=gpu,job_id=cmd['job_id'],source_id=sid,start=start.state,end=cut.state,record=record,sent_perf=time.perf_counter()))
  torch.cuda.synchronize();results.put(dict(kind='drained',worker=name,pid=os.getpid()))
 except BaseException:results.put(dict(kind='failed',worker=name,pid=os.getpid(),traceback=traceback.format_exc(),sent_perf=time.perf_counter()))
