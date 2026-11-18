"""Research gate controls: task fidelity is stronger than matching final quality."""
import copy,json,pathlib,tempfile,unittest
from run_service_campaign import audit_cell,opportunity,task

class CampaignControls(unittest.TestCase):
 def state(self,commit='a'):
  return dict(frontier=8000,transcript='x',tokens=[9],contract=dict(immutable='fixed',stage_execution=dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype='float32',source_commit=commit)))
 def test_projection_changes_only_declared_stage_tag(self):
  self.assertEqual(task(self.state('a')),task(self.state('b')))
  changed=self.state('b');changed['tokens']=[10];self.assertNotEqual(task(self.state()),task(changed))
 def test_wrong_precision_tag_cannot_hide_changed_task(self):
  changed=self.state();changed['contract']['stage_execution']['asr_dtype']='float16'
  with self.assertRaises(AssertionError):task(changed)
 def fixture(self,path,selected):
  state=self.state('b');(path/'CANONICAL_HISTORIES.json').write_text(json.dumps({'s':[dict(F=8000,state=state,token_ids=[9])]}));(path/'canonical_wal.jsonl').write_text(json.dumps(dict(source_id='s',state=state,selected=selected))+'\n')
  return dict(settings=dict(sources=[dict(source_id='s')])),[dict(source_id='s',end=8000,original_full_cut=self.state('a'),original_full_result=dict(token_ids=[9],selected_correction={'choice':'x'}))]
 def test_full_reference_passes_only_declared_projection(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);c,r=self.fixture(p,{'choice':'x'});self.assertEqual(audit_cell(c,p,r)['checked_steps'],1)
 def test_different_selection_rejected_despite_same_state_text_tokens(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);c,r=self.fixture(p,{'choice':'other'});
   with self.assertRaisesRegex(AssertionError,'selection'):audit_cell(c,p,r)
 def test_latency_screen_requires_absolute_and_relative_and_same_credit(self):
  thresholds=dict(credit_absolute_audio_seconds=.5,certified_median_absolute_seconds=.1,certified_median_relative_fraction=.1,service_energy_relative_fraction=.1)
  base=dict(arm='control',primary=dict(dual_deadline_audio_credit_seconds=8.,complete_coverage_and_original_quantile_pass=True),latency_medians=dict(all_offered_C50=2.),service_board_joules=1000.)
  candidate=copy.deepcopy(base);candidate['arm']='candidate';candidate['latency_medians']['all_offered_C50']=1.89
  self.assertFalse(opportunity(candidate,base,thresholds)['engineering_GO'])
  candidate['latency_medians']['all_offered_C50']=1.7;self.assertTrue(opportunity(candidate,base,thresholds)['latency_opportunity'])
  candidate['primary']['dual_deadline_audio_credit_seconds']=7.5;self.assertFalse(opportunity(candidate,base,thresholds)['engineering_GO'])

if __name__=='__main__':unittest.main()
