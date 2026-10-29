import pathlib,os,sys,json,subprocess,datetime,hashlib,traceback
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';M=B/'models/revtrace_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HOME=str(cache/'huggingface'),HF_MODULES_CACHE=str(cache/'huggingface/modules'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
S=P/'runtime_source_v6';manifest=json.loads((P/'SOURCE_v6.json').read_text())
if not S.exists():
 subprocess.run(['git','clone','--no-hardlinks',str(P/'SOURCE_v6.bundle'),str(S)],check=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout','--detach',manifest['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==manifest['source_commit']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True)
for row in manifest['files']:
 b=(S/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
sys.path.insert(0,str(S))
from native_bridge import corrector_interface
import torch,transformers,numpy as np
record=dict(experiment_id='SC_NATIVE_CPU_CONFIG_PATH_REPAIR_PREFLIGHT_V6',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_runtime_commit=manifest['source_commit'],python=sys.executable,transformers=transformers.__version__,native_neural_calls=0,scope='actual original configuration and processor only; no weight/model construction')
try:
 cfg,processor=corrector_interface(corrector_base=M/'ultravox_b95bec8',text_backbone=M/'llama32_1b_instruct_f8e6b',corrector_audio_processor=M/'whisper_large_v3_turbo_feature_extractor_41f01f3f')
 probe=processor(text='<|audio|>',audio=np.zeros(16000,dtype=np.float32),sampling_rate=16000,return_tensors='pt')
 record.update(status='PASS_ORIGINAL_LOCAL_CONFIG_PROCESSOR_PATH_REPAIR',text_model_id=cfg.text_model_id,feature_size=processor.audio_processor.feature_size,probe={k:dict(shape=list(v.shape),dtype=str(v.dtype)) for k,v in probe.items() if torch.is_tensor(v)})
except Exception as e:
 record.update(status='FAILED_V6_CONFIG_PROCESSOR_PATH_PREFLIGHT',error=type(e).__name__,message=str(e)[:1500],frames=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])
record['torch_cuda_initialized']=torch.cuda.is_initialized();assert not record['torch_cuda_initialized']
(O/'CPU_CONFIG_RESOLUTION_REPAIR_DIAGNOSTIC_v6.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
