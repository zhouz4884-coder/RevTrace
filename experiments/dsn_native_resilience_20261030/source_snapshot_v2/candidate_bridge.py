"""Original native full call and protected already-ready candidate consumption."""
import pathlib,inspect,time,json,copy,hashlib,dataclasses,types
from native_bridge import NativeBridge,export_cut,restore_cut,identity_prediction
from feedback_contract import FeedbackCut
from stage_packet import CandidatePacket,capture_packet,restore_open,input_key,AUTHOR_SHA,cfg_value,canonical

class KnownInvalidASRPrefix(RuntimeError):
 def __init__(self,proof):self.proof=proof;super().__init__('owned full call has a controller-proven invalid dependency before C')

class CandidateBridge(NativeBridge):
 def __init__(self,*,stage_role,source_commit,corrector_dtype='float32',**backend):
  assert stage_role in ('authority','protected_asr_stage');self.stage_role=stage_role;self.execution_source=source_commit
  contract=copy.deepcopy(backend['contract']);contract['stage_execution']=dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype=corrector_dtype,source_commit=source_commit)
  backend=dict(backend,contract=contract);super().__init__(**backend,role='authority' if stage_role=='authority' else 'private',corrector_dtype=corrector_dtype)
  self.author_file=pathlib.Path(backend['author_root'])/'simul_whisper/simul_whisper.py';assert hashlib.sha256(self.author_file.read_bytes()).hexdigest()==AUTHOR_SHA
  self.runtime_identity=dict(source_commit=source_commit,author_sha256=AUTHOR_SHA,contract=self.contract,asr_config=cfg_value(self.engine.cfg))
  from native_tail import compile_original_tail
  self.compiled_tail=compile_original_tail(self.author_file,expected_sha256=AUTHOR_SHA)
 def key(self,*,audio,start,end,is_last):return input_key(start,audio=audio,end=end,is_last=is_last,runtime_identity=self.runtime_identity)
 def full_step(self,*,audio,start,end,is_last,on_asr=None,capture_required=False,before_corrector=None):
  original=self.engine._run_SpeechLM_error_corrector;key=self.key(audio=audio,start=start,end=end,is_last=is_last)
  def boundary(*args,**kwargs):
   frame=inspect.currentframe().f_back
   assert frame.f_code.co_name=='infer' and pathlib.Path(frame.f_code.co_filename).resolve()==self.author_file.resolve()
   if before_corrector is not None:before_corrector()
   capture_begin=time.perf_counter();packet=capture_packet(self.engine,key_json=key,caller_locals=frame.f_locals) if capture_required else None;captured=time.perf_counter()
   projection=self.project_open(caller_locals=frame.f_locals,start=start,end=end);projected=time.perf_counter()
   del frame
   wire=packet.wire() if packet is not None else None;serialized=time.perf_counter()
   event=dict(kind='candidate' if packet is not None else 'asr_early',producer_role=self.stage_role,start_state_sha=start.sha256,start_state=start.state,end_frontier=end,is_last=is_last,provisional_text=projection['end']['transcript'],provisional_appended_token_ids=projection['token_ids'],projection=projection,produced_perf=serialized,candidate_wire=wire,packet_capture_seconds=captured-capture_begin,identity_projection_seconds=projected-captured,wire_serialization_seconds=serialized-projected)
   if on_asr is not None:on_asr(event)
   return original(*args,**kwargs)
  if capture_required or on_asr is not None or before_corrector is not None:self.engine._run_SpeechLM_error_corrector=boundary
  try:cut,record=super().step(audio=audio,start=start,end=end,is_last=is_last)
  finally:self.engine._run_SpeechLM_error_corrector=original
  record.update(producer_role=self.stage_role,stage_execution='original_full_infer',authority_ASR_executed=self.stage_role=='authority',protected_ASR_executed=True,candidate_handoff=False)
  return cut,record
 def _projection_engine(self):
  e=copy.copy(self.engine);e.context=copy.copy(self.engine.context);e.inference=copy.copy(self.engine.inference);e.token_decoder=copy.copy(self.engine.token_decoder)
  e._run_SpeechLM_error_corrector=types.MethodType(identity_prediction,e);return e
 def _run_projection(self,e,local,start,end):
  from native_tail import run_identity_tail
  wall=time.time();local.update(corrector_model=object(),corrector_processor=None,start_time=wall,infer_start_time=wall,t_before_decoding=wall)
  ids,g=run_identity_tail(e,local,compiled=self.compiled_tail);text=e.tokenizer.decode(ids);cut=export_cut(e,frontier=end,transcript=start.transcript+text,contract=start.state['contract'])
  return dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,original_full_infer_completed=False,token_ids=list(ids),end=cut.state,end_state_sha=cut.sha256)
 def project_open(self,*,caller_locals,start,end):
  import torch,numpy as np
  from stage_packet import ENGINE_FIELDS,SEMANTIC_LOCALS
  def clone(x):
   if torch.is_tensor(x):return x.detach().clone()
   if isinstance(x,np.ndarray):return np.array(x,copy=True)
   if isinstance(x,dict):return {k:clone(v) for k,v in x.items()}
   if isinstance(x,list):return [clone(v) for v in x]
   if isinstance(x,tuple):return tuple(clone(v) for v in x)
   if type(x).__module__.endswith('generation_progress'):
    if type(x).__name__=='Logits':return {'diagnostic_elision':'Logits','shape':list(x.tokens.shape),'dtype':str(x.tokens.dtype)}
    y=copy.copy(x);y.tokens=clone(x.tokens);return y
   return copy.copy(x)
  e=self._projection_engine()
  for k in ENGINE_FIELDS:setattr(e,k,clone(getattr(self.engine,k)))
  e.context.text=self.engine.context.text;e.context.prefix_token_ids=list(self.engine.context.prefix_token_ids)
  local={k:clone(caller_locals[k]) for k in SEMANTIC_LOCALS}
  return self._run_projection(e,local,start,end)
 def project_packet(self,*,packet,audio,start,end,is_last):
  packet=CandidatePacket.from_wire(packet) if isinstance(packet,bytes) else packet;e=self._projection_engine();local=restore_open(e,packet,expected_key=self.key(audio=audio,start=start,end=end,is_last=is_last));return self._run_projection(e,local,start,end)
 def consume(self,*,packet,audio,start,end,is_last):
  import torch
  from native_tail import run_tail
  assert self.stage_role=='authority';decode_begin=time.perf_counter();packet=CandidatePacket.from_wire(packet) if isinstance(packet,bytes) else packet;decoded=time.perf_counter()
  torch.cuda.synchronize();begin=time.perf_counter();wall=time.time();expected=self.key(audio=audio,start=start,end=end,is_last=is_last)
  local=restore_open(self.engine,packet,expected_key=expected);local.update(corrector_model=self.corrector_model,corrector_processor=self.corrector_processor,start_time=wall,infer_start_time=wall,t_before_decoding=wall);torch.cuda.synchronize();restored=time.perf_counter()
  with torch.no_grad():ids,g=run_tail(self.engine,local,compiled=self.compiled_tail)
  torch.cuda.synchronize();finished=time.perf_counter();text=self.engine.tokenizer.decode(ids);cut=export_cut(self.engine,frontier=end,transcript=start.transcript+text,contract=start.state['contract']);correction=g.get('error_corrector');before=correction['candidates'][0] if correction else None;chosen=(correction['previous_transcription']+correction['corrected_appended_text']).strip() if correction else None
  record=dict(role='authority',producer_role='authority',start=start.frontier,end=end,is_last=is_last,start_state=start.sha256,end_state=cut.sha256,token_ids=list(ids),text=text,selected_correction=correction,selection_changed=before!=chosen if correction else None,top1_full_text=before,selected_full_text=chosen,model_start=begin,model_end=finished,model_seconds=finished-begin,author_start_time_wall=wall,clock_domains=dict(service_and_model='perf_counter',author_telemetry='time.time'),inference='mechanically extracted original C/U tail after protected complete input match',native_model_evaluated=True,authority_ASR_executed=False,protected_ASR_executed=True,candidate_handoff=True,candidate_payload_sha256=packet.payload_sha256,candidate_key_sha256=hashlib.sha256(packet.key_json.encode()).hexdigest(),debug_logits_values_elided=True,physical_early_exit=False)
  record.update(wire_decode_verify_seconds=decoded-decode_begin,input_match_open_restore_seconds=restored-begin,original_C_U_tail_seconds=finished-restored)
  return cut,record
 def rebind_warm_cut(self,old_cut,source_sha):
  state=copy.deepcopy(old_cut);state['contract']=dict(self.contract,source_sha=source_sha);return FeedbackCut(state)
 def warm_neural_ready(self,*,audio,start,end=32000):
  begun=time.perf_counter();cut,row=self.full_step(audio=audio,start=start,end=end,is_last=False)
  if self.stage_role=='authority':assert row['selected_correction'] is not None,'fixed 1.5 to 2.0s warmup failed to execute original neural C; do not replace the warmup input'
  # Warmup predictions/packets are never published or admitted. Reset feedback
  # and telemetry to genesis, retaining only fixed loaded neural runtime caches.
  genesis=self.initial_for(start.state['contract']['source_sha']);restore_cut(self.engine,genesis,audio=audio,contract=genesis.state['contract']);self.engine.first_token_generated=False;self.engine.first_token_latency=None
  return dict(seconds=time.perf_counter()-begun,original_record=row,neural_C_confirmed=row['selected_correction'] is not None if self.stage_role=='authority' else None,ASR_only_producer=self.stage_role=='protected_asr_stage',fixed_warm_start=24000,fixed_warm_end=end,reset_to_genesis=True,warmup_packet_admitted=False)

def semantic_packet_signature(packet):
 """Exact captured semantic comparison, excluding declared telemetry clocks."""
 p=copy.deepcopy(packet.verify());p.pop('created_perf',None)
 for k in ('first_token_generated','first_token_latency'):p['engine'].pop(k,None)
 p['locals']['generation'].pop('first_token_latency',None)
 return hashlib.sha256(canonical(dict(key=json.loads(packet.key_json),payload=p)).encode()).hexdigest()
