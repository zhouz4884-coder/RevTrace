import unittest
from dataclasses import replace
from model import *

def initial(n=2):
    return replace(State(),accepted=n,original_clocks=tuple(range(n+1)),clocks=tuple(range(n+1)))

def asr(s,jid,bit):
    s=project(s,jid,bit);check(s);return s

def full(s,jid,choice):
    s=receive_full(execute_original(s,jid,choice),jid);check(s);return s

def commit(s,jid):
    s=install(sync_record(prepare(s,jid)));check(s);return s

def drain(s):
    while s.publications:
        s=apply_consumer(s);check(s)
    return s

def pending_two():
    s=dispatch(initial(),0,Cut(0,0));s=asr(s,0,0)
    s=dispatch(s,1,Cut(1,0));s=asr(s,1,1)
    return s

class RefinementControls(unittest.TestCase):
    def test_original_C_U_is_allowed_relation_not_single_replay(self):
        s=dispatch(initial(),0,Cut(0,0))
        a=commit(full(s,0,0),0);b=commit(full(s,0,1),0)
        self.assertNotEqual(a.canonical,b.canonical);check(a);check(b)

    def test_confirmed_input_does_not_require_own_prediction_correct(self):
        s=asr(dispatch(initial(),0,Cut(0,0)),0,0)
        s=commit(full(s,0,1),0)
        self.assertEqual(s.canonical,Cut(1,1))
        self.assertEqual(s.jobs[0].projection,Cut(1,0))

    def test_future_complete_result_buffers_until_parent(self):
        s=pending_two();s=full(s,1,0)
        self.assertEqual(s.canonical,Cut(0,0))
        self.assertEqual(input_status(s,s.jobs[1]),"UNKNOWN")
        with self.assertRaises(Violation):prepare(s,1)
        s=commit(full(s,0,0),0);s=commit(s,1)
        self.assertEqual(s.canonical,Cut(2,0))

    def test_complete_before_confirmation_and_confirmation_before_complete(self):
        a=pending_two();a=full(a,1,1);a=commit(full(a,0,0),0);a=commit(a,1)
        b=pending_two();b=commit(full(b,0,0),0);b=commit(full(b,1,1),1)
        self.assertEqual([r.end for r in a.records],[r.end for r in b.records])

    def test_same_frontier_mismatch_refutes_not_text_equality(self):
        s=pending_two();s=commit(full(s,0,1),0)
        self.assertTrue(same_text(s.canonical,s.jobs[1].start))
        self.assertEqual(input_status(s,s.jobs[1]),"REFUTED")
        with self.assertRaises(Violation):prepare(full(s,1,0),1)

    def test_unknown_future_input_survives_ancestor_loss_then_converges(self):
        s=replace(pending_two(),accepted=3,original_clocks=(0,1,2,3),clocks=(0,1,2,3))
        s=full(s,1,0);s=dispatch(s,1,Cut(2,0),4);s=asr(s,2,1)
        s=commit(full(s,0,1),0)
        self.assertEqual(input_status(s,s.jobs[2]),"UNKNOWN")
        self.assertIsNone(invalidity(s,s.jobs[2]))
        with self.assertRaisesRegex(Violation,"does_not_refute"):
            cancel(s,2,mutation="ancestor_mismatch_cancels_unknown")
        birth=s.jobs[2].birth
        s=dispatch(s,0,Cut(1,1),4);s=commit(full(s,3,1),3)
        self.assertEqual(input_status(s,s.jobs[2]),"CONFIRMED")
        s=commit(full(s,2,0),2)
        self.assertEqual(s.canonical,Cut(3,0));self.assertEqual(s.jobs[2].birth,birth)

    def test_unknown_input_is_not_a_C_entry_cancel_proof(self):
        s=pending_two()
        with self.assertRaisesRegex(Violation,"UNKNOWN"):cancel(s,1)

    def test_known_same_F_mismatch_can_cancel_without_result(self):
        s=commit(full(pending_two(),0,1),0);s=cancel(s,1);check(s)
        self.assertEqual(s.jobs[1].phase,"cancelled");self.assertIsNone(s.jobs[1].result)

    def test_incompatible_completed_full_is_discarded(self):
        s=commit(full(pending_two(),0,1),0);s=full(s,1,0)
        self.assertEqual(s.jobs[1].phase,"discarded")
        self.assertEqual(len(s.records),1)

    def test_original_projection_cannot_be_promoted_as_C_U(self):
        s=asr(dispatch(initial(),0,Cut(0,0)),0,0)
        j=replace(s.jobs[0],phase="buffered",result=Cut(1,0),receipt_owned=True)
        s=set_job(s,j)
        with self.assertRaisesRegex(Violation,"not_original"):
            sync_record(prepare(s,0))

    def test_mutation_unconfirmed_prepare_has_counterexample(self):
        s=full(pending_two(),1,0)
        bad=prepare(s,1,mutation="commit_unknown_input")
        with self.assertRaisesRegex(Violation,"confirmed_owned_input"):check(bad)

    def test_compatible_application_keeps_whole_ahead_view(self):
        s=drain(pending_two());self.assertEqual(tail(s.consumer_canonical,s.consumer_steps),Cut(2,1))
        s=commit(full(s,0,0),0);s=apply_consumer(s);check(s)
        self.assertEqual(s.consumer_canonical,Cut(1,0))
        self.assertEqual(tail(s.consumer_canonical,s.consumer_steps),Cut(2,1))

    def test_snapshot_consumer_mutation_is_observably_false(self):
        s=commit(full(drain(pending_two()),0,0),0)
        with self.assertRaisesRegex(Violation,"withdrew_whole_view"):
            apply_consumer(s,mutation="snapshot_consumer")

    def test_incompatible_application_withdraws_needed_view(self):
        s=commit(full(drain(pending_two()),0,1),0)
        s=apply_consumer(s);check(s)
        self.assertEqual(s.consumer_canonical,Cut(1,1))
        self.assertEqual(s.consumer_steps,())

    def test_provisional_application_never_advances_certification(self):
        s=pending_two()
        with self.assertRaisesRegex(Violation,"acquired_certification"):
            apply_consumer(s,mutation="certify_private_projection")

    def test_each_queued_commit_has_its_own_root_snapshot(self):
        s=full(pending_two(),1,0);s=commit(full(s,0,0),0);s=commit(s,1)
        pubs=[p for p in s.publications if p.kind=="private"]
        self.assertTrue(any(p.root==Cut(1,0) for p in pubs))
        s=drain(s);self.assertEqual(s.consumer_canonical,Cut(2,0))

    def test_final_root_alias_mutation_breaks_first_commit_snapshot(self):
        s=drain(pending_two());s=full(s,1,0);s=commit(full(s,0,0),0);s=commit(s,1)
        pubs=list(s.publications)
        target=next(i for i,p in enumerate(pubs) if p.kind=="private" and p.root.frontier==1)
        pubs[target]=replace(pubs[target],root=s.canonical)
        s=replace(s,publications=tuple(pubs))
        for _ in range(target):s=apply_consumer(s)
        with self.assertRaisesRegex(Violation,"wrong_applied_root"):apply_consumer(s)

    def test_full_buffer_remains_usable_after_worker_only_restart(self):
        s=full(pending_two(),1,0)
        s=restart_worker(observe_exit(fail_worker(s,1),1),1)
        self.assertEqual(s.worker_incarnations[1],1)
        self.assertEqual(s.jobs[1].incarnation,0)
        s=commit(full(s,0,0),0);s=commit(s,1);check(s)
        self.assertEqual(s.canonical,Cut(2,0))
        self.assertEqual(s.records[1].authorized_incarnation,0)

    def test_worker_exit_must_be_observed_before_slot_reuse(self):
        s=fail_worker(dispatch(initial(),0,Cut(0,0)),0)
        with self.assertRaisesRegex(Violation,"observed_exit"):restart_worker(s,0)
        bad=restart_worker(replace(s,worker_states=("exited","up")),0)
        with self.assertRaisesRegex(Violation,"physical_lease"):check(bad)

    def test_expected_duplicate_is_local_idempotent_rejection(self):
        s=commit(full(dispatch(initial(),0,Cut(0,0)),0,0),0)
        again,kind=receive_duplicate_or_late(s,0)
        self.assertEqual(again,s);self.assertIn("LOCAL_REJECT",kind)
        s=dispatch(s,0,s.canonical);s=commit(full(s,1,1),1)
        self.assertEqual(s.canonical.frontier,2)

    def test_owner_crash_before_sync_does_not_create_a_fact(self):
        s=prepare(full(dispatch(initial(),0,Cut(0,0)),0,1),0)
        s=recover(owner_crash(s));check(s)
        self.assertEqual(s.canonical,Cut(0,0));self.assertEqual(s.records,())
        again,kind=receive_duplicate_or_late(s,0)
        self.assertEqual(again,s);self.assertIn("LOCAL_REJECT",kind)

    def test_post_sync_preinstall_recovery_replays_old_fact_not_new_work(self):
        s=sync_record(prepare(full(dispatch(initial(),0,Cut(0,0)),0,1),0))
        s=recover(owner_crash(s));check(s)
        self.assertEqual(s.canonical,Cut(1,1))
        self.assertEqual(s.consumer_canonical,Cut(0,0))
        s=drain(s);self.assertEqual(s.consumer_canonical,Cut(1,1))
        self.assertEqual(s.accepted-s.canonical.frontier,1)
        self.assertEqual(sum(j.choice is not None for j in s.jobs),1)

    def test_recovery_keeps_supervisor_consumer_certified_facts_and_original_clocks(self):
        s=drain(commit(full(dispatch(initial(),0,Cut(0,0)),0,1),0))
        s=recover(owner_crash(s));check(s)
        self.assertEqual(s.consumer_canonical,Cut(1,1))
        self.assertEqual(s.clocks,(0,1,2))
        with self.assertRaisesRegex(Violation,"clock_changed"):
            check(recover(owner_crash(s),mutation="reset_input_clocks"))

    def test_illegal_install_before_sync_has_counterexample(self):
        s=prepare(full(dispatch(initial(),0,Cut(0,0)),0,1),0)
        with self.assertRaisesRegex(Violation,"durable_prefix"):
            check(install(s,mutation="install_before_sync"))

    def test_old_epoch_complete_cannot_be_reauthorized_under_identical_root(self):
        s=full(dispatch(initial(),0,Cut(0,0)),0,0);s=recover(owner_crash(s))
        s=set_job(s,replace(s.jobs[0],phase="buffered"))
        with self.assertRaisesRegex(Violation,"unconfirmed"):prepare(s,0)
        with self.assertRaisesRegex(Violation,"confirmed_owned_input"):
            check(prepare(s,0,mutation="commit_unknown_input"))

    def test_new_legal_work_finishes_after_fail_stop_and_recovery(self):
        s=fail_worker(dispatch(initial(),0,Cut(0,0)),0)
        s=restart_worker(observe_exit(s,0),0)
        s=dispatch(s,0,Cut(0,0));s=drain(commit(full(s,1,1),1))
        s=owner_crash(s);s=recover(s);s=drain(s)
        for w in (0,1):
            s=restart_worker(observe_exit(s,w),w)
        s=dispatch(s,0,s.canonical,4);s=drain(commit(full(s,2,0),2))
        self.assertEqual(s.canonical.frontier,s.accepted)
        self.assertEqual(s.consumer_canonical,s.canonical)
        check(s)

    def test_owner_namespace_session_epoch_and_worker_incarnation_are_separate(self):
        s=dispatch(initial(),0,Cut(0,0))
        old=s.jobs[0];s=fence_session(s)
        self.assertEqual((s.epoch,s.session_epoch,s.worker_incarnations),(0,1,(0,0)))
        self.assertEqual(invalidity(s,old),"session_epoch_changed")
        with self.assertRaisesRegex(Violation,"ASR_fenced"):project(s,0,0)
        s=recover(owner_crash(s))
        self.assertEqual((s.epoch,s.session_epoch),(1,1));check(s)

if __name__=="__main__":
    unittest.main()

