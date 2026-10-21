"""Controlled processed-input layouts; actual FP32 GPU calls, not SDC incidence."""
import hashlib,json,sys,time
from pathlib import Path
def main():
 B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';S=P/'d1_v1';sys.path.insert(0,str(S/'scripts'));sys.path.insert(0,str(S/'src'))
 from tc_live_worker import GPUExecutor
 from revtrace.live_qwen import fingerprint
 import numpy as np,soundfile as sf,torch
 torch.set_num_threads(2)
 from transformers import AutoProcessor
 from qwen_asr import Qwen3ASRModel
 O=B/'results/revtrace/phaseD_20261021/R6_realization';O.mkdir(exist_ok=False)
 (O/'RUN.json').write_text(json.dumps({'experiment_id':'PHASE-D-R6-REALIZED-INPUT','tool_identity':json.loads(Path(__file__).with_name('TOOL_SOURCE_IDENTITY.json').read_text()),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'same target and actual prompt, controlled layouts; independent CPU replay'},indent=2))
 cell=B/'results/revtrace/phaseN_20261021/t1_v4/coarse-decoupled-obs1-r0';records=[json.loads(l) for l in (cell/'worker_records.jsonl').read_text().splitlines()];jobs=[]
 for source in ['chinese-05','chinese-00','english-00','english-01']:
  js=[r['job'] for r in records if r['job']['role']=='authority' and r['job']['source_id']==source];jobs.append(max(js,key=lambda j:j['audio_end_sample']))
 model=B/'models/Qwen3-ASR-1.7B';manifest=B/'datasets/tc_live_20260906/manifest.json';processor=AutoProcessor.from_pretrained(model,local_files_only=True);tok=processor.tokenizer
 waves={r['source_id']:sf.read(r['path'],dtype='float32')[0] for r in json.loads(manifest.read_text())['sessions']}
 engine=Qwen3ASRModel.__new__(Qwen3ASRModel);engine.processor=processor
 def prompt(j):
  raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
  if j['chunk_id']>=2 and raw:
   ids=tok.encode(raw);k=5
   while True:
    prefix=tok.decode(ids[:max(0,len(ids)-k)])
    if '\ufffd' not in prefix or k>=len(ids):break
    k+=1
  return engine._build_text_prompt('',j['language'])+prefix
 # Use the installed library's actual language-specific base construction.
 # Inspected worker source constructs the exact same system/user chat below.
 worker_bytes=(S/'scripts/tc_live_worker.py').read_bytes();(O/'WORKER_SOURCE_SHA256.json').write_text(json.dumps({'sha256':hashlib.sha256(worker_bytes).hexdigest(),'unit':'raw file bytes','code_commit':json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit']}))
 config={'model':str(model),'manifest':str(manifest),'gpu':1,'dtype':'float32','microbatch':16,'max_new_tokens':256,'runtime_digest':'PHASE-D-R6-FP32','capture_model_inputs':True,'lifecycle_instrumentation':True}
 rootcell=B/'results/revtrace/phaseN_20261021/root_readiness_v1/root-shadow-r0'
 rootrows=[json.loads(l) for l in (rootcell/'worker_records.jsonl').read_text().splitlines() if json.loads(l)['job']['role']=='authority']
 worker=GPUExecutor('r6-fp32',config);worker.wait_ready();rows=[]
 try:
  for i,target in enumerate(jobs):
   for layout in ['singleton','heterogeneous4','recorded_original']:
    for repeat in range(2):
     if layout=='singleton':batch=[target];target_index=0
     elif layout=='heterogeneous4':batch=[target]+[j for j in jobs if j['source_id']!=target['source_id']];target_index=0
     else:
      pool=rootrows if target['source_id']=='chinese-05' else [r for r in records if r['job']['role']=='authority']
      item=next(r for r in pool if r['job']['source_id']==target['source_id'] and r['job']['audio_end_sample']==target['audio_end_sample'] and r['job']['prompt_tokens']==target['prompt_tokens'] and r['job']['chunk_id']==target['chunk_id'])
      group=[r for r in pool if r['result']['started_perf']==item['result']['started_perf']]
      batch=[r['job'] for r in group];target_index=next(k for k,r in enumerate(group) if r['job']['job_id']==item['job']['job_id'])
     actual=[]
     for k,j in enumerate(batch):
      x=dict(j,job_id=f'r6-{i}-{layout}-{repeat}-{k}',audio_ready_perf=0.,enqueue_perf=time.perf_counter(),runtime_digest=config['runtime_digest']);actual.append(x)
     worker.submit(actual)
     while True:
      result=worker.poll()
      worker.drain_telemetry()
      if result is not None:break
      time.sleep(.001)
     r=result[target_index];a=r['model_input_audit'];cpu=[]
     for attempt in range(2):
      inp=processor(text=[prompt(j) for j in actual],audio=[waves[j['source_id']][:j['audio_end_sample']] for j in actual],return_tensors='pt',padding=True)
      ids=inp['input_ids'][target_index][inp['attention_mask'][target_index].bool()].tolist();features=hashlib.sha256(inp['input_features'][target_index].contiguous().numpy().tobytes()).hexdigest()
      batch_hashes={k:hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest() for k,v in inp.items()}
      assert all(batch_hashes[k]==a['batch_tensors'][k]['sha256'] for k in batch_hashes)
      cpu.append({'ids':ids,'features_sha256':features,'valid_feature_mask_sum':int(inp['feature_attention_mask'][target_index].sum()),'full_batch_tensor_hashes':batch_hashes})
     assert cpu[0]==cpu[1] and cpu[0]['ids']==a['unpadded_input_ids'] and cpu[0]['features_sha256']==a['row_features']['input_features']['sha256']
     row={'source_id':target['source_id'],'language':target['language'],'layout':layout,'repeat':repeat,'target_index':target_index,'target_job':actual[target_index],'batch_jobs':actual,'batch_results':result,'target_result':r,'cpu_replayed_twice':cpu,'processed_input_ids':a['unpadded_input_ids'],'actual_waveform_sha256':a['waveform_sha256'],'generated_Z':r['token_ids'],'projected_P':r['state_tokens'],'text':r['text'],'scope':'controlled same-target/context, different actual batch layout; recorded_original is an old exact-layout positive control; neither natural prevalence nor proof of GPU SDC'}
     rows.append(row);(O/f'case-{i}-{layout}-r{repeat}.json').write_text(json.dumps(row,indent=2)+'\n');print(i,layout,repeat,flush=True)
  comparisons=[]
  for i,j in enumerate(jobs):
   one=[r for r in rows if r['source_id']==j['source_id'] and r['layout']=='singleton'];many=[r for r in rows if r['source_id']==j['source_id'] and r['layout']=='heterogeneous4']
   recorded=[r for r in rows if r['source_id']==j['source_id'] and r['layout']=='recorded_original']
   comparisons.append({'source_id':j['source_id'],'language':j['language'],'waveform_equal':one[0]['actual_waveform_sha256']==many[0]['actual_waveform_sha256']==recorded[0]['actual_waveform_sha256'],'processed_ids_equal':one[0]['processed_input_ids']==many[0]['processed_input_ids'],'singleton_length':len(one[0]['processed_input_ids']),'batch_length':len(many[0]['processed_input_ids']),'recorded_layout_length':len(recorded[0]['processed_input_ids']),'recorded_layout_rows':len(recorded[0]['batch_jobs']),'Z_equal_across_layouts':one[0]['generated_Z']==many[0]['generated_Z']==recorded[0]['generated_Z'],'P_equal_across_layouts':one[0]['projected_P']==many[0]['projected_P']==recorded[0]['projected_P'],'within_layout_repeats_equal':all(rs[0]['processed_input_ids']==rs[1]['processed_input_ids'] and rs[0]['generated_Z']==rs[1]['generated_Z'] for rs in [one,many,recorded])})
  (O/'SUMMARY.json').write_text(json.dumps({'status':'COMPLETE','comparisons':comparisons,'model_hash_assumption':'checked by final pipeline preflight','prior_V0_V1_NO_GO_retained':True,'V2_started':False},indent=2)+'\n')
 finally:worker.close()
if __name__=='__main__':main()
