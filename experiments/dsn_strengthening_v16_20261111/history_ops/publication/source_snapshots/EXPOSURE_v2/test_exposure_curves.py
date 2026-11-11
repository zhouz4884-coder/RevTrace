"""Prepared v2 controls; do not run before new freeze/preregistration."""
import unittest
from exposure_curves import stable_prefix_curve,exposure_from_spans
class ExposureControls(unittest.TestCase):
 def test_future_revision_retroactively_limits_prefix(self):
  r=stable_prefix_curve([dict(observed=0,text='abc'),dict(observed=2,text='abx'),dict(observed=5,text='abxy')])
  self.assertEqual([x['retrospective_stable_prefix_code_points'] for x in r['curves']],[2,3,4])
  self.assertEqual(r['curves'][-1]['step_duration_seconds'],0)
 def test_area_and_edit_exposure_conservation(self):
  r=stable_prefix_curve([dict(observed=0,text='ab'),dict(observed=3,text='ac'),dict(observed=5,text='ac')])
  spans=[dict(char='b',retracted=True,retraction_operation='S',lifetime_seconds=3),
   dict(char='a',retracted=False,observed_lifetime_seconds=5),dict(char='c',retracted=False,observed_lifetime_seconds=2)]
  e=exposure_from_spans(spans,r,'minimum_edit')
  self.assertEqual(e['exposed_then_modified_code_point_seconds'],3)
  self.assertEqual(e['right_censored_survivor_observed_code_point_seconds'],7)
 def test_lcp_is_separate(self):
  r=stable_prefix_curve([dict(observed=0,text='a'),dict(observed=2,text='')])
  with self.assertRaises(ValueError):exposure_from_spans([dict(char='a',retracted=True,retraction_operation='LCP_SUFFIX_CLOSE',lifetime_seconds=2)],r,'minimum_edit')
 def test_future_horizon_is_censored(self):
  r=stable_prefix_curve([dict(observed=4,text='abcd')])
  self.assertEqual(r['visible_code_point_seconds'],0)
  self.assertTrue(r['terminal_full_length_is_vacuous_at_frozen_horizon'])
 def test_clock_reversal_fails(self):
  with self.assertRaises(ValueError):stable_prefix_curve([dict(observed=2,text='a'),dict(observed=1,text='a')])
 def test_wrong_residence_area_fails(self):
  r=stable_prefix_curve([dict(observed=0,text='a'),dict(observed=2,text='a')])
  with self.assertRaises(ValueError):exposure_from_spans([dict(char='a',retracted=False,observed_lifetime_seconds=1)],r,'minimum_edit')
