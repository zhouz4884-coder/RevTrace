"""Run actual Owner code with a synthetic CPU protocol executor.

These fixtures are deliberately not neural/serving evidence.  Actual model
calls, GPU releases and OS fail-stop behavior are tested in their own tiers.
They exercise the real Owner->FactStore->SurvivorConsumer call path before
an expensive neural pilot, without loading torch or contacting a remote host.
"""
import collections
import copy
import hashlib
import json
import os
import pathlib
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
import numpy as np

import resilience_owner as owner_module
from feedback_contract import FeedbackCut
from resilience_consumer import SurvivorConsumer
from resilience_storage import FactStore, canonical, scan
from test_resilience_consumer import private
from test_resilience_storage import body, cut


class Control:
    def __init__(self):
        self.items = collections.deque()
    def poll(self):
        return bool(self.items)
    def recv(self):
        return self.items.popleft()
    def send(self, value):
        self.items.append(value)


class FakeProcess:
    def __init__(self, pid):
        self.pid, self.exitcode, self.alive = pid, None, True
    def is_alive(self):
        return self.alive
    def join(self, timeout=None):
        return None


class Command:
    def __init__(self, harness, slot, incarnation):
        self.harness, self.slot, self.incarnation = harness, slot, incarnation
    def send(self, command):
        if command is not None:
            self.harness.execute(self.slot, self.incarnation, command)


class Harness:
    def __init__(self, folder, *, arm="conservative", stray=False,
                 reset_session=False, future_first=False, fault=None, recovered=False,
                 closed_channel_first=False):
        self.folder, self.arm = folder, arm
        self.stray, self.reset_session, self.future_first = stray, reset_session, future_first
        self.closed_channel_first = closed_channel_first
        self.root = cut(0)
        self.initials = {"s": self.root.state}
        self.origin = types.SimpleNamespace(value=0.0)
        self.accepted = {"s": types.SimpleNamespace(value=16000)}
        self.control = Control()
        self.consumer = None
        self.inbox = None
        self.policy = None
        self.epoch = 1 if recovered else 0
        self.events, self.commands, self.held = [], [], []
        self.config = dict(
            cell_id="DEVELOPMENT_SYNTHETIC_CPU_OWNER_PROTOCOL",
            arm=arm, maximum_service_seconds=2.0, fault=fault or {"kind": "none"},
            settings=dict(
                source_commit="DEVELOPMENT_NOT_A_NEURAL_RUN", primary_gpu=0,
                max_ahead_frames=32000,
                sources=[dict(source_id="s", path="unused.wav",
                              frames=16000, audio_sha256="immutable")],
            ),
        )
        if recovered:
            metadata = dict(
                config_sha256=hashlib.sha256(canonical(self.config)).hexdigest(),
                actual_source_commit=self.config["settings"]["source_commit"],
                sources=[dict(source_id="s", frames=16000, audio_sha256="immutable")],
            )
            store = FactStore(folder / "facts.wal", self.initials, metadata)
            transition = body(self.root, cut(8000, "frozen8000"))
            transition["owner_epoch"] = 0
            transition["job"]["job_id"] = "e0-j000000001"
            receipt = store.commit(transition)
            store.close()
            self.consumer = self.new_consumer()
            self.consumer.begin_owner(0)
            self.consumer.replay_fact(receipt)
            self.consumer.begin_owner(1)
            self.origin.value = time.perf_counter() - .05

    def new_consumer(self):
        return SurvivorConsumer(self.initials, self.folder / "consumer.jsonl",
                                self.folder / "rejects.jsonl", self.folder / "facts.wal")

    def send(self, message):
        self.events.append(copy.deepcopy(message))
        kind = message["kind"]
        if kind == "owner_ready" and self.consumer is None:
            self.consumer = self.new_consumer()
            self.consumer.begin_owner(self.epoch)
            self.origin.value = time.perf_counter()
            if self.stray:
                # A current channel's unsolicited frame must stay a local drop,
                # even before the first owned job or dispatch-local import.
                self.enqueue("full0", 0, dict(
                    kind="completed", worker="full0", worker_incarnation=0,
                    job_id=f"e{self.epoch}-j999999999", source_id="s", dispatch_epoch=0))
        elif kind == "publication":
            result = self.consumer.apply(message["event"], self.epoch)
            refs = result.get("visible_job_ids", [])
            self.control.send(dict(kind="consumer_ack",
                                   publication_id=message["event"]["publication_id"],
                                   visible_job_ids=refs))

    def enqueue(self, slot, incarnation, event):
        self.inbox.put(dict(type="message", slot=slot, incarnation=incarnation,
                            payload=event, received_perf=time.perf_counter()))

    def start_worker(self, ctx, slot, gpu, settings, incarnation, inbox,
                     fault, fired, lock):
        self.inbox = inbox
        process = FakeProcess((20001 if slot == "full0" else 20002) + incarnation * 100)
        ready = dict(
            kind="ready", worker=slot, worker_incarnation=incarnation,
            pid=process.pid, gpu=gpu, mode="authority",
            runtime_identity={"scope": "synthetic CPU executor; no neural calls"},
            initials=self.initials,
            neural_ready_warmup=dict(neural_C_confirmed=True, reset_to_genesis=True,
                                    warmup_packet_admitted=False),
        )
        self.enqueue(slot, incarnation, ready)
        return dict(process=process, commands=Command(self, slot, incarnation),
                    hints=Control(), slot=slot, gpu=gpu, incarnation=incarnation,
                    pid=process.pid, start_ticks=None)

    def execute(self, slot, incarnation, command):
        self.commands.append(copy.deepcopy(command))
        start = FeedbackCut(command["start"])
        end = cut(command["end"], "frozen" + str(command["end"]))
        projection = dict(
            kind="typed_ASR_stage_identity_feedback_projection",
            learned_C_executed=False, original_full_infer_completed=False,
            token_ids=[end.frontier], end=end.state, end_state_sha=end.sha256,
        )
        early = dict(
            kind="asr_early", worker=slot, worker_incarnation=incarnation,
            job_id=command["job_id"], source_id="s",
            dispatch_epoch=command["dispatch_epoch"], start_state=start.state,
            start_state_sha=start.sha256, end_frontier=end.frontier,
            producer_role="authority", produced_perf=time.perf_counter(),
            projection=projection, candidate_wire=None,
        )
        record = body(start, end)["record"]
        record.update(model_start=self.policy.jobs[command["job_id"]]["dispatched_perf"],
                      model_end=time.perf_counter())
        complete = dict(
            kind="completed", worker=slot, worker_incarnation=incarnation,
            job_id=command["job_id"], source_id="s",
            dispatch_epoch=command["dispatch_epoch"],
            start=start.state, end=end.state, record=record,
        )
        if self.reset_session:
            self.reset_session = False
            self.policy.reset_epoch("s", self.policy.canonical("s"))
        if self.closed_channel_first:
            self.closed_channel_first = False
            self.inbox.put(dict(type="channel_exit", slot=slot,
                                incarnation=incarnation, partial_frame=False,
                                error="CPU fixture: EOF observed before result-reader delivery"))
        self.enqueue(slot, incarnation, early)
        if self.future_first and start.frontier == 0:
            self.held.append((slot, incarnation, complete))
        else:
            self.enqueue(slot, incarnation, complete)
            for held in self.held:
                self.enqueue(*held)
            self.held.clear()

    def stop_worker(self, worker, force=False):
        worker["process"].alive = False
        worker["process"].exitcode = 0
        return dict(confirmed_exit=True, confirmed_dead=True, slot=worker["slot"],
                    incarnation=worker["incarnation"], pid=worker["pid"],
                    exitcode=0, result_channel_closed=True,
                    control_channel_closed=True, partial_frame_thread_blocked=False)

    def run(self):
        real_policy = owner_module.ResilientFullSpecCoordinator
        def policy(**kwargs):
            self.policy = real_policy(**kwargs)
            return self.policy
        fake_ctx = types.SimpleNamespace(Event=threading.Event, Lock=threading.Lock)
        fake_sf = types.SimpleNamespace(read=lambda *args, **kw: (np.zeros(16000, dtype=np.float32), 16000))
        old_origin = self.origin.value
        with patch.object(owner_module.mp, "get_context", return_value=fake_ctx), \
             patch.object(owner_module, "start_worker", side_effect=self.start_worker), \
             patch.object(owner_module, "stop_worker", side_effect=self.stop_worker), \
             patch.object(owner_module, "wait_cuda_release",
                          return_value={"scope": "CPU protocol fixture; no CUDA context"}), \
             patch.object(owner_module, "ResilientFullSpecCoordinator", side_effect=policy), \
             patch.object(owner_module.os, "setsid", create=True), \
             patch.object(owner_module.os, "getpgrp", return_value=os.getpid(), create=True), \
             patch.dict("sys.modules", {"soundfile": fake_sf}):
            owner_module.owner_main(
                self.config, "unused-manifest", self.folder, self.epoch,
                self.control, self, self.accepted, self.origin,
                self.initials if self.epoch else None,
            )
        if self.epoch:
            assert self.origin.value == old_origin
        return self

    def close(self):
        if self.consumer is not None:
            self.consumer.close()


class OwnerProtocolIntegrationControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = pathlib.Path(self.tmp.name)

    def harness(self, **kwargs):
        h = Harness(self.folder, **kwargs)
        self.addCleanup(h.close)
        return h

    def assert_complete(self, h):
        self.assertFalse(any(e["kind"] == "owner_error" for e in h.events))
        self.assertTrue(any(e["kind"] == "owner_finished" for e in h.events))
        self.assertEqual(h.consumer.snapshot("s")["certified_frontier"], 16000)
        facts = [obj for obj, _ in scan(self.folder / "facts.wal") if obj["kind"] == "canonical"]
        self.assertEqual([r["body"]["next_state"]["frontier"] for r in facts], [8000, 16000])
        return facts

    def test_actual_owner_consumer_store_path_completes_conservative_fixture(self):
        self.assert_complete(self.harness().run())

    def test_actual_owner_buffers_future_then_installs_parent_order(self):
        h = self.harness(arm="fullcall", future_first=True).run()
        self.assert_complete(h)
        self.assertEqual(h.policy.history_stats()["audit_total"]["discarded_full"], 0)
        publications = [e["event"] for e in h.events if e["kind"] == "publication"
                        and e["event"]["kind"] == "canonical"]
        self.assertEqual([p["durable_receipt"]["journal_seq"] for p in publications], [2, 3])

    def test_predispatch_unknown_frame_is_rejected_and_owner_continues(self):
        h = self.harness(stray=True).run()
        self.assert_complete(h)
        rows = [json.loads(line) for line in
                (self.folder / "owner_e0/owner_events.jsonl").read_text().splitlines()]
        rejects = [r for r in rows if r["kind"] == "local_message_disposition"]
        self.assertEqual(len(rejects), 1)
        self.assertEqual(rejects[0]["result"]["disposition"], "reject_unknown")
        self.assertEqual(rejects[0]["before"]["busy"], rejects[0]["after"]["busy"])

    def test_fenced_terminal_releases_its_exact_old_busy_and_service_continues(self):
        h = self.harness(reset_session=True).run()
        self.assert_complete(h)
        rows = [json.loads(line) for line in
                (self.folder / "owner_e0/owner_events.jsonl").read_text().splitlines()]
        terminal = next(r for r in rows if r["kind"] == "local_message_disposition"
                        and r["result"]["disposition"] == "retire_fenced_terminal")
        self.assertTrue(terminal["result"]["physical_terminal"])
        self.assertIsNone(terminal["after"]["busy"]["full0"])

    def test_actual_duplicate_replay_does_not_create_extra_original_program_facts(self):
        h = self.harness(fault=dict(kind="duplicate_late", source_id="s", target=8000)).run()
        self.assert_complete(h)
        rows = [json.loads(line) for line in
                (self.folder / "owner_e0/owner_events.jsonl").read_text().splitlines()]
        duplicate = [r for r in rows if r["kind"] == "local_message_disposition"
                     and r["result"]["disposition"] == "ignore_duplicate"]
        self.assertGreaterEqual(len(duplicate), 2)

    def test_recovered_owner_uses_frozen_canonical_and_original_clock(self):
        h = self.harness(recovered=True).run()
        facts = self.assert_complete(h)
        self.assertEqual(h.commands[0]["start"]["frontier"], 8000)
        self.assertEqual(facts[-1]["body"]["owner_epoch"], 1)
        self.assertEqual(facts[-1]["body"]["session_epoch"], 0)
        self.assertEqual(facts[-1]["body"]["job"]["dispatch_epoch"], 0)
        self.assertTrue(facts[-1]["body"]["job"]["job_id"].startswith("e1-j"))

    def test_control_EOF_before_queued_complete_does_not_force_legal_recomputation(self):
        h = self.harness(closed_channel_first=True).run()
        facts = self.assert_complete(h)
        self.assertEqual(len(h.commands), 2)
        self.assertEqual(facts[0]["body"]["job"]["job_id"], "e0-j000000001")
        self.assertEqual(facts[0]["body"]["job"]["worker_incarnation"], 0)
        self.assertTrue(any(e["kind"] == "worker_death_confirmed" for e in h.events))
        rows = [json.loads(line) for line in
                (self.folder / "owner_e0/owner_events.jsonl").read_text().splitlines()]
        loss = next(r for r in rows if r["kind"] == "worker_death_confirmed")
        self.assertTrue(loss["proof"]["confirmed_exit"])


if __name__ == "__main__":
    unittest.main()
