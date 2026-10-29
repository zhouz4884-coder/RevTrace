import copy,unittest
from midpoint_analysis import strong_decision,full_non_eos_interval

class StrongDecisionControls(unittest.TestCase):
    def test_full_nonterminal_accepted(self):self.assertTrue(full_non_eos_interval(dict(audio_seconds=2.,frontier=32000),64000))
    def test_exact_two_second_terminal_excluded(self):self.assertFalse(full_non_eos_interval(dict(audio_seconds=2.,frontier=64000),64000))
    def test_partial_excluded(self):self.assertFalse(full_non_eos_interval(dict(audio_seconds=.215,frontier=64000),64000))
    def test_nearly_two_not_exact_full(self):self.assertFalse(full_non_eos_interval(dict(audio_seconds=1.999999999,frontier=32000),64000))
    def runs(self):
        return [dict(arm=arm,repeat=r,whole_run_dual_P99_pass=True,
            strong_full_non_EOS_timely_compatible_windows=int(arm=='R1_S0' and r<2),
            compatible=dict(timely_interval_loss_windows=int(arm=='R1_S0')))
            for arm in ['R0_S0','R0_S1','R1_S0','R1_S1'] for r in range(3)]
    def test_two_of_three_suffices(self):self.assertTrue(strong_decision(self.runs(),True)['strong_witness'])
    def test_one_of_three_not_enough(self):
        r=self.runs();next(x for x in r if x['arm']=='R1_S0' and x['repeat']==1)['strong_full_non_EOS_timely_compatible_windows']=0
        self.assertFalse(strong_decision(r,True)['strong_witness'])
    def test_one_P99_failure_blocks_strong(self):
        r=self.runs();next(x for x in r if x['arm']=='R1_S1')['whole_run_dual_P99_pass']=False
        self.assertFalse(strong_decision(r,True)['strong_witness'])
    def test_joint_loss_blocks_strong(self):
        r=self.runs();next(x for x in r if x['arm']=='R1_S1')['compatible']['timely_interval_loss_windows']=1
        self.assertFalse(strong_decision(r,True)['strong_witness'])
    def test_history_difference_blocks_attribution(self):self.assertFalse(strong_decision(self.runs(),False)['strong_witness'])
    def test_missing_repeat_not_success(self):self.assertFalse(strong_decision(self.runs()[:-1],True)['strong_witness'])
    def test_first_credit_not_requirement(self):
        r=self.runs()
        for x in r:x['original_dual_credited_audio_seconds']=100 if x['arm']=='R1_S0' else 90
        self.assertTrue(strong_decision(r,True)['strong_witness'])

if __name__=='__main__':unittest.main()
