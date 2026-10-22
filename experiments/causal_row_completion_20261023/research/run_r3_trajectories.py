"""Real singleton neural trajectories with declared normalization and censoring."""
from pathlib import Path
import hashlib,importlib.metadata,json,math,os,subprocess,sys,time

def main():
 B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
 D=O/'r3_gpu_v2';assert not D.exists();D.mkdir()
 sys.path[:0]=[str(P),str(P/'runtime/src'),str(P/'runtime/scripts')]
 from r3_core import quality,trajectory_summary,validate_runtime_manifest
 def read(p):return json.loads(p.read_text())
 def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
 def sha(p):
  with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
 code=read(P/'SOURCE_MANIFEST.json')
 for r in code['files']:assert sha(P/r['path'])==r['sha256']
 selection_path=O/'r3_source_v1/MANIFEST.json';source=read(selection_path);sessions=source['sessions']
 assert source['status']=='FROZEN_NATIVE_LONG_SOURCES' and len(sessions)==8
 runtime_manifest=dict(source,sessions=[dict(s,language='English') for s in sessions])
 validate_runtime_manifest(runtime_manifest)
 manifest_path=D/'RUNTIME_SOURCE_MANIFEST.json';save(manifest_path,runtime_manifest)
 coverage=read(O/'r3_coverage_v2/SUMMARY.json')
 assert coverage['all_sources_support_long_prefix'],'Do not pretend unsupported audio was consumed'
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 import numpy as np,soundfile as sf
 waves={}
 for s in sessions:
  wave,sr=sf.read(s['path'],dtype='float32');assert sr==16000 and hashlib.sha256(np.asarray(wave,dtype='<f4').tobytes()).hexdigest()==s['audio_sha256'];waves[s['source_id']]=wave
 old=B/'results/revtrace/online_admission_20261022'
 donor_data=read(B/'projects/revtrace_online_admission_20261022/DONORS.json')['donors']
 save(D/'RUN.json',{'experiment_id':'REVTRACE-R3-NATIVE-LONG-v2','source_commit':code['code_commit'],
  'source_selection_manifest_sha256':sha(selection_path),'runtime_manifest_sha256':sha(manifest_path),'protocol_sha256':sha(P/'R3_PRE_GPU_CLARIFICATIONS.md'),
  'v1_schema_failure_and_zero_trajectory_calls_retained':True,
  'subjects':8,'repeats':2,'families':['Qwen3-ASR-1.7B','Whisper-small.en'],'dtype':'float32',
  'physical_layout':'singleton per arm; alternating call order; fixed native audio',
  'evidence_tier':'controlled_neural_trajectories_not_deployed_serving',
  'fault':'one wrong-context neural call followed by declared-history field normalization, then actual consumption of resulting P',
  'Qwen_step_s':2,'Qwen_fault_window':6,'Whisper_step_s':10,'Whisper_fault_window':2,
  'per_window_quality':'partial hypothesis versus full reference diagnostic; only endpoint is full-source WER/CER',
  'source_ending_and_budget_limits_not_permanent_nonconvergence':True})
 all_cases=[];call_count=0;worker=None
 def record_call(name,j,result):
  nonlocal call_count
  call_count+=1;save(D/'calls'/f'{call_count:05d}-{name}.json',{'job':j,'result':result,'source_commit':code['code_commit']})
  return call_count
 (D/'calls').mkdir()
 def save_case(family,s,rep,windows,fault_window):
  summary=trajectory_summary(windows,fault_window)
  final=windows[-1]
  out={'family':family,'source_id':s['source_id'],'speaker':s['speaker'],'repeat':rep,
      'source_duration':s['duration'],'windows':windows,'summary':summary,
      'final_quality':final['quality'],'caps':[sum(w['caps'][i] for w in windows) for i in [0,1]],
      'endpoint_full_audio_supplied':True,'not_a_serving_or_natural_incidence_estimate':True}
  save(D/f'{family}-{s["source_id"]}-r{rep}.json',out);all_cases.append(out)
  save(D/'PROGRESS.json',{'cases':len(all_cases),'expected':32,'model_calls':call_count,'last':f'{family}-{s["source_id"]}-r{rep}'})
  print(f'{family} {s["source_id"]} r{rep}',flush=True)
 try:
  # Real old Worker on new native-source manifest, not a CPU reconstruction.
  from tc_live_worker import GPUExecutor
  cfg=read(old/'formal_v1/fine-sync16-clean-r0/config.json')['authority_runtime']
  for w in read(old/'FORMAL_FREEZE.json')['weights']:assert sha(B/'models/Qwen3-ASR-1.7B'/w['file'])==w['sha256']
  rt=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
  wc={**cfg,'gpu':1,'model':str(B/'models/Qwen3-ASR-1.7B'),'manifest':str(manifest_path),
      'runtime_digest':rt,'online_selection_mode':None,'capture_model_inputs':True,
      'lifecycle_instrumentation':True,'allow_execution_context_override':True}
  worker=GPUExecutor('r3-Qwen-native',wc);worker.wait_ready();save(D/'QWEN_WORKER.json',{'config':wc,'ready':worker.ready,'pid':worker.process.pid})
  for s in sessions:
   wave=waves[s['source_id']]
   for rep in range(2):
    hist=[[],[]];windows=[]
    for k in range(1,math.ceil(len(wave)/32000)+1):
     end=min(len(wave),k*32000);pair=[None,None];jobs=[None,None];ids=[None,None]
     for arm in ([0,1] if (rep+k)%2==0 else [1,0]):
      j={'job_id':f'r3-{s["source_id"]}-{rep}-{k}-{arm}','session_id':0,'source_id':s['source_id'],
       'role':'proposal','language':'English','parent':k-1,'prompt_tokens':list(hist[arm]),'chunk_id':k-1,
       'chunk_advance':1,'end_window':k,'audio_start_sample':(k-1)*32000,'audio_end_sample':end,
       'audio_ready_perf':0.,'enqueue_perf':time.perf_counter(),'runtime_digest':rt,'contract_digest':'R3-controlled-unprotected-history',
       'prefix_audio_sha256':hashlib.sha256(np.asarray(wave[:end],dtype='<f4').tobytes()).hexdigest()}
      if k==6 and arm==1:j['fault_actual_prompt_tokens']=donor_data[sessions.index(s)%len(donor_data)]['tokens']
      worker.submit([j]);start=time.perf_counter()
      while True:
       z=worker.poll();worker.drain_telemetry()
       if z is not None:break
       if time.perf_counter()-start>180:raise TimeoutError('R3 native operation exceeded bounded timeout')
       time.sleep(.001)
      z=z[0];expected=j.get('fault_actual_prompt_tokens',hist[arm])
      assert z['execution_context_audit']['executed_prompt_tokens']==list(expected)
      pair[arm]=z;jobs[arm]=j;ids[arm]=record_call('Qwen',j,z)
     hist=[p['state_tokens'] for p in pair]
     if k<6:assert hist[0]==hist[1] and pair[0]['token_ids']==pair[1]['token_ids'],'pre-fault same-input control diverged'
     windows.append({'window':k,'audio_end_s':end/16000,'calls':ids,
       'P_equal':hist[0]==hist[1],'Z_equal':pair[0]['token_ids']==pair[1]['token_ids'],'Y_equal':pair[0]['text']==pair[1]['text'],
       'P':hist,'Z':[p['token_ids'] for p in pair],'Y':[p['text'] for p in pair],
       'actual_input_IDs_equal':pair[0]['model_input_audit']['unpadded_input_ids']==pair[1]['model_input_audit']['unpadded_input_ids'],
       'quality':[quality(s['reference'],p['text']) for p in pair],
       'quality_scope':'endpoint-full-source' if end==len(wave) else 'partial-hypothesis-vs-full-reference-diagnostic',
       'caps':[p['hit_token_limit'] for p in pair]})
    save_case('Qwen',s,rep,windows,6)
  worker.close();worker=None
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'do not contend with another GPU task'
  # Exact explicit-prompt path used by actual Phase-D R5; no assumed truncation.
  import torch
  from transformers import WhisperProcessor,WhisperForConditionalGeneration,AutoProcessor
  from qwen_asr import parse_asr_output
  torch.set_num_threads(2)
  qtok=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).tokenizer
  raw=qtok.decode(donor_data[0]['tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
  _,wrong_history=parse_asr_output(raw,user_language='English');assert wrong_history
  path=B/'models/whisper-small.en';proc=WhisperProcessor.from_pretrained(path,local_files_only=True)
  weights=[p for p in path.iterdir() if p.suffix in ['.safetensors','.bin']]
  save(D/'WHISPER_MODEL_IDENTITY.json',{'files':[{'file':p.name,'sha256':sha(p)} for p in weights],
    'generation_config_sha256':sha(path/'generation_config.json'),'processor_path':'explicit get_prompt_ids'})
  model=WhisperForConditionalGeneration.from_pretrained(path,local_files_only=True,torch_dtype=torch.float32,attn_implementation='eager').to('cuda:0');model.eval()
  eos=model.generation_config.eos_token_id
  for s in sessions:
   wave=waves[s['source_id']]
   for rep in range(2):
    hist=['',''];windows=[]
    for k in range(1,math.ceil(len(wave)/160000)+1):
     start_sample=(k-1)*160000;end=min(len(wave),k*160000);pair=[None,None];ids=[None,None]
     for arm in ([0,1] if (rep+k)%2==0 else [1,0]):
      actual=wrong_history if k==2 and arm==1 else hist[arm]
      cpu=proc(wave[start_sample:end],sampling_rate=16000,return_tensors='pt').input_features
      features=cpu.to(model.device,model.dtype);seen=[]
      def hook(mod,args,kwargs):
       v=kwargs.get('decoder_input_ids')
       if not seen and v is not None:seen.append(v.detach().cpu().tolist())
      handle=model.register_forward_pre_hook(hook,with_kwargs=True)
      kw={'prompt_ids':proc.get_prompt_ids(actual,return_tensors='pt').to(model.device)} if actual else {}
      began=time.perf_counter()
      try:
       with torch.inference_mode():full=model.generate(features,do_sample=False,num_beams=1,temperature=0.,compression_ratio_threshold=None,logprob_threshold=None,no_speech_threshold=None,return_timestamps=False,max_new_tokens=128,return_dict_in_generate=True,**kw).sequences[0].detach().cpu().tolist()
      finally:handle.remove()
      assert seen and full[:len(seen[0][0])]==seen[0][0]
      Z=full[len(seen[0][0]):];assert 0<len(Z)<=128
      text=proc.tokenizer.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False).strip()
      projected=(hist[arm]+' '+text).strip()
      payload={'actual_conditioning_history':actual,'declared_history_before':hist[arm],
        'generation_started_perf':began,'generation_completed_perf':time.perf_counter(),
        'dtype':'float32','gpu':0,'max_new_tokens':128,
        'field_normalization_not_correct_parent_generation':k==2 and arm==1,
        'actual_first_decoder_ids':seen[0][0],'new_Z_excludes_copied_prefix':Z,
        'full_returned_tokens':full,'P':proc.get_prompt_ids(projected,return_tensors='pt').tolist(),
        'Y':projected,'new_text':text,'cap':len(Z)==128 and Z[-1]!=eos,
        'audio_sha256':hashlib.sha256(np.asarray(wave[start_sample:end],dtype='<f4').tobytes()).hexdigest(),
        'actual_cast_feature_sha256':hashlib.sha256(features.detach().cpu().contiguous().numpy().tobytes()).hexdigest()}
      pair[arm]=payload;ids[arm]=record_call('Whisper',{'source_id':s['source_id'],'window':k,'arm':arm,'repeat':rep},payload)
     hist=[p['Y'] for p in pair]
     if k<2:assert pair[0]['P']==pair[1]['P'] and pair[0]['new_Z_excludes_copied_prefix']==pair[1]['new_Z_excludes_copied_prefix']
     windows.append({'window':k,'audio_end_s':end/16000,'calls':ids,'P_equal':pair[0]['P']==pair[1]['P'],
       'Z_equal':pair[0]['new_Z_excludes_copied_prefix']==pair[1]['new_Z_excludes_copied_prefix'],'Y_equal':hist[0]==hist[1],
       'P':[p['P'] for p in pair],'Z':[p['new_Z_excludes_copied_prefix'] for p in pair],'Y':hist,
       'actual_input_IDs_equal':pair[0]['actual_first_decoder_ids']==pair[1]['actual_first_decoder_ids'],
       'quality':[quality(s['reference'],p['Y']) for p in pair],
       'quality_scope':'endpoint-full-source' if end==len(wave) else 'partial-hypothesis-vs-full-reference-diagnostic',
       'caps':[p['cap'] for p in pair]})
    save_case('Whisper',s,rep,windows,2)
  model.cpu();del model;torch.cuda.empty_cache()
  repeat_checks=[]
  for family in ['Qwen','Whisper']:
   for s in sessions:
    a=next(c for c in all_cases if c['family']==family and c['source_id']==s['source_id'] and c['repeat']==0)
    b=next(c for c in all_cases if c['family']==family and c['source_id']==s['source_id'] and c['repeat']==1)
    equal=all(x['P']==y['P'] and x['Z']==y['Z'] and x['Y']==y['Y'] for x,y in zip(a['windows'],b['windows']))
    repeat_checks.append({'family':family,'source_id':s['source_id'],'full_repeat_equal':equal})
  save(D/'SUMMARY.json',{'status':'COMPLETE_R3_NATIVE_TRAJECTORIES','cases':32,'independent_subjects':8,
    'repeats':repeat_checks,'all_repeats_equal':all(r['full_repeat_equal'] for r in repeat_checks),
    'model_calls':call_count,'permanent_irrecoverability_or_finite_recovery_not_claimed':True,
    'evidence_tier':'real_GPU_fixed_future_native_trajectory_not_serving'})
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'completed_cases':len(all_cases),'model_calls':call_count,'no_silent_retry':True});raise
 finally:
  if worker is not None:worker.close()

if __name__=='__main__':main()
