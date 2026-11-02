"""Development CPU controls: actual coordinator transitions, no model replay."""
import copy
import unittest
import numpy as np

from feedback_contract import FeedbackCut
from resilience_inbound import IntegrityError, WritesFrozenError
from resilience_policy import CommitHookError, ResilientFullSpecCoordinator


def cut(frontier, text=""):
    return FeedbackCut(dict(
        audio_segments=[], tokens=[[[1, 2, 3, 4]] * 4, [[frontier]] * 4],
        context=dict(text="", prefix_token_ids=[9], token_ids=[9]),
        last_attend_frame=frontier // 100, detected_language="zh",
        initial_tokens=[[1, 2, 3, 4]], initial_token_length=4, sot_index=0,
        decoder_type="beam", contract=dict(source_sha="immutable", dtype="float32"),
        frontier=frontier, transcript=text,
    ))


class ResiliencePolicyControls(unittest.TestCase):
    def setUp(self):
        self.sid, self.root, self.serial = "s", cut(0), 0
        self.commits, self.audit = [], []
        self.c = self.make()

    def make(self, hook=None, history_limit=4):
        def commit(transition):
            self.assertTrue(self.c.canonical(self.sid).same(FeedbackCut(transition["parent_state"])))
            self.commits.append(copy.deepcopy(transition))
            return dict(transition_id="commit-" + str(len(self.commits)),
                        journal_seq=len(self.commits), record_sha="a" * 64)
        return ResilientFullSpecCoordinator(
            initials={self.sid: self.root.state}, audio={self.sid: np.zeros(2000000, dtype=np.float32)},
            runtime_identity={"source": "fixed"}, source_frames={self.sid: 2000000},
            authority_workers=("f0", "f1"), owner_epoch=7,
            worker_incarnations={"f0": 0, "f1": 0}, before_commit=hook or commit,
            history_limit=history_limit,
            audit_sink=lambda kind, record: self.audit.append((kind, record)),
        )

    def register(self, worker="f0", start=None):
        self.serial += 1
        job_id = "e7-j" + f"{self.serial:09d}"
        start = self.c.canonical(self.sid) if start is None else start
        self.c.register(job_id=job_id, worker=worker, kind="full", source_id=self.sid,
                        start=start, end=start.frontier + 8000,
                        dispatched_perf=self.serial * 10.0)
        return job_id

    def early_event(self, job_id, end):
        job = self.c.jobs[job_id]
        projection = dict(kind="typed_ASR_stage_identity_feedback_projection",
                          learned_C_executed=False, original_full_infer_completed=False,
                          token_ids=[end.frontier], end=end.state, end_state_sha=end.sha256)
        return dict(kind="asr_early", worker=job["worker"],
                    worker_incarnation=job["worker_incarnation"], job_id=job_id,
                    dispatch_epoch=job["dispatch_epoch"], source_id=self.sid,
                    start_state=job["start"].state, start_state_sha=job["start"].sha256,
                    end_frontier=job["end"], producer_role="authority",
                    produced_perf=job["dispatched_perf"] + 1, projection=projection,
                    candidate_wire=None)

    def completion_event(self, job_id, end):
        job = self.c.jobs[job_id]
        return dict(kind="completed", worker=job["worker"],
                    worker_incarnation=job["worker_incarnation"], job_id=job_id,
                    dispatch_epoch=job["dispatch_epoch"], source_id=self.sid,
                    start=job["start"].state, end=end.state,
                    record=dict(start_state=job["start"].sha256, end_state=end.sha256,
                                role="authority", candidate_handoff=False,
                                token_ids=[end.frontier], selected_correction={"actual": "C"}))

    def deliver(self, event, slot=None, incarnation=None):
        slot = event["worker"] if slot is None else slot
        incarnation = event["worker_incarnation"] if incarnation is None else incarnation
        return self.c.receive_event(slot, incarnation, event, received_perf=100000.0)

    def early(self, job_id, end):
        return self.deliver(self.early_event(job_id, end))

    def finish(self, job_id, end):
        return self.deliver(self.completion_event(job_id, end))

    def death(self, slot, incarnation=0):
        return dict(confirmed_exit=True, slot=slot, incarnation=incarnation,
                    pid=123, exitcode=-9, observed_perf=100.0)

    def two_pending(self):
        first = self.register("f0")
        p1 = cut(8000, "prediction1")
        self.early(first, p1)
        second = self.register("f1", p1)
        p2 = cut(16000, "prediction2")
        self.early(second, p2)
        return first, second, p1, p2

    def test_journal_hook_precedes_actual_install_and_receipt_is_bound(self):
        job = self.register()
        result = self.finish(job, cut(8000, "chosen"))
        self.assertEqual(result["outcome"]["kind"], "canonical")
        self.assertEqual(result["outcome"]["durable_receipt"]["journal_seq"], 1)
        self.assertEqual(self.commits[0]["job"]["job_id"], job)
        self.assertEqual(self.commits[0]["job"]["start"], self.root.state)
        self.assertEqual(self.commits[0]["full_record"]["selected_correction"], {"actual": "C"})
        self.assertEqual(self.c.canonical(self.sid).frontier, 8000)

    def test_hook_failure_freezes_writes_without_advancing_Canon(self):
        def failing(_):
            raise OSError("uncertain write")
        self.c = self.make(hook=failing)
        job = self.register()
        with self.assertRaises(CommitHookError):
            self.finish(job, cut(8000, "chosen"))
        self.assertTrue(self.c.canonical(self.sid).same(self.root))
        with self.assertRaises(WritesFrozenError):
            self.register("f1")

    def test_missing_durable_receipt_cannot_silently_install(self):
        self.c = self.make(hook=lambda _: None)
        job = self.register()
        with self.assertRaises(CommitHookError):
            self.finish(job, cut(8000))
        self.assertEqual(self.c.canonical(self.sid).frontier, 0)

    def test_hook_receives_copy_not_mutable_actual_job_or_cut(self):
        def hook(transition):
            transition["job"]["start"]["transcript"] = "tampered copy"
            transition["next_state"]["transcript"] = "tampered copy"
            return dict(transition_id="t", journal_seq=1, record_sha="a" * 64)
        self.c = self.make(hook=hook)
        job = self.register()
        self.finish(job, cut(8000, "real"))
        self.assertEqual(self.c.canonical(self.sid).transcript, "real")

    def test_duplicate_completion_does_not_install_twice_or_release_new_busy_job(self):
        job = self.register()
        event = self.completion_event(job, cut(8000, "chosen"))
        self.deliver(event)
        new_job = self.register()
        duplicate = self.deliver(dict(event, sent_perf=999.0, received_perf=1000.0))
        self.assertEqual(duplicate["disposition"], "ignore_duplicate")
        self.assertFalse(duplicate["physical_terminal"])
        self.assertIn(new_job, self.c.jobs)
        self.assertEqual(len(self.commits), 1)

    def test_contradictory_duplicate_completion_freezes(self):
        job = self.register()
        event = self.completion_event(job, cut(8000, "chosen"))
        self.deliver(event)
        altered = copy.deepcopy(event)
        altered["record"]["token_ids"] = [777]
        with self.assertRaises(IntegrityError):
            self.deliver(altered)
        self.assertTrue(self.c.writes_frozen)
        self.assertEqual(len(self.commits), 1)

    def test_duplicate_early_view_is_idempotent(self):
        job = self.register()
        event = self.early_event(job, cut(8000, "early"))
        self.deliver(event)
        duplicate = self.deliver(event)
        self.assertEqual(duplicate["disposition"], "ignore_duplicate")
        self.assertEqual(len(self.c.owners[self.sid].steps), 1)

    def test_late_first_ASR_after_completion_is_local_drop(self):
        job = self.register()
        early = self.early_event(job, cut(8000, "early"))
        self.finish(job, cut(8000, "selected"))
        result = self.deliver(early)
        self.assertEqual(result["disposition"], "ignore_retired")
        self.assertFalse(result["physical_terminal"])
        self.assertEqual(self.c.canonical(self.sid).transcript, "selected")
        self.assertFalse(self.c.writes_frozen)

    def test_unknown_foreign_message_does_not_clear_owned_work(self):
        job = self.register()
        event = self.completion_event(job, cut(8000))
        event["job_id"] = "e7-j999999999"
        result = self.deliver(event)
        self.assertEqual(result["disposition"], "reject_unknown")
        self.assertFalse(result["physical_terminal"])
        self.assertIn(job, self.c.jobs)
        self.assertFalse(self.c.writes_frozen)

    def test_foreign_channel_is_rejected_without_touching_job(self):
        job = self.register()
        result = self.deliver(self.completion_event(job, cut(8000)), slot="f1")
        self.assertEqual(result["disposition"], "reject_envelope")
        self.assertIn(job, self.c.jobs)
        self.assertFalse(self.c.writes_frozen)

    def test_current_job_changed_frozen_start_is_integrity_failure(self):
        job = self.register()
        event = self.completion_event(job, cut(8000))
        event["start"]["transcript"] = "different actual input"
        with self.assertRaises(IntegrityError):
            self.deliver(event)
        self.assertEqual(self.c.canonical(self.sid).frontier, 0)

    def test_old_session_ASR_drops_but_terminal_retires_exact_old_lease(self):
        job = self.register()
        early = self.early_event(job, cut(8000))
        complete = self.completion_event(job, cut(8000))
        self.c.reset_epoch(self.sid, self.root)
        new_job = self.register("f1")
        old_asr = self.deliver(early)
        self.assertEqual(old_asr["disposition"], "ignore_fenced")
        self.assertIn(job, self.c.jobs)
        terminal = self.deliver(complete)
        self.assertEqual(terminal["disposition"], "retire_fenced_terminal")
        self.assertTrue(terminal["physical_terminal"])
        self.assertNotIn(job, self.c.jobs)
        self.assertIn(new_job, self.c.jobs)
        self.assertEqual(len(self.commits), 0)

    def test_old_epoch_malformed_terminal_does_not_release_lease(self):
        job = self.register()
        event = self.completion_event(job, cut(8000))
        self.c.reset_epoch(self.sid, self.root)
        event["record"]["end_state"] = "bad"
        with self.assertRaises(IntegrityError):
            self.deliver(event)
        self.assertIn(job, self.c.jobs)

    def test_worker_replacement_requires_confirmed_exit(self):
        job = self.register()
        proof = self.death("f0")
        proof["confirmed_exit"] = False
        with self.assertRaises(ValueError):
            self.c.worker_lost("f0", 0, proof)
        with self.assertRaises(ValueError):
            self.c.replace_worker("f0", 1)
        self.assertIn(job, self.c.jobs)

    def test_worker_loss_preserves_valid_view_and_restarts_missing_work(self):
        job = self.register()
        view = cut(8000, "already delivered")
        self.early(job, view)
        result = self.c.worker_lost("f0", 0, self.death("f0"))
        self.assertEqual(result["retired_live_jobs"], [job])
        self.assertTrue(self.c.tail(self.sid).same(view))
        self.assertTrue(self.c.canonical(self.sid).same(self.root))
        self.c.replace_worker("f0", 1)
        replay = self.register("f0")
        self.assertEqual(self.c.jobs[replay]["worker_incarnation"], 1)
        self.finish(replay, view)
        self.assertTrue(self.c.canonical(self.sid).same(view))

    def test_dead_incarnation_cannot_clear_replacement_job(self):
        old = self.register()
        event = self.completion_event(old, cut(8000))
        self.c.worker_lost("f0", 0, self.death("f0"))
        self.c.replace_worker("f0", 1)
        new = self.register()
        for channel_inc in (0, 1):
            result = self.deliver(event, incarnation=channel_inc)
            self.assertEqual(result["disposition"], "ignore_fenced")
            self.assertFalse(result["physical_terminal"])
            self.assertIn(new, self.c.jobs)

    def test_worker_loss_retains_already_accepted_complete_future(self):
        parent, child, p1, p2 = self.two_pending()
        self.assertEqual(self.finish(child, p2)["outcome"]["kind"], "buffered_full")
        self.c.worker_lost("f1", 0, self.death("f1"))
        self.assertIn(child, self.c.completed_full)
        self.finish(parent, p1)
        ready = self.c.pop_ready_commits()
        self.assertEqual([r["job"]["job_id"] for r in ready], [child])
        self.assertEqual(ready[0]["job"]["worker_incarnation"], 0)
        self.assertEqual(len(self.commits), 2)

    def test_gc_keeps_actual_same_F_rejection_witness_for_live_job(self):
        parent, child, p1, p2 = self.two_pending()
        actual1 = cut(8000, "selected differently")
        self.finish(parent, actual1)
        actual_next = self.register("f0", actual1)
        self.finish(actual_next, cut(16000, "actual next"))
        self.c.collect_history()
        proof = self.c.invalidations()[child]
        self.assertEqual(proof["kind"], "actual_canonical_disagrees_with_complete_start")
        self.assertEqual(proof["witness_frontier"], 8000)

    def test_gc_does_not_turn_unknown_future_into_mismatch(self):
        parent, child, p1, p2 = self.two_pending()
        self.finish(child, p2)
        future = self.register("f1", p2)
        actual1 = cut(8000, "different ancestor")
        self.finish(parent, actual1)
        self.c.collect_history()
        self.assertNotIn(future, self.c.invalidations())
        actual_next = self.register("f0", actual1)
        self.finish(actual_next, p2)
        self.assertTrue(self.c.jobs[future]["promoted_to_canonical"])
        self.assertNotIn(future, self.c.invalidations())

    def test_gc_and_dedup_memory_follow_live_dependencies_not_history_length(self):
        self.c = self.make(history_limit=2)
        old_event = None
        for _ in range(32):
            job = self.register()
            event = self.completion_event(job, cut(self.c.jobs[job]["end"], "chosen"))
            old_event = event if old_event is None else old_event
            self.deliver(event)
            stats = self.c.collect_history()
            self.assertEqual(stats["canonical_witnesses"], 1)
            self.assertLessEqual(stats["inbox"]["terminal"], 2)
            self.assertLessEqual(stats["issued_id_memory_entries"], 1)
        dropped = self.deliver(old_event)
        self.assertEqual(dropped["disposition"], "ignore_retired")
        with self.assertRaises(ValueError):
            self.c.register(job_id=old_event["job_id"], worker="f0", kind="full",
                            source_id=self.sid, start=self.c.canonical(self.sid),
                            end=self.c.canonical(self.sid).frontier + 8000,
                            dispatched_perf=99999)

    def test_pending_view_reference_pins_node_and_terminal_receipt(self):
        self.c = self.make(history_limit=1)
        first = self.register()
        projected = cut(8000, "view")
        self.early(first, projected)
        self.finish(first, projected)
        self.c.collect_history(pending_job_ids=[first])
        for _ in range(3):
            job = self.register()
            self.finish(job, cut(self.c.jobs[job]["end"]))
            self.c.collect_history(pending_job_ids=[first])
        self.assertIn(first, self.c.nodes)
        self.assertIn(first, self.c.inbound.terminal)
        self.c.collect_history()
        self.assertNotIn(first, self.c.nodes)
        self.assertLessEqual(len(self.c.inbound.terminal), 1)

    def test_audit_stream_keeps_full_worker_loss_while_recent_memory_is_bounded(self):
        self.c = self.make(history_limit=2)
        for incarnation in range(12):
            self.c.worker_lost("f0", incarnation, self.death("f0", incarnation))
            self.c.replace_worker("f0", incarnation + 1)
        records = [r for kind, r in self.audit if kind == "worker_lost"]
        self.assertEqual(len(records), 12)
        self.assertEqual(records[-1]["death_proof"]["exitcode"], -9)
        self.assertEqual(self.c.worker_losses.total_count, 12)
        self.assertEqual(len(self.c.worker_losses), 2)

    def test_promotions_stream_actual_complete_input_and_parent(self):
        parent, child, p1, p2 = self.two_pending()
        self.finish(parent, p1)
        record = next(r for kind, r in self.audit if kind == "promotion")
        self.assertEqual(record["owned_job"]["job_id"], child)
        self.assertEqual(record["owned_job"]["start"], p1.state)
        self.assertEqual(record["actual_parent_state"], p1.state)

    def test_abandonment_requires_issued_proof_and_emits_no_fact(self):
        parent, child, p1, p2 = self.two_pending()
        self.finish(parent, cut(8000, "different"))
        job = self.c.jobs[child]
        proof = self.c.invalidations()[child]
        event = dict(kind="abandoned", worker=job["worker"], worker_incarnation=0,
                     source_id=self.sid, job_id=child, dispatch_epoch=0,
                     start=job["start"].state, target_end=job["end"], proof=proof,
                     asr_prefix_executed=True, learned_C_executed=False,
                     C_U_completed=False, feedback_cut_emitted=False,
                     actual_cache_decoder_cleared=True)
        result = self.deliver(event)
        self.assertTrue(result["physical_terminal"])
        self.assertFalse(result["outcome"]["certified_output"])
        record = next(r for kind, r in self.audit if kind == "abandoned_full")
        self.assertFalse(record["worker_terminal_event"]["C_U_completed"])
        self.assertEqual(len(self.commits), 1)


if __name__ == "__main__":
    unittest.main()
