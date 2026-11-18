"""CPU storage controls: durability, corruption and exact replay boundaries."""
import builtins
import copy
import hashlib
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import resilience_storage as storage
from feedback_contract import FeedbackCut


def cut(frontier, text=""):
    return FeedbackCut(dict(
        audio_segments=[], tokens=[[[1, 2, 3, 4]] * 4, [[frontier]] * 4],
        context=dict(text="", prefix_token_ids=[9], token_ids=[9]),
        last_attend_frame=frontier // 100, detected_language="zh",
        initial_tokens=[[1, 2, 3, 4]], initial_token_length=4, sot_index=0,
        decoder_type="beam", contract=dict(source_sha="immutable", dtype="float32"),
        frontier=frontier, transcript=text,
    ))


def body(parent, end, serial=1):
    return dict(
        kind="original_full_canonical_transition", owner_epoch=7, session_epoch=0,
        source_id="s", parent_state=parent.state, parent_state_sha256=parent.sha256,
        next_state=end.state, next_state_sha256=end.sha256,
        record=dict(role="authority", candidate_handoff=False,
                    start=parent.frontier, end=end.frontier, is_last=False,
                    start_state=parent.sha256, end_state=end.sha256,
                    token_ids=[end.frontier], selected_correction={"choice": "original"},
                    native_model_evaluated=True, model_start=1.0, model_end=2.0,
                    text=end.transcript),
        job=dict(job_id="e7-j" + f"{serial:09d}", worker="f0", worker_incarnation=0,
                 source_id="s", dispatch_epoch=0, birth_canonical_sha=parent.sha256,
                 start=parent.state, end=end.frontier),
    )


class HalfThenStall:
    """A real partial file write followed by no progress, not a fake receipt."""
    def __init__(self, wrapped):
        self.wrapped, self.first = wrapped, True

    def write(self, raw):
        if self.first:
            self.first = False
            return self.wrapped.write(raw[:len(raw) // 2])
        return 0

    def __getattr__(self, name):
        return getattr(self.wrapped, name)


class StorageControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name) / "facts.wal"
        self.root, self.first, self.second = cut(0), cut(8000, "first"), cut(16000, "second")
        self.metadata = dict(origin_perf=123.0, source_manifest="frozen",
                             input_clock="original_performance_counter")
        self.store = storage.FactStore(self.path, {"s": self.root.state}, self.metadata)
        self.addCleanup(lambda: self.store.close() if not self.store.f.closed else None)

    def reopen(self, repair_tail=False):
        if not self.store.f.closed:
            self.store.close()
        value = storage.FactStore(self.path, {"s": self.root.state}, self.metadata,
                                  repair_tail=repair_tail)
        self.addCleanup(value.close)
        return value

    def append_raw(self, raw):
        self.store.close()
        with self.path.open("ab") as stream:
            stream.write(raw)

    def next_raw(self, transition=None, kind="canonical"):
        return storage.encoded(dict(
            sequence=self.store.sequence + 1, previous=self.store.previous,
            kind=kind, body=transition or body(self.store.roots["s"], self.second, 2),
        ))

    def test_sync_happens_before_receipt_and_visible_root_changes(self):
        old_receipt = copy.deepcopy(self.store.last_receipt)
        seen = []
        real_sync = storage.os.fsync
        def sync(fd):
            seen.append(self.store.sequence)
            self.assertTrue(self.store.roots["s"].same(self.root))
            self.assertEqual(self.store.last_receipt, old_receipt)
            return real_sync(fd)
        with patch.object(storage.os, "fsync", side_effect=sync):
            receipt = self.store.commit(body(self.root, self.first))
        self.assertEqual(seen, [1])
        self.assertTrue(self.store.roots["s"].same(self.first))
        self.assertEqual(receipt["journal_seq"], 2)
        self.assertEqual(receipt["record_sha"], receipt["record_sha256"])

    def test_fsync_failure_yields_no_canonical_receipt_or_state_change(self):
        initial_receipt = copy.deepcopy(self.store.last_receipt)
        with patch.object(storage.os, "fsync", side_effect=OSError("uncertain sync")):
            with self.assertRaises((OSError, storage.JournalIntegrityError)):
                self.store.commit(body(self.root, self.first))
        self.assertTrue(self.store.roots["s"].same(self.root))
        self.assertEqual(self.store.last_receipt, initial_receipt)
        # An uncertain append is not permission to append a second sequence2.
        with self.assertRaises(storage.JournalIntegrityError):
            self.store.commit(body(self.root, self.first))

    def test_partial_write_cannot_issue_a_full_durable_receipt(self):
        self.store.f = HalfThenStall(self.store.f)
        with self.assertRaises((OSError, storage.JournalIntegrityError)):
            self.store.commit(body(self.root, self.first))
        self.assertEqual(self.store.sequence, 1)
        self.assertTrue(self.store.roots["s"].same(self.root))
        recovered = self.reopen(repair_tail=True)
        self.assertTrue(recovered.roots["s"].same(self.root))

    def test_complete_correction_and_IDs_are_bound_into_receipt(self):
        transition = body(self.root, self.first)
        receipt = self.store.commit(transition)
        exact = storage.verify_frame(self.path, receipt)
        self.assertEqual(exact["body"]["record"]["token_ids"], [8000])
        self.assertEqual(exact["body"]["record"]["selected_correction"],
                         {"choice": "original"})
        self.assertEqual(exact["body"]["parent_state"], self.root.state)
        self.assertEqual(exact["body"]["next_state"], self.first.state)

    def test_original_C_IDs_and_model_completion_schema_required_before_append(self):
        for key in ("token_ids", "selected_correction", "native_model_evaluated"):
            transition = body(self.root, self.first)
            del transition["record"][key]
            old_bytes = self.path.read_bytes()
            with self.subTest(key=key), self.assertRaises(storage.JournalIntegrityError):
                self.store.commit(transition)
            self.assertEqual(self.path.read_bytes(), old_bytes)
            self.assertTrue(self.store.roots["s"].same(self.root))

    def test_native_model_evaluated_and_ID_types_not_truthy_coercions(self):
        for key, value in (("native_model_evaluated", "yes"),
                           ("token_ids", None), ("token_ids", [True])):
            transition = body(self.root, self.first)
            transition["record"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(storage.JournalIntegrityError):
                self.store.commit(transition)

    def test_original_buffer_only_full_call_may_have_no_neural_selection(self):
        transition = body(self.root, self.first)
        transition["record"].update(native_model_evaluated=False,
                                    selected_correction=None, token_ids=[])
        receipt = self.store.commit(transition)
        self.assertEqual(self.store.processed["s"], 0)
        self.assertEqual(storage.verify_frame(self.path, receipt)["kind"], "canonical")

    def test_stale_parent_rejects_without_new_frame(self):
        self.store.commit(body(self.root, self.first))
        before = self.path.read_bytes()
        with self.assertRaises(storage.JournalIntegrityError):
            self.store.commit(body(self.root, self.second, 2))
        self.assertEqual(self.path.read_bytes(), before)

    def test_explicit_complete_state_hashes_cannot_disagree(self):
        for key in ("parent_state_sha256", "next_state_sha256"):
            parent = self.store.roots["s"]
            transition = body(parent, cut(parent.frontier + 8000), self.store.sequence)
            transition[key] = "b" * 64
            with self.subTest(key=key), self.assertRaises(storage.JournalIntegrityError):
                self.store.commit(transition)

    def test_unknown_provisional_kind_is_not_a_canonical_fact(self):
        transition = body(self.root, self.first)
        transition["kind"] = "typed_ASR_stage_identity_feedback_projection"
        with self.assertRaises(storage.JournalIntegrityError):
            self.store.commit(transition)

    def test_missing_genesis_never_binds_different_metadata_implicitly(self):
        self.store.close()
        self.path.write_bytes(storage.encoded(dict(
            sequence=1, previous="0" * 64, kind="canonical",
            body=body(self.root, self.first),
        )))
        with self.assertRaises(storage.JournalIntegrityError):
            self.reopen()

    def test_changed_metadata_or_initials_rejected(self):
        self.store.commit(body(self.root, self.first))
        self.store.close()
        with self.assertRaises(storage.JournalIntegrityError):
            storage.FactStore(self.path, {"s": self.root.state},
                              dict(self.metadata, origin_perf=999.0))
        with self.assertRaises(storage.JournalIntegrityError):
            storage.FactStore(self.path, {"s": self.first.state}, self.metadata)

    def test_exact_recovery_loads_only_recorded_facts_without_model_calls(self):
        receipt = self.store.commit(body(self.root, self.first))
        self.store.close()
        original_import = builtins.__import__
        def no_model(name, *args, **kwargs):
            if name.split(".")[0] in ("torch", "transformers", "peft"):
                raise AssertionError("recovery invoked a neural library")
            return original_import(name, *args, **kwargs)
        with patch.object(builtins, "__import__", side_effect=no_model):
            recovered = self.reopen()
        self.assertTrue(recovered.roots["s"].same(self.first))
        self.assertEqual(recovered.sequence, receipt["sequence"])
        self.assertEqual(recovered.processed["s"], 8000)

    def test_incomplete_final_payload_is_the_only_repairable_append(self):
        self.store.commit(body(self.root, self.first))
        size = self.path.stat().st_size
        raw = self.next_raw()
        self.append_raw(raw[:len(raw) // 2])
        with self.assertRaises(storage.JournalIntegrityError):
            self.reopen()
        recovered = self.reopen(repair_tail=True)
        self.assertEqual(self.path.stat().st_size, size)
        self.assertTrue(recovered.roots["s"].same(self.first))
        recovered.commit(body(self.first, self.second, 2))
        self.assertEqual(recovered.roots["s"].frontier, 16000)

    def test_partial_final_header_repairs_without_changing_valid_prefix(self):
        self.store.commit(body(self.root, self.first))
        prefix = self.path.read_bytes()
        self.append_raw(b"RV")
        recovered = self.reopen(repair_tail=True)
        self.assertEqual(self.path.read_bytes(), prefix)
        self.assertTrue(recovered.roots["s"].same(self.first))

    def test_complete_checksum_corruption_is_not_tail_repair(self):
        self.store.commit(body(self.root, self.first))
        raw = bytearray(self.path.read_bytes())
        raw[-1] ^= 1
        self.store.close()
        self.path.write_bytes(raw)
        for repair in (False, True):
            with self.subTest(repair=repair), self.assertRaises(storage.JournalIntegrityError):
                self.reopen(repair_tail=repair)
            self.assertEqual(self.path.read_bytes(), bytes(raw))

    def test_semantically_invalid_but_checksum_valid_frame_is_not_replayed(self):
        transition = body(self.root, self.first)
        transition["record"]["role"] = "identity_predictor"
        raw = self.next_raw(transition)
        self.append_raw(raw)
        with self.assertRaises(storage.JournalIntegrityError):
            self.reopen(repair_tail=True)
        self.assertTrue(self.path.read_bytes().endswith(raw))

    def test_private_publication_never_promoted_by_recovery(self):
        raw = self.next_raw(dict(state=self.first.state), kind="private_projection")
        self.append_raw(raw)
        with self.assertRaises(storage.JournalIntegrityError):
            self.reopen(repair_tail=True)

    def test_receipt_from_another_frame_cannot_authorize_publication(self):
        receipt = self.store.commit(body(self.root, self.first))
        with self.assertRaises(storage.JournalIntegrityError):
            storage.verify_frame(self.path, dict(receipt, record_sha256="f" * 64))
        with self.assertRaises(storage.JournalIntegrityError):
            storage.verify_frame(self.path, dict(receipt, sequence=123))

    def test_publication_aliases_and_transition_ID_cannot_disagree_with_frame(self):
        receipt = self.store.commit(body(self.root, self.first))
        for key, wrong in (("journal_seq", 123), ("record_sha", "f" * 64),
                           ("transition_id", "other transition")):
            with self.subTest(key=key), self.assertRaises(storage.JournalIntegrityError):
                storage.verify_frame(self.path, dict(receipt, **{key: wrong}))

    def test_retired_worker_complete_buffer_does_not_require_live_channel(self):
        # It was already accepted as a protected complete result before failure.
        transition = body(self.root, self.first)
        transition["job"]["worker_incarnation"] = 0
        receipt = self.store.commit(transition)
        self.assertEqual(storage.verify_frame(self.path, receipt)["body"]["job"]
                         ["worker_incarnation"], 0)


if __name__ == "__main__":
    unittest.main()
