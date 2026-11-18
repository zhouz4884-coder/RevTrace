"""Protected ASR candidate packets. Open state is distinct from a closed cut.

Only unused diagnostic Logits values are elided, by the pinned original tail's
read-set. Every C/U semantic local is required; no object/pickle decoding.
"""
from __future__ import annotations
import base64,dataclasses,hashlib,json,time,math
from feedback_contract import FeedbackCut

KIND='protected_original_asr_open_candidate_v1'
AUTHOR_SHA='9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7'
SEMANTIC_LOCALS=('current_tokens','token_len_before_decoding','input_segments','fire_detected','is_last','generation','corrector_type')
ENGINE_FIELDS=('segments','tokens','last_attend_frame','detected_language','initial_tokens','initial_token_length','sot_index','decoder_type','is_warmup','first_token_generated','first_token_latency')
GENERATION_KEYS=('starting_tokens','token_len_before_decoding','frames_len','frames_threshold','logits_starting','no_speech_prob','no_speech','progress','first_token_latency','frame_delay')
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def cfg_value(cfg):return dataclasses.asdict(cfg) if dataclasses.is_dataclass(cfg) else vars(cfg).copy()

def encode(x):
 import torch,numpy as np
 if torch.is_tensor(x):
  t=x.detach().cpu().contiguous();raw=t.reshape(-1).view(torch.uint8).numpy().tobytes();return {'@tensor':str(t.dtype),'shape':list(t.shape),'data':base64.b64encode(raw).decode()}
 if isinstance(x,np.ndarray):return {'@array':str(x.dtype),'shape':list(x.shape),'data':base64.b64encode(np.ascontiguousarray(x).tobytes()).decode()}
 if isinstance(x,np.generic):return encode(x.item())
 if isinstance(x,float) and not math.isfinite(x):return {'@float':repr(x)}
 if x is None or isinstance(x,(str,int,float,bool)):return x
 if isinstance(x,(list,tuple)):return [encode(v) for v in x]
 if isinstance(x,dict):return {str(k):encode(v) for k,v in x.items()}
 name=type(x).__name__;module=type(x).__module__
 if module.endswith('generation_progress') and name=='Logits':
  return {'@diagnostic_elision':'Logits','shape':list(x.tokens.shape),'dtype':str(x.tokens.dtype),'reason':'pinned C/U tail never reads diagnostic Logits values; full debug payload equality not claimed'}
 if module.endswith('generation_progress') and name in ('Tokens','BeamTokens'):
  r={'@generation_tokens':name,'tokens':encode(x.tokens)}
  if name=='BeamTokens':r['beam_size']=int(x.beam_size)
  return r
 raise TypeError('unsupported semantic packet object: '+module+'.'+name)

def decode(x,device='cpu'):
 import torch,numpy as np
 if isinstance(x,list):return [decode(v,device) for v in x]
 if isinstance(x,dict):
  if '@tensor' in x:
   assert set(x)=={'@tensor','shape','data'};dtype=getattr(torch,x['@tensor'].removeprefix('torch.'));raw=bytearray(base64.b64decode(x['data'],validate=True));t=torch.frombuffer(raw,dtype=torch.uint8).clone().view(dtype).reshape(x['shape']) if raw else torch.empty(x['shape'],dtype=dtype);return t.to(device)
  if '@array' in x:
   assert set(x)=={'@array','shape','data'};return np.frombuffer(base64.b64decode(x['data'],validate=True),dtype=np.dtype(x['@array'])).copy().reshape(x['shape'])
  if '@generation_tokens' in x:
   from simul_whisper.generation_progress import Tokens,BeamTokens
   return BeamTokens(decode(x['tokens'],device),x['beam_size']) if x['@generation_tokens']=='BeamTokens' else Tokens(decode(x['tokens'],device))
  if '@diagnostic_elision' in x:
   assert x['@diagnostic_elision']=='Logits';return x.copy()
  if '@float' in x:return float(x['@float'])
  return {k:decode(v,device) for k,v in x.items()}
 return x

def input_key(start:FeedbackCut,*,audio,end,is_last,runtime_identity):
 import numpy as np
 assert 0<=start.frontier<end<=len(audio)
 segment=np.asarray(audio[start.frontier:end],dtype=np.float32)
 return canonical(dict(kind=KIND,complete_start_cut=start.state,source_sha256=start.state['contract']['source_sha'],target_frontier=int(end),is_last=bool(is_last),added_audio_float32_sha256=sha(segment.tobytes()),runtime_identity=runtime_identity))

def validate_tree(x,path=()):
 """Diagnostic markers may never stand in for a true C/U semantic input."""
 if isinstance(x,list):
  for i,v in enumerate(x):validate_tree(v,path+(str(i),))
 elif isinstance(x,dict):
  if '@diagnostic_elision' in x:
   assert path[:2]==('locals','generation') and path[-1] in ('logits_starting','logits_before_suppress','logits_after_suppress')
   assert x['@diagnostic_elision']=='Logits' and set(x)=={'@diagnostic_elision','shape','dtype','reason'}
  elif '@tensor' in x or '@array' in x:
   import numpy as np
   assert set(x)==({'@tensor','shape','data'} if '@tensor' in x else {'@array','shape','data'})
   dtype=x.get('@array',x.get('@tensor','').removeprefix('torch.'));sizes={'float32':4,'float16':2,'bfloat16':2,'int64':8,'int32':4,'bool':1,'uint8':1}
   assert dtype in sizes and all(isinstance(i,int) and i>=0 for i in x['shape'])
   assert len(base64.b64decode(x['data'],validate=True))==math.prod(x['shape'])*sizes[dtype]
  elif '@generation_tokens' in x:
   assert x['@generation_tokens'] in ('Tokens','BeamTokens');validate_tree(x['tokens'],path+('tokens',))
   if x['@generation_tokens']=='BeamTokens':assert x['beam_size']==4
  elif '@float' in x:assert path[:2]==('locals','generation') and x['@float'] in ('inf','-inf','nan')
  else:
   assert not any(k.startswith('@') for k in x)
   for k,v in x.items():validate_tree(v,path+(k,))
 else:assert x is None or isinstance(x,(str,int,float,bool))

@dataclasses.dataclass(frozen=True)
class CandidatePacket:
 key_json:str
 payload_json:str
 payload_sha256:str
 kind:str=KIND
 def verify(self):
  assert self.kind==KIND and sha(self.payload_json.encode())==self.payload_sha256
  key=json.loads(self.key_json);p=json.loads(self.payload_json)
  assert key['kind']==KIND and p['kind']==KIND and p['open_state'] is True and p['closed_cut'] is False
  validate_tree(p)
  assert p['author_sha256']==AUTHOR_SHA and p['producer_role']=='protected_asr_stage'
  assert set(SEMANTIC_LOCALS)<=set(p['locals']) and set(ENGINE_FIELDS)<=set(p['engine'])
  assert p['locals']['corrector_type']=='speechlm' and p['locals']['is_last']==key['is_last']
  assert isinstance(p['locals']['fire_detected'],bool) and isinstance(p['locals']['is_last'],bool)
  generation=p['locals']['generation'];assert isinstance(generation,dict) and set(GENERATION_KEYS)<=set(generation) and 'error_corrector' not in generation
  assert p['engine']['is_warmup'] is False and p['engine']['decoder_type']=='beam'
  for name in ('current_tokens','input_segments'):
   v=p['locals'][name];assert isinstance(v,dict) and ('@tensor' in v or name=='input_segments' and '@array' in v),'semantic tensor cannot be an elision marker'
  tokens=p['locals']['current_tokens'];assert tokens['@tensor']=='torch.int64' and len(tokens['shape'])==2 and tokens['shape'][0]==4
  assert 4<=p['locals']['token_len_before_decoding']<=tokens['shape'][1]
  assert p['locals']['token_len_before_decoding']==generation['token_len_before_decoding']
  assert p['engine']['detected_language']=='zh' and p['cfg']['beam_size']==4 and p['cfg']['language']=='zh'
  assert isinstance(generation['starting_tokens'],dict) and generation['starting_tokens'].get('@generation_tokens')=='BeamTokens'
  assert p['key_sha256']==sha(self.key_json.encode())
  return p
 def wire(self):
  self.verify();return canonical(dataclasses.asdict(self)).encode()
 @classmethod
 def from_wire(cls,wire):
  d=json.loads(wire);assert set(d)=={'key_json','payload_json','payload_sha256','kind'};p=cls(**d);p.verify();return p
 @property
 def bytes(self):return len(self.wire())

def capture_packet(engine,*,key_json,caller_locals):
 assert not engine.is_warmup
 local={k:encode(caller_locals[k]) for k in SEMANTIC_LOCALS}
 state={k:encode(getattr(engine,k)) for k in ENGINE_FIELDS}
 state['context']=dict(text=engine.context.text,prefix_token_ids=list(engine.context.prefix_token_ids),token_ids=list(engine.context.as_token_ids()))
 payload=dict(kind=KIND,open_state=True,closed_cut=False,author_sha256=AUTHOR_SHA,producer_role='protected_asr_stage',key_sha256=sha(key_json.encode()),locals=local,engine=state,cfg=cfg_value(engine.cfg),unused_ephemeral_resources=dict(kv_cache='original C/U never reads cache values; original cleanup still required',dec_attns='original C/U never reads attention values; original cleanup still required',beam_survivors='original tail only resets decoder, never reads survivors'),created_perf=time.perf_counter())
 text=canonical(payload);packet=CandidatePacket(key_json,text,sha(text.encode()));packet.verify();return packet

def restore_open(engine,packet:CandidatePacket,*,expected_key):
 import torch,numpy as np
 p=packet.verify();assert packet.key_json==expected_key,'candidate input mismatch; do not restore'
 assert cfg_value(engine.cfg)==p['cfg'],'original ASR configuration differs'
 device=engine.model.device
 # These resources are unread by C/U and will be reset again by the original
 # extracted tail; clearing avoids retaining unrelated fallback work's cache.
 engine._clean_cache()
 for k in ENGINE_FIELDS:
  setattr(engine,k,decode(p['engine'][k],device if k in ('tokens','initial_tokens') else 'cpu'))
 c=p['engine']['context'];engine.context.text=c['text'];engine.context.prefix_token_ids=c['prefix_token_ids']
 assert engine.context.as_token_ids()==c['token_ids'],'tokenizer/context differs'
 local={k:decode(v,device if k in ('current_tokens','generation') else 'cpu') for k,v in p['locals'].items()}
 merged=torch.cat(engine.segments,dim=0) if len(engine.segments)>1 else engine.segments[0]
 a=local['input_segments'];a=a.detach().cpu().numpy() if torch.is_tensor(a) else np.asarray(a)
 assert a.dtype==np.float32 and merged.detach().cpu().numpy().tobytes()==a.tobytes(),'captured C audio and native buffer differ'
 return local

class ReadyCache:
 """Only fully received immutable packets can be selected. No wait primitive."""
 def __init__(self,limit=64):self.ready={};self.limit=limit
 def admit(self,packet,received_perf):
  packet.verify();self.ready[packet.key_json]=(packet,float(received_perf))
  while len(self.ready)>self.limit:del self.ready[next(iter(self.ready))]
 def take(self,key,dispatch_perf):
  value=self.ready.get(key)
  if value is None or value[1]>dispatch_perf:return None
  del self.ready[key];return value
