"""CPU accounting fixtures. They are not GPU serving evidence."""
import math
import unittest
from summarize_v5 import good_audio, quantile, quality_counts, visibility_sensitivity, paired_effect


class AccountingTests(unittest.TestCase):
    def test_first_visible_credit_is_not_stable_credit_after_withdrawal(self):
        views = [dict(observed=1.,valid_visible_frontier=10,certified_frontier=0),
                 dict(observed=1.5,valid_visible_frontier=0,certified_frontier=0),
                 dict(observed=3.,valid_visible_frontier=10,certified_frontier=10)]
        extra = visibility_sensitivity(views,10,0.,2.9)
        self.assertEqual(extra['stable_display'],3.)
        self.assertTrue(extra['first_visible_withdrawn_before_certified'])
        self.assertFalse(extra['visible_at_owner_install'])
        row = dict(audio_seconds=2.,display=1.,commit=2.9,certified_consumer=3.,**extra)
        self.assertEqual(good_audio([row]),2.)
        self.assertEqual(good_audio([row],display_key='stable_display',commit_key='certified_consumer'),0.)

    def test_early_display_preserves_pending_commit_value(self):
        views = [dict(observed=1.,valid_visible_frontier=10,certified_frontier=0),
                 dict(observed=7.,valid_visible_frontier=10,certified_frontier=10)]
        extra = visibility_sensitivity(views,10,0.,6.9)
        self.assertEqual(extra['stable_display'],1.)
        self.assertFalse(extra['first_visible_withdrawn_before_certified'])
        self.assertEqual(good_audio([dict(audio_seconds=2.,display=1.,commit=6.9)]),2.)

    def test_unfinished_frontier_cannot_vanish_or_earn_credit(self):
        rows = [dict(audio_seconds=2.,display=1.,commit=1.),
                dict(audio_seconds=2.,display=None,commit=None)]
        self.assertEqual(sum(r['audio_seconds'] for r in rows),4.)
        self.assertEqual(good_audio(rows),2.)
        self.assertTrue(math.isinf(quantile([r['commit'] for r in rows],.99)))

    def test_full_reference_retains_unfinished_words(self):
        q = quality_counts('one two three','one')
        self.assertEqual(q['WER_errors'],2)
        self.assertEqual(q['reference_words'],3)

    def test_ratio_of_group_medians_not_used_as_paired_effect(self):
        baseline = {0:{'x':1.},1:{'x':10.},2:{'x':100.}}
        changed = {0:{'x':2.},1:{'x':20.},2:{'x':50.}}
        result = paired_effect(baseline,changed,'x',draws=100)
        self.assertEqual(result['paired_values'],[1.,1.,-.5])
        self.assertEqual(result['paired_median'],1.)
        self.assertFalse(result['all_repeats_positive'])


if __name__ == '__main__':
    unittest.main()
