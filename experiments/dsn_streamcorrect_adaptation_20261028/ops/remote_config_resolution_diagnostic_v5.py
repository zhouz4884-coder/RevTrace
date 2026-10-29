"""CPU-only partial-asset config preflight; never a native inference claim."""
import pathlib,os,sys,json,datetime,hashlib,traceback
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028';M=B/'models/revtrace_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HOME=str(cache/'huggingface'),HF_MODULES_CACHE=str(cache/'huggingface/modules'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
import torch,transformers
from transformers import AutoConfig
record=dict(experiment_id='SC_NATIVE_CPU_CONFIG_PATH_PREFLIGHT_V5',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_runtime_commit='a652f6097c2269232b332ad046e399f9968b16e2',python=sys.executable,transformers=transformers.__version__,native_neural_calls=0,scope='actual configuration loader only; no weight/model construction',metadata={})
for p in [M/'ultravox_b95bec8/config.json',M/'ultravox_b95bec8/ultravox_config.py',M/'llama32_1b_instruct_f8e6b/config.json']:
 b=p.read_bytes();record['metadata'][str(p)]=hashlib.sha256(b).hexdigest()
try:
 cfg=AutoConfig.from_pretrained(str(M/'ultravox_b95bec8'),text_model_id=str(M/'llama32_1b_instruct_f8e6b'),trust_remote_code=True,local_files_only=True)
 record.update(status='PASS_EXISTING_V5_CONFIG_PATH',text_model_id=cfg.text_model_id)
except Exception as e:
 record.update(status='FAILED_EXISTING_V5_CONFIG_PATH',error=type(e).__name__,message=str(e)[:2000],frames=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])
record['torch_cuda_initialized']=torch.cuda.is_initialized();assert not record['torch_cuda_initialized']
(O/'CPU_CONFIG_RESOLUTION_DIAGNOSTIC_v5.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
