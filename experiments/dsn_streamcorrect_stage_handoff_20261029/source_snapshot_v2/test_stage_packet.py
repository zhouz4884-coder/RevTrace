import unittest,types,json,copy,sys
from unittest.mock import patch
import numpy as np,torch
from native_bridge import export_cut
from stage_packet import CandidatePacket,ReadyCache,capture_packet,input_key,restore_open,canonical,sha,encode,decode

class Tokens:
 __module__='simul_whisper.generation_progress'
 def __init__(self,tokens):self.tokens=tokens
class BeamTokens(Tokens):
 __module__='simul_whisper.generation_progress'
 def __init__(self,tokens,beam_size):super().__init__(tokens);self.beam_size=beam_size
class Logits(Tokens):__module__='simul_whisper.generation_progress'
class Context:
 def __init__(self):self.text='前';self.prefix_token_ids=[9]
 def as_token_ids(self):return self.prefix_token_ids+[ord(x) for x in self.text]
class Engine:
 def __init__(self):
  self.model=types.SimpleNamespace(device='cpu');self.cfg=types.SimpleNamespace(beam_size=4,language='zh');self.decoder_type='beam';self.detected_language='zh';self.is_warmup=False;self.first_token_generated=False;self.first_token_latency=None;self.tokens=[torch.tensor([[1,2,3,4]]).repeat(4,1)];self.initial_tokens=torch.tensor([[1,2,3,4]]);self.initial_token_length=4;self.sot_index=0;self.last_attend_frame=7;self.context=Context();self.segments=[];self.inference=types.SimpleNamespace(kv_cache={});self.token_decoder=types.SimpleNamespace(finished_sequences=None);self.kv_cache={};self.dec_attns=[]
 def _clean_cache(self):self.kv_cache={};self.dec_attns=[];self.inference.kv_cache={};self.token_decoder.finished_sequences=None

class PacketControls(unittest.TestCase):
 def setUp(self):
  self.module=types.ModuleType('simul_whisper.generation_progress');self.module.Tokens=Tokens;self.module.BeamTokens=BeamTokens;self.module.Logits=Logits;self.patch=patch.dict(sys.modules,{'simul_whisper.generation_progress':self.module});self.patch.start();self.addCleanup(self.patch.stop)
  self.audio=np.linspace(-.1,.2,16000,dtype=np.float32);self.e=Engine();self.e.segments=[torch.from_numpy(self.audio[:8000].copy())];self.start=export_cut(self.e,frontier=8000,transcript='旧',contract={'source_sha':'immutable','precision':'float32'});self.key=input_key(self.start,audio=self.audio,end=16000,is_last=False,runtime_identity={'source':'protected'});self.e.segments=[torch.from_numpy(self.audio.copy())];self.e.kv_cache={'dirty':torch.ones(3)}
  self.local=dict(current_tokens=torch.tensor([[1,2,3,4,9],[1,2,3,4,8],[1,2,3,4,7],[1,2,3,4,6]]),token_len_before_decoding=4,input_segments=self.e.segments[0],fire_detected=False,is_last=False,corrector_type='speechlm',generation=dict(starting_tokens=BeamTokens(torch.tensor([1,2,3,4]),4),token_len_before_decoding=4,frames_len=50,frames_threshold=20,logits_starting=Logits(torch.zeros(4,4,100)),no_speech_prob=.01,no_speech=False,progress=[{'logits_before_suppress':Logits(torch.zeros(4,100)),'completed':False,'sum_logprobs':[float('-inf'),0,0,0]}],first_token_latency=None,frame_delay=True))
  self.p=capture_packet(self.e,key_json=self.key,caller_locals=self.local)
 def changed(self,fn):
  body=json.loads(self.p.payload_json);fn(body);text=canonical(body);return CandidatePacket(self.p.key_json,text,sha(text.encode()))
 def test_full_ordered_beams_audio_and_context_roundtrip(self):
  target=Engine();local=restore_open(target,CandidatePacket.from_wire(self.p.wire()),expected_key=self.key);self.assertTrue(torch.equal(local['current_tokens'],self.local['current_tokens']));self.assertEqual(target.context.as_token_ids(),self.e.context.as_token_ids());self.assertEqual(local['input_segments'].numpy().tobytes(),self.audio.tobytes())
 def test_packet_is_immutable_snapshot_not_live_tensor_alias(self):
  before=self.p.wire();self.local['current_tokens'][0,4]=99;self.e.segments[0].zero_();self.assertEqual(self.p.wire(),before)
 def test_only_logit_values_are_explicitly_elided(self):
  body=self.p.verify();self.assertEqual(set(body['locals']['generation']),set(self.local['generation']));self.assertEqual(body['locals']['generation']['logits_starting']['@diagnostic_elision'],'Logits');self.assertIn('@generation_tokens',body['locals']['generation']['starting_tokens'])
 def test_required_semantic_local_missing_is_rejected(self):
  for k in ['current_tokens','input_segments','fire_detected','generation']:
   with self.subTest(k=k),self.assertRaises(AssertionError):self.changed(lambda b:b['locals'].pop(k)).verify()
 def test_diagnostic_marker_cannot_replace_beam_or_audio(self):
  for key in ['current_tokens','input_segments']:
   with self.subTest(k=key),self.assertRaises(AssertionError):self.changed(lambda b:b['locals'].__setitem__(key,b['locals']['generation']['logits_starting'])).verify()
 def test_injected_preselected_feedback_is_rejected(self):
  with self.assertRaises(AssertionError):self.changed(lambda b:b['locals']['generation'].__setitem__('error_corrector',{'corrected_appended_token_ids':[99]})).verify()
 def test_beam_loss_or_prefix_mismatch_is_rejected(self):
  with self.assertRaises(AssertionError):self.changed(lambda b:b['locals']['current_tokens']['shape'].__setitem__(0,3)).verify()
  with self.assertRaises(AssertionError):self.changed(lambda b:b['locals'].__setitem__('token_len_before_decoding',3)).verify()
 def test_checksum_mutation_is_rejected(self):
  p=CandidatePacket(self.p.key_json,self.p.payload_json+' ',self.p.payload_sha256)
  with self.assertRaises(AssertionError):p.verify()
 def test_foreign_full_input_cannot_be_restored(self):
  changed=input_key(self.start,audio=self.audio,end=15000,is_last=False,runtime_identity={'source':'protected'})
  with self.assertRaises(AssertionError):restore_open(Engine(),self.p,expected_key=changed)
 def test_fixed_asr_configuration_is_required(self):
  e=Engine();e.cfg.language='en'
  with self.assertRaises(AssertionError):restore_open(e,self.p,expected_key=self.key)
 def test_wrong_context_tokenizer_is_rejected(self):
  e=Engine();e.context.as_token_ids=lambda:[999]
  with self.assertRaises(AssertionError):restore_open(e,self.p,expected_key=self.key)
 def test_actual_buffer_and_C_audio_must_agree(self):
  import base64
  p=self.changed(lambda b:b['locals']['input_segments'].__setitem__('data',base64.b64encode(np.zeros(16000,dtype=np.float32).tobytes()).decode()))
  with self.assertRaises(AssertionError):restore_open(Engine(),p,expected_key=self.key)
 def test_ready_only_never_waits_for_future_receipt(self):
  c=ReadyCache();self.assertIsNone(c.take(self.key,9));c.admit(self.p,10);self.assertIsNone(c.take(self.key,9));self.assertEqual(c.take(self.key,10)[0],self.p);self.assertIsNone(c.take(self.key,11))
 def test_prediction_end_is_not_an_admission_input(self):
  self.assertNotIn('predicted_end',json.loads(self.key));c=ReadyCache();c.admit(self.p,10);self.assertIsNotNone(c.take(self.key,10))
 def test_scalar_and_empty_tensor_codecs(self):
  for t in [torch.tensor(4),torch.empty(0,dtype=torch.float32),torch.tensor([1.25],dtype=torch.bfloat16)]:self.assertTrue(torch.equal(t,decode(encode(t))))

if __name__=='__main__':unittest.main()
