"""Consumed-history intervention; target-task real GPU fixed-state evidence."""
import hashlib,json,re,sys,time
from pathlib import Path
import numpy as np,soundfile as sf,torch
from transformers import WhisperProcessor,WhisperForConditionalGeneration
B=Path(sys.argv[1]);O=B/'results/revtrace/phaseD_20261021/R5_whisper';O.mkdir(exist_ok=False)
torch.set_num_threads(2)
(O/'RUN.json').write_text(json.dumps({'experiment_id':'PHASE-D-R5-CONSUMED-F2','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'code_identity':json.loads(Path(__file__).with_name('TOOL_SOURCE_IDENTITY.json').read_text()),'max_new_tokens':128,'sampling':False,'slices':'three contiguous partitions covering complete utterance','repeats':2,'dtype':['float16','float32'],'evidence':'real_GPU_fixed_state_intervention_not_deployed_service'},indent=2)+'\n')
manifest=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text());src=manifest['sessions'];modelpath=B/'models/whisper-small.en'
proc=WhisperProcessor.from_pretrained(modelpath,local_files_only=True)
models={}
for dtype,gpu in [(torch.float16,0),(torch.float32,1)]:
 m=WhisperForConditionalGeneration.from_pretrained(modelpath,local_files_only=True,torch_dtype=dtype,attn_implementation='eager').to('cuda:'+str(gpu));m.eval();models[gpu]=m
def digest(v):return hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
CALL_ID=0
def generate(wav,prompt,gpu,tag):
 global CALL_ID
 CALL_ID+=1;call_id=CALL_ID;m=models[gpu];cpu_features=proc(wav,sampling_rate=16000,return_tensors='pt').input_features;features=cpu_features.to(m.device,m.dtype);seen=[]
 supplied={'precast_sha256':hashlib.sha256(cpu_features.contiguous().numpy().tobytes()).hexdigest(),'actual_cast_argument_sha256':hashlib.sha256(features.detach().cpu().contiguous().numpy().tobytes()).hexdigest(),'shape':list(features.shape),'dtype':str(features.dtype)}
 def hook(mod,args,kw):
  v=kw.get('decoder_input_ids')
  if not seen and v is not None:seen.append(v.detach().cpu().tolist())
 handle=m.register_forward_pre_hook(hook,with_kwargs=True);kw={}
 if prompt:kw['prompt_ids']=proc.get_prompt_ids(prompt,return_tensors='pt').to(m.device)
 try:
  torch.cuda.synchronize(m.device);start=time.perf_counter()
  with torch.inference_mode():seq=m.generate(features,do_sample=False,num_beams=1,temperature=0.0,
      compression_ratio_threshold=None,logprob_threshold=None,no_speech_threshold=None,
      return_timestamps=False,max_new_tokens=128,return_dict_in_generate=True,**kw).sequences
  torch.cuda.synchronize(m.device);end=time.perf_counter()
 finally:handle.remove()
 full=seq[0].detach().cpu().tolist()
 raw={'call_id':call_id,'tag':tag,'prompt':prompt,'gpu':gpu,'audio_sha256':hashlib.sha256(np.asarray(wav,dtype='<f4').tobytes()).hexdigest(),'supplied_features':supplied,'actual_decoder_inputs':seen,'full_returned_tokens':full,'generation_started_perf':start,'generation_completed_perf':end}
 with (O/'calls_raw.jsonl').open('a') as f:f.write(json.dumps(raw)+'\n')
 assert seen,'No actual decoder prefix observed; F2 cannot be claimed'
 prefix=seen[0][0]
 assert full[:len(prefix)]==prefix,'Unexpected HF returned-token unit; stop instead of mixing prompt with generated Z'
 ids=full[len(prefix):];assert 0<len(ids)<=128
 text=proc.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False).strip()
 output={'call_id':call_id,'tag':tag,'text':text,'tokens':ids,'full_returned_tokens_including_decoder_prefix':full,'generated_offset':len(prefix),'actual_first_decoder_ids':prefix,'actual_first_decoder_sha256':digest(prefix),'prompt':prompt,'audio_sha256':raw['audio_sha256'],'supplied_features':supplied,'elapsed_wall_seconds':end-start,'elapsed_scope':'generate-only including decoder observer; excludes feature preparation, not serving cost','eos':m.generation_config.eos_token_id,'hit_cap':len(ids)>=128 and ids[-1]!=m.generation_config.eos_token_id,'gpu':gpu,'dtype':str(m.dtype)}
 with (O/'calls_validated.jsonl').open('a') as f:f.write(json.dumps(output)+'\n')
 return output
def words(x):return re.findall('[A-Z0-9]+',x.upper())
def errors(a,b):
 a,b=words(a),words(b);row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  new=[i]
  for j,y in enumerate(b,1):new.append(min(row[j]+1,new[-1]+1,row[j-1]+(x!=y)))
  row=new
 return row[-1],len(a)
histories=[];history_repeats=[];waves=[];rows=[]
try:
 for r in src:
  wav,sr=sf.read(r['path'],dtype='float32');assert sr==16000
  cut=len(wav)//3;parts=[wav[:cut],wav[cut:2*cut],wav[2*cut:]];waves.append(parts);h=generate(parts[0],None,1,r['source_id']+'/initial/r0');repeat=generate(parts[0],None,1,r['source_id']+'/initial/r1');assert h['tokens']==repeat['tokens'];histories.append(h);history_repeats.append(repeat)
 for i,r in enumerate(src):
  parts=waves[i];H0=histories[i]['text'];wrong=histories[(i+1)%len(src)]['text'];records={}
  assert H0 and wrong and H0!=wrong,'Valid nonempty history requirement failed; preserve source'
  for name,prompt,gpu in [('oracle',H0,1),('native',H0,0),('fault',wrong,0)]:
   pair=[generate(parts[1],prompt,gpu,r['source_id']+'/'+name+'/r'+str(attempt)) for attempt in range(2)];records[name]=pair
  # Restore the common original H0; retain only the generated transition delta.
  baseline_future=generate(parts[2],H0+' '+records['native'][0]['text'],0,r['source_id']+'/native_future/r0')
  baseline_future_repeat=generate(parts[2],H0+' '+records['native'][0]['text'],0,r['source_id']+'/native_future/r1')
  fault_future=generate(parts[2],H0+' '+records['fault'][0]['text'],0,r['source_id']+'/fault_future/r0')
  fault_future_repeat=generate(parts[2],H0+' '+records['fault'][0]['text'],0,r['source_id']+'/fault_future/r1')
  decoder_changed=records['native'][0]['actual_first_decoder_ids']!=records['fault'][0]['actual_first_decoder_ids']
  changed=records['native'][0]['tokens']!=records['fault'][0]['tokens']
  qualifies=decoder_changed and H0!=wrong
  native_text=' '.join([H0,records['native'][0]['text'],baseline_future['text']]);fault_text=' '.join([H0,records['fault'][0]['text'],fault_future['text']])
  en,n=errors(r['reference'],native_text);ef,_=errors(r['reference'],fault_text)
  projection=H0+' '+records['fault'][0]['text'];rebuilt=H0+' '+proc.tokenizer.decode(records['fault'][0]['tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False).strip()
  cheap={'projection_consistent':projection.encode()==rebuilt.encode(),'declared_parent_sha256':hashlib.sha256(H0.encode()).hexdigest(),'actual_fault_parent_sha256':hashlib.sha256(wrong.encode()).hexdigest(),'audio_unchanged':records['native'][0]['audio_sha256']==records['fault'][0]['audio_sha256'],'authority_reference_rejects_generated_Z':records['fault'][0]['tokens']!=records['oracle'][0]['tokens'],'tier':'CPU projection/self-consistency adaptation and offline FP32 Oracle comparison on actual GPU results; NOT native MarginGate, online verifier, or installed service'}
  row={'source_id':r['source_id'],'speaker':r['speaker'],'actual_context_changed':decoder_changed,'valid_consumed_F2':qualifies,'output_changed_vs_same_precision_native':changed,'candidate_matches_FP32_oracle':records['fault'][0]['tokens']==records['oracle'][0]['tokens'],'native_matches_FP32_oracle':records['native'][0]['tokens']==records['oracle'][0]['tokens'],'same_input_repeats_equal':all(pair[0]['tokens']==pair[1]['tokens'] for pair in records.values()),'future_repeats_equal':baseline_future['tokens']==baseline_future_repeat['tokens'] and fault_future['tokens']==fault_future_repeat['tokens'],'future_output_changed':baseline_future['tokens']!=fault_future['tokens'],'future_duration_seconds':len(parts[2])/16000,'native_errors':en,'fault_errors':ef,'reference_words':n,'cheap_check':cheap,'records':records,'initial_oracle':histories[i],'initial_oracle_repeat':history_repeats[i],'baseline_future':baseline_future,'baseline_future_repeat':baseline_future_repeat,'fault_future':fault_future,'fault_future_repeat':fault_future_repeat,'scope':'artificial consumed-history GPU intervention; not natural frequency or deployed-serving cost'}
  (O/(r['source_id']+'.json')).write_text(json.dumps(row,indent=2)+'\n');rows.append({k:v for k,v in row.items() if k not in ['records','initial_oracle','baseline_future','fault_future']});(O/'PROGRESS.json').write_text(json.dumps({'completed':len(rows),'expected':16}));print(r['source_id'],flush=True)
 (O/'SUMMARY.json').write_text(json.dumps({'status':'COMPLETE','sources':rows,'independent_speakers':16,'valid_consumed_faults':sum(x['valid_consumed_F2'] for x in rows),'cold_start_control':'initial oracle repeated without history; not counted as effective F2','R2_adapter_migration':'not claimed; Whisper prompt/segment interface differs'},indent=2)+'\n')
except BaseException as e:(O/'STOP.json').write_text(json.dumps({'error':repr(e),'completed':len(rows)}));raise
