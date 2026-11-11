import unittest
from exposure_audit_core import naive_prefix_lengths,areas,span_totals
class IndependentExposureControls(unittest.TestCase):
 def test_future_rewrite(self):self.assertEqual(naive_prefix_lengths([dict(text='abc'),dict(text='abx')]),[2,3])
 def test_growth(self):self.assertEqual(naive_prefix_lengths([dict(text='a'),dict(text='ab')]),[1,2])
 def test_empty_break(self):self.assertEqual(naive_prefix_lengths([dict(text='a'),dict(text='')]),[0,0])
 def test_area(self):self.assertEqual(areas([dict(observed=0,text='abc'),dict(observed=2,text='ab')],[2,2]),(6,4))
 def test_terminal_has_no_area(self):self.assertEqual(areas([dict(observed=9,text='abcdef')],[6]),(0,0))
 def test_closed_and_censored_separate(self):self.assertEqual(span_totals([dict(retracted=True,closing_observed=4,first_observed=1),dict(retracted=False,censor_observed=9,first_observed=2)]),(3,7))
