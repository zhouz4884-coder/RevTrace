import pathlib,tempfile,unittest
from stage_service import StageConsumer
from test_feedback_contract import state

class ActualStageConsumerControls(unittest.TestCase):
 def make(self,initial):
  root=pathlib.Path(__file__).resolve().parent.parent/'cpu_scratch';root.mkdir(exist_ok=True);tmp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(tmp.cleanup);return StageConsumer({'s':initial},pathlib.Path(tmp.name)/'consumer.jsonl',0.)
 def event(self,a,*ends):
  previous=a;steps=[]
  for i,end in enumerate(ends):steps.append(dict(job_id=str(i),start=previous.state,end=end.state,kind='typed_ASR_projection',actual_identity_full_step_completed=False,actual_full_C_U_completed=False));previous=end
  return dict(kind='private',source_id='s',canonical_sha=a.sha256,steps=steps,publication_id=1)
 def test_stage_projection_never_advances_certified_frontier(self):
  a,b=state(0,''),state(8,'early');v=self.make(a);v.publish(self.event(a,b));v.close();self.assertEqual(v.rows[-1]['visible_frontier'],8);self.assertEqual(v.rows[-1]['certified_frontier'],0);self.assertEqual(v.rows[-1]['view_node']['kind'],'typed_ASR_projection');self.assertFalse(v.rows[-1]['view_node']['actual_full_C_U_completed'])
 def test_compatible_canonical_advance_preserves_early_tail(self):
  a,b,c=state(0,''),state(8,'first'),state(16,'firstnext');v=self.make(a);v.publish(self.event(a,b,c));v.publish(dict(kind='canonical',source_id='s',state=b.state,processed_frontier=8,publication_id=2));v.close();self.assertEqual(v.rows[-1]['visible_frontier'],16);self.assertEqual(v.rows[-1]['certified_frontier'],8)
 def test_changed_complete_state_withdraws_stage_view(self):
  a,b,c=state(0,''),state(8,'first'),state(16,'firstnext');different=state(8,'first',last_attend_frame=777);v=self.make(a);v.publish(self.event(a,b,c));v.publish(dict(kind='canonical',source_id='s',state=different.state,processed_frontier=8,publication_id=2));v.close();self.assertEqual(v.rows[-1]['visible_frontier'],8);self.assertIsNone(v.rows[-1]['private_job'])

if __name__=='__main__':unittest.main()
