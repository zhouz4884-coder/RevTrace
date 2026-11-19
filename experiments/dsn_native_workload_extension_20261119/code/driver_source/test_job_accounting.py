import unittest
from job_accounting import audit_records,resource_diagnostic
def jobs(*ids):return [dict(job_id=j,owner_epoch=0) for j in ids]
def fact():return dict(transition_id='t',record={'native_model_evaluated':True})
class AccountingControls(unittest.TestCase):
    def test_closed_disjoint_sum_and_promotions_not_terminals(self):
        r=audit_records(dispatches=jobs('a','b','c','d'),installed=['a'],durable_jobs={'a':fact()},
          discarded={'b':{}},skipped={'c':{'worker_terminal_event':dict(learned_C_executed=False,C_U_completed=False,feedback_cut_emitted=False)}},
          fenced=['d'],promotions=['a'],closed=True)
        self.assertTrue(r['status'].startswith('PASS'));self.assertEqual(r['closed_drain_terminal_sum'],4)
        self.assertEqual(r['selected_promoted_jobs'],1)
    def test_zero_ready_reuse_is_audit_not_hard_failure_or_equivalence(self):
        r=audit_records(dispatches=jobs('a'),installed=['a'],durable_jobs={'a':fact()},closed=True)
        self.assertTrue(r['status'].startswith('PASS'));self.assertTrue(r['zero_ready_reuse_requires_timing_audit'])
        self.assertFalse(r['zero_ready_reuse_establishes_policy_equivalence'])
    def test_terminal_overlap_cannot_be_hidden(self):
        r=audit_records(dispatches=jobs('a'),installed=['a'],durable_jobs={'a':fact()},discarded={'a':{}},closed=True)
        self.assertFalse(r['disjoint']);self.assertTrue(r['status'].startswith('FAIL'))
    def test_pending_ready_and_live_partition_but_do_not_close(self):
        r=audit_records(dispatches=jobs('a','b'),ready=['a'],closed=True)
        self.assertEqual(r['counts']['still_ready'],1);self.assertEqual(r['counts']['still_inflight'],1)
        self.assertTrue(r['status'].startswith('FAIL'))
    def test_owner_death_keeps_durable_replayed_selection_separate(self):
        r=audit_records(dispatches=jobs('a','b'),durable_jobs={'a':fact()},replayed_transition_ids=['t'],owner_dead_epochs=[0],closed=True)
        self.assertTrue(r['status'].startswith('PASS'));self.assertEqual(r['counts']['selected_durable_replayed'],1)
        self.assertEqual(r['counts']['owner_lifecycle_terminated'],1)
    def test_UIR_checks_no_skip_and_no_known_mismatched_selection(self):
        proof=dict(kind='actual_canonical_disagrees_with_complete_start')
        r=audit_records(dispatches=jobs('a'),discarded={'a':{'proof':proof}},full_results={'a':{}},
          hints=[dict(job_id='a',proof=proof,c_entry_skip_hint_sent=False,kind='input_or_coverage_reason_observed_without_C_entry_skip')],closed=True,uir=True)
        self.assertTrue(r['status'].startswith('PASS'));self.assertEqual(r['UIR']['known_mismatched_full_results_discarded'],1)
        r=audit_records(dispatches=jobs('a'),installed=['a'],durable_jobs={'a':fact()},hints=[dict(job_id='a',proof=proof,c_entry_skip_hint_sent=True)],closed=True,uir=True)
        self.assertTrue(r['status'].startswith('FAIL'))
    def test_skipped_prefix_does_not_require_model_evaluated_true(self):
        r=audit_records(dispatches=jobs('a'),skipped={'a':{'worker_terminal_event':dict(learned_C_executed=False,C_U_completed=False,feedback_cut_emitted=False)}},closed=True)
        self.assertTrue(r['status'].startswith('PASS'))
    def test_selected_promoted_job_requires_its_full_model_record(self):
        r=audit_records(dispatches=jobs('a'),installed=['a'],durable_jobs={'a':{'record':{'native_model_evaluated':False}}},promotions=['a'],closed=True)
        self.assertTrue(r['status'].startswith('FAIL'))
    def test_resource_drift_is_retained_diagnostic(self):
        r=resource_diagnostic({'bytes':100},{'bytes':104})
        self.assertTrue(r['diagnostic_required']);self.assertFalse(r['reject_or_retry']);self.assertFalse(r['exclude_or_drop_outcome'])
if __name__=='__main__':unittest.main()
