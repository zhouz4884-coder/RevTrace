"""UIR compute-retention/use-authority separation; synthetic CPU controls only."""
import copy
import unittest
import test_versioned_policy as fixtures
from feedback_contract import FeedbackCut
from resilience_inbound import IntegrityError
from resilience_policy import ResilientFullSpecCoordinator
from retention_policy import UnconditionalInflightCoordinator,process_c_entry_hints
from versioned_policy import ReadyOnlyCoordinator
from test_resilience_policy import cut


class HintSink:
    def __init__(self):self.rows=[]
    def send(self,value):self.rows.append(copy.deepcopy(value))


class UIRControls(unittest.TestCase):
    register=fixtures.VersionedControls.register
    early_event=fixtures.VersionedControls.early_event
    completion_event=fixtures.VersionedControls.completion_event
    deliver=fixtures.VersionedControls.deliver
    early=fixtures.VersionedControls.early
    finish=fixtures.VersionedControls.finish
    two_pending=fixtures.VersionedControls.two_pending
    make=fixtures.VersionedControls.make

    def setUp(self):
        self.sid,self.root,self.serial='s',cut(0),0
        self.commits,self.audit=[],[]
        self.c=self.make(UnconditionalInflightCoordinator)

    def hint_path(self):
        sinks={slot:HintSink() for slot in ('f0','f1')};logs=[];observed=set()
        workers={slot:{'hints':sink} for slot,sink in sinks.items()}
        process_c_entry_hints(self.c,workers,observed,lambda kind,**body:logs.append(dict(kind=kind,**body)))
        return workers,sinks,logs,observed

    def test_safe_uir_inherits_input_classification_AU_SUP_and_ready_selection(self):
        for method in ('_reason','_commit','admit_asr','pop_ready_commits','view_event'):
            self.assertIs(getattr(UnconditionalInflightCoordinator,method),getattr(ResilientFullSpecCoordinator,method))

    def test_safe_uir_retains_invalid_computation_without_forwarding_C_skip(self):
        parent,child,p1,p2=self.two_pending();self.finish(parent,cut(8000,'actual differs'))
        proof=self.c.invalidations()[child]
        self.assertEqual(proof['kind'],'actual_canonical_disagrees_with_complete_start')
        workers,sinks,logs,observed=self.hint_path()
        self.assertEqual(sum(len(s.rows) for s in sinks.values()),0)
        self.assertIn(child,self.c.jobs);self.assertIn(child,observed)
        self.assertEqual(logs[0]['kind'],'input_or_coverage_reason_observed_without_C_entry_skip')
        self.assertFalse(logs[0]['c_entry_skip_hint_sent']);self.assertTrue(logs[0]['complete_input_refuted'])
        process_c_entry_hints(self.c,workers,observed,lambda *a,**k:self.fail('duplicate diagnostic'))

    def test_RevTrace_forwards_same_actual_input_refutation_at_shared_checkpoint(self):
        self.c=self.make(ResilientFullSpecCoordinator)
        parent,child,p1,p2=self.two_pending();self.finish(parent,cut(8000,'actual differs'))
        workers,sinks,logs,observed=self.hint_path()
        self.assertEqual(len(sinks['f1'].rows),1)
        self.assertEqual(sinks['f1'].rows[0]['job_id'],child)
        self.assertTrue(logs[0]['c_entry_skip_hint_sent'])

    def test_safe_uir_full_invalid_result_is_completed_then_discarded_without_fact(self):
        parent,child,p1,p2=self.two_pending();self.finish(parent,cut(8000,'different'))
        out=self.finish(child,p2)['outcome']
        self.assertEqual(out['kind'],'discarded')
        self.assertEqual(out['proof']['kind'],'actual_canonical_disagrees_with_complete_start')
        self.assertEqual(len(self.commits),1)
        self.assertEqual(self.c.pop_ready_commits(),[])
        self.assertEqual(self.c.abandoned_full.total_count,0)

    def test_safe_uir_valid_cross_birth_result_still_selects_original_result(self):
        parent,child,p1,p2=self.two_pending();self.finish(parent,p1)
        out=self.finish(child,p2)['outcome']
        self.assertEqual(out['kind'],'canonical')
        self.assertEqual(len(self.commits),2)
        self.assertEqual(self.commits[-1]['full_record']['selected_correction'],{'actual':'C'})

    def test_safe_uir_direct_AU_rejects_wrong_actual_parent_even_without_C_skip(self):
        parent,child,p1,p2=self.two_pending();job=self.c.jobs[child]
        self.finish(parent,cut(8000,'actual differs'))
        item=dict(job=job,cut=p2,record=self.completion_event(child,p2)['record'])
        with self.assertRaises(IntegrityError):self.c._commit(item)
        self.assertEqual(len(self.commits),1)
        self.assertEqual(self.c.canonical(self.sid).frontier,8000)

    def test_unsafe_UseAll_CPU_fault_model_exhibits_wrong_parent_transition(self):
        # Deliberate fault model, not a coordinator subclass or live arm:
        # directly calling low-level install removes selection authority.
        parent,child,p1,p2=self.two_pending();job=self.c.jobs[child]
        actual=cut(8000,'actual differs');self.finish(parent,actual)
        self.assertFalse(job['start'].same(actual))
        self.c.owners[self.sid].install(p2)
        self.assertTrue(self.c.canonical(self.sid).same(p2))
        self.assertFalse(job['start'].same(actual),'unchecked UseAll violates actual-parent invariant')
        self.assertEqual(len(self.commits),1,'unsafe low-level transition created no durable authorized fact')

    def test_safe_uir_session_fence_still_retires_only_exact_old_terminal(self):
        job=self.register();self.c.reset_epoch(self.sid,self.root)
        out=self.finish(job,cut(8000,'old session'))
        self.assertEqual(out['disposition'],'retire_fenced_terminal')
        self.assertFalse(out['outcome']['certified_output'])
        self.assertEqual(self.commits,[])

    def test_ready_only_validated_receipt_precedes_install_by_policy_sequence(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending();ready=self.finish(child,p2)['outcome']
        selected=self.finish(parent,p1)['outcome']
        self.assertLess(ready['complete_receipt_order']['sequence'],selected['canonical_install_order']['sequence'])
        self.assertEqual(selected['other_ready_full_receipts_before_install'][0]['job_id'],child)
        self.assertEqual(self.c.pop_ready_commits()[0]['job']['job_id'],child)

    def test_ready_only_physical_end_or_queued_receipt_does_not_override_dequeue_order(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending();late=self.completion_event(child,p2)
        late['record'].update(model_end=1.0,worker_job_end_perf=1.1);late['sent_perf']=1.2
        selected=self.finish(parent,p1)['outcome']
        self.assertEqual(selected['other_ready_full_receipts_before_install'],[])
        fence=self.c.invalidations()[child]
        self.assertEqual(fence['fence_canonical_install_order'],selected['canonical_install_order'])
        out=self.deliver(late)['outcome']
        self.assertGreater(out['complete_receipt_order']['sequence'],selected['canonical_install_order']['sequence'])
        self.assertEqual(out['kind'],'discarded')


if __name__=='__main__':unittest.main()
