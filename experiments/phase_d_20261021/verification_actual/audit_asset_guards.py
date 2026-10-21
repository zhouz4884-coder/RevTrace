"""CPU-only mocked engine, no model weights or GPU generation."""
import hashlib,inspect,importlib.util,importlib.metadata,json,sys
from pathlib import Path
from types import SimpleNamespace
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';S=P/'continuity_v6';O=B/'results/revtrace/phaseD_20261021';sys.path[:0]=[str(S/'src')]
from qwen_asr import Qwen3ASRModel,parse_asr_output
spec=importlib.util.spec_from_file_location('guard_worker',S/'scripts/tc_live_worker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
class Sink:
 def __init__(self):self.values=[]
 def put(self,v):self.values.append(v)
class NeverCommands:
 def get(self):raise AssertionError('Guard must fail before model execution')
class StubProcessor:tokenizer=None
original=Qwen3ASRModel.from_pretrained;loaded=[]
def fake(*args,**kw):loaded.append(True);return SimpleNamespace(model=None,processor=StubProcessor())
Qwen3ASRModel.from_pretrained=fake;rows=[]
try:
 for attack,expected in [('asset','renderer/worker asset mismatch'),('parser','renderer/parser source mismatch'),('tokenizer_version','renderer/tokenizer runtime mismatch'),('processor','renderer/worker processor source mismatch')]:
  declared={'assets':{},'parse_source_sha256':hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest(),'tokenizers_version':importlib.metadata.version('tokenizers'),'processor_source_sha256':'BAD'}
  if attack=='asset':declared['assets']={'config.json':'BAD'}
  if attack=='parser':declared['parse_source_sha256']='BAD'
  if attack=='tokenizer_version':declared['tokenizers_version']='BAD'
  before=len(loaded);sink=Sink();config={'gpu':-1,'model':str(B/'models/Qwen3-ASR-1.7B'),'manifest':str(B/'datasets/tc_live_20260906/manifest.json'),'dtype':'float32','microbatch':16,'max_new_tokens':256,'render_contract':declared}
  worker.worker_main(NeverCommands(),sink,config)
  assert len(sink.values)==1 and sink.values[0]['kind']=='error' and expected in sink.values[0]['traceback']
  rows.append({'case':attack,'fail_closed':True,'mock_model_constructor_calls':len(loaded)-before,'real_gpu_generations':0,'tier':'CPU_MOCK_ENGINE_GUARD_NOT_GPU_FAULT'})
finally:Qwen3ASRModel.from_pretrained=original
(O/'CPU_ASSET_GUARD_AUDIT.json').write_text(json.dumps({'status':'PASS_CPU_GUARDS','cases':rows,'worker_source_sha256':hashlib.sha256((S/'scripts/tc_live_worker.py').read_bytes()).hexdigest()},indent=2)+'\n');print(json.dumps(rows))
