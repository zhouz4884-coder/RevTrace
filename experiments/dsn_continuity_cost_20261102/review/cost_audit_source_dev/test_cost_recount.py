"""Prepared independent controls. No model, driver or raw campaign execution."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from cost_forest import AuditError, forest, window_accounts
import cost_recount as c


def span(ident=1, parent=None, begin=0, end=100, cpu=120, pid=1, thread=1,
         role='owner', exclusive_wall=None, exclusive_cpu=None):
    return dict(span_id=ident, parent_span_id=parent, role=role, pid=pid, thread_id=thread,
                label='IDENTITY.test', start_ns=begin, end_ns=end, wall_ns=end-begin,
                thread_cpu_ns=cpu, process_cpu_ns=cpu,
                exclusive_wall_ns=end-begin if exclusive_wall is None else exclusive_wall,
                exclusive_thread_cpu_ns=cpu if exclusive_cpu is None else exclusive_cpu,
                exception=False)


class Controls(unittest.TestCase):
    def test_asymmetric_timer_bracket_cpu_above_wall_is_preserved(self):
        result = forest([span()])[0]
        self.assertTrue(result['timer_bracket_CPU_exceeds_wall'])
        self.assertEqual(result['wall_minus_thread_cpu_ns_signed'], -20)

    def test_nested_exclusive_is_independently_recomputed(self):
        result = forest([span(exclusive_wall=60, exclusive_cpu=70),
                         span(2, 1, 10, 50, 50)])
        self.assertEqual(result[0]['independent_exclusive_thread_cpu_ns'], 70)

    def test_reused_span_number_in_different_process_is_not_merged(self):
        self.assertEqual(len(forest([span(pid=1), span(pid=2)])), 2)

    def test_missing_parent_is_rejected(self):
        with self.assertRaisesRegex(AuditError, 'missing parent'):
            forest([span(2, 1)])

    def test_parent_cannot_cross_threads(self):
        with self.assertRaisesRegex(AuditError, 'cross-thread parent'):
            forest([span(), span(2, 1, 10, 50, 50, thread=2)])

    def test_overlapping_siblings_are_rejected(self):
        with self.assertRaisesRegex(AuditError, 'overlapping same-thread sibling'):
            forest([span(end=200, cpu=300, exclusive_wall=60, exclusive_cpu=160),
                    span(2, 1, 10, 90, 80), span(3, 1, 80, 140, 60)])

    def test_clamped_negative_child_accounting_is_not_hidden(self):
        with self.assertRaisesRegex(AuditError, 'negative exclusive'):
            forest([span(cpu=30, exclusive_wall=60, exclusive_cpu=0), span(2, 1, 10, 50, 40)])

    def test_declared_exclusive_cannot_be_substituted(self):
        with self.assertRaisesRegex(AuditError, 'reported exclusive'):
            forest([span(exclusive_wall=99)])

    def test_partial_parent_is_not_cpu_prorated(self):
        rows = forest([span(exclusive_wall=70, exclusive_cpu=80), span(2, 1, 30, 60, 40)])
        result = window_accounts(rows, {'slice': (20e-9, 80e-9)})['slice']
        self.assertEqual(result['fully_contained'], 1)
        self.assertEqual(result['boundary_not_prorated'], 1)
        self.assertEqual(result['thread_root_accounts'][0]['root_thread_cpu_ns'], 40)

    def test_parallel_roles_remain_separate_accounts(self):
        rows = forest([span(role='owner'), span(role='supervisor_consumer', pid=2)])
        result = window_accounts(rows, {'all': None})['all']
        self.assertEqual(len(result['thread_root_accounts']), 2)
        self.assertTrue(result['cross_role_or_parallel_wall_total_NOT_COMPUTED'])

    def test_binary_fact_checksum_and_sequence_are_independent(self):
        obj = dict(sequence=1, previous='0'*64, kind='genesis', body=dict(initials={}))
        payload = c.canonical(obj)
        frame = b'RVN1'+struct.pack('>I', len(payload))+payload+hashlib.sha256(payload).digest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'facts.wal'; path.write_bytes(frame)
            self.assertEqual(len(c.facts(path)), 1)
            path.write_bytes(frame[:-1]+bytes([frame[-1] ^ 1]))
            with self.assertRaisesRegex(AuditError, 'corrupt fact payload'):
                c.facts(path)

    def test_final_partial_eos_is_in_all_offered_denominator(self):
        sources = [dict(source_id='s', frames=16001)]
        rows = [dict(source_id='s', observed=101., visible_frontier=8000, certified_frontier=8000),
                dict(source_id='s', observed=102., visible_frontier=16001, certified_frontier=16001)]
        result = c.endpoint_recount(rows, sources, 100.)
        self.assertEqual(result['offered_frontiers'], 3)
        self.assertEqual(result['frontiers'][-1]['frontier'], 16001)
        self.assertAlmostEqual(result['offered_audio_seconds'], 16001/16000)
        self.assertTrue(result['complete_coverage_and_original_quantile_pass'])

    def test_missing_tail_is_not_omitted_for_p99(self):
        result = c.endpoint_recount([dict(source_id='s', observed=101., visible_frontier=8000,
                                         certified_frontier=8000)], [dict(source_id='s', frames=16001)], 100.)
        self.assertIsNone(result['primary_linear_all_offered_C99'])
        self.assertFalse(result['complete_coverage_and_original_quantile_pass'])

    def test_two_board_energy_uses_actual_boundaries(self):
        power = [dict(time=0., boards={'0': dict(watts=0.), '1': dict(watts=50.)}),
                 dict(time=10., boards={'0': dict(watts=100.), '1': dict(watts=50.)})]
        self.assertEqual(c.energy_recount(power, 2., 8.)['total_joules'], 600.)
        with self.assertRaisesRegex(AuditError, 'misses original endpoint'):
            c.energy_recount(power, -1., 8.)

    def test_physical_release_requires_no_live_actual_worker(self):
        observation = dict(observation_end_perf=10., compute_processes=[],
                           worker_process_states={'1': 'absent', '2': 'Z'})
        c.physical_drain_proof([observation], dict(confirmed_perf=10., worker_pids=[1, 2]))
        observation['worker_process_states']['2'] = 'S'
        with self.assertRaisesRegex(AuditError, 'live/CUDA owner'):
            c.physical_drain_proof([observation], dict(confirmed_perf=10., worker_pids=[1, 2]))

    def test_incomplete_off_on_pairs_cannot_produce_positive_effect(self):
        with self.assertRaisesRegex(AuditError, 'incomplete frozen eight'):
            c.pair_effects([])

    def test_duplicate_off_on_mode_is_rejected(self):
        cell = dict(source_id='s', arm='fullcall', repeat=0, observation=True)
        with self.assertRaisesRegex(AuditError, 'duplicate off/on'):
            c.pair_effects([cell, dict(cell)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
