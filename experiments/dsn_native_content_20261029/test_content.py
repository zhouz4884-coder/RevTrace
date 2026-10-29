import unittest
from analyze_content import Occurrences,analyze_cell,event_type,normalize

class ContentControls(unittest.TestCase):
    def test_cumulative_nonempty_F_advance_is_not_new_text(self):
        rows=[dict(source_id='s',observed=100.6,kind='canonical',text='A',visible_frontier=8000,certified_frontier=8000),
              dict(source_id='s',observed=101.1,kind='canonical',text='A',visible_frontier=16000,certified_frontier=16000)]
        s,e,sp,f=analyze_cell(dict(cell_id='case'),rows,{'s':{'frames':16000}},100.)
        self.assertEqual(s['original_dual_credit_audio_seconds'],1.)
        self.assertEqual(s['raw']['introduced_code_point_occurrences'],1)
        self.assertEqual(s['raw']['original_credit_by_first_visible_row_class']['unchanged'],.5)
        self.assertEqual(s['raw']['positive_F_advance_with_unchanged_text_rows'],1)
    def test_append_preserves_prefix_identity(self):
        t=Occurrences('c','s','raw');t.observe('A',1.,0,'private');unit=t.active[0].copy();t.observe('AB',2.,1,'private')
        self.assertEqual(t.active[0],unit);self.assertEqual(t.active[1]['birth_row'],1)
    def test_LCP_replacement_does_not_assume_LCS_alignment(self):
        t=Occurrences('c','s','raw');t.observe('ABC',1.,0,'private');r=t.observe('AXC',2.,1,'canonical')
        self.assertEqual((r['LCP_code_points'],r['erased_code_points'],r['introduced_code_points']),(1,2,2))
        self.assertEqual(t.active[-1]['birth_row'],1)
    def test_reappearing_literal_gets_new_identity(self):
        t=Occurrences('c','s','raw');t.observe('AB',1.,0,'private');t.observe('A',2.,1,'canonical');t.observe('AB',3.,2,'private')
        self.assertEqual(t.closed[0]['text'],'B');self.assertEqual(t.active[-1]['birth_row'],2)
    def test_whitespace_is_only_normalization(self):
        self.assertEqual(normalize(' \tA\n B '),'AB')
        self.assertEqual(event_type(normalize('A B'),normalize('A\tB'))[0],'unchanged')
        self.assertNotEqual(normalize('A!'),normalize('a'))
    def test_no_change_has_no_churn(self):
        t=Occurrences('c','s','raw');t.observe('AB',1.,0,'private');r=t.observe('AB',2.,1,'canonical')
        self.assertEqual((r['introduced_code_points'],r['erased_code_points']),(0,0));self.assertFalse(t.closed)
    def test_survivors_censored_at_last_actual_observation(self):
        t=Occurrences('c','s','raw');t.observe('AB',2.,0,'private');t.finish(3.,1)
        self.assertEqual(t.closed[0]['observed_lifetime_seconds'],1.);self.assertTrue(t.closed[0]['right_censored_at_last_source_observation']);self.assertFalse(t.closed[0]['retracted'])
    def test_code_points_and_erase_only_are_explicit(self):
        t=Occurrences('c','s','raw');r=t.observe(chr(0x7532)+chr(0x4e59),1.,0,'private')
        self.assertEqual(r['introduced_code_points'],2);r=t.observe(chr(0x7532),2.,1,'canonical')
        self.assertEqual(r['classification'],'erase_only');self.assertEqual(t.closed[0]['code_points'],1)

if __name__=='__main__':unittest.main()
