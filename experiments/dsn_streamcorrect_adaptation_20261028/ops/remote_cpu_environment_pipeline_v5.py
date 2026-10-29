"""Detached prerequisite pipeline, begins only after exact assets gate passes."""
import pathlib,json,subprocess,os,sys,datetime,time,traceback
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
out=O/'cpu_environment_pipeline_v5';out.mkdir(exist_ok=False)
def write(status,**kw):
 r=dict(status=status,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit='a652f6097c2269232b332ad046e399f9968b16e2',native_neural_calls=0,gpu_launched=False,**kw)
 (out/'STATUS.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',HF_HOME=str(cache/'huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
 PIP_CACHE_DIR=str(cache/'pip'),TORCH_HOME=str(cache/'torch'),XDG_CACHE_HOME=str(cache/'xdg'),NUMBA_CACHE_DIR=str(cache/'numba'),HF_MODULES_CACHE=str(cache/'huggingface/modules'),
 TRITON_CACHE_DIR=str(cache/'triton'),TORCHINDUCTOR_CACHE_DIR=str(cache/'inductor'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
steps=['remote_bootstrap_cpu_env_v5.py','remote_prepare_native_environment_v5.py','remote_native_source_cpu_gate_v5.py','remote_native_interface_cpu_gate_v5.py','remote_build_campaign_v5.py']
stage='wait_exact_assets'
try:
 write('WAITING_EXACT_ASSET_GATE')
 while True:
  gate=O/'assets_v1/GATE.json'
  if gate.exists() and json.loads(gate.read_text()).get('status')=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED':break
  time.sleep(15)
 for stage in steps:
  py=B/'envs/revbatch-cu128/bin/python' if stage=='remote_bootstrap_cpu_env_v5.py' else B/'envs/revtrace-streamcorrect-20261028/bin/python'
  write('ACTIVE_CPU_PREPARATION',stage=stage)
  subprocess.run([str(py),'-B',str(P/'cpu_setup_v5'/stage)],env=env,check=True)
 write('PASS_READY_FOR_ROOT_SERIALIZED_NATIVE_GPU_WINDOW',completed_steps=steps)
except BaseException as e:
 write('INCOMPLETE_CPU_PREPARATION_PRESERVED',stage=stage,error=type(e).__name__,frames=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])
 raise SystemExit(1)
