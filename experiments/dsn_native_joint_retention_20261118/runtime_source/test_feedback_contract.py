import copy,unittest
from feedback_contract import FeedbackCut,BranchStep,Reconciler,STATE_FIELDS

def state(frontier,text,**changes):
    s=dict(audio_segments=[{'sha256':str(frontier),'samples':frontier,'dtype':'float32'}],tokens=[[[1,2]]],
        context={'prefix_token_ids':[3],'token_ids':[],'text':''},last_attend_frame=4,detected_language='zh',
        initial_tokens=[[1]],initial_token_length=1,sot_index=0,decoder_type='beam',contract={'id':'frozen'},
        frontier=frontier,transcript=text)
    s.update(changes);return FeedbackCut(s)

class Contracts(unittest.TestCase):
    def test_actual_boundary_and_ahead_tail_retained(self):
        c0=state(0,'');c1=state(8,'你');c2=state(16,'你好')
        r=Reconciler(c0,True);r.append(BranchStep('a',c0.sha256,c0,c1));r.append(BranchStep('b',c1.sha256,c1,c2))
        x=r.install(copy.deepcopy(c1));self.assertTrue(x['compatible']);self.assertEqual(r.visible()['visible_frontier'],16)
    def test_conservative_discards_even_when_full_boundary_matches(self):
        c0=state(0,'');c1=state(8,'你');c2=state(16,'你好');r=Reconciler(c0,False)
        r.append(BranchStep('a',c0.sha256,c0,c1));r.append(BranchStep('b',c1.sha256,c1,c2));r.install(c1)
        self.assertEqual(r.visible()['visible_frontier'],8)
    def test_raw_text_match_is_not_a_certificate(self):
        c0=state(0,'');p=state(8,'你');r=Reconciler(c0,True);r.append(BranchStep('a',c0.sha256,c0,p))
        q=state(8,'你',last_attend_frame=5);self.assertFalse(r.install(q)['compatible'])
    def test_all_native_fields_fence_retention(self):
        for name in STATE_FIELDS:
            if name in ('frontier','contract'):continue
            with self.subTest(name=name):
                c0=state(0,'');p=state(8,'你');d=copy.deepcopy(p.state)
                if name=='last_attend_frame':d[name]+=1
                elif name=='transcript':d[name]+='!'
                elif name=='detected_language':d[name]='en'
                elif name in ('initial_token_length','sot_index'):d[name]+=1
                elif name=='decoder_type':d[name]='greedy'
                elif name=='context':d[name]['text']='hidden'
                else:d[name]=[]
                r=Reconciler(c0,True);r.append(BranchStep('a',c0.sha256,c0,p));self.assertFalse(r.install(FeedbackCut(d))['compatible'])
    def test_no_boundary_or_no_output_match_forced(self):
        c0=state(0,'');p=state(16,'你好');r=Reconciler(c0,True);r.append(BranchStep('a',c0.sha256,c0,p))
        self.assertFalse(r.install(state(8,'你'))['compatible'])
    def test_changed_contract_and_reordered_feedback_denied(self):
        c0=state(0,'');r=Reconciler(c0,True)
        with self.assertRaises(ValueError):r.install(c0)
        with self.assertRaises(ValueError):r.install(state(8,'你',contract={'id':'changed'}))
    def test_late_stale_private_completion_denied(self):
        c0=state(0,'');p=state(8,'你');r=Reconciler(c0,True);r.install(state(8,'他'))
        with self.assertRaises(ValueError):r.append(BranchStep('a',c0.sha256,c0,p))
    def test_snapshot_closed_schema(self):
        q=state(8,'你').state.copy();q.pop('last_attend_frame')
        with self.assertRaises(ValueError):FeedbackCut(q)

if __name__=='__main__':unittest.main()
