"""CPU state-machine controls for the strong two-full speculative assembly."""
import copy,unittest,numpy as np
from feedback_contract import FeedbackCut
from fullspec_policy import FullSpecCoordinator

def cut(F,text=''):
 return FeedbackCut(dict(audio_segments=[],tokens=[[[1,2,3,4]]*4,[[F]]*4],
  context=dict(text='',prefix_token_ids=[9],token_ids=[9]),last_attend_frame=F//100,
  detected_language='zh',initial_tokens=[[1,2,3,4]],initial_token_length=4,sot_index=0,
  decoder_type='beam',contract=dict(source_sha='immutable',dtype='float32'),frontier=F,transcript=text))

class FullSpecControls(unittest.TestCase):
 def setUp(self):
  self.sid='s';self.root=cut(0);self.c=FullSpecCoordinator(initials={self.sid:self.root.state},
   audio={self.sid:np.zeros(40000,dtype=np.float32)},runtime_identity={'source':'fixed'},
   source_frames={self.sid:40000},authority_workers=('f0','f1'))
 def register(self,j,worker,start=None,end=None,t=1):
  start=self.root if start is None else start;end=start.frontier+8000 if end is None else end
  return self.c.register(job_id=j,worker=worker,kind='full',source_id=self.sid,start=start,end=end,dispatched_perf=t)
 def early(self,j,end,t=2):
  job=self.c.jobs[j];p=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,
   original_full_infer_completed=False,token_ids=[end.frontier],end=end.state,end_state_sha=end.sha256)
  e=dict(kind='asr_early',worker=job['worker'],job_id=j,dispatch_epoch=job['dispatch_epoch'],source_id=self.sid,
   start_state=job['start'].state,start_state_sha=job['start'].sha256,end_frontier=job['end'],
   producer_role='authority',produced_perf=t,projection=p,candidate_wire=None)
  return self.c.admit_asr(job['worker'],e,received_perf=t+.1)
 def completed(self,j,end,t=5):
  job=self.c.jobs[j]
  return dict(worker=job['worker'],job_id=j,dispatch_epoch=job['dispatch_epoch'],source_id=self.sid,
   start=job['start'].state,end=end.state,record=dict(start_state=job['start'].sha256,end_state=end.sha256,
   role='authority',candidate_handoff=False,token_ids=[end.frontier],selected_correction={'actual':'C'}))
 def finish(self,j,end,t=5):
  e=self.completed(j,end,t);return self.c.complete(e['worker'],e,received_perf=t)
 def two_pending(self):
  self.register('j0','f0');p1=cut(8000,'p1');self.early('j0',p1)
  self.register('j1','f1',p1,t=3);p2=cut(16000,'p2');self.early('j1',p2,t=4)
  return p1,p2
 def test_prefer_current_missing_then_legal_projection_tail(self):
  self.assertIsNone(self.c.next_full_start(self.sid,7999))
  self.assertTrue(self.c.next_full_start(self.sid,8000).same(self.root))
  self.register('j0','f0');self.assertIsNone(self.c.next_full_start(self.sid,16000))
  p=cut(8000,'pred');self.early('j0',p);self.assertTrue(self.c.next_full_start(self.sid,16000).same(p))
 def test_duplicate_full_input_and_busy_worker_rejected(self):
  self.register('j0','f0')
  with self.assertRaisesRegex(ValueError,'duplicate'):self.register('dup','f1')
  p=cut(8000,'pred');self.early('j0',p)
  with self.assertRaisesRegex(ValueError,'worker already'):self.register('busy','f0',p)
 def test_inflight_promoted_without_renaming_birth_or_recompute(self):
  p1,p2=self.two_pending();birth=self.c.jobs['j1']['birth_canonical_sha'];self.finish('j0',p1)
  self.assertEqual(self.c.active_authority[self.sid],'j1');self.assertTrue(self.c.jobs['j1']['promoted_to_canonical'])
  self.assertEqual(self.c.jobs['j1']['birth_canonical_sha'],birth);self.assertEqual(birth,self.root.sha256)
  self.assertTrue(self.c.next_full_start(self.sid,24000).same(p2))
 def test_completed_future_buffers_then_commits_when_actual_parent_matches(self):
  p1,p2=self.two_pending();self.assertEqual(self.finish('j1',p2)['kind'],'buffered_full')
  self.assertTrue(self.c.canonical(self.sid).same(self.root));self.assertEqual(self.c.pop_ready_commits(),[])
  self.finish('j0',p1);ready=self.c.pop_ready_commits();self.assertEqual(len(ready),1)
  self.assertEqual(ready[0]['job']['job_id'],'j1');self.assertTrue(self.c.canonical(self.sid).same(p2))
 def test_original_C_end_can_differ_from_identity_prediction(self):
  self.register('j0','f0');self.early('j0',cut(8000,'pred'));actual=cut(8000,'corrected')
  out=self.finish('j0',actual);self.assertEqual(out['kind'],'canonical');self.assertTrue(self.c.canonical(self.sid).same(actual))
 def test_conditional_completed_full_replaces_projection_and_prunes_suffix(self):
  p1,p2=self.two_pending();actual2=cut(16000,'full C changed prediction')
  self.assertEqual(self.finish('j1',actual2)['kind'],'buffered_full');self.assertTrue(self.c.tail(self.sid).same(actual2))
  self.assertTrue(self.c.canonical(self.sid).same(self.root))
  self.assertTrue(self.c.nodes['j1']['actual_full_C_U_completed'])
  self.finish('j0',p1);self.assertTrue(self.c.pop_ready_commits()[0]['cut'].same(actual2))
 def test_unknown_future_parent_never_becomes_known_wrong(self):
  self.two_pending();self.assertEqual(self.c.invalidations(),{})
  with self.assertRaisesRegex(ValueError,'no owned'):self.c.abandon('f1','j1',{'kind':'future unconfirmed'})
 def test_actual_equal_F_parent_mismatch_supplies_proof_and_no_commit(self):
  p1,p2=self.two_pending();self.finish('j0',cut(8000,'actual differs'))
  proof=self.c.invalidations()['j1'];self.assertEqual(proof['kind'],'actual_canonical_disagrees_with_complete_start')
  self.assertEqual(proof['witness_frontier'],8000);out=self.finish('j1',p2)
  self.assertEqual(out['kind'],'discarded');self.assertEqual(self.c.pop_ready_commits(),[])
 def test_known_wrong_C_entry_can_abandon_without_closed_cut(self):
  self.two_pending();self.finish('j0',cut(8000,'wrong prediction'));proof=self.c.invalidations()['j1']
  out=self.c.abandon('f1','j1',proof);self.assertEqual(out['kind'],'abandoned_full')
  self.assertNotIn('cut',out);self.assertFalse(out['certified_output']);self.assertNotIn('j1',self.c.jobs)
 def test_foreign_channel_or_proof_cannot_abandon(self):
  self.two_pending();self.finish('j0',cut(8000,'wrong'));proof=self.c.invalidations()['j1']
  with self.assertRaisesRegex(ValueError,'foreign'):self.c.abandon('f0','j1',proof)
  forged=dict(proof,witness_frontier=999)
  with self.assertRaisesRegex(ValueError,'no owned'):self.c.abandon('f1','j1',forged)
 def test_buffered_full_wrong_actual_parent_is_discarded(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.finish('j0',cut(8000,'not p1'))
  self.assertEqual(self.c.pop_ready_commits(),[]);self.assertNotIn('j1',self.c.completed_full)
  self.assertEqual(self.c.discarded_full[-1]['job']['job_id'],'j1')
 def test_full_result_prune_does_not_pretend_unconfirmed_conditional_C_is_Canon(self):
  p1,p2=self.two_pending();self.finish('j1',cut(16000,'changed'));self.register('j2','f1',self.c.tail(self.sid),t=6)
  self.assertEqual(self.c.invalidations(),{});self.assertTrue(self.c.canonical(self.sid).same(self.root))
 def test_epoch_change_invalidates_jobs_even_when_parent_hash_identical(self):
  self.register('j0','f0');self.c.reset_epoch(self.sid,self.root)
  self.assertNotIn(self.sid,self.c.active_authority);self.assertEqual(self.c.invalidations()['j0']['kind'],'session_epoch_changed')
  self.register('new','f1');self.assertEqual(self.c.active_authority[self.sid],'new')
  self.assertEqual(self.finish('j0',cut(8000,'old'))['kind'],'discarded')
 def test_physical_channel_binding_and_end_hash_still_required(self):
  self.register('j0','f0');e=self.completed('j0',cut(8000,'x'))
  with self.assertRaises(ValueError):self.c.complete('f1',e,received_perf=5)
  e['record']['end_state']='wrong'
  with self.assertRaises(ValueError):self.c.complete('f0',e,received_perf=5)
 def test_offered_and_lookahead_limits(self):
  self.register('j0','f0');p=cut(8000,'p');self.early('j0',p)
  self.assertIsNone(self.c.next_full_start(self.sid,15999));self.assertIsNone(self.c.next_full_start(self.sid,16000,max_ahead_frames=8000))
 def test_job_identity_cannot_be_reused_after_completion(self):
  self.register('j0','f0');self.finish('j0',cut(8000,'x'))
  with self.assertRaisesRegex(ValueError,'reused'):self.register('j0','f0',self.c.canonical(self.sid))
 def test_two_completed_future_nodes_commit_in_actual_parent_order(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.register('j2','f1',p2,t=6)
  p3=cut(24000,'p3');self.early('j2',p3,t=7);self.finish('j2',p3,t=8)
  self.assertEqual(self.c.pop_ready_commits(),[]);self.finish('j0',p1,t=9)
  commits=self.c.pop_ready_commits();self.assertEqual([r['job']['job_id'] for r in commits],['j1','j2'])
  self.assertEqual([r['view_event_snapshot']['canonical_sha'] for r in commits],[p2.sha256,p3.sha256])
  self.assertTrue(self.c.canonical(self.sid).same(p3))
 def test_ancestor_mismatch_does_not_cancel_unresolved_future_complete_input(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.register('j2','f1',p2,t=6)
  self.finish('j0',cut(8000,'different parent'),t=7)
  self.assertNotIn('j2',self.c.invalidations());loss=self.c.dependency_support_losses()['j2']
  self.assertEqual(loss['witness_frontier'],8000);self.assertFalse(loss['c_entry_cancellation_authorized'])
  self.assertEqual(self.c.jobs['j2']['start'].frontier,16000)
 def test_future_complete_input_can_converge_and_promote_despite_old_ancestor_loss(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.register('j2','f1',p2,t=6)
  actual1=cut(8000,'different parent');self.finish('j0',actual1,t=7)
  self.register('actual_next','f0',actual1,t=8);self.finish('actual_next',p2,t=9)
  self.assertEqual(self.c.active_authority[self.sid],'j2');self.assertNotIn('j2',self.c.invalidations())
  self.assertNotIn('j2',self.c.dependency_support_losses())
  self.assertTrue(self.c.jobs['j2']['promoted_to_canonical'])
  self.assertEqual(self.c.jobs['j2']['birth_canonical_sha'],self.root.sha256)
 def test_future_start_is_cancelable_only_after_its_own_frontier_disagrees(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.register('j2','f1',p2,t=6)
  actual1=cut(8000,'different parent');self.finish('j0',actual1,t=7)
  self.assertNotIn('j2',self.c.invalidations());self.register('actual_next','f0',actual1,t=8)
  self.finish('actual_next',cut(16000,'different complete start'),t=9)
  proof=self.c.invalidations()['j2'];self.assertEqual(proof['witness_frontier'],16000)
  self.assertEqual(proof['kind'],'actual_canonical_disagrees_with_complete_start')
 def test_buffered_current_parent_prevents_duplicate_dispatch(self):
  p1,p2=self.two_pending();self.finish('j1',p2);self.finish('j0',p1)
  # Its full result is already ready and must be committed rather than rerun.
  start=self.c.next_full_start(self.sid,16000);self.assertIsNone(start)
  self.assertEqual(len(self.c.pop_ready_commits()),1)
 def test_returned_proof_cannot_mutate_owned_invalidation(self):
  self.two_pending();self.finish('j0',cut(8000,'different'))
  proof=self.c.invalidations()['j1'];proof['witness_frontier']=999
  with self.assertRaisesRegex(ValueError,'no owned'):self.c.abandon('f1','j1',proof)

if __name__=='__main__':unittest.main()
