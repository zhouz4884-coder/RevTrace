import unittest
from ledger_core import overlap,proxy,indexed,digest
class LedgerControls(unittest.TestCase):
 def test_before_begin(self):self.assertEqual(overlap(2,6,1),0)
 def test_inside_interval(self):self.assertEqual(overlap(2,6,4),2)
 def test_after_end(self):self.assertEqual(overlap(2,6,7),4)
 def test_proxy_is_prefix_minus_export(self):self.assertEqual(proxy(4,2,6,7),1)
 def test_duplicate_identity_rejected(self):
  with self.assertRaises(ValueError):indexed([dict(job_id='j'),dict(job_id='j')])
 def test_text_equality_does_not_imply_cut_equality(self):
  self.assertNotEqual(digest(dict(text='相同',tokens=[1])),digest(dict(text='相同',tokens=[2])))
