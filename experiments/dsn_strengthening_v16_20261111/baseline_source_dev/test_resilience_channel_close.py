"""Closed-channel CPU controls, including one real child/Pipe closure barrier."""
import copy
import multiprocessing as mp
import pathlib
import queue
import tempfile
import unittest
import numpy as np

from resilience_channel_close import (
    ClosedChannelError, WorkerReportedFailure, drain_closed_worker_channel,
)
from resilience_policy import ResilientFullSpecCoordinator
from resilience_storage import FactStore
from resilience_transport import FramedReader, FramedSender
from test_resilience_storage import body, cut


def finished_child(results, control, event):
    try:
        FramedSender(results, slot="f0", incarnation=0).put(event)
        control.send(dict(kind="state_telemetry", row=dict(boundary="context_trim")))
    finally:
        results.close()
        control.close()


def proof(**changes):
    result = dict(slot="f0", incarnation=0, pid=123, exitcode=-9,
                  confirmed_exit=True, result_channel_closed=True,
                  control_channel_closed=True, partial_frame_thread_blocked=False)
    result.update(changes)
    return result


def packet(kind="completed", *, slot="f0", incarnation=0, serial=1):
    return dict(type="message", slot=slot, incarnation=incarnation,
                received_perf=123.0,
                payload=dict(kind=kind, job_id=f"e0-j{serial:09d}",
                             worker=slot, worker_incarnation=incarnation,
                             source_id="s", dispatch_epoch=0))


class ClosedChannelControls(unittest.TestCase):
    def setUp(self):
        self.inbox = queue.Queue()

    def drain(self, callback, **kwargs):
        return drain_closed_worker_channel(
            self.inbox, slot="f0", incarnation=0, death_proof=kwargs.pop("death_proof", proof()),
            on_message=callback, **kwargs)

    def test_no_admission_before_real_exit_and_both_readers_are_closed(self):
        self.inbox.put(packet())
        called = []
        for fields in ({"confirmed_exit": False}, {"result_channel_closed": False},
                       {"control_channel_closed": False},
                       {"partial_frame_thread_blocked": True}, {"incarnation": 1},
                       {"exitcode": None}):
            with self.subTest(fields=fields), self.assertRaises(ClosedChannelError):
                self.drain(called.append, death_proof=proof(**fields))
        self.assertFalse(called)
        self.assertEqual(self.inbox.qsize(), 1)

    def test_result_FIFO_is_preserved_while_EOF_grants_no_result(self):
        first, second = packet("asr_early"), packet("completed")
        self.inbox.put(first)
        self.inbox.put(dict(type="channel_exit", slot="f0", incarnation=0,
                            partial_frame=True))
        self.inbox.put(second)
        received = []
        result = self.drain(lambda p: received.append(p["payload"]["kind"]))
        self.assertEqual(received, ["asr_early", "completed"])
        self.assertEqual(result["counts"]["partial_logical_frame"], 1)
        self.assertFalse(result["new_authority_granted_by_helper"])
        self.assertEqual(self.inbox.unfinished_tasks, 0)

    def test_other_channel_old_entries_stay_before_concurrent_new_entries(self):
        other_old = packet(slot="f1", serial=2)
        self.inbox.put(other_old)
        self.inbox.put(packet())
        other_new = packet(slot="f1", serial=3)
        def callback(_):
            self.inbox.put(other_new)
        self.drain(callback)
        self.assertIs(self.inbox.get_nowait(), other_old)
        self.assertIs(self.inbox.get_nowait(), other_new)

    def test_new_incarnation_is_not_stolen_by_old_channel_drain(self):
        fresh = packet(incarnation=1)
        self.inbox.put(packet())
        self.inbox.put(fresh)
        old = []
        self.drain(old.append)
        self.assertEqual(len(old), 1)
        self.assertIs(self.inbox.get_nowait(), fresh)

    def test_worker_reported_failure_is_fatal_even_after_valid_queued_completion(self):
        self.inbox.put(packet())
        self.inbox.put(packet("failed"))
        self.inbox.put(dict(type="channel_exit", slot="f0", incarnation=0))
        called, audited = [], []
        with self.assertRaises(WorkerReportedFailure):
            self.drain(called.append, audit_packet=audited.append)
        self.assertFalse(called)
        self.assertEqual(len(audited), 3)
        self.assertEqual(self.inbox.unfinished_tasks, 0)

    def test_integrity_failure_is_not_masked_as_normal_EOF(self):
        self.inbox.put(packet())
        self.inbox.put(dict(type="channel_integrity_failure", slot="f0", incarnation=0))
        received = []
        with self.assertRaises(ClosedChannelError):
            self.drain(received.append)
        self.assertFalse(received)

    def test_final_native_state_control_is_observational_not_a_result(self):
        diagnostic = dict(type="control", slot="f0", incarnation=0,
                          payload=dict(kind="state_telemetry", row={"boundary": "audio_insert"}))
        self.inbox.put(diagnostic)
        results, controls = [], []
        summary = self.drain(results.append, on_control=controls.append)
        self.assertFalse(results)
        self.assertEqual(controls, [diagnostic])
        self.assertEqual(summary["counts"]["control_records"], 1)

    def test_retired_ready_and_drain_cannot_regrant_process_readiness(self):
        self.inbox.put(packet("ready"))
        self.inbox.put(packet("drained"))
        received = []
        result = self.drain(received.append)
        self.assertFalse(received)
        self.assertEqual(result["counts"]["retired_process_controls"], 2)

    def test_callback_integrity_error_is_not_swallowed(self):
        self.inbox.put(packet())
        def fail(_):
            raise RuntimeError("strict Original input failed")
        with self.assertRaisesRegex(RuntimeError, "strict Original"):
            self.drain(fail)
        self.assertEqual(self.inbox.unfinished_tasks, 0)

    def test_real_closed_Pipe_complete_result_is_admitted_before_worker_fence(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root, end = cut(0), cut(8000, "original selected")
        store = FactStore(pathlib.Path(tmp.name) / "facts.wal",
                          {"s": root.state}, {"scope": "CPU protocol fixture"})
        self.addCleanup(store.close)
        def commit(value):
            value = dict(value)
            value["record"] = value.pop("full_record")
            return store.commit(value)
        coordinator = ResilientFullSpecCoordinator(
            initials={"s": root.state}, audio={"s": np.zeros(16000, dtype=np.float32)},
            runtime_identity={"scope": "synthetic CPU executor"},
            source_frames={"s": 16000}, authority_workers=("f0", "f1"),
            owner_epoch=0, before_commit=commit, worker_incarnations={"f0": 0, "f1": 0})
        job_id = "e0-j000000001"
        coordinator.register(job_id=job_id, worker="f0", worker_incarnation=0,
                             kind="full", source_id="s", start=root, end=8000,
                             dispatched_perf=0.0)
        message = dict(
            kind="completed", worker="f0", job_id=job_id, source_id="s", dispatch_epoch=0,
            start=root.state, end=end.state, record=body(root, end)["record"])
        ctx = mp.get_context("spawn")
        result_rx, result_tx = ctx.Pipe(duplex=False)
        control_rx, control_tx = ctx.Pipe(duplex=False)
        process = ctx.Process(target=finished_child, args=(result_tx, control_tx, message))
        process.start()
        result_tx.close()
        control_tx.close()
        result_reader = FramedReader(result_rx, "f0", 0, self.inbox)
        control_reader = FramedReader(control_rx, "f0", 0, self.inbox, "control")
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
            self.fail("CPU child did not close its frames")
        result_reader.thread.join(5)
        control_reader.thread.join(5)
        self.assertFalse(result_reader.thread.is_alive())
        self.assertFalse(control_reader.thread.is_alive())
        actual_proof = proof(pid=process.pid, exitcode=process.exitcode,
                             result_channel_closed=result_reader.closed,
                             control_channel_closed=control_reader.closed)
        admitted = []
        def receive(value):
            self.assertEqual(coordinator.inbound.worker_incarnations["f0"], 0)
            response = coordinator.receive_event(
                value["slot"], value["incarnation"], value["payload"],
                received_perf=value["received_perf"])
            admitted.append(copy.deepcopy(value))
            return response
        result = self.drain(receive, death_proof=actual_proof)
        self.assertEqual(result["counts"]["disposition_accept"], 1)
        self.assertTrue(coordinator.canonical("s").same(end))
        self.assertTrue(store.roots["s"].same(end))
        loss = coordinator.worker_lost("f0", 0, actual_proof)
        self.assertEqual(loss["retired_live_jobs"], [])
        coordinator.replace_worker("f0", 1)
        old = admitted[0]
        late = coordinator.receive_event("f0", 0, old["payload"],
                                         received_perf=old["received_perf"] + 1)
        self.assertEqual(late["disposition"], "ignore_fenced")
        self.assertEqual(store.sequence, 2)


if __name__ == "__main__":
    unittest.main()
