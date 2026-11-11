"""Inbox controls: no neural modules, input, reference or performance outputs."""
import copy
import unittest
from types import SimpleNamespace

from resilience_inbound import IntegrityError, ResilientInbound


class InboundControls(unittest.TestCase):
    def setUp(self):
        self.epoch = 0
        self.inbox = ResilientInbound(
            owner_epoch=5, worker_incarnations={"a": 0, "b": 0},
            session_epoch=lambda _: self.epoch, terminal_limit=2,
        )
        self.job = dict(job_id="e5-j000000001", worker="a", source_id="s",
                        dispatch_epoch=0, start=SimpleNamespace(sha256="start"), end=8)
        self.inbox.register(self.job, 0)
        self.event = dict(kind="completed", worker="a", worker_incarnation=0,
                          job_id=self.job["job_id"], source_id="s",
                          dispatch_epoch=0, immutable_result={"ids": [1]})

    def test_different_owner_epoch_is_fenced(self):
        result = self.inbox.classify("a", 0, dict(self.event, job_id="e4-j000000001"))
        self.assertEqual(result.action, "ignore_fenced")
        self.assertIn(self.job["job_id"], self.inbox.active)

    def test_contradictory_result_after_accept_is_integrity_failure(self):
        self.assertEqual(self.inbox.classify("a", 0, self.event).action, "accept")
        self.inbox.accept(self.event, terminal=True)
        changed = copy.deepcopy(self.event)
        changed["immutable_result"]["ids"] = [2]
        with self.assertRaises(IntegrityError):
            self.inbox.classify("a", 0, changed)

    def test_only_transport_timestamps_may_change_on_retransmit(self):
        self.inbox.accept(self.event, terminal=True)
        result = self.inbox.classify("a", 0, dict(self.event, sent_perf=999,
                                                received_perf=1000,
                                                physical_channel_worker="a"))
        self.assertEqual(result.action, "ignore_duplicate")

    def test_unbound_incarnation_cannot_acquire_job_authority(self):
        event = dict(self.event, worker_incarnation=1)
        result = self.inbox.classify("a", 0, event)
        self.assertEqual(result.action, "reject_envelope")
        self.assertFalse(result.physical_terminal)

    def test_session_fence_does_not_release_lease_on_ASR(self):
        self.epoch = 1
        result = self.inbox.classify("a", 0, dict(self.event, kind="asr_early"))
        self.assertEqual(result.action, "ignore_fenced")
        self.assertFalse(result.physical_terminal)
        self.assertIn(self.job["job_id"], self.inbox.active)

    def test_terminal_and_new_phase_never_equal_two_completions(self):
        self.inbox.accept(self.event, terminal=True)
        with self.assertRaises(IntegrityError):
            self.inbox.classify("a", 0, dict(self.event, kind="abandoned"))

    def test_classification_does_not_mutate_owned_phase_ledger(self):
        before = copy.deepcopy(self.inbox.active)
        self.inbox.classify("a", 0, self.event)
        self.assertEqual(self.inbox.active, before)


if __name__ == "__main__":
    unittest.main()
