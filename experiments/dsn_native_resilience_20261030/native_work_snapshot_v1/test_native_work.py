import math,unittest
from native_work import selected_record_counts
class Controls(unittest.TestCase):
 def test_markers_are_strict_bool_not_inferred_from_returned_ids(self):
  r=selected_record_counts([dict(native_model_evaluated=True,token_ids=[]),dict(native_model_evaluated=False,token_ids=[1,2]),dict(native_model_evaluated=1,token_ids=[3]),{}]);self.assertEqual(r['canonical_selected_steps'],4);self.assertEqual(r['native_model_evaluated_marker_true'],1);self.assertEqual(r['native_model_evaluated_marker_false'],1);self.assertEqual(r['native_model_evaluated_marker_unknown'],2);self.assertEqual(r['returned_token_ids_total'],3);self.assertEqual(r['zero_returned_id_steps'],1);self.assertEqual(r['returned_ids_unknown'],1)
 def test_missing_nonfinite_negative_seconds_never_become_measured_zero(self):
  r=selected_record_counts([{'model_seconds':2.},{'model_seconds':0.},{'model_seconds':None},{'model_seconds':math.inf},{'model_seconds':-1},{'model_seconds':True}]);self.assertEqual(r['model_seconds_sum'],2.);self.assertEqual(r['model_seconds_unknown'],4)
 def test_correction_key_presence_does_not_mean_non_null_or_a_forward(self):
  r=selected_record_counts([{'selected_correction':None},{'selected_correction':{}},{'selected_correction':{'chosen':'a'}},{}]);self.assertEqual(r['correction_key_present'],3);self.assertEqual(r['correction_payload_none'],1);self.assertEqual(r['correction_payload_non_null'],2);self.assertEqual(r['correction_key_missing'],1)
 def clock(self,end=11.,marker=True,cert=16000,replay=False,original=12.,before=True):
  from native_work import post_fault_clock_audit
  rows=([dict(kind='provisional',source_id='s',observed=9.,certified_frontier=8000)] if before else [])+[dict(kind='canonical',source_id='s',observed=12.,certified_frontier=cert,journal_sequence=2,recovery_replay=replay),dict(kind='canonical',source_id='s',observed=14.,certified_frontier=24000,journal_sequence=3,recovery_replay=False)]
  facts={2:dict(record=dict(model_end=end,native_model_evaluated=marker),next_state={'frontier':16000}),3:dict(record=dict(model_end=13.,native_model_evaluated=True),next_state={'frontier':24000})}
  return post_fault_clock_audit(rows,facts,dict(fault_perf=10.,pre_fault_durable_sequence=1,first_new_model_completed_after_fault_and_certified_consume_perf=original))
 def test_strict_clock_has_actual_advance_and_positive_model_end_margin(self):
  r=self.clock();self.assertTrue(r['original_selected_strict_verified']);self.assertEqual(r['strict_fault_to_new_certified_consume_seconds'],2.);self.assertEqual(r['strict_first_actual_consume']['model_end_minus_fault'],1.)
 def test_model_end_equal_fault_is_not_strict(self):
  r=self.clock(end=10.);self.assertFalse(r['original_selected_strict_verified']);self.assertEqual(r['strict_fault_to_new_certified_consume_seconds'],4.)
 def test_no_new_marker_or_no_certified_advance_is_not_new_work(self):
  for kwargs in ({'marker':False},{'cert':8000},{'replay':True}):
   r=self.clock(**kwargs);self.assertFalse(r['original_selected_strict_verified']);self.assertEqual(r['strict_fault_to_new_certified_consume_seconds'],4.)
 def test_missing_actual_prefault_baseline_stays_unknown(self):
  r=self.clock(before=False);self.assertIsNone(r['original_selected_strict_verified']);self.assertIsNone(r['strict_fault_to_new_certified_consume_seconds'])
 def test_missing_original_clock_is_not_replaced_or_filled_with_zero(self):
  r=self.clock(original=None);self.assertIsNone(r['original_selected_consume_perf']);self.assertIsNone(r['original_selected_strict_verified']);self.assertEqual(r['strict_fault_to_new_certified_consume_seconds'],2.)
if __name__=='__main__':unittest.main()
