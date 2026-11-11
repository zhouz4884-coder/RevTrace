"""CPU isolation controls; original-tail math is tested independently."""
import unittest,copy,torch,types
from unittest.mock import patch
from candidate_bridge import CandidateBridge
import test_stage_packet as fixtures

class ProjectionIsolation(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.PacketControls();self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.e.tokenizer=types.SimpleNamespace(decode=lambda ids:'projection');self.b=CandidateBridge.__new__(CandidateBridge);self.b.engine=self.f.e;self.b.compiled_tail=None;self.b.runtime_identity={'source':'protected'}
 def fake_identity_tail(self,e,local,compiled=None):
  self.assertEqual(type(local['corrector_model']),object);self.assertIsNone(local['corrector_processor']);e.tokens.append(torch.tensor([[99]]).repeat(4,1));e.context.text='projection';e.context.prefix_token_ids.append(77);local['generation']['error_corrector']={'projection_only':True};e._clean_cache();return [99],local['generation']
 def test_projection_does_not_mutate_live_asr_or_generation(self):
  before_tokens=[x.clone() for x in self.f.e.tokens];before_audio=self.f.e.segments[0].clone();before_context=self.f.e.context.as_token_ids();before_generation=set(self.f.local['generation'])
  with patch('native_tail.run_identity_tail',self.fake_identity_tail):r=self.b.project_open(caller_locals=self.f.local,start=self.f.start,end=16000)
  self.assertEqual(r['kind'],'typed_ASR_stage_identity_feedback_projection');self.assertFalse(r['learned_C_executed']);self.assertFalse(r['original_full_infer_completed']);self.assertEqual(len(self.f.e.tokens),len(before_tokens));self.assertTrue(torch.equal(before_audio,self.f.e.segments[0]));self.assertEqual(before_context,self.f.e.context.as_token_ids());self.assertEqual(before_generation,set(self.f.local['generation']));self.assertIn('dirty',self.f.e.kv_cache)
 def test_packet_projection_and_open_projection_share_update(self):
  with patch('native_tail.run_identity_tail',self.fake_identity_tail):
   a=self.b.project_open(caller_locals=self.f.local,start=self.f.start,end=16000);b=self.b.project_packet(packet=self.f.p,audio=self.f.audio,start=self.f.start,end=16000,is_last=False)
  self.assertEqual(a['end'],b['end']);self.assertEqual(a['token_ids'],b['token_ids'])

if __name__=='__main__':unittest.main()
