import unittest
from run_confirmation_content import contrast

def row(F,credited,supported):return dict(frontier=F,audio_seconds=.5,original_dual_credit=credited,support_at_actual_view_G=dict(raw_equal=supported,whitespace_stripped_equal=supported))

class PairAccountingControls(unittest.TestCase):
    def test_primary_gain_can_have_no_strict_content_gain(self):
        r=contrast([row(8000,True,True),row(16000,False,True)],[row(8000,True,True),row(16000,True,False)])
        self.assertEqual(r['original_credit']['net_fullspec_minus_conservative_seconds'],.5)
        self.assertEqual(r['raw_same_actual_G_supported_credit']['net_fullspec_minus_conservative_seconds'],0)
    def test_zero_net_preserves_gross_gain_and_loss(self):
        r=contrast([row(8000,True,True),row(16000,False,True)],[row(8000,False,True),row(16000,True,True)])
        self.assertEqual(r['original_credit']['net_fullspec_minus_conservative_seconds'],0)
        self.assertEqual(r['original_credit']['gross_gained_seconds'],.5)
        self.assertEqual(r['original_credit']['gross_lost_seconds'],.5)

if __name__=='__main__':unittest.main()
