"""Actual Consumer CPU controls; journaled facts are synthetic unit fixtures."""
import copy
import pathlib
import tempfile
import unittest

from feedback_contract import FeedbackCut
from resilience_consumer import ConsumerIntegrityError, SurvivorConsumer
from resilience_storage import FactStore, JournalIntegrityError
from test_resilience_storage import body, cut


def private(root, *ends, publication_id=1, source_id="s", namespace=0):
    previous = root
    steps = []
    for index, end in enumerate(ends):
        steps.append(dict(job_id=f"e{namespace}-j{index + 1:09d}",
                          start=previous.state, end=end.state,
                          kind="typed_ASR_projection",
                          actual_full_C_U_completed=False))
        previous = end
    return dict(kind="private", source_id=source_id, canonical_sha=root.sha256,
                steps=steps, publication_id=publication_id)


class SurvivorConsumerControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = pathlib.Path(self.tmp.name)
        self.root, self.first, self.second = cut(0), cut(8000, "first"), cut(16000, "second")
        self.path = self.folder / "facts.wal"
        self.store = FactStore(self.path, {"s": self.root.state},
                               dict(scope="synthetic CPU journal fixture", origin_perf=1.0))
        self.addCleanup(self.store.close)
        self.consumer = SurvivorConsumer({"s": self.root.state},
                                         self.folder / "consumer.jsonl",
                                         self.folder / "rejections.jsonl", self.path)
        self.addCleanup(self.consumer.close)
        self.consumer.begin_owner(0)

    def commit(self, parent, end, serial=1, owner_epoch=0):
        transition = body(parent, end, serial)
        transition["owner_epoch"] = owner_epoch
        transition["job"]["job_id"] = f"e{owner_epoch}-j{serial:09d}"
        return self.store.commit(transition)

    def fact(self, receipt, end, publication_id=1, source_id="s"):
        return dict(kind="canonical", source_id=source_id, state=end.state,
                    durable_receipt=receipt, publication_id=publication_id)

    def snapshot_all(self):
        return {sid: self.consumer.snapshot(sid) for sid in self.consumer.states}

    def test_provisional_whole_view_never_advances_certified_progress(self):
        result = self.consumer.apply(private(self.root, self.first, self.second), 0)
        self.assertTrue(result["applied"])
        self.assertEqual(result["row"]["visible_frontier"], 16000)
        self.assertEqual(result["row"]["certified_frontier"], 0)
        self.assertEqual(result["row"]["private_job"], "e0-j000000002")

    def test_compatible_fact_keeps_actual_ahead_whole_view(self):
        self.consumer.apply(private(self.root, self.first, self.second), 0)
        receipt = self.commit(self.root, self.first)
        result = self.consumer.apply(self.fact(receipt, self.first, 2), 0)
        self.assertEqual(result["row"]["visible_frontier"], 16000)
        self.assertEqual(result["row"]["text"], "second")
        self.assertEqual(result["row"]["certified_frontier"], 8000)
        self.assertEqual(result["row"]["private_job"], "e0-j000000002")

    def test_same_text_different_complete_state_requires_withdrawal(self):
        self.consumer.apply(private(self.root, self.first, self.second), 0)
        state = self.first.state
        state["last_attend_frame"] = 777
        actual = FeedbackCut(state)
        receipt = self.commit(self.root, actual)
        result = self.consumer.apply(self.fact(receipt, actual, 2), 0)
        self.assertEqual(result["row"]["visible_frontier"], 8000)
        self.assertIsNone(result["row"]["private_job"])

    def test_bad_published_state_is_checked_before_any_install(self):
        receipt = self.commit(self.root, self.first)
        wrong = cut(8000, "wrong published text")
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(self.fact(receipt, wrong), 0)
        self.assertEqual(self.snapshot_all(), before)
        self.assertEqual(self.consumer.durable_highwater, 1)
        self.assertEqual(self.consumer.pub_highwater, 0)

    def test_wrong_source_receipt_cannot_mutate_another_session(self):
        other = self.root.state
        other["contract"]["source_sha"] = "other immutable audio"
        self.consumer.states["other"] = __import__("feedback_contract").Reconciler(
            FeedbackCut(other), True)
        self.consumer.processed["other"] = 0
        receipt = self.commit(self.root, self.first)
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(self.fact(receipt, self.first, source_id="other"), 0)
        self.assertEqual(self.snapshot_all(), before)

    def test_duplicate_publication_is_local_and_does_not_add_observation(self):
        receipt = self.commit(self.root, self.first)
        event = self.fact(receipt, self.first)
        self.consumer.apply(event, 0)
        result = self.consumer.apply(event, 0)
        self.assertEqual(result["reason"], "exact_duplicate_publication")
        self.assertEqual(self.consumer.applied, 1)
        self.assertEqual(self.consumer.snapshot("s")["certified_frontier"], 8000)

    def test_same_publication_ID_different_content_is_not_ignored(self):
        self.consumer.apply(private(self.root, self.first), 0)
        altered = private(self.root, cut(8000, "altered"))
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(altered, 0)
        self.assertEqual(self.snapshot_all(), before)

    def test_covered_old_publication_cannot_rewind_current_view(self):
        first = private(self.root, self.first)
        self.consumer.apply(first, 0)
        self.consumer.apply(private(self.root, self.first, self.second, publication_id=2), 0)
        result = self.consumer.apply(first, 0)
        self.assertEqual(result["reason"], "covered_publication_sequence")
        self.assertEqual(self.consumer.snapshot("s")["visible_frontier"], 16000)

    def test_publication_gap_is_fatal_before_state_changes(self):
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(private(self.root, self.first, publication_id=2), 0)
        self.assertEqual(self.snapshot_all(), before)

    def test_stale_private_root_is_rejected_locally_then_service_continues(self):
        receipt = self.commit(self.root, self.first)
        self.consumer.apply(self.fact(receipt, self.first), 0)
        rejected = self.consumer.apply(private(self.root, self.first, publication_id=2), 0)
        self.assertEqual(rejected["reason"], "stale_private_root")
        result = self.consumer.apply(private(self.first, self.second, publication_id=3), 0)
        self.assertTrue(result["applied"])
        self.assertEqual(result["row"]["visible_frontier"], 16000)

    def test_old_owner_message_drops_before_parsing_or_mutating_new_namespace(self):
        self.consumer.apply(private(self.root, self.first), 0)
        self.consumer.begin_owner(1)
        before = self.snapshot_all()
        result = self.consumer.apply(dict(publication_id=999, source_id="unknown"), 0)
        self.assertEqual(result["reason"], "retired_owner_namespace")
        self.assertEqual(self.snapshot_all(), before)
        self.assertEqual(self.consumer.pub_highwater, 0)

    def test_unregistered_future_owner_cannot_publish(self):
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(private(self.root, self.first), 1)
        self.assertEqual(self.snapshot_all(), before)

    def test_owner_restart_keeps_existing_read_view_without_certifying_it(self):
        self.consumer.apply(private(self.root, self.first, self.second), 0)
        self.consumer.begin_owner(1)
        before = self.snapshot_all()
        result = self.consumer.apply(private(self.root, publication_id=1, namespace=1), 1)
        self.assertEqual(self.snapshot_all(), before)
        self.assertEqual(result["row"]["certified_frontier"], 0)
        self.assertEqual(result["row"]["private_job"], "e0-j000000002")

    def test_durable_not_yet_consumed_fact_replays_before_new_worker_progress(self):
        self.consumer.apply(private(self.root, self.first, self.second), 0)
        receipt = self.commit(self.root, self.first)
        self.consumer.begin_owner(1)
        result = self.consumer.replay_fact(receipt)
        self.assertTrue(result["applied"])
        self.assertTrue(result["row"]["recovery_replay"])
        self.assertEqual(result["row"]["original_fact_owner_epoch"], 0)
        self.assertEqual(result["row"]["certified_frontier"], 8000)
        self.assertEqual(result["row"]["visible_frontier"], 16000)
        self.assertEqual(result["row"]["private_job"], "e0-j000000002")

    def test_already_consumed_fact_replay_is_not_new_progress(self):
        receipt = self.commit(self.root, self.first)
        self.consumer.apply(self.fact(receipt, self.first), 0)
        self.consumer.begin_owner(1)
        result = self.consumer.replay_fact(receipt)
        self.assertFalse(result["applied"])
        self.assertEqual(result["reason"], "already_applied_durable_fact")
        self.assertEqual(self.consumer.applied, 1)

    def test_old_owner_fact_requires_explicit_replay_if_not_already_consumed(self):
        receipt = self.commit(self.root, self.first)
        self.consumer.begin_owner(1)
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.apply(self.fact(receipt, self.first), 1)
        self.assertEqual(self.consumer.snapshot("s")["certified_frontier"], 0)
        self.assertTrue(self.consumer.replay_fact(receipt)["applied"])

    def test_recovered_old_fact_then_new_fact_form_one_ordered_program_trace(self):
        old = self.commit(self.root, self.first)
        self.consumer.begin_owner(1)
        self.consumer.replay_fact(old)
        new = self.commit(self.first, self.second, 2, owner_epoch=1)
        result = self.consumer.apply(self.fact(new, self.second), 1)
        self.assertEqual(result["row"]["certified_frontier"], 16000)
        self.assertEqual(self.consumer.durable_highwater, 3)

    def test_replay_gap_never_invents_missing_parent(self):
        self.commit(self.root, self.first)
        later = self.commit(self.first, self.second, 2)
        before = self.snapshot_all()
        with self.assertRaises(ConsumerIntegrityError):
            self.consumer.replay_fact(later)
        self.assertEqual(self.snapshot_all(), before)

    def test_checksum_mismatch_receipt_is_not_a_publication_authority(self):
        receipt = self.commit(self.root, self.first)
        with self.assertRaises(JournalIntegrityError):
            self.consumer.apply(self.fact(dict(receipt, record_sha256="f" * 64), self.first), 0)
        self.assertEqual(self.consumer.snapshot("s")["certified_frontier"], 0)

    def test_ACK_contains_all_surviving_consumer_view_references(self):
        from feedback_contract import Reconciler
        other = self.root.state
        other["contract"]["source_sha"] = "second immutable source"
        other_root = FeedbackCut(other)
        other_next = other_root.state
        other_next.update(frontier=8000, transcript="other view")
        other_next = FeedbackCut(other_next)
        self.consumer.states["other"] = Reconciler(other_root, True)
        self.consumer.processed["other"] = 0
        self.consumer.apply(private(other_root, other_next, source_id="other"), 0)
        event = private(self.root, self.first, publication_id=2, namespace=1)
        result = self.consumer.apply(event, 0)
        self.assertEqual(set(result["visible_job_ids"]),
                         {"e0-j000000001", "e1-j000000001"})


if __name__ == "__main__":
    unittest.main()
