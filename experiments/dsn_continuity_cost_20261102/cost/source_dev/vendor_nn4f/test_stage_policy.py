import unittest,types,copy,torch,numpy as np
import test_stage_packet as fixtures
from stage_policy import StageCoordinator
from native_bridge import export_cut
from feedback_contract import FeedbackCut

class OwnershipControls(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.PacketControls();self.f.setUp();self.addCleanup(self.f.doCleanups);self.sid='source';self.c=StageCoordinator(initials={self.sid:self.f.start.state},audio={self.sid:self.f.audio},runtime_identity={'source':'protected'},source_frames={self.sid:24000},producer_worker='producer',authority_workers=('authority',))
  # Input target16k is nonfinal in this policy fixture, exactly as its packet.
  self.c.audio[self.sid]=np.concatenate([self.f.audio,np.zeros(8000,dtype=np.float32)])
  self.f.e._clean_cache();self.f.e.tokens.append(torch.tensor([[9]]).repeat(4,1));self.end=export_cut(self.f.e,frontier=16000,transcript='旧x',contract=self.f.start.state['contract']);self.proj=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,original_full_infer_completed=False,token_ids=[9],end=self.end.state,end_state_sha=self.end.sha256)
  self.job=self.c.register(job_id='p1',worker='producer',kind='full',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=1)
  self.event=dict(kind='candidate',worker='producer',job_id='p1',dispatch_epoch=0,source_id=self.sid,start_state=self.f.start.state,start_state_sha=self.f.start.sha256,end_frontier=16000,producer_role='protected_asr_stage',produced_perf=2,projection=self.proj,candidate_wire=self.f.p.wire())
 def admit(self,e=None,channel='producer'):return self.c.admit_asr(channel,e or self.event,received_perf=3,ready_perf=4)
 def test_correct_packet_key_wrong_physical_channel_rejected(self):
  with self.assertRaises(ValueError):self.admit(channel='authority')
 def test_correct_packet_key_foreign_worker_or_job_rejected(self):
  for key,val in [('worker','foreign'),('job_id','unknown')]:
   e=dict(self.event);e[key]=val
   with self.subTest(key=key),self.assertRaises(ValueError):self.admit(e)
 def test_current_packet_does_not_authorize_wrong_successor_input(self):
  self.admit();wrong=self.end.state;wrong['transcript']='other';start=FeedbackCut(wrong)
  with self.assertRaises(ValueError):self.c.register(job_id='p2',worker='producer',kind='full',source_id=self.sid,start=start,end=24000,dispatched_perf=5)
 def test_root_change_before_C_U_completion_rejected(self):
  self.c.register(job_id='a1',worker='authority',kind='full',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=2);self.c.owners[self.sid].canonical=self.end
  r=dict(worker='authority',job_id='a1',dispatch_epoch=0,source_id=self.sid,start=self.f.start.state,end=self.end.state,record=dict(start_state=self.f.start.sha256,end_state=self.end.sha256,candidate_handoff=False))
  with self.assertRaises(ValueError):self.c.complete('authority',r,received_perf=5)
 def test_epoch_change_during_C_U_rejects_even_identical_parent_hash(self):
  self.c.register(job_id='a1',worker='authority',kind='full',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=2);self.c.reset_epoch(self.sid,self.f.start)
  r=dict(worker='authority',job_id='a1',dispatch_epoch=0,source_id=self.sid,start=self.f.start.state,end=self.end.state,record=dict(start_state=self.f.start.sha256,end_state=self.end.sha256,candidate_handoff=False))
  with self.assertRaises(ValueError):self.c.complete('authority',r,received_perf=5)
 def test_old_epoch_producer_completion_cannot_append_after_reset(self):
  self.c.reset_epoch(self.sid,self.f.start);r=dict(worker='producer',job_id='p1',dispatch_epoch=0,source_id=self.sid,start=self.f.start.state,end=self.end.state,record=dict(start_state=self.f.start.sha256,end_state=self.end.sha256,token_ids=[9]))
  with self.assertRaises(ValueError):self.c.complete('producer',r,received_perf=5)
  self.assertEqual(self.c.tail(self.sid).sha256,self.f.start.sha256)
 def test_new_epoch_can_dispatch_without_old_active_owner_slot(self):
  self.c.register(job_id='a1',worker='authority',kind='full',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=2);self.c.reset_epoch(self.sid,self.f.start)
  self.c.register(job_id='a2',worker='authority',kind='full',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=5);self.assertEqual(self.c.active_authority[self.sid],'a2')
 def test_no_wait_or_use_before_complete_verified_receipt(self):
  self.assertIsNone(self.c.take_ready(self.sid,16000,2));self.admit();self.assertIsNone(self.c.take_ready(self.sid,16000,3.9));self.assertIsNotNone(self.c.take_ready(self.sid,16000,4))
 def test_prediction_end_difference_does_not_invalidate_ready_C_input(self):
  receipt=self.admit()['receipt'];ready=self.c.take_ready(self.sid,16000,5);self.assertEqual(receipt,ready);self.c.register(job_id='a1',worker='authority',kind='consume',source_id=self.sid,start=self.f.start,end=16000,dispatched_perf=5,receipt=ready);actual=self.end.state;actual['transcript']='corrected';actual=FeedbackCut(actual)
  r=dict(worker='authority',job_id='a1',dispatch_epoch=0,source_id=self.sid,start=self.f.start.state,end=actual.state,record=dict(start_state=self.f.start.sha256,end_state=actual.sha256,candidate_handoff=True));self.c.complete('authority',r,received_perf=6);self.assertEqual(self.c.canonical(self.sid).sha256,actual.sha256);self.assertEqual(self.c.consumptions[0]['birth_canonical_sha'],self.f.start.sha256)
 def test_message_cannot_rewrite_original_birth_ownership(self):
  event=dict(self.event,birth_canonical_sha='forged');r=self.admit(event)['receipt'];self.assertEqual(r.birth_canonical_sha,self.f.start.sha256);self.assertEqual(r.producer_job_id,'p1')
 def test_projection_is_not_claimed_as_learned_C_or_full_completion(self):
  e=copy.deepcopy(self.event);e['projection']['learned_C_executed']=True
  with self.assertRaises(ValueError):self.admit(e)

if __name__=='__main__':unittest.main()
