"""Formal small plan/selection controls; no model, raw reader or GPU calls."""
from __future__ import annotations
import copy,unittest
from confirmation_common import SPLIT_NAMESPACE,SPLIT_DIRECTORY,abba_blocks,validate_matrix,selected_sources,GateError

def sources(n):return [dict(source_id=f'BAC009S{1000+i:04d}W0001',speaker_id=f'S{1000+i:04d}') for i in range(n)]
def cells(items):
    blocks,_=abba_blocks(items);out=[]
    for b in blocks:
        for a in b['strategies']:
            out.append(dict(cell_id=str(len(out)),source_id=b['source']['source_id'],strategy=a,repeat=b['repeat'],primary_gpu=b['primary_gpu'],position=len(out)))
    return out
def receipt():
    ss=sources(2)
    for s in ss:s.update(original_split=SPLIT_NAMESPACE,split_directory=SPLIT_DIRECTORY,archive_member=dict(path=SPLIT_DIRECTORY+'/'+s['source_id']+'.wav'),header=dict(sample_rate=16000,channels=1,sample_width=2),frames=132000,duration=8.25)
    return dict(status='PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE',sources=ss,model_calls=0)

class Controls(unittest.TestCase):
    def test_even_and_odd_metadata_counts_have_complete_ABBA(self):
        for n in (1,8,9,10):validate_matrix(cells(sources(n)),sources(n))
    def test_seed_plan_is_metadata_deterministic(self):
        self.assertEqual(abba_blocks(sources(9)),abba_blocks(list(reversed(sources(9)))))
    def test_policy_order_not_reversed_is_rejected(self):
        ss=sources(8);cs=cells(ss);sid=ss[0]['source_id'];r0=[c['strategy'] for c in cs if c['source_id']==sid and c['repeat']==0]
        r1=[c for c in cs if c['source_id']==sid and c['repeat']==1]
        for c,a in zip(r1,r0):c['strategy']=a
        with self.assertRaises(GateError):validate_matrix(cs,ss)
    def test_missing_cell_not_allowed(self):
        ss=sources(8);cs=cells(ss);cs.pop()
        with self.assertRaises(GateError):validate_matrix(cs,ss)
    def test_same_repeat_GPU_roles_required(self):
        ss=sources(8);cs=cells(ss);cs[0]['primary_gpu']=1
        with self.assertRaises(GateError):validate_matrix(cs,ss)
    def test_strict_test_receipt_accepted(self):self.assertEqual(len(selected_sources(receipt(),2)),2)
    def test_train_split_or_duplicate_speaker_rejected(self):
        r=receipt();r['sources'][0]['original_split']='StreamCorrect/aishell1_trainset'
        with self.assertRaises(GateError):selected_sources(r,2)
        r=receipt();r['sources'][1]['speaker_id']=r['sources'][0]['speaker_id']
        with self.assertRaises(GateError):selected_sources(r,2)
    def test_neural_selection_or_outcome_source_count_change_rejected(self):
        r=receipt();r['model_calls']=1
        with self.assertRaises(GateError):selected_sources(r,2)
        with self.assertRaises(GateError):selected_sources(receipt(),1)
    def test_versioned_test_namespace_required(self):
        for wrong in (SPLIT_DIRECTORY,SPLIT_NAMESPACE+'-other-version'):
            r=receipt();r['sources'][0]['original_split']=wrong
            with self.assertRaises(GateError):selected_sources(r,2)

if __name__=='__main__':unittest.main()

