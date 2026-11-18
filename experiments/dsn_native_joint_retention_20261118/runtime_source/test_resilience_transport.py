"""Real CPU child-process IPC controls; no CUDA or serving measurements."""
import hashlib
import json
import multiprocessing as mp
import pickle
import queue
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import resilience_transport as transport
from resilience_inbound import ResilientInbound


def event(serial=1, slot="f0", label="original"):
    return dict(kind="completed", worker=slot, job_id="e5-j" + f"{serial:09d}",
                source_id="s", dispatch_epoch=0, label=label)


def child_send(connection, payload, incarnation):
    try:
        transport.FramedSender(connection, slot=payload["worker"],
                               incarnation=incarnation).put(payload)
    finally:
        connection.close()


def child_raw(connection, raw, declared_sha=None, declared_size=None):
    try:
        header = dict(bytes=len(raw) if declared_size is None else declared_size,
                      sha256=declared_sha or hashlib.sha256(raw).hexdigest())
        connection.send_bytes(json.dumps(header).encode())
        connection.send_bytes(raw)
    finally:
        connection.close()


def child_partial(connection, control, initial=None, incarnation=0):
    try:
        if initial is not None:
            transport.FramedSender(connection, slot="f0",
                                   incarnation=incarnation).put(initial)
        raw = pickle.dumps(dict(event(), worker_incarnation=incarnation), protocol=5)
        connection.send_bytes(json.dumps(dict(
            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())).encode())
        control.send(dict(header_written=True, pid=mp.current_process().pid))
        time.sleep(30)  # Parent performs real termination after the header.
    finally:
        control.close()
        connection.close()


def child_drain(commands, results, hints, control, incarnation):
    try:
        if commands.recv() is not None:
            raise RuntimeError("unexpected test command")
        transport.FramedSender(results, slot="f0", incarnation=incarnation).put(
            dict(kind="drained", worker="f0"))
    finally:
        for connection in (commands, results, hints, control):
            connection.close()


class TransportControls(unittest.TestCase):
    def setUp(self):
        self.ctx = mp.get_context("spawn")
        self.inbox = queue.Queue()
        self.processes, self.readers = [], []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for process in self.processes:
            if process.is_alive():
                process.kill()
            process.join(5)
        for reader in self.readers:
            reader.thread.join(5)
            if reader.thread.is_alive():
                reader.c.close()

    def start(self, target, arguments, slot="f0", incarnation=0):
        receive, send = self.ctx.Pipe(duplex=False)
        process = self.ctx.Process(target=target, args=(send, *arguments))
        process.start()
        send.close()  # Only the child retains the write end.
        reader = transport.FramedReader(receive, slot, incarnation, self.inbox)
        self.processes.append(process)
        self.readers.append(reader)
        return process, reader

    def partial(self, initial=None, incarnation=0):
        receive, send = self.ctx.Pipe(duplex=False)
        control_rx, control_tx = self.ctx.Pipe(duplex=False)
        process = self.ctx.Process(target=child_partial,
                                   args=(send, control_tx, initial, incarnation))
        process.start()
        send.close()
        control_tx.close()
        self.addCleanup(control_rx.close)
        reader = transport.FramedReader(receive, "f0", incarnation, self.inbox)
        self.processes.append(process)
        self.readers.append(reader)
        self.assertTrue(control_rx.poll(5), "child did not reach the physical IPC boundary")
        self.assertTrue(control_rx.recv()["header_written"])
        return process, reader

    def take(self, kind):
        deadline = time.monotonic() + 5
        skipped = []
        while time.monotonic() < deadline:
            try:
                record = self.inbox.get(timeout=max(.001, deadline - time.monotonic()))
            except queue.Empty:
                break
            if record["type"] == kind:
                for previous in skipped:
                    self.inbox.put(previous)
                return record
            skipped.append(record)
        for previous in skipped:
            self.inbox.put(previous)
        self.fail("missing " + kind)

    def test_complete_frame_keeps_bound_physical_incarnation(self):
        payload = dict(event(), worker_incarnation=999)
        process, reader = self.start(child_send, (payload, 3), incarnation=3)
        received = self.take("message")
        self.assertEqual(received["incarnation"], 3)
        self.assertEqual(received["payload"]["worker_incarnation"], 3)
        self.assertEqual(received["payload"]["label"], "original")
        process.join(5)
        reader.thread.join(5)
        self.assertTrue(reader.closed)

    def test_partial_logical_frame_exits_reader_after_real_child_termination(self):
        process, reader = self.partial()
        self.assertTrue(reader.thread.is_alive())
        # No body has arrived; the Owner's thread remains free.
        self.assertEqual(sum(range(1000)), 499500)
        process.kill()
        process.join(5)
        self.assertFalse(process.is_alive())
        self.assertIsNotNone(process.exitcode)
        closed = self.take("channel_exit")
        self.assertTrue(closed["partial_frame"])
        reader.thread.join(5)
        self.assertFalse(reader.thread.is_alive())
        self.assertTrue(reader.closed)

    def test_blocked_old_reader_does_not_block_another_legitimate_channel(self):
        old, old_reader = self.partial()
        good, good_reader = self.start(child_send, (event(2, "f1", "other work"), 0),
                                       slot="f1", incarnation=0)
        received = self.take("message")
        self.assertEqual(received["slot"], "f1")
        self.assertEqual(received["payload"]["label"], "other work")
        self.assertTrue(old.is_alive())
        self.assertTrue(old_reader.thread.is_alive())
        old.kill()
        old.join(5)
        old_reader.thread.join(5)
        good.join(5)
        good_reader.thread.join(5)
        self.assertFalse(old_reader.thread.is_alive())

    def test_checksum_corruption_is_never_emitted_as_a_worker_event(self):
        raw = pickle.dumps(dict(event(), worker_incarnation=0), protocol=5)
        process, reader = self.start(child_raw, (raw, "0" * 64))
        failure = self.take("channel_integrity_failure")
        self.assertIn("corrupt", failure["error"])
        process.join(5)
        reader.thread.join(5)
        records = []
        while not self.inbox.empty():
            records.append(self.inbox.get_nowait())
        self.assertFalse(any(row["type"] == "message" for row in records))

    def test_oversize_declared_frame_rejected_before_body_authority(self):
        raw = pickle.dumps(dict(event(), worker_incarnation=0), protocol=5)
        process, reader = self.start(child_raw, (raw, None, transport.MAX_WIRE + 1))
        failure = self.take("channel_integrity_failure")
        self.assertIn("bounded", failure["error"])
        process.join(5)
        reader.thread.join(5)

    def test_complete_pickled_non_event_cannot_acquire_message_authority(self):
        process, reader = self.start(child_raw, (pickle.dumps(["not an event"]),))
        failure = self.take("channel_integrity_failure")
        self.assertIn("not an event", failure["error"])
        process.join(5)
        reader.thread.join(5)

    def test_actual_old_channel_payload_does_not_migrate_into_replacement_authority(self):
        inbox = ResilientInbound(owner_epoch=5, worker_incarnations={"f0": 0},
                                 session_epoch=lambda _: 0, terminal_limit=2)
        old_job = dict(job_id="e5-j000000001", worker="f0", source_id="s",
                       dispatch_epoch=0, start=SimpleNamespace(sha256="start"), end=8)
        inbox.register(old_job, 0)
        old_process, old_reader = self.partial(initial=event(1, label="old execution"))
        delayed = self.take("message")  # Real received bytes, deliberately held.
        old_process.kill()
        old_process.join(5)
        old_reader.thread.join(5)
        self.assertFalse(old_process.is_alive())
        inbox.lose_worker("f0", 0)
        inbox.replace_worker("f0", 1)
        new_job = dict(old_job, job_id="e5-j000000002")
        inbox.register(new_job, 1)
        new_process, new_reader = self.start(child_send, (event(2, label="new execution"), 1),
                                             incarnation=1)
        fresh = self.take("message")
        late = inbox.classify(delayed["slot"], delayed["incarnation"], delayed["payload"])
        self.assertEqual(late.action, "ignore_fenced")
        self.assertFalse(late.physical_terminal)
        self.assertIn(new_job["job_id"], inbox.active)
        self.assertEqual(inbox.classify(fresh["slot"], fresh["incarnation"],
                                       fresh["payload"]).action, "accept")
        new_process.join(5)
        new_reader.thread.join(5)

    def test_stop_worker_proof_has_policy_compatible_exit_identity(self):
        command_rx, command_tx = self.ctx.Pipe(duplex=False)
        result_rx, result_tx = self.ctx.Pipe(duplex=False)
        hint_rx, hint_tx = self.ctx.Pipe(duplex=False)
        control_rx, control_tx = self.ctx.Pipe(duplex=False)
        process = self.ctx.Process(target=child_drain,
                                   args=(command_rx, result_tx, hint_rx, control_tx, 0))
        process.start()
        for endpoint in (command_rx, result_tx, hint_rx, control_tx):
            endpoint.close()
        result = transport.FramedReader(result_rx, "f0", 0, self.inbox)
        control = transport.FramedReader(control_rx, "f0", 0, self.inbox, "control")
        self.processes.append(process)
        self.readers += [result, control]
        worker = dict(process=process, commands=command_tx, hints=hint_tx,
                      result_reader=result, control_reader=control, incarnation=0,
                      slot="f0", gpu=0, pid=process.pid,
                      start_ticks=transport.start_ticks(process.pid))
        proof = transport.stop_worker(worker)
        self.assertTrue(proof["confirmed_exit"])
        self.assertEqual(proof["slot"], "f0")
        self.assertEqual(proof["incarnation"], 0)
        self.assertEqual(proof["pid"], process.pid)
        self.assertIsNotNone(proof["exitcode"])
        self.assertFalse(proof["partial_frame_thread_blocked"])

    def test_CUDA_slot_reuse_waits_for_process_and_context_release(self):
        samples = iter(("321\n", "256\n", "", "160\n", "", "24\n"))
        with patch.object(transport.subprocess, "check_output",
                          side_effect=lambda *a, **k: next(samples)), \
             patch.object(transport.time, "sleep"):
            proof = transport.wait_cuda_release(0, 321, timeout=2)
        self.assertTrue(proof["gpu_context_released"])
        self.assertEqual(proof["memory_used_MiB"], 24)


if __name__ == "__main__":
    unittest.main()
