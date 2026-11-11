"""Focused positive/negative controls for phase-correct refinement checks."""
import unittest
from dataclasses import replace
import model as m
from invariants import check, check_action


def synced():
    s=m.dispatch(m.State(),0,m.Cut(0,0))
    s=m.receive_full(m.execute_original(s,0,1),0)
    return m.sync_record(m.prepare(s,0))


class PhaseInvariantControls(unittest.TestCase):
    def test_synced_preinstall_is_legal_and_refutes_tail_equals_installed(self):
        s=synced();check(s)
        self.assertNotEqual(s.canonical,s.records[-1].end)
        self.assertEqual((s.canonical_index,len(s.records)),(0,1))

    def test_crash_preserves_legal_synced_install_gap(self):
        s=synced();out=m.owner_crash(s)
        check_action(s,'Owner_process_crash',out)
        self.assertEqual(out.records,s.records)
        self.assertNotEqual(out.canonical,out.records[-1].end)

    def test_recover_closes_install_gap_without_neural_transition(self):
        s=m.owner_crash(synced());out=m.recover(s)
        check_action(s,'recover_durable_facts_without_new_neural_work',out)
        self.assertEqual(out.records,s.records)
        self.assertEqual(out.canonical,out.records[-1].end)
        self.assertEqual(out.consumer_canonical,m.Cut(0,0))
        applied=m.apply_consumer(out)
        check_action(out,'actual_Consumer_application',applied)
        self.assertEqual(applied.consumer_canonical,applied.records[-1].end)

    def test_idle_writable_owner_cannot_forget_pending_synced_fact(self):
        bad=replace(synced(),transaction=None)
        with self.assertRaisesRegex(m.Violation,'writable_idle'):
            check(bad)

    def test_non_append_completion_cannot_create_a_fact(self):
        before=m.receive_full(m.execute_original(m.dispatch(m.State(),0,m.Cut(0,0)),0,1),0)
        after=m.install(m.sync_record(m.prepare(before,0)))
        with self.assertRaisesRegex(m.Violation,'non_append_action'):
            check_action(before,'receive_full:0',after)

    def test_dispatch_evidence_may_not_disappear_silently(self):
        s=m.dispatch(m.State(),0,m.Cut(0,0))
        with self.assertRaisesRegex(m.Violation,'immutable_dispatch_evidence'):
            check(replace(s,dispatch_evidence=()))

    def test_recovery_cannot_add_an_extra_existing_job_result(self):
        s=m.owner_crash(synced());out=m.recover(s)
        bad=m.set_job(out,replace(out.jobs[0],choice=0,result=m.Cut(1,0)))
        with self.assertRaises(m.Violation):
            check_action(s,'recover_durable_facts_without_new_neural_work',bad)

    def test_sync_is_append_without_install_then_install_stutters_prefix(self):
        prepared=m.prepare(m.receive_full(m.execute_original(m.dispatch(m.State(),0,m.Cut(0,0)),0,1),0),0)
        durable=m.sync_record(prepared)
        check_action(prepared,'sync_original_transition',durable)
        installed=m.install(durable)
        check_action(durable,'install_durable_transition',installed)
        self.assertEqual(durable.records,installed.records)


if __name__=='__main__':unittest.main()
