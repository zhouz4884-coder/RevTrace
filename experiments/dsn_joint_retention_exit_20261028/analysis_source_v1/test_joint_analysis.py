"""Small adversarial checks for ancestry and the fixed study design."""
import copy
import unittest
from build_plan import build
from joint_recount import compatible_input

class JointAnalysisTests(unittest.TestCase):
    def test_factorial_is_complete_with_shared_actuator(self):
        p=build();self.assertEqual(len(p['cells']),24)
        for arrival in ('sync','staggered'):
            for repeat in range(3):
                rows=[r for r in p['cells'] if r['arrival']==arrival and r['repeat']==repeat]
                self.assertEqual({r['arm'] for r in rows},{'R0K0','R0K1','R1K0','R1K1'})
                for r in rows:
                    self.assertEqual(r['confirmation_consumer'],'two_lane')
                    self.assertEqual(r['policy'],'covered' if r['K'] else 'no_cancel')
                    self.assertEqual(r['output'],r['argv'][r['argv'].index('--out')+1])

    def fixture(self):
        job=dict(job_id='child',role='proposal',session_id=0,source_id='same',contract_epoch=1,contract_digest='x',
                 branch_generation=0,chunk_id=2,end_window=3,audio_end_sample=96000,prompt_tokens=[20],enqueue_perf=10.)
        prior=dict(job,job_id='parent',chunk_id=1,end_window=2,audio_end_sample=64000,prompt_tokens=[10],enqueue_perf=4.)
        records={'parent':dict(job=prior,result=dict(state_tokens=[20],received_perf=6.,
             execution_context_audit=dict(executed_prompt_tokens=[10])))}
        return job,records,{'parent':7.}

    def test_actual_published_ancestor_supports_compatibility(self):
        job,records,published=self.fixture()
        self.assertEqual(compatible_input(job,32000,[10],records,published)[0],True)

    def test_future_publication_cannot_be_ancestry(self):
        job,records,published=self.fixture();published['parent']=11.
        self.assertIsNone(compatible_input(job,32000,[10],records,published)[0])

    def test_wrong_selected_state_rejects_same_frontier(self):
        job,records,published=self.fixture()
        self.assertEqual(compatible_input(job,32000,[99],records,published)[0],False)

    def test_fault_conditioning_is_not_legal_pressure(self):
        job,records,published=self.fixture();records['parent']['result']['execution_context_audit']['executed_prompt_tokens']=[99]
        self.assertIsNone(compatible_input(job,32000,[10],records,published)[0])

if __name__=='__main__':unittest.main()
