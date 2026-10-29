"""Load exact native classes/config/processor only; no model construction."""
import pathlib,json,hashlib,datetime,os,sys,inspect
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
assert json.loads((O/'assets_v1/GATE.json').read_text())['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
plan=json.loads((O/'assets_v1/PUBLIC_PLAN.json').read_text());M=pathlib.Path(plan['model_root'])
import torch,numpy as np
from transformers import AutoConfig,AutoProcessor
from transformers.dynamic_module_utils import get_class_from_dynamic_module
sys.path.insert(0,str(P/'author_StreamCorrect_bbb9f7f'))
from simul_whisper.simul_whisper import PaddedAlignAttWhisper
from simul_whisper.config import AlignAttConfig
cfg=AutoConfig.from_pretrained(str(M/'ultravox_b95bec8'),text_model_id=str(M/'llama32_1b_instruct_f8e6b'),trust_remote_code=True,local_files_only=True)
processor=AutoProcessor.from_pretrained(str(M/'ultravox_b95bec8'),config=cfg,trust_remote_code=True,local_files_only=True)
model_class=get_class_from_dynamic_module(cfg.auto_map['AutoModel'],str(M/'ultravox_b95bec8'),local_files_only=True)
probe=processor(text='<|audio|>',audio=np.zeros(16000,dtype=np.float32),sampling_rate=16000,return_tensors='pt')
assert all(not x.is_cuda for x in probe.values() if torch.is_tensor(x))
assert not torch.cuda.is_initialized()
assert pathlib.Path(cfg.text_model_id).resolve()==(M/'llama32_1b_instruct_f8e6b').resolve()
record=dict(status='PASS_EXACT_NATIVE_CLASSES_CONFIG_PROCESSOR_CPU_ONLY',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 python=sys.executable,torch_cuda_initialized=False,native_model_constructed=False,native_neural_calls=0,
 native_author_class=inspect.getfile(PaddedAlignAttWhisper),corrector_class=inspect.getfile(model_class),processor_class=inspect.getfile(type(processor)),
 text_model_id=cfg.text_model_id,text_model_type=cfg.text_config.model_type,text_model_vocab_size=cfg.text_config.vocab_size,
 processor_cpu_synthetic_probe={k:dict(shape=list(v.shape),dtype=str(v.dtype)) for k,v in probe.items() if torch.is_tensor(v)},
 synthetic_probe_scope='configuration/tokenization/audio-feature interface only; no target-task inference or quality evidence')
(O/'NATIVE_INTERFACE_CPU_GATE_v5.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
