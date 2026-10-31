"""Counterexamples for the pure adapter contract; execute only after freeze."""
import copy
import unittest

from pairing import (dispatch_timebins, exactly_aligned_reference,
                     pair_dispatches, rolling_confirmation_marker)


def state(frontier=8000):
    return dict(audio_segments=[], tokens=[[1]], context={"text": "same"},
                last_attend_frame=0, detected_language="zh", initial_tokens=[1],
                initial_token_length=1, sot_index=0, decoder_type="original",
                contract={"source_sha": "a"*64}, frontier=frontier, transcript="same")


def dispatch(jid="e0-j1", start=None, **updates):
    row = dict(cell_id="case", logical_session_id="request", source_id="source",
               owner_epoch=0, job_id=jid, start=state() if start is None else start,
               started_on_canonical=False, dispatched_perf=1.)
    row.update(updates)
    return row


def witness(cut=None, **updates):
    row = dict(cell_id="case", logical_session_id="request", source_id="source",
               state=state() if cut is None else cut, provenance="wal:seq2",
               observed_perf=2.)
    row.update(updates)
    return row


class PairingCounterexamples(unittest.TestCase):
    def test_own_wrong_end_does_not_refute_actual_successor_input(self):
        row = dispatch(own_prediction_changed=True)
        paired, _ = pair_dispatches([row], [witness()])
        self.assertEqual(paired[0]["input_status"], "CONFIRMED")

    def test_same_text_wrong_hidden_context_is_refuted(self):
        cut = state()
        cut["context"]["text"] = "different hidden context"
        paired, _ = pair_dispatches([dispatch(own_prediction_changed=False)], [witness(cut)])
        self.assertEqual(paired[0]["input_status"], "REFUTED")
        self.assertEqual(paired[0]["different_top_level_fields"], ["context"])

    def test_ancestor_mismatch_future_convergence_is_confirmed(self):
        row = dispatch(ancestor_support_loss=True)
        paired, _ = pair_dispatches([row], [witness(state(0)), witness()])
        self.assertEqual(paired[0]["input_status"], "CONFIRMED")

    def test_only_earlier_ancestor_witness_is_unresolved(self):
        paired, _ = pair_dispatches([dispatch()], [witness(state(0))])
        self.assertEqual(paired[0]["input_status"], "UNRESOLVED")

    def test_dead_job_can_be_semantically_confirmed_without_install(self):
        row = dispatch(physical_terminal="kill", install_eligible=False, actual_install=False)
        paired, _ = pair_dispatches([row], [witness()])
        self.assertEqual(paired[0]["input_status"], "CONFIRMED")
        self.assertFalse(paired[0]["install_eligible"])
        self.assertFalse(paired[0]["actual_install"])

    def test_completion_and_promotion_fields_do_not_change_denominator(self):
        row = dispatch(completion_receipts=2, promotion_audit=False, actual_install=True)
        _, summary = pair_dispatches([row, copy.deepcopy(row)], [witness()])
        self.assertEqual(summary["unique_actual_dispatches"], 1)
        self.assertEqual(summary["duplicate_identical_dispatch_rows"], 1)

    def test_owner_and_request_identities_do_not_merge(self):
        rows = [dispatch(), dispatch(owner_epoch=1)]
        paired, summary = pair_dispatches(rows, [witness(logical_session_id="different-request")])
        self.assertEqual(summary["unique_actual_dispatches"], 2)
        self.assertTrue(all(r["input_status"] == "UNRESOLVED" for r in paired))

    def test_conflicting_selected_cut_at_same_frontier_fails(self):
        other = state()
        other["tokens"] = [[2]]
        with self.assertRaisesRegex(ValueError, "contradictory selected"):
            pair_dispatches([dispatch()], [witness(), witness(other)])

    def test_bytes_preserve_numeric_representation_in_different_field_list(self):
        other = state()
        other["last_attend_frame"] = 0.0
        paired, _ = pair_dispatches([dispatch()], [witness(other)])
        self.assertEqual(paired[0]["input_status"], "REFUTED")
        self.assertEqual(paired[0]["different_top_level_fields"], ["last_attend_frame"])

    def test_no_dispatch_bin_is_retained_with_null_rate(self):
        rows, _ = pair_dispatches([dispatch()], [witness()])
        bins = dispatch_timebins(rows, origin_perf=0., duration_seconds=30.)
        self.assertEqual(len(bins), 3)
        self.assertEqual(bins[1]["N"], 0)
        self.assertIsNone(bins[1]["resolved_confirmation_rate"])

    def test_exact_final_bin_endpoint_does_not_create_zero_width_interval(self):
        rows, _ = pair_dispatches([dispatch(dispatched_perf=30.)], [witness()])
        bins = dispatch_timebins(rows, origin_perf=0., duration_seconds=30.)
        self.assertEqual(len(bins), 3)
        self.assertEqual(bins[-1]["N"], 1)

    def test_unknown_is_not_failure_and_stays_in_window(self):
        rows = [dispatch(jid=f"e0-j{i}", dispatched_perf=float(i),
                         input_status="UNRESOLVED", start_frontier=8000) for i in range(20)]
        marker = rolling_confirmation_marker(rows)
        self.assertIsNone(marker["first_low_window"])

    def test_part_reference_never_rounds_to_call_grid(self):
        parts = [dict(start_sample=0, end_sample=9000, reference="first utterance"),
                 dict(start_sample=9000, end_sample=17000, reference="second")]
        self.assertIsNone(exactly_aligned_reference(parts, 16000))
        self.assertEqual(exactly_aligned_reference(parts, 9000), "first utterance")
        self.assertEqual(exactly_aligned_reference(parts, 17000), "first utterance second")


if __name__ == "__main__":
    unittest.main()
