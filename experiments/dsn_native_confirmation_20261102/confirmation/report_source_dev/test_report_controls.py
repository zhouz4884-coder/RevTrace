"""Pre-result statistical/accounting controls, never model or raw experiments."""
from __future__ import annotations
import copy,math,unittest
from report_common import (ReportError,SPEAKERS,DRAWS,SEED,percentile,run_p99_distribution,effect_points,paired_bootstrap)

def source_rows(delta=.1):
    return [dict(source_id=str(i),offered_audio_s=1.,conservative_credit_audio_s=.4,fullcall_credit_audio_s=.4+delta) for i in range(SPEAKERS)]

class Controls(unittest.TestCase):
    def test_fixed_size_and_credit_bounds(self):
        with self.assertRaises(ReportError):effect_points(source_rows()[:-1])
        r=source_rows();r[0]['fullcall_credit_audio_s']=1.1
        with self.assertRaises(ReportError):effect_points(r)
    def test_source_mean_and_duration_ratio_are_distinct(self):
        r=source_rows();r[-1].update(offered_audio_s=100.,conservative_credit_audio_s=50.,fullcall_credit_audio_s=40.)
        p=effect_points(r);self.assertAlmostEqual(p['mean_speaker_paired_gain_pp'],7.5)
        self.assertLess(p['duration_weighted_ratio_gain_pp'],0)
    def test_negative_effects_are_not_clipped_or_excluded(self):
        b,s=paired_bootstrap(source_rows(-.1));self.assertEqual(len(s),DRAWS)
        self.assertLess(b['intervals']['mean_speaker_paired_gain_pp']['upper95'],0)
        self.assertLess(b['intervals']['duration_weighted_ratio_gain_pp']['upper95'],0)
    def test_constant_source_effect_has_degenerate_correct_interval(self):
        b,_=paired_bootstrap(source_rows(.1));interval=b['intervals']['duration_weighted_ratio_gain_pp']
        self.assertAlmostEqual(interval['lower95'],10.);self.assertAlmostEqual(interval['upper95'],10.)
    def test_seeded_resampling_reproducible_with_eight_speaker_draws(self):
        r=source_rows();r[0]['fullcall_credit_audio_s']=.2
        a,da=paired_bootstrap(r);b,db=paired_bootstrap(r)
        self.assertEqual(a,b);self.assertEqual(da,db);self.assertEqual(a['seed'],SEED)
        self.assertTrue(all(len(x['sampled_source_indices'].split(','))==8 for x in da))
    def test_percentile_is_linear_not_nearest_rank(self):
        self.assertEqual(percentile([0.,10.],.25),2.5)
    def test_missing_or_unbounded_run_not_silently_dropped(self):
        d=run_p99_distribution([1.,None]);self.assertIsNone(d['median_seconds']);self.assertIsNone(d['maximum_seconds'])
        self.assertEqual(d['missing_or_unbounded_runs'],1);self.assertEqual(d['run_count'],2)
    def test_repeats_already_combined_are_not_resampled_as_frontiers(self):
        b,_=paired_bootstrap(source_rows());self.assertEqual(b['independent_speakers'],8)
        self.assertEqual(b['draws'],20000);self.assertIn('two timing repeats held together',b['method'])

if __name__=='__main__':unittest.main()

