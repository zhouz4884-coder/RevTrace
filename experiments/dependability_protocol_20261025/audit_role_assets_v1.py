"""Actual CPU input/Phi replay of operator native and coherently corrupted rows."""
from pathlib import Path
import argparse,hashlib,inspect,json,os,subprocess
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='2';os.environ['TOKENIZERS_PARALLELISM']='false'
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
def tensor(x):
 y=x.detach().cpu().contiguous();return dict(shape=list(y.shape),dtype=str(y.dtype),sha256=hashlib.sha256(y.numpy().tobytes()).hexdigest())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
 ap.add_argument('--model',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();assert not a.output.exists()
 launch=a.stage.parent/'PILOT_LAUNCH.json';d=read(launch);q=Path('/proc')/str(d['pid'])
 assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 import numpy as np,soundfile as sf,torch
 from transformers import AutoProcessor
 from qwen_asr import Qwen3ASRModel,parse_asr_output
 torch.set_num_threads(2);processor=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=processor.tokenizer
 helper=object.__new__(Qwen3ASRModel);helper.processor=processor;bases={lang:helper._build_text_prompt(context='',force_language=lang) for lang in ['English','Chinese']}
 waves={}
 for row in read(a.manifest)['sessions']:
  wave,rate=sf.read(row['path'],dtype='float32');wave=np.asarray(wave,dtype='<f4');assert rate==16000
  assert hashlib.sha256(wave.tobytes()).hexdigest()==row['audio_sha256'];waves[row['source_id']]=wave
 out=[]
 for name in read(a.stage/'SUMMARY.json')['completed']:
  D=a.stage/name;cfg=read(D/'config.json');assets=cfg['authority_runtime']['render_contract'];calls=read(D/'PHYSICAL_CALLS.json')['calls']
  for file,digest in assets['assets'].items():assert hashlib.sha256((a.model/file).read_bytes()).hexdigest()==digest
  assert hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()==assets['parse_source_sha256']
  originals={}
  for path in D.glob('worker-*-receipts.jsonl'):
   for x in lines(path):
    if x['kind']=='row-complete':originals[x['message']['binding']['job_id']]=json.loads(x['message']['payload_json'])
  native_render=corrupt_render=0;input_detections=[]
  for c in calls:
   j=c['job'];r=originals[j['job_id']];m=r['model_input_audit'];raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
   if j['chunk_id']>=2 and raw:
    ids=tok.encode(raw);k=5
    while True:
     prefix=tok.decode(ids[:max(0,len(ids)-k)])
     if '\ufffd' not in prefix or k>=len(ids):break
     k+=1
   assert m['rollback_prefix']==prefix
   inputs=processor(text=[bases[j['language']]+prefix],audio=[waves[j['source_id']][:j['audio_end_sample']]],return_tensors='pt',padding=True)
   assert {k:tensor(v) for k,v in inputs.items()}==m['batch_tensors']
   assert inputs['input_ids'][0].tolist()==m['input_ids'] and inputs['attention_mask'][0].tolist()==m['attention_mask']
   for body,kind in [(r,'native-worker'),(c['result'],'owner-channel')]:
    Z=body['token_ids'];stops=[i for i,t in enumerate(Z) if t in m['eos_token_ids']]
    assert stops==[len(Z)-1] or (not stops and len(Z)==m['max_new_tokens'])
    combined=prefix+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False);P=tok.encode(combined);_,Y=parse_asr_output(combined,user_language=j['language'])
    assert body['state_tokens']==P and body['text'].encode()==Y.encode()
    if kind=='native-worker':native_render+=1
    elif body['token_ids']!=r['token_ids']:corrupt_render+=1
   actual_ids=tok.decode(m['unpadded_input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
   input_detections.append(dict(job_id=j['job_id'],role=j['role'],purpose=c['purpose'],
    actual_processed_IDs_have_frozen_substring='violet saturn alder' in actual_ids.casefold(),
    original_worker_Z_has_substring='violet saturn alder' in tok.decode(r['token_ids'],skip_special_tokens=True).casefold()))
  assert native_render==len(calls)
  out.append(dict(case=name,actual_base_input_batches_reprocessed=len(calls),native_worker_rows_rendered=native_render,
   corrupted_rows_Phi_checked_not_claimed_neural=corrupt_render,input_detections=input_detections))
 a.output.write_text(json.dumps(dict(status='PASS8_ACTUAL_BASE_INPUT_AND_NATIVE_CORRUPT_PHI_ASSET_REPLAY',runs=out,
  new_neural_GPU_calls=0,limits='base processor/cast-contract replay, not hardware attestation or new inference; corruptedZ not model-generated'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(out),base_inputs=sum(r['actual_base_input_batches_reprocessed'] for r in out))))
if __name__=='__main__':main()
