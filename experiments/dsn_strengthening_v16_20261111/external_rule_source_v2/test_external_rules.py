"""Focused controls: no neural imports or source-model instantiation."""
import ast,copy,logging,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from agreement import LocalAgreement2,lcp
from support import WholeView,pick,rebase_all
from text_metrics import align,ledger
from shadow_replay import source_replay,endpoints


def cut(F,text='',context=None):
    from feedback_contract import FeedbackCut
    return FeedbackCut(dict(audio_segments=[],tokens=[],context=context or [],last_attend_frame=0,
        detected_language='zh',initial_tokens=[],initial_token_length=0,sot_index=0,
        decoder_type='original',contract='frozen',frontier=F,transcript=text))


def view(F=16000,text='你好',received=1.):
    from feedback_contract import BranchStep
    zero=cut(0); mid=cut(8000,'你'); end=cut(F,text)
    chain=(BranchStep('a',zero.sha256,zero,mid),BranchStep('b',mid.sha256,mid,end))
    return WholeView('actual', 's', received, zero, chain, end, text)


def refutation_replay():
    sid='s';z=cut(0);a8=cut(8000,'AB');c8=cut(8000,'A',['actual C/U']);a16=cut(16000,'ABX');c16=a16
    pubs=[];rows=[]
    def private(seq,t,start,end,jid,G):
        e=dict(kind='private',source_id=sid,publication_id=seq,canonical_sha=start.sha256,steps=[dict(job_id=jid,start=start.state,end=end.state)])
        pubs.append(dict(bound_owner_epoch=0,event=e));rows.append(dict(kind='private',source_id=sid,observed=t,owner_epoch=0,publication_id=seq,canonical_sha=start.sha256,text=end.transcript,visible_frontier=end.frontier,certified_frontier=G,private_job=jid))
    def canonical(seq,jseq,t,end):
        e=dict(kind='canonical',source_id=sid,publication_id=seq,state=end.state)
        pubs.append(dict(bound_owner_epoch=0,event=e));rows.append(dict(kind='canonical',source_id=sid,observed=t,owner_epoch=0,publication_id=seq,journal_sequence=jseq,canonical_sha=end.sha256,text=end.transcript,visible_frontier=end.frontier,certified_frontier=end.frontier,private_job=None))
    private(1,.8,z,a8,'p8',0);canonical(2,2,1.,c8);private(3,1.5,c8,a16,'p16',8000);canonical(4,3,2.,c16)
    facts=[dict(sequence=2,body=dict(source_id=sid,next_state=c8.state,record=dict(native_model_evaluated=True))),dict(sequence=3,body=dict(source_id=sid,next_state=c16.state,record=dict(native_model_evaluated=True)))]
    ingress=[dict(kind='accepted_input',source_id=sid,frontier=F,observed=t,original_offer=t) for F,t in ((8000,.5),(16000,1.))]
    return source_replay(sid,rows,pubs,facts,z.state,ingress,16000,2.)


class Rules(unittest.TestCase):
    def test_01_first_new_audio_does_not_confirm(self):
        a=LocalAgreement2();self.assertFalse(a.update('你好A',8000));self.assertEqual(a.confirmed,'')
    def test_02_second_distinct_audio_confirms_lcp(self):
        a=LocalAgreement2();a.update('你好A',8000);a.update('你好B',16000);self.assertEqual(a.confirmed,'你好')
    def test_03_ASR_full_same_frontier_not_two_updates(self):
        a=LocalAgreement2();a.update('你好A',8000);a.update('你好B',8000);self.assertEqual((a.updates,a.confirmed),(1,''))
    def test_04_late_older_frontier_not_update(self):
        a=LocalAgreement2();a.update('A',16000);a.update('A',8000);self.assertEqual(a.updates,1)
    def test_05_unchanged_text_new_audio_is_real_update(self):
        a=LocalAgreement2();a.update('甲',8000);a.update('甲',16000);self.assertEqual(a.confirmed,'甲')
    def test_06_Unicode_codepoints_explicit(self):
        self.assertEqual(lcp('你🙂甲','你🙂乙'),'你🙂');self.assertEqual(len(lcp('e\u0301X','e\u0301Y')),2)
    def test_07_confirmed_content_not_retracted_on_model_revision(self):
        a=LocalAgreement2();a.update('你好A',8000);a.update('你好B',16000);a.update('再见C',24000)
        self.assertEqual(a.confirmed,'你好');self.assertEqual(a.committed_prefix_conflicts_ignored,1)
    def test_08_canonical_conflict_resets(self):
        a=LocalAgreement2(confirmed='你好',previous='你好A');self.assertTrue(a.canonical('再见'))
        self.assertEqual((a.confirmed,a.previous),('再见',None))
    def test_09_full_state_refutation_resets_even_equal_text(self):
        a=LocalAgreement2(confirmed='你好');self.assertTrue(a.canonical('你好',True));self.assertEqual(a.canonical_resets,1)
    def test_10_terminal_is_not_an_agreement_update(self):
        a=LocalAgreement2();a.update('尾A',8000);a.terminal('尾B');self.assertEqual((a.updates,a.confirmed,a.terminal_releases),(1,'尾B',1))
    def test_11_author_HypothesisBuffer_core_agrees(self):
        path=Path(__file__).parent/'author'/'whisper_online.py';tree=ast.parse(path.read_text(encoding='utf8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='HypothesisBuffer')
        ns={'sys':sys,'logger':logging.getLogger('source-control')};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
        b=ns['HypothesisBuffer']();b.insert([(i+1.,i+1.5,c) for i,c in enumerate('你好A')],0);self.assertEqual(b.flush(),[])
        b.insert([(i+1.,i+1.5,c) for i,c in enumerate('你好B')],0);self.assertEqual(''.join(x[2] for x in b.flush()),'你好')
    def test_12_author_finish_flushes_without_agreement(self):
        path=Path(__file__).parent/'author'/'whisper_online.py';tree=ast.parse(path.read_text(encoding='utf8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='OnlineASRProcessor')
        ns={'sys':sys,'logger':logging.getLogger('source-control')};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
        o=ns['OnlineASRProcessor'].__new__(ns['OnlineASRProcessor']);o.transcript_buffer=SimpleNamespace(complete=lambda:[(0.,1.,'尾')]);o.asr=SimpleNamespace(sep='');o.buffer_time_offset=0.;o.audio_buffer=[0]*16000
        self.assertEqual(o.finish(),(0.,1.,'尾'))
    def test_13_partial_prefix_has_no_fractional_audio(self):
        v=view();c=WholeView('C','s',0.,cut(0),(),cut(0),'');self.assertEqual(pick([v],c,1.,confirmed='你').visible_frontier,0)
    def test_14_actual_earlier_wholeview_can_map(self):
        v=view(text='你好');c=WholeView('C','s',0.,cut(0),(),cut(0),'');self.assertEqual(pick([v],c,1.,confirmed='你好世界').visible_frontier,16000)
    def test_15_future_candidate_rejected(self):
        v=view(received=2.);c=WholeView('C','s',0.,cut(0),(),cut(0),'')
        with self.assertRaises(ValueError):pick([v],c,1.)
    def test_16_compatible_full_state_rebase_keeps_tail(self):
        status,v=view().rebase(cut(8000,'你'));self.assertEqual((status,len(v.steps),v.end.frontier),('supported',1,16000))
    def test_17_equal_text_different_context_refutes(self):
        status,v=view().rebase(cut(8000,'你',['different feedback']));self.assertEqual((status,v),('refuted',None))
    def test_18_missing_exact_boundary_refutes(self):
        self.assertEqual(view().rebase(cut(12000,'你'))[0],'refuted')
    def test_19_fixed_lag_cannot_publish_early(self):
        v=view();c=WholeView('C','s',0.,cut(0),(),cut(0),'');self.assertEqual(pick([v],c,1.49,lag=.5).identity,'C');self.assertEqual(pick([v],c,1.5,lag=.5).identity,'actual')
    def test_20_refuted_lag_pending_cannot_reappear(self):
        kept,counts=rebase_all([view()],cut(8000,'你',['different']));self.assertEqual(kept,[]);self.assertEqual(counts['refuted'],1)
    def test_21_codepoint_I_D_S_conservation(self):
        rows=[dict(text='甲乙',observed=0.),dict(text='甲丙丁',observed=2.),dict(text='甲丁',observed=3.)]
        r=ledger(rows);self.assertEqual(r['I']-r['D'],2);self.assertEqual(r['minimum_edit_distance'],r['I']+r['D']+r['S']);self.assertEqual(r['retired_characters'],r['D']+r['S'])
    def test_22_alignment_ties_keep_minimum_distance(self):
        a,b='ABA','BAB';p=align(a,b);q=align(a,b,True);self.assertEqual(sum(x[0]!='M' for x in p),sum(x[0]!='M' for x in q));self.assertNotEqual(p,q)
    def test_23_exposure_and_survivor_censoring_separate(self):
        r=ledger([dict(text='甲',observed=1.),dict(text='乙',observed=4.),dict(text='乙',observed=6.)]);self.assertEqual(r['retired_character_seconds'],3.);self.assertEqual(r['right_censored_survivor_character_seconds'],2.)
    def test_24_audio_credit_uses_all_offered_not_character_fraction(self):
        rows=[dict(observed=1.,visible_frontier=8000,certified_frontier=0),dict(observed=2.,visible_frontier=16000,certified_frontier=16000)]
        offers={8000:dict(original_offer=.5),16000:dict(original_offer=1.)};r=endpoints(rows,offers,16000)
        self.assertEqual(sum(x['weight_audio_seconds'] for x in r),1.);self.assertEqual([x['offline_shadow_D'] for x in r],[.5,1.]);self.assertTrue(all(x['dual_credit'] for x in r))
    def test_25_piecewise_coverage_keeps_partial_recovery(self):
        rows=[dict(observed=.5,visible_frontier=8000,certified_frontier=8000),dict(observed=1.,visible_frontier=0,certified_frontier=8000),dict(observed=1.5,visible_frontier=8000,certified_frontier=8000),dict(observed=2.5,visible_frontier=8000,certified_frontier=8000)]
        e=endpoints(rows,{8000:dict(original_offer=.5)},8000)[0]
        self.assertEqual(e['within_D_window_observed_covered_wall_seconds'],1.5);self.assertTrue(e['actual_retreat_after_first_cover_within_observed_D_window']);self.assertEqual(e['within_D_window_unobserved_right_censored_wall_seconds'],0.)
    def test_26_coverage_censoring_is_bound_not_extrapolation(self):
        rows=[dict(observed=.5,visible_frontier=8000,certified_frontier=8000),dict(observed=1.,visible_frontier=8000,certified_frontier=8000)]
        e=endpoints(rows,{8000:dict(original_offer=.5)},8000)[0]
        self.assertEqual(e['within_D_window_coverage_wall_seconds_lower_bound'],.5);self.assertEqual(e['within_D_window_coverage_wall_seconds_upper_bound'],2.);self.assertIsNone(e['covered_at_D_deadline'])
    def test_27_refuted_same_frontier_cannot_be_LA_sample_one(self):
        output,prefix,counts,decisions=refutation_replay()
        row=next(r for r in prefix if r['observed']==1.5)
        self.assertEqual(row['text'],'A');self.assertGreaterEqual(counts['agreement']['canonical_resets'],1)
    def test_28_fixed_lag_delays_nonterminal_canonical_too(self):
        output,prefix,counts,decisions=refutation_replay()
        lag=next(r for r in output['fixed_lag_0p5'] if r['observed']==1.)
        canonical=next(r for r in output['canonical_only'] if r['observed']==1.)
        self.assertEqual(lag['visible_frontier'],0);self.assertEqual(canonical['visible_frontier'],8000)
        self.assertEqual(output['fixed_lag_0p5'][-1]['text'],'ABX')


if __name__=='__main__':unittest.main()
