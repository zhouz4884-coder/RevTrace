"""CPU-only token/adapter/full-physical-input replay of recorded crash traces.

Must run AFTER the serving GPU controller exits, to avoid CPU contention.
No model weights or new neural predictions are loaded/generated.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,os,subprocess
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='2';os.environ['TOKENIZERS_PARALLELISM']='false'
def read(p):return json.loads(p.read_text())
def rows(p):
 if not p.exists():return []
 raw=p.read_bytes();items=[]
 for i,line in enumerate(raw.splitlines(keepends=True)):
  try:items.append(json.loads(line))
  except (json.JSONDecodeError,UnicodeDecodeError):assert not line.endswith(b'\n') and i==len(raw.splitlines())-1
 return items
def tensor(x):
 y=x.detach().cpu().contiguous();return dict(shape=list(y.shape),dtype=str(y.dtype),sha256=hashlib.sha256(y.numpy().tobytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
 p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 # An idle gap BETWEEN cells is not permission to contend with a live study.
 launch=a.root/'FORMAL_FAULT_LAUNCH.json'
 if launch.exists():
  d=read(launch);proc=Path('/proc')/str(d['pid'])
  assert not (proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
  assert read(a.root/'formal_fault/SUMMARY.json')['cells']==21
 import numpy as np,soundfile as sf,torch
 from transformers import AutoProcessor
 from qwen_asr import Qwen3ASRModel,parse_asr_output
 torch.set_num_threads(2);processor=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=processor.tokenizer
 helper=object.__new__(Qwen3ASRModel);helper.processor=processor
 bases={lang:helper._build_text_prompt(context='',force_language=lang) for lang in ['English','Chinese']}
 waves={}
 for s in read(a.manifest)['sessions']:
  wave,rate=sf.read(s['path'],dtype='float32');wave=np.asarray(wave,dtype='<f4');assert rate==16000 and wave.ndim==1
  assert hashlib.sha256(wave.tobytes()).hexdigest()==s['audio_sha256'];waves[s['source_id']]=wave
 def prefix(job):
  raw=tok.decode(job['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);out=''
  if job['chunk_id']>=2 and raw:
   ids=tok.encode(raw);k=5
   while True:
    out=tok.decode(ids[:max(0,len(ids)-k)])
    if '\ufffd' not in out or k>=len(ids):break
    k+=1
  return out
 out=[]
 for name in read(a.root/'formal_fault/SUMMARY.json')['completed']:
  E=a.root/'formal_fault'/name
  for attempt in [0,1]:
   D=E/f'attempt{attempt}';cfg=read(D/'config.json');assets=cfg['authority_runtime']['render_contract']
   for key,value in assets['assets'].items():assert hashlib.sha256((a.model/key).read_bytes()).hexdigest()==value
   assert hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()==assets['parse_source_sha256']
   batches=[];result={};rendered=checked=unobserved=0
   for path in D.glob('*.submissions'):batches+=rows(path)
   for path in D.glob('worker-*-receipts.jsonl'):
    for r in rows(path):
     if r['kind']=='row-complete':
      m=r['message'];assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
      body=json.loads(m['payload_json']);result[body['job_id']]=body
   for batch in batches:
    jobs=batch['jobs'];prefixes=[prefix(j) for j in jobs]
    available=[(i,result[j['job_id']]) for i,j in enumerate(jobs) if j['job_id'] in result]
    if not available:unobserved+=1;continue
    tensors=processor(text=[bases[j['language']]+pre for j,pre in zip(jobs,prefixes)],
     audio=[waves[j['source_id']][:j['audio_end_sample']] for j in jobs],return_tensors='pt',padding=True)
    identities={k:tensor(v) for k,v in tensors.items()}
    for i,r in available:
     j=jobs[i];z=r['token_ids'];m=r['model_input_audit'];stops=[k for k,t in enumerate(z) if t in m['eos_token_ids']]
     assert z and len(z)<=256 and (stops==[len(z)-1] or (not stops and len(z)==256))
     assert m['batch_tensors']==identities and m['input_ids']==tensors['input_ids'][i].tolist()
     assert m['attention_mask']==tensors['attention_mask'][i].tolist() and m['rollback_prefix']==prefixes[i]
     raw=prefixes[i]+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
     P=tok.encode(raw);_,Y=parse_asr_output(raw,user_language=j['language'])
     assert r['state_tokens']==P and r['text'].encode()==Y.encode();rendered+=1
    checked+=1
   assert rendered==len(result)
   out.append(dict(episode=name,attempt=attempt,rendered_actual_completed_rows=rendered,
    full_batch_input_reprocessed_where_actual_row_audit_exists=checked,submitted_batches_with_no_complete_neural_output=unobserved))
 a.output.write_text(json.dumps(dict(status='PASS_CPU_CRASH_TRACE_ASSET_RENDER_AND_FULL_INPUT_REPLAY',runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8',
  runs=out,new_neural_GPU_calls=0,scope='actual completed rows only; unfinished GPU outputs not invented; CPU processor replay not neural oracle'),indent=2)+'\n')
 print(json.dumps(out))
if __name__=='__main__':main()
