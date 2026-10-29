import unittest
from continuity import analyze_cell

class Controls(unittest.TestCase):
    def case(self, compatible=True, timely=True, next_root_covers=True, recover_at_deadline=False):
        rows=[dict(session_id=0,source_kind='display',observed_perf=.8,valid_visible_frontier=20,certified_frontier=0),
              dict(session_id=0,source_kind='canonical-display',canonical_version=1,observed_perf=1.,valid_visible_frontier=10,certified_frontier=10),
              dict(session_id=0,source_kind='canonical-display',canonical_version=2,observed_perf=2. if recover_at_deadline else 3.,valid_visible_frontier=20 if next_root_covers else 10,certified_frontier=20 if next_root_covers else 10)]
        if not next_root_covers:
            rows.append(dict(session_id=0,source_kind='canonical-display',canonical_version=3,observed_perf=4.,valid_visible_frontier=20,certified_frontier=20))
        final=rows[-1]['observed_perf']
        fs=[dict(session_id=0,frontier=20,audio_seconds=1.,original_ready_perf=0 if timely else -2,
                 first_actual_visible_perf=.8,first_actual_certified_perf=final,
                 display_latency=.8 if timely else 2.8,commit_view_latency=final if timely else final+2,dual_credit=timely)]
        uu=[]
        prev=20
        for r in rows[1:]:
            uu.append(dict(session_id=0,version=r['canonical_version'],observed_perf=r['observed_perf'],
                 before_visible_F=prev,after_visible_F=r['valid_visible_frontier'],consumer_matched=True,
                 complete_selected_root_matched=True,compatible=compatible,compatibility_reason='synthetic-control',chain=[],
                 visible_job_id='p',selected_job_id='a',selected_P_sha256='x'))
            prev=r['valid_visible_frontier']
        return analyze_cell(dict(cell_id='synthetic'),rows,fs,uu)

    def test_compatible_timely_loss(self):
        r,l,e=self.case();self.assertEqual(r['compatible']['timely_deficit_area'],2.)
        self.assertEqual(r['compatible']['original_D2_read_in_deficit_audio_seconds'],1.)
    def test_incompatible_separate(self):
        r,_,_=self.case(compatible=False);self.assertEqual(r['compatible']['timely_deficit_area'],0.)
        self.assertEqual(r['incompatible']['timely_deficit_area'],2.)
    def test_untimely_not_credited(self):
        r,l,e=self.case(timely=False);self.assertEqual(l,[]);self.assertEqual(len(e),1)
    def test_cross_root_censored(self):
        r,l,e=self.case(next_root_covers=False);self.assertEqual(l[0]['stop_perf'],3.)
        self.assertTrue(l[0]['right_censored_at_next_canonical'])
    def test_unknown_not_compatible(self):
        r,_,_=self.case(compatible=None);self.assertEqual(r['UNKNOWN']['timely_deficit_area'],2.)
    def test_right_open_deadline(self):
        r,_,_=self.case(recover_at_deadline=True);self.assertEqual(r['compatible']['original_D2_read_in_deficit_audio_seconds'],0.)

if __name__=='__main__':
    unittest.main()
