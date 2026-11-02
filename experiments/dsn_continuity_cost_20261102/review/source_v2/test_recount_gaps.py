"""Independent interval/classification controls; no raw/model execution.

Prepared only. Root freezes/runs these; the author has not executed them.
"""
import unittest
import recount_gaps as r


def atom(a=1.0, b=2.0, job='old', actual=32000, selected=64000, **extra):
    return dict(session_id=0, start_perf=a, end_perf=b, selected_job=job,
                actual_frontier=actual, selected_frontier=selected,
                canonical_version=1, category='restore_originally_visible_same_node',
                duration_seconds=b-a,
                area_audio_seconds_x_wall_seconds=(selected-actual)/16000*(b-a),
                global_prefix_extension_after_session_last_apply=False,
                right_censored=False, **extra)


class IndependentControls(unittest.TestCase):
    def test_union_does_not_duplicate_time_or_audio(self):
        self.assertEqual(r.union_length([(1, 4), (2, 3), (4, 7)]), 6)

    def test_original_zero_duration_has_zero_area(self):
        self.assertEqual(r.totals([atom(3, 3)], 16000)['joint_gap_session_wall_seconds'], 0)

    def test_independent_partitions_compare_same_complete_support(self):
        r.same_coverage([atom(1, 2), atom(2, 3)], [atom(1, 3)])

    def test_same_total_area_with_shifted_endpoint_is_rejected(self):
        with self.assertRaisesRegex(r.AuditError, 'positive time support differs'):
            r.same_coverage([atom(1, 2)], [atom(1.2, 2.2)])

    def test_changed_original_uid_is_rejected(self):
        with self.assertRaisesRegex(r.AuditError, 'selected_job'):
            r.same_coverage([atom()], [atom(job='new-identity')])

    def test_time_overlap_is_rejected(self):
        with self.assertRaisesRegex(r.AuditError, 'overlapping positive intervals'):
            r.same_coverage([atom(1, 2), atom(1.5, 2.5)], [atom(1, 2.5)])

    def test_newly_legal_is_not_falsely_called_restored_node(self):
        self.assertEqual(r.classification('old', {'old'}, 64000, 64000),
                         'restore_originally_visible_same_node')
        self.assertEqual(r.classification('other', {'old'}, 64000, 64000),
                         'new_legal_node_for_previously_visible_audio')
        self.assertEqual(r.classification('other', {'old'}, 32000, 64000),
                         'registered_old_publication_newly_visible_audio')

    def test_right_censored_tail_is_not_silently_uncensored(self):
        a = atom()
        a['right_censored'] = True
        with self.assertRaisesRegex(r.AuditError, 'right-censoring differs'):
            r.same_coverage([a], [atom()])

    def test_global_extension_and_within_source_are_separate(self):
        first, tail = atom(1, 2), atom(2, 4)
        tail['global_prefix_extension_after_session_last_apply'] = True
        values = r.totals([first, tail], 16000)
        self.assertEqual(values['joint_gap_area_within_session_observation'], 2)
        self.assertEqual(values['joint_gap_area_global_prefix_extension'], 4)
        self.assertEqual(values['joint_gap_area_audio_seconds_x_wall_seconds'], 6)

    def test_missing_ahead_repair_is_separate_from_optional_legal_ahead_upgrade(self):
        missing, upgrade = atom(), atom(actual=48000)
        missing['canonical_frontier'] = upgrade['canonical_frontier'] = 32000
        result = r.strategy_scope_totals([missing, upgrade])
        self.assertEqual(result['recover_ahead_from_certified_snapshot']['duration_seconds'], 1)
        self.assertEqual(result['recover_ahead_from_certified_snapshot']['area_audio_seconds_x_wall_seconds'], 2)
        self.assertEqual(result['upgrade_over_existing_legal_ahead_view']['duration_seconds'], 1)
        self.assertEqual(result['upgrade_over_existing_legal_ahead_view']['area_audio_seconds_x_wall_seconds'], 1)

    def test_partial_eos_first_deadline_function_requires_final_snapshot(self):
        sessions = [dict(session_id=0, offset=0, duration=3.1)]
        points = [dict(session_id=0, time=103, actual=32000, certified=32000,
                       selected=32000, legal=True),
                  dict(session_id=0, time=104, actual=49600, certified=49600,
                       selected=49600, legal=True)]
        result = r.deadline_totals({}, sessions, 100, points, 16000, 32000)
        self.assertEqual(result['offered_intervals'], 2)
        self.assertEqual(result['partial_EOS_intervals'], 1)
        self.assertAlmostEqual(result['actual_joint_D2_C8_audio_seconds'], 3.1)
        without_final = r.deadline_totals({}, sessions, 100, points[:1], 16000, 32000)
        self.assertAlmostEqual(without_final['actual_joint_D2_C8_audio_seconds'], 2.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
