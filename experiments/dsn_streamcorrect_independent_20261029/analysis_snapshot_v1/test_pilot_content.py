from __future__ import annotations
import unittest
from analyze_pilot_content import analyze,quantile,same_f_support
from native_content_endpoint import analyze_cell


class PilotContentControls(unittest.TestCase):
    def fixture(self):
        meta=dict(cell_id="fixture",arm="fixture",stage="fixture",cohort="fixture",repeat=0)
        config=dict(settings=dict(sources=[dict(source_id="s",frames=24000)]))
        origin=dict(origin_perf=0.,original_D=2.,original_C=8.)
        def row(t,F,C,text,kind):return dict(source_id="s",observed=t,visible_frontier=F,certified_frontier=C,text=text,kind=kind,view_node=dict(kind=kind))
        rows=[row(.6,0,0,"","canonical"),row(1.1,16000,16000,"A","private"),row(1.7,24000,16000,"B ","private"),row(1.9,24000,24000,"B","canonical")]
        wal=[dict(state=dict(frontier=F,transcript=T),state_sha256=str(F)) for F,T in ((8000,""),(16000,"A"),(24000,"B"))]
        content,_,_,frontiers=analyze_cell(meta,rows,{"s":dict(frames=24000)},0.)
        primary=dict(dual_deadline_audio_credit_seconds=1.5,offered_frontiers=3,offered_audio_seconds=1.5,
                     primary_linear_all_offered_D99=quantile([f["D"] for f in frontiers],.99),
                     primary_linear_all_offered_C99=quantile([f["C"] for f in frontiers],.99),D2_misses_all_offered=0,C8_misses_all_offered=0)
        return meta,config,origin,rows,wal,primary,content

    def test_higher_cover_is_not_an_exact_offered_F_comparison(self):
        rr,ff,*_=analyze(*self.fixture())
        self.assertEqual(rr["primary"]["dual_deadline_audio_credit_seconds"],1.5)
        self.assertFalse(ff[0]["support_at_exact_offered_F"]["comparable"])
        self.assertIsNone(ff[0]["support_at_exact_offered_F"]["raw_equal"])
        self.assertTrue(ff[0]["support_at_actual_view_G"]["raw_equal"])
        self.assertEqual(rr["raw_support"]["original_credit_with_exact_offered_F_aligned_text_match"],.5)

    def test_raw_and_whitespace_are_distinct_and_fulltext_required(self):
        rr,ff,*_=analyze(*self.fixture())
        self.assertFalse(ff[2]["support_at_actual_view_G"]["raw_equal"])
        self.assertTrue(ff[2]["support_at_actual_view_G"]["whitespace_stripped_equal"])
        self.assertEqual(rr["raw_support"]["original_credit_with_same_actual_G_complete_text_match"],1.)
        self.assertEqual(rr["whitespace_stripped_support"]["original_credit_with_same_actual_G_complete_text_match"],1.5)
        s=same_f_support(dict(visible_frontier=10,text="A"),{10:dict(state=dict(transcript="AB"),state_sha256="x")})
        self.assertFalse(s["raw_equal"])

    def test_no_higher_or_later_reference_substitution(self):
        s=same_f_support(dict(visible_frontier=10,text="A"),{20:dict(state=dict(transcript="A"),state_sha256="x")})
        self.assertFalse(s["exact_reference_exists"])
        self.assertIsNone(s["raw_equal"])

    def test_text_erasure_does_not_fabricate_audio_withdrawal(self):
        rr,ff,events,spans,first,unique,withdrawals,corrections=analyze(*self.fixture())
        self.assertEqual(rr["audio_frontier_withdrawals"],0)
        self.assertEqual(len(corrections),2)
        self.assertEqual(rr["canonical_text_replacement_rows"],1)
        self.assertEqual(corrections[-1]["raw_LCP_erased"],1)
        self.assertEqual(len(first),2)
        self.assertEqual(len(unique),3)

    def test_changed_original_credit_is_rejected(self):
        fixture=list(self.fixture());fixture[5]["dual_deadline_audio_credit_seconds"]=1.
        with self.assertRaises(AssertionError):analyze(*fixture)


if __name__=="__main__":unittest.main()
