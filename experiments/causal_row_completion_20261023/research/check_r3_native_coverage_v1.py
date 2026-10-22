"""CPU-only actual processor coverage, not neural regeneration or GPU evidence."""
from pathlib import Path
import hashlib,inspect,json,sys

def main():
 B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'r3_coverage_v1';D.mkdir(exist_ok=False)
 try:
  import numpy as np,soundfile as sf
  from transformers import AutoProcessor
  from qwen_asr import Qwen3ASRModel
  proc=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True)
  fake=Qwen3ASRModel.__new__(Qwen3ASRModel);fake.processor=proc
  base=fake._build_text_prompt(context='',force_language='English')
  rows=json.loads((O/'r3_source_v1/MANIFEST.json').read_text())['sessions'];findings=[]
  for r in rows:
   wave,sr=sf.read(r['path'],dtype='float32');assert sr==16000
   changed=wave.copy();changed[30*16000:]=0
   a=proc(text=[base],audio=[wave],return_tensors='pt',padding=True)
   z=proc(text=[base],audio=[changed],return_tensors='pt',padding=True)
   def ident(data):
    return {k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest(),
       'mask_sum':int(v.sum()) if 'mask' in k else None} for k,v in data.items()}
   ai,zi=ident(a),ident(z);features=[k for k in a if 'feature' in k and 'mask' not in k]
   feature_changed=any(ai[k]['sha256']!=zi[k]['sha256'] for k in features)
   masks=[k for k in a if 'feature' in k and 'mask' in k]
   available=max([ai[k]['mask_sum'] for k in masks] or [max(ai[k]['shape'][-1] for k in features)])
   expected=len(wave)//160
   findings.append({'source_id':r['source_id'],'duration':len(wave)/16000,'original_inputs':ai,
      'tail_only_changed_inputs':zi,'beyond30s_changes_actual_features':feature_changed,
      'expected_feature_frames_approx':expected,'observed_active_frames_or_tensor_length':available,
      'full_prefix_audio_tensor_coverage_supported':feature_changed and available>=expected-2,
      'CPU_only_not_a_neural_effect':True})
  out={'status':'COMPLETE_NATIVE_PROCESSOR_COVERAGE','sources':findings,
    'all_sources_support_long_prefix':all(r['full_prefix_audio_tensor_coverage_supported'] for r in findings),
    'processor_class':str(type(proc)),'native_engine_source':inspect.getfile(Qwen3ASRModel),
    'build_prompt_source_sha256':hashlib.sha256(inspect.getsource(Qwen3ASRModel._build_text_prompt).encode()).hexdigest(),
    'new_GPU_calls':0,'scope':'actual CPU processor tensors only, not proof of semantic use of every frame'}
  (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
 except BaseException as e:
  (D/'STOP.json').write_text(json.dumps({'error':repr(e),'not_a_GPU_failure':True})+'\n');raise

if __name__=='__main__':main()
