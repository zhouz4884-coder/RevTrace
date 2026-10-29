import copy,unittest
from audit_presence_consumer_v1 import verify_fault_target

class ActualFaultBindingTests(unittest.TestCase):
    def fixture(self):
        fixture=dict(fault_plan={'0:3':4},targets={'0:3':dict(source_id='s',chunk_id=2,donor_index=4)},donors=[dict(tokens=[7]),dict(tokens=[8])])
        job=dict(session_id=0,end_window=3,chunk_id=2,role='proposal',source_id='s',prompt_tokens=[9],fault_actual_prompt_tokens=[7])
        context=dict(executed_prompt_tokens=[7],fault_override=True)
        return job,context,fixture

    def test_exact_modulo_donor_binding(self):
        job,context,fixture=self.fixture();self.assertTrue(verify_fault_target(job,context,fixture))

    def test_changed_actual_donor_rejected(self):
        job,context,fixture=self.fixture();context['executed_prompt_tokens']=[8]
        with self.assertRaises(AssertionError):verify_fault_target(job,context,fixture)

    def test_wrong_source_target_rejected(self):
        job,context,fixture=self.fixture();job['source_id']='other'
        with self.assertRaises(AssertionError):verify_fault_target(job,context,fixture)

    def test_frozen_target_cannot_silently_be_clean(self):
        job,context,fixture=self.fixture();del job['fault_actual_prompt_tokens'];context=dict(executed_prompt_tokens=[9],fault_override=False)
        with self.assertRaises(AssertionError):verify_fault_target(job,context,fixture)

if __name__=='__main__':unittest.main()
