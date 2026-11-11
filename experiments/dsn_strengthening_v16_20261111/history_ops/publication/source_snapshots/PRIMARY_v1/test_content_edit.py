"""Prepared controls; root must freeze and run them before formal analysis."""
import unittest
import itertools
from content_edit import alignment, Ledger, analyze_rows


class EditControls(unittest.TestCase):
    def test_insert_shift_does_not_retract_existing_suffix(self):
        x = Ledger(); x.observe("ab", 0, 0, "private"); x.observe("axb", 3, 1, "canonical")
        self.assertEqual(x.summary()["retracted_edit_occurrences"], 0)
        self.assertEqual(x.events[-1]["lcp_suffix_closed"], 1)
        self.assertEqual(x.summary()["I"], 3)

    def test_substitution_closes_actual_old_unit(self):
        x = Ledger(); x.observe("ab", 0, 0, "private"); x.observe("ac", 3, 1, "canonical")
        self.assertEqual(x.summary()["S"], 1)
        self.assertEqual(x.summary()["edit_retractions_age_ge_threshold"], 1)
        self.assertEqual(x.closed[0]["char"], "b")

    def test_unicode_code_points_not_utf8_or_utf16(self):
        x = alignment("😀中", "😀国")
        self.assertEqual(x["distance"], 1)
        self.assertEqual(x["operation_counts"]["M"], 1)

    def test_equivalent_alignment_is_reported(self):
        x = alignment("aa", "a", old_births=[0, 5], observed=6)
        self.assertEqual(x["optimal_alignment_count"], "2")
        self.assertEqual(x["all_optimal_bounds_conditional_on_current_identity_history"]
                         ["retracted_age_ge_threshold"], (0, 1))

    def test_initial_snapshot_is_included(self):
        x = Ledger(); x.observe("abc", 3, 4, "private")
        self.assertEqual(x.summary()["I"], 3)
        self.assertEqual(x.summary()["distance"], 3)

    def test_censor_at_last_actual_observation(self):
        x = Ledger(); x.observe("abc", 3, 4, "private"); x.observe("abc", 5, 5, "canonical")
        self.assertEqual(x.summary()["right_censored_survivors"], 3)
        self.assertEqual(x.summary()["right_censor_time_last_actual_source_observation"], 5)
        self.assertEqual(x.summary()["retracted_edit_occurrences"], 0)

    def test_source_clocks_separate(self):
        ll = analyze_rows([dict(source_id="a", text="a", observed=10),
                           dict(source_id="b", text="b", observed=1)])
        self.assertEqual(len(ll), 12)

    def test_time_reversal_fails(self):
        x = Ledger(); x.observe("a", 3, 0, "private")
        with self.assertRaises(ValueError): x.observe("a", 2, 1, "private")

    def test_exact_2s_boundary_inclusive(self):
        x = Ledger(); x.observe("a", 0, 0, "private"); x.observe("", 2, 1, "canonical")
        self.assertEqual(x.summary()["edit_retractions_age_ge_threshold"], 1)

    def test_whitespace_mode_separate(self):
        ll = analyze_rows([dict(source_id="a", text="中 文", observed=1)])
        self.assertEqual(ll["a", "raw", "primary"].summary()["I"], 3)
        self.assertEqual(ll["a", "whitespace_stripped", "primary"].summary()["I"], 2)

    def test_lcp_age_is_not_true_edit_age(self):
        ll = analyze_rows([dict(source_id="a", text="ab", observed=0),
                           dict(source_id="a", text="axb", observed=3)])
        self.assertEqual(ll["a", "raw", "LCP_suffix_identity"].summary()
                         ["lcp_retractions_age_ge_threshold"], 1)
        self.assertEqual(ll["a", "raw", "primary"].summary()
                         ["edit_retractions_age_ge_threshold"], 0)

    def test_exhaustive_short_strings_independent_distance(self):
        def independent(a, b):
            row = list(range(len(b) + 1))
            for i, x in enumerate(a, 1):
                nxt = [i]
                for j, y in enumerate(b, 1):
                    nxt.append(min(row[j] + 1, nxt[-1] + 1, row[j - 1] + (x != y)))
                row = nxt
            return row[-1]
        strings = ["".join(x) for n in range(5) for x in itertools.product("ab", repeat=n)]
        for a in strings:
            for b in strings:
                for priority in (("M", "S", "D", "I"), ("D", "I", "M", "S")):
                    result = alignment(a, b, priority)
                    self.assertEqual(result["distance"], independent(a, b), (a, b, priority))


if __name__ == "__main__": unittest.main()
