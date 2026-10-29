"""Bounded real-input legacy failure and original-PyTorch legal median controls."""
import argparse,pathlib,json,hashlib,subprocess,sys,os,datetime,platform,time,statistics
R=pathlib.Path(__file__).resolve().parent
def put(p,x):p.write_text(json.dumps(x,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 cfg=json.loads(a.config.read_text());manifest=json.loads(a.manifest.read_text());commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
 assert commit==manifest['source_commit'] and not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True)
 for row in manifest['files']:
  b=(R/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 os.environ.update(CUDA_VISIBLE_DEVICES='0,1',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
 cache=pathlib.Path(cfg['cache_root'])
 for key,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
  q=cache/rel;q.mkdir(parents=True,exist_ok=True);os.environ[key]=str(q)
 (cache/'xdg/torch/kernels').mkdir(parents=True,exist_ok=True)
 import torch,numpy as np,soundfile as sf,triton
 torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
 env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),torch=torch.__version__,triton=triton.__version__,cuda=torch.version.cuda,cache_root=str(cache))
 put(a.out/'ENVIRONMENT.json',env);put(a.out/'CONFIG.json',cfg)
 put(a.out/'PRELAUNCH_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.config),frozen_config_sha256=sha(a.config),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out/'ACTUAL_NATIVE_MEDIAN_INPUT.pt'),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
 from native_bridge import NativeBridge
 model=NativeBridge(**cfg['backend'],role='private')
 import simul_whisper.simul_whisper as native
 original_filter=native.median_filter;module=model.triton_compat['module'];legacy=model.triton_compat['original'];patched=model.triton_compat['patched'];captured=[];legacy_errors=[]
 def capture(x,width):
  if not captured:
   tensor=x.detach().cpu().clone();captured.append(tensor);torch.save(tensor,a.out/'ACTUAL_NATIVE_MEDIAN_INPUT.pt')
   for repeat in range(2):
    module.median_kernel=legacy
    try:original_filter(x,width);raise AssertionError('legacy API unexpectedly passed')
    except TypeError as e:
     assert '_set_src' in str(e);legacy_errors.append(dict(repeat=repeat,type=type(e).__name__,message=str(e)))
    finally:module.median_kernel=patched
  return original_filter(x,width)
 native.median_filter=capture
 source=cfg['source'];path=pathlib.Path(source['path']);assert sha(path)==source['audio_sha256'];audio,sr=sf.read(path,dtype='float32');assert sr==16000
 cut,record=model.step(audio=audio,start=model.initial_for(source['audio_sha256']),end=16000,is_last=False)
 native.median_filter=original_filter;assert captured and len(legacy_errors)==2
 actual=captured[0];assert bool(torch.isfinite(actual).all()) and bool((actual>=0).all())
 generator=torch.Generator().manual_seed(20261029)
 cases=[('actual_native_first_warmup',actual),('short_identity',torch.rand(4,6,2,generator=generator)),('one_dimensional',torch.rand(31,generator=generator)),('two_dimensional_ties',(torch.rand(4,51,generator=generator)*4).round()),('noncontiguous',torch.rand(4,6,300,generator=generator)[...,::2])]
 for n in [50,300,1500,3000]:cases.append(('finite_attention_like_4x6x'+str(n),torch.rand(4,6,n,generator=generator)))
 rows=[];timing=[]
 for gpu in [0,1]:
  torch.cuda.set_device(gpu)
  for name,cpu in cases:
   x=cpu.to('cuda:'+str(gpu))
   if not cpu.is_contiguous():
    storage=torch.empty(*cpu.shape[:-1],cpu.shape[-1]*2,device='cuda:'+str(gpu),dtype=cpu.dtype);x=storage[...,::2];x.copy_(cpu)
   for width in [1,3,5,7,9]:
    expected=original_filter(cpu,width);bits=expected.contiguous().view(torch.int32)
    for repeat in range(3):
     result=original_filter(x,width).cpu();assert torch.equal(result.contiguous().view(torch.int32),bits),(name,gpu,width,repeat)
    rows.append(dict(case=name,gpu=gpu,width=width,shape=list(cpu.shape),cpu_noncontiguous=not cpu.is_contiguous(),gpu_noncontiguous=not x.is_contiguous(),repeats=3,bitwise_original_cpu_oracle_equal=True))
   if name in ('actual_native_first_warmup','finite_attention_like_4x6x3000'):
    def fallback_gpu():
     shape=x.shape;y=x[None,None,:] if x.ndim==1 else x[None,:] if x.ndim==2 else x
     y=torch.nn.functional.pad(y,(3,3),mode='reflect').unfold(-1,7,1).sort()[0][...,3]
     return y.reshape(shape)
    for method,fn in [('native_repaired_triton',lambda:original_filter(x,7)),('original_torch_sort_formula_on_gpu',fallback_gpu)]:
     for _ in range(3):fn()
     samples=[]
     for _ in range(15):
      torch.cuda.synchronize(gpu);t=time.perf_counter();fn();torch.cuda.synchronize(gpu);samples.append(time.perf_counter()-t)
     timing.append(dict(case=name,gpu=gpu,method=method,repeats=15,median_seconds=statistics.median(samples),scope='median operator only, not serving performance'))
 exceptional=[]
 for name,cpu in [('signed_zero',torch.tensor([0.,-0.,0.,-0.,0.,-0.,0.])),('nan_payload',torch.tensor([1.,float('nan'),.2,.1,.3,.4,.5]))]:
  for gpu in [0,1]:
   expected=original_filter(cpu,7);result=original_filter(cpu.to('cuda:'+str(gpu)),7).cpu()
   exceptional.append(dict(case=name,gpu=gpu,bitwise_original_cpu_oracle_equal=bool(torch.equal(result.contiguous().view(torch.int32),expected.contiguous().view(torch.int32))),within_observed_actual_finite_nonnegative_attention_domain=False))
 summary=dict(status='PASS_NATIVE_MEDIAN_API_AND_FINITE_INPUT_GPU_ORACLE_CONTROLS',source_commit=commit,legacy_same_input_repeated_errors=legacy_errors,
  generated_kernel_source_proof=model.triton_compat['source_proof'],actual_input=dict(shape=list(actual.shape),dtype=str(actual.dtype),tensor_bytes=actual.numel()*actual.element_size(),all_finite_nonnegative=True,serialized_sha256=sha(a.out/'ACTUAL_NATIVE_MEDIAN_INPUT.pt')),
  actual_native_asr_warmup_completed=True,actual_warmup_record=record,actual_warmup_end_state_sha=cut.sha256,oracle_cases=rows,oracle_repeated_comparisons=len(rows)*3,operator_timings=timing,exceptional_inputs=exceptional,
  scope='Native ASR warmup plus component/API controls only; no application serving result, no learned Authority correction witness, no model/selector change')
 put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',dict(status=summary['status'],oracle_cases=len(rows),repeated_comparisons=len(rows)*3));print(json.dumps(dict(status=summary['status'],actual_shape=list(actual.shape),oracle_cases=len(rows),repeated_comparisons=len(rows)*3),indent=2))
if __name__=='__main__':main()
