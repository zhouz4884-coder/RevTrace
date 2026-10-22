"""CPU-only independent replay of actual F2 batches, not neural regeneration."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,sys
import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor
from qwen_asr import Qwen3ASRModel
torch.set_num_threads(2)
B=Path(sys.argv[1]);stage=sys.argv[2];O=B/'results/revtrace/online_admission_20261022';proc=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True);tok=proc.tokenizer
obj=object.__new__(Qwen3ASRModel);obj.processor=proc;bases={lang:obj._build_text_prompt('',lang) for lang in ['English','Chinese']}
manifest=json.loads((O/'PILOT_MANIFEST.json').read_text()) if stage.startswith('pilot') else json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text());waves={}
for s in manifest['sessions']:
 p=Path(s['path']);wav,rate=sf.read(p,dtype='float32');assert rate==16000 and wav.ndim==1;waves[s['source_id']]=np.asarray(wav,dtype='<f4')
def identity(x):
 x=x.detach().cpu().contiguous();return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
results=[]
for c in sorted((O/stage).iterdir()):
 if not c.is_dir() or not (c/'result.json').exists():continue
 rows=[json.loads(l) for l in (c/'worker_records.jsonl').read_text().splitlines()];batches=defaultdict(list)
 for r in rows:batches[r['job']['role'],r['result']['started_perf'],r['result']['completed_perf']].append(r)
 for key,rs in batches.items():
  relevant_fault=any('fault_actual_prompt_tokens' in r['job'] for r in rs)
  relevant_verify=any(r['result'].get('online_verification') for r in rs)
  if not relevant_fault and not relevant_verify:continue
  prompts=[];correct_prompts=[];wavs=[]
  for rr in rs:
   j=rr['job'];actual=j.get('fault_actual_prompt_tokens',j['prompt_tokens']);raw=tok.decode(actual,skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
   if j['chunk_id']>=2 and raw:
    ids=tok.encode(raw);k=5
    while True:
     prefix=tok.decode(ids[:max(0,len(ids)-k)])
     if '\ufffd' not in prefix or k>=len(ids):break
     k+=1
   assert prefix==rr['result']['model_input_audit']['rollback_prefix'];prompts.append(bases[j['language']]+prefix);wavs.append(waves[j['source_id']][:j['audio_end_sample']])
   original=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);cp=''
   if j['chunk_id']>=2 and original:
    ids=tok.encode(original);k=5
    while True:
     cp=tok.decode(ids[:max(0,len(ids)-k)])
     if '\ufffd' not in cp or k>=len(ids):break
     k+=1
   correct_prompts.append(bases[j['language']]+cp)
  first=proc(text=prompts,audio=wavs,return_tensors='pt',padding=True);repeat=proc(text=prompts,audio=wavs,return_tensors='pt',padding=True)
  ids={k:identity(v) for k,v in first.items()};assert ids=={k:identity(v) for k,v in repeat.items()}
  correct=proc(text=correct_prompts,audio=wavs,return_tensors='pt',padding=True);changed=[]
  for i,rr in enumerate(rs):
   a=rr['result']['model_input_audit'];assert ids==a['batch_tensors'] and first['input_ids'][i].tolist()==a['input_ids'] and first['attention_mask'][i].tolist()==a['attention_mask']
   if 'fault_actual_prompt_tokens' in rr['job']:
    actualids=first['input_ids'][i][first['attention_mask'][i].bool()].tolist();correctids=correct['input_ids'][i][correct['attention_mask'][i].bool()].tolist();changed.append({'job_id':rr['job']['job_id'],'effective_processed_ID_change':actualids!=correctids})
  results.append({'cell':c.name,'role':key[0],'batch_rows':len(rs),'job_ids':[r['job']['job_id'] for r in rs],'actual_batch_tensors':ids,'counterfactual_no_override_batch_tensors':{k:identity(v) for k,v in correct.items()},'F2_jobs':sum('fault_actual_prompt_tokens' in r['job'] for r in rs),'actual_vs_correct_context':changed,'same_batch_actual_processor_all_tensors_exact':True,'CPU_repeat_exact':True,'model_generation_calls':0,'online_operation':rs[0]['result'].get('online_verification',{}).get('mode','proposal_generation'),'unprotected_target_inputs_staged_not_neurally_verified':bool(rs[0]['result'].get('online_verification',{}).get('unsafe_no_FP32_selection'))})
out={'status':'PASS_ACTUAL_F2_PROCESSOR_BATCH_REPLAY' if results else 'NO_COMPLETED_F2_BATCHES_YET','stage':stage,'batches':results,'model_generation_calls':0,'scope':'CPU recomputation of processed inputs before dtype cast; not GPU arithmetic equivalence or regenerated outputs'}
(O/(stage+'_PROCESSOR_REPLAY_v4.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'stage':stage,'batches':len(results),'model_generation_calls':0}))
