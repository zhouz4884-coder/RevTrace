import unittest,math
from core import endpoints,score,eos_counterfactual
class Controls(unittest.TestCase):
    def rows(self):return [dict(D=1.,C=2.,audio_seconds=.5,is_EOS=False) for _ in range(16)]+[dict(D=3.,C=2.,audio_seconds=.1380625,is_EOS=True)]
    def test_weighted_EOS_is_not_half_second_or_uncertainty(self):
        r=self.rows();self.assertAlmostEqual(score(eos_counterfactual(r,1.999999))['credit_audio_seconds']-score(r)['credit_audio_seconds'],.1380625)
    def test_nonEOS_late_point_can_remain_after_EOS_idealization(self):
        r=self.rows();r[15]['D']=2.5
        self.assertFalse(score(eos_counterfactual(r,1.999999))['quantile_pass']);self.assertFalse(score(eos_counterfactual(r,0.))['quantile_pass']);self.assertEqual(r[-1]['D'],3.)
    def test_missing_nonEOS_stays_missing_with_fixed_C(self):
        r=self.rows();r[0]['D']=None;r[3]['C']=9.;x=eos_counterfactual(r,0.)
        self.assertEqual(score(x)['missing_D'],1);self.assertEqual(score(x)['C8_misses'],1);self.assertFalse(score(x)['quantile_pass'])
    def test_all_original_frontiers_and_partial_EOS_remain(self):
        self.assertEqual(endpoints(16000),[8000,16000]);self.assertEqual(endpoints(16209),[8000,16000,16209]);self.assertEqual(len(eos_counterfactual(self.rows(),0.)),17)
if __name__=='__main__':unittest.main()
