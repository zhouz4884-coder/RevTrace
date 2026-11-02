"""Pre-result statistical/accounting controls, never model or raw experiments."""
from __future__ import annotations
import copy,math,unittest
from report_common import (ReportError,SPEAKERS,DRAWS,SEED,percentile,run_p99_distribution,effect_points,paired_bootstrap)
from posterior_content import parse_partition,combine,pair_content

def source_rows(delta=.1):
    return [dict(source_id=str(i),offered_audio_s=1.,conservative_credit_audio_s=.4,fullcall_credit_audio_s=.4+delta) for i in range(SPEAKERS)]

def posterior_fixture(raw=(.1,.2,.2),whitespace=(.25,.05,.2),counts=None):
    def part(values):return dict(original_credit_supported_seconds=values[0],original_credit_mismatching_seconds=values[1],original_credit_unknown_seconds=values[2],all_offered_frontier_counts=counts or dict(supported=1,mismatching=1,unknown=1))
    original=dict(primary=dict(offered_audio_seconds=1.,offered_frontiers=3,dual_deadline_audio_credit_seconds=.5),content=dict(original_dual_credit_audio_seconds=.5,offered_frontiers=3),posterior_whole_text_support=dict(raw=part(raw),whitespace_stripped=part(whitespace)))
    cell=dict(cell_id='controlled',source_id='source',speaker_id='speaker',policy='conservative',repeat=0,offered_audio_s=1.,offered_frontiers=3,credit_audio_s=.5)
    return original,cell

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
    def test_posterior_credit_and_all_offered_partitions_conserve(self):
        o,c=posterior_fixture();p=parse_partition(o,c);self.assertAlmostEqual(p[0]['supported_audio_s']+p[0]['mismatching_audio_s']+p[0]['unknown_audio_s']+p[0]['deadline_missed_audio_s'],1.)
        o['posterior_whole_text_support']['raw']['original_credit_supported_seconds']=.2
        with self.assertRaises(ReportError):parse_partition(o,c)
        o,c=posterior_fixture();o['content']['offered_frontiers']=2
        with self.assertRaises(ReportError):parse_partition(o,c)
    def test_posterior_raw_and_whitespace_remain_distinct(self):
        o,c=posterior_fixture();p=parse_partition(o,c)
        self.assertEqual([x['mode'] for x in p],['raw','whitespace_stripped']);self.assertEqual(p[0]['supported_audio_s'],.1);self.assertEqual(p[1]['supported_audio_s'],.25)
    def test_posterior_unknown_is_not_mismatch_and_zero_counter_keys_valid(self):
        o,c=posterior_fixture(raw=(0.,0.,.5),whitespace=(0.,0.,.5),counts=dict(unknown=3));p=parse_partition(o,c)
        self.assertEqual(p[0]['unknown_audio_s'],.5);self.assertEqual(p[0]['mismatching_audio_s'],0.);self.assertEqual(p[0]['all_offered_supported_frontiers'],0)
        o['posterior_whole_text_support']['raw']['all_offered_frontier_counts']['other']=1
        with self.assertRaises(ReportError):parse_partition(o,c)
    def test_posterior_negative_paired_supported_difference_not_clipped(self):
        o,c=posterior_fixture(raw=(.3,.2,0.),whitespace=(.3,.2,0.));con=combine([parse_partition(o,c)[0]])
        o,c=posterior_fixture(raw=(.1,.2,.2),whitespace=(.1,.2,.2));full=combine([parse_partition(o,c)[0]])
        paired=pair_content(con,full);self.assertAlmostEqual(paired['supported_gain_audio_s'],-.2);self.assertAlmostEqual(paired['supported_gain_pp'],-20.)

if __name__=='__main__':unittest.main()

