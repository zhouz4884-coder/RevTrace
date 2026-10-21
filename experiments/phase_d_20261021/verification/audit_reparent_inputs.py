"""CPU replay of actual frozen batches; metadata reparenting is NOT re-inference."""
from pathlib import Path
import hashlib,json,sys,copy
import numpy as np,soundfile as sf,torch
from transformers import AutoProcessor
from qwen_asr import Qwen3ASRModel
B=Path(sys.argv[1]);O=B/'results/revtrace/phaseD_20261021';torch.set_num_threads(2)
processor=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True);tok=processor.tokenizer;engine=Qwen3ASRModel.__new__(Qwen3ASRModel);engine.processor=processor
manifest=json.loads((B/'datasets/tc_live_20260906/manifest.json').read_text());audio={}
for s in manifest['sessions']:
 p=Path(s['path']);p=p if p.exists() else B/'datasets/tc_live_20260906'/p.name;v,r=sf.read(p,dtype='float32');assert r==16000;audio[s['source_id']]=np.asarray(v,dtype='<f4')
def prompt(j):
 raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
 if j['chunk_id']>=2 and raw:
  ids=tok.encode(raw);k=5
  while True:
   prefix=tok.decode(ids[:max(0,len(ids)-k)])
   if '\ufffd' not in prefix or k>=len(ids):break
   k+=1
 return engine._build_text_prompt('',j['language'])+prefix
def encode(jobs):return processor(text=[prompt(j) for j in jobs],audio=[audio[j['source_id']][:j['audio_end_sample']] for j in jobs],return_tensors='pt',padding=True)
def hashes(inputs):return {k:hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest() for k,v in inputs.items()}
rows=[]
for c in sorted((O/'R2_continuity').iterdir()):
 if 'keep1-two_lane' not in c.name or not (c/'result.json').exists():continue
 es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];vs=[json.loads(l) for l in (c/'consumer.jsonl').read_text().splitlines()];records=[]
 for line in (c/'worker_records.jsonl').open():records.append(json.loads(line))
 chosen=None
 for view in vs:
  if not view['compatible_provisional_retained']:continue
  pubs=[e for e in es if e['kind']=='display' and e['session_id']==view['session_id'] and e['displayed']<=view['server_time'] and e['audio_end_sample']==view['valid_visible_frontier'] and e['text']==view['visible_text']]
  for e in reversed(pubs):
   x=next(r for r in records if r['job']['job_id']==e['job_id'])
   if x['job']['chunk_id']>=2 and x['result']['model_input_audit']['rollback_prefix']:
    chosen=view,x;break
  if chosen:break
 if not chosen:rows.append({'cell':c.name,'status':'NO_QUALIFYING_RETAINED_CONSUMED_PREFIX','tier':'CPU_only'});continue
 view,x=chosen;batch=[r for r in records if r['job']['role']=='proposal' and r['result']['started_perf']==x['result']['started_perf']];idx=next(i for i,r in enumerate(batch) if r['job']['job_id']==x['job']['job_id']);old=[r['job'] for r in batch];new=copy.deepcopy(old)
 new[idx].update(parent=view['canonical_version'],audio_start_sample=view['certified_frontier'],parent_prompt_digest=view['certified_P_sha256'])
 a=encode(old);b=encode(new);ha,hb=hashes(a),hashes(b);assert ha==hb
 recorded=x['result']['model_input_audit']['batch_tensors'];assert all(ha[k]==recorded[k]['sha256'] for k in ha)
 wrong=copy.deepcopy(old);wrong[idx]['prompt_tokens']=tok.encode('clearly unrelated previous conditioning context '*12);bad=encode(wrong)
 assert not torch.equal(a['input_ids'],bad['input_ids']),'Negative prompt control was not consumed'
 rows.append({'cell':c.name,'status':'PASS_FROZEN_BATCH_METADATA_REPARENT_INVARIANCE','session_id':view['session_id'],'version':view['canonical_version'],'job_id':x['job']['job_id'],'source_id':x['job']['source_id'],'actual_batch_rows':len(batch),'target_index':idx,'all_processor_tensors_byte_equal':True,'original_GPU_input_observation_reproduced':True,'changed_prompt_negative_control_changes_actual_IDs':True,'frozen_batch_hashes':ha,'tier':'CPU_REPLAY_OF_RECORDED_GPU_INPUTS_NOT_NEW_GPU_GENERATION','scope':'does not assert equivalence across a different batch realization; does not certify provisional output as authority choice'})
assert any(r['status'].startswith('PASS_') for r in rows)
(O/'REPARENT_INPUT_INVARIANCE_AUDIT.json').write_text(json.dumps({'status':'PASS_BOUNDED_CPU_REPARENT_INPUT_CONTROLS','cases':rows,'new_GPU_generations':0},indent=2)+'\n');print(json.dumps(rows))
