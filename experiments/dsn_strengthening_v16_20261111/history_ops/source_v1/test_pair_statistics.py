import unittest
from historical_pairs import exact_sign_diagnostic
from speaker_sensitivity import recount_new8


class PairControls(unittest.TestCase):
    def test_exact_sign_zero_pairs(self):
        self.assertEqual(exact_sign_diagnostic([0,0])['two_sided_p'],1)
    def test_exact_sign_eight_positive(self):
        self.assertEqual(exact_sign_diagnostic([1]*8)['two_sided_p'],2/256)
    def test_new8_two_sided_minimum_and_leave_out(self):
        report=dict(timing_repeats_per_policy=2,source_pairs=[dict(speaker_id=str(i),source_id='s'+str(i),
            timing_repeats=2,offered_audio_s=10,conservative_credit_audio_s=1,fullcall_credit_audio_s=6,
            paired_gain_audio_s=5) for i in range(8)])
        r=recount_new8(report)
        self.assertEqual(r['exact_two_sided_p'],2/256)
        self.assertEqual(len(r['all_leave_zero_one_two_out']),37)
        self.assertTrue(all(x['coverage_gain_pp']==50 for x in r['all_leave_zero_one_two_out']))
    def test_repeated_speaker_fails(self):
        with self.assertRaises(ValueError):recount_new8(dict(source_pairs=[dict(speaker_id='same')]*8))
