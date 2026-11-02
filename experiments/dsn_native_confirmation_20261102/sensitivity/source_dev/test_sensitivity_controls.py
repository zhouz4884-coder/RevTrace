"""Statistical/accounting controls only; no raw reader, model or serving run."""
from __future__ import annotations
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent/'vendor'))
from sensitivity_common import SOURCES,credit,denominator,validate_primary,validate_source_extent,GateError
from analyze_sensitivity import curves

class Controls(unittest.TestCase):
    def test_C8_failure_never_filters_offered_denominator(self):
        rows=[dict(audio_seconds=.5,D=1.,C=1.),dict(audio_seconds=.5,D=1.,C=9.)]
        self.assertEqual(credit(rows,6.),.5);self.assertEqual(denominator(rows),1.)
    def test_missing_D_stays_in_denominator(self):
        rows=[dict(audio_seconds=.5,D=None,C=1.),dict(audio_seconds=.2,D=1.,C=1.)]
        self.assertEqual(credit(rows,6.),.2);self.assertEqual(denominator(rows),.7)
    def test_threshold_boundary_exact(self):
        rows=[dict(audio_seconds=.5,D=2.,C=8.),dict(audio_seconds=.5,D=2.0001,C=8.)]
        self.assertEqual(credit(rows,2.),.5);self.assertEqual(credit(rows,2.25),1.)
    def test_partial_EOS_weight_not_full_chunk(self):
        rows=[dict(audio_seconds=.5,D=1.,C=1.),dict(audio_seconds=.01,D=9.,C=1.)]
        self.assertEqual(credit(rows,2.),.5);self.assertEqual(denominator(rows),.51)
    def test_original_unweighted_P99_is_not_weighted_coverage(self):
        rs=[dict(source_id='S',frontier=8000,is_EOS=False,offer=10.5,audio_seconds=.5,D=.5,C=.5,D2=True,C8=True),dict(source_id='S',frontier=8160,is_EOS=True,offer=10.51,audio_seconds=.01,D=9.,C=1.,D2=False,C8=True)]
        p=dict(frontiers=rs,offered_frontiers=2,offered_audio_seconds=.51,primary_linear_all_offered_D99=8.915,primary_linear_all_offered_C99=.995,dual_deadline_audio_credit_seconds=.5,D2_misses_all_offered=1,C8_misses_all_offered=0,EOS_D2_misses=1,missing_D_frontiers=0,missing_C_frontiers=0,complete_coverage_and_original_quantile_pass=False)
        result=validate_primary(p,'S',10.);self.assertFalse(result['original_D2_C8_pass']);self.assertGreater(credit(rs,2.)/denominator(rs),.98)
    def test_changed_original_P99_rejected(self):
        rs=[dict(source_id='S',frontier=8000,is_EOS=True,offer=10.5,audio_seconds=.5,D=1.5,C=1.,D2=True,C8=True)]
        p=dict(frontiers=rs,offered_frontiers=1,offered_audio_seconds=.5,primary_linear_all_offered_D99=1.6,primary_linear_all_offered_C99=1.,dual_deadline_audio_credit_seconds=.5,D2_misses_all_offered=0,C8_misses_all_offered=0,EOS_D2_misses=0,missing_D_frontiers=0,missing_C_frontiers=0,complete_coverage_and_original_quantile_pass=True)
        with self.assertRaises(GateError):validate_primary(p,'S',10.)
    def test_source_and_bank_not_pooled_and_negative_gain_retained(self):
        units=[]
        for b in ('matched','resident'):
            for sid in SOURCES:
                for arm in ('conservative','fullcall'):
                    for r in (0,1):
                        d=1. if arm=='conservative' else 3.
                        units.append(dict(bank=b,source_id=sid,arm=arm,repeat=r,primary=dict(frontiers=[dict(audio_seconds=.5,D=d,C=1.)])))
        sources,banks,pairs=curves(units,[2.])
        self.assertEqual(len(pairs),8);self.assertTrue(all(r['paired_gain_audio_s']==-1. for r in pairs))
        self.assertTrue(all(r['independent_speakers']==4 for r in banks))
        self.assertTrue(all(r['timing_repeats']==2 for r in sources))
    def test_original_grid_contains_D2(self):
        grid=[.5+i*.25 for i in range(23)];self.assertEqual((grid[0],grid[-1]),(.5,6.));self.assertIn(2.,grid)
    def test_source_receipt_catches_missing_tail_even_if_rows_self_consistent(self):
        rs=[dict(frontier=8000,audio_seconds=.5)]
        spec=dict(frames=8160,header=dict(sample_rate=16000,frames=8160))
        with self.assertRaises(GateError):validate_source_extent(rs,spec)

if __name__=='__main__':unittest.main()
