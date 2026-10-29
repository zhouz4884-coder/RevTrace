"""Complete bounded environment receipt, CPU only, before timed campaigns."""
import pathlib,json,subprocess,sys,os,hashlib,datetime,platform
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
os.environ['CUDA_VISIBLE_DEVICES']=''
assert json.loads((O/'cpu_environment_pipeline_v6/STATUS.json').read_text())['status']=='PASS_READY_FOR_ROOT_SERIALIZED_NATIVE_GPU_WINDOW'
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
import torch
assert not torch.cuda.is_initialized()
plan=P/'NATIVE_CAMPAIGN_v6_FROZEN.json';frozen=json.loads(plan.read_text());env=pathlib.Path(frozen['environment_record'])
r=dict(experiment_id='SC_NATIVE_ENVIRONMENT_RECEIPT_V6',status='PASS_COMPLETE_CPU_ENVIRONMENT_RECEIPT_NO_GPU',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 native_runtime_commit=frozen['source_commit'],frozen_native_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),frozen_native_environment_sha256=hashlib.sha256(env.read_bytes()).hexdigest(),
 python=sys.version,executable=sys.executable,platform=platform.platform(),packages=json.loads(subprocess.check_output([sys.executable,'-m','pip','list','--format=json','--disable-pip-version-check'],text=True)),
 torch_version=torch.__version__,torch_compiled_cuda=torch.version.cuda,torch_build_configuration=torch.__config__.show(),
 gpu_inventory=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True).strip().splitlines(),
 native_neural_calls=0,torch_cuda_initialized=False,
 cache_policy={k:os.environ[k] for k in ['HF_HOME','HF_MODULES_CACHE','PIP_CACHE_DIR','TORCH_HOME','XDG_CACHE_HOME','NUMBA_CACHE_DIR','TRITON_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR'] if k in os.environ})
p=O/'ENVIRONMENT_COMPLETE_v6.json';assert not p.exists();p.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['packages','torch_build_configuration']},indent=2))
