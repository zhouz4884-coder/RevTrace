"""Synthetic CPU semantic controls; no model execution or serving evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import history_analysis as h
from reference_view import EnvelopeView, digest_tokens, text_sha


CONTRACT = 'c' * 64


def fixture(directory, *, tail=64000, retirement=None, deep=False,
            ambiguity_received=None, same_last_time=False):
    """A previously visible B survives loss of a newer incompatible C.

    All results are explicitly SCRIPTED CPU records. Original timestamps are
    declared fixture inputs, never measured neural latency or replay time.
    """
    owner, epoch = 100.0, 7
    events = [dict(kind='run-start', t0_perf=owner, time=0, contract_digest=CONTRACT)]
    workers = []
    revision = 0

    def private(jid, when, start, end_window, end, prompt, state, text, published=True):
        nonlocal revision
        job = dict(job_id=jid, source_id='scripted-source', session_id=0, role='proposal',
                   chunk_id=start, end_window=end_window, audio_end_sample=end,
                   prompt_tokens=prompt, branch_generation=0, contract_epoch=epoch,
                   contract_digest=CONTRACT)
        result = dict(received_perf=owner + when - .02, state_tokens=state,
                      token_ids=state, text=text)
        workers.append(dict(job=job, result=result))
        if published:
            revision += 1
            events.append(dict(kind='display', time=when, displayed=when,
                session_id=0, job_id=jid, chunk_id=start, end_window=end_window,
                audio_end_sample=end, canonical_version=0, branch_generation=0,
                contract_epoch=epoch, contract_digest=CONTRACT, display_revision=revision,
                input_projection_sha256=digest_tokens(prompt),
                output_projection_sha256=digest_tokens(state), text=text, text_sha256=text_sha(text)))

    private('A', 2.1, 0, 1, 32000, [], [101], 'a')
    private('B', 4.1, 1, 2, tail, [101], [102], 'ab')
    if deep:
        private('D', 6.05, 2, 3, 96000, [102], [103], 'abc')
        private('C', 6.1, 2, 3, 96000, [999], [999], 'bad')
    else:
        private('C', 6.1, 1, 2, tail, [999], [999], 'bad')

    def canonical(version, frontier, tokens, text, when):
        nonlocal revision
        revision += 1
        txn = 'canonical-' + str(version)
        cert = dict(contract_digest=CONTRACT, display_sha256=digest_tokens(tokens))
        events.append(dict(kind='commit', time=when - .01, session_id=0, version=version,
                           segment_id=txn, audio_end_sample=frontier, next_prompt_tokens=tokens,
                           certificate=cert))
        events.append(dict(kind='canonical-display', time=when, displayed=when, session_id=0,
            version=version, audio_end_sample=frontier, text=text, transaction_id=txn,
            canonical_projection_sha256=digest_tokens(tokens), canonical_Z_sha256=digest_tokens(tokens),
            text_sha256=text_sha(text), contract_epoch=epoch, contract_digest=CONTRACT,
            display_revision=revision))

    canonical(1, 32000, [101], 'a', 6.3)
    if retirement is not None:
        events.append(dict(kind='private-generation-retired', time=retirement - owner,
                           session_id=0, generation=1))
    canonical(2, tail if not deep else 96000, [102] if not deep else [103],
              'ab' if not deep else 'abc', 6.3 if same_last_time else 8.3)
    events.sort(key=lambda event: event.get('time', 0))
    if ambiguity_received is not None:
        private('B-unpublished-equal-state', ambiguity_received - owner + .02,
                1, 2, 64000, [101], [102], 'ab', published=False)
    native = EnvelopeView(policy='two_lane', strict_bound=True, fine_samples=32000)
    consumer = []
    for event in events:
        observed = owner + event.get('time', 0) + .1
        row = native.consume(event, observed)
        if row is not None:
            row = dict(row, consumer_received_perf=observed - .05)
            consumer.append(row)
    cfg = dict(sample_rate=16000, fine_seconds=2, episode_origin_perf=owner,
               authority_runtime=dict(code_commit='SCRIPTED_CPU_FIXTURE'))
    duration = (96000 if deep else tail) / 16000
    data = {'events.jsonl': events, 'consumer.jsonl': consumer, 'worker_records.jsonl': workers,
            'sessions.json': [dict(session_id=0, source_id='scripted-source', offset=0, duration=duration)],
            'config.json': cfg}
    paths = {}
    for name, value in data.items():
        path = directory / name
        if name.endswith('.jsonl'):
            path.write_text(''.join(json.dumps(row)+'\n' for row in value))
        else:
            path.write_text(json.dumps(value))
        paths[name] = path
    entry = dict(attempt='SCRIPTED_CPU_FIXTURE', bank='synthetic', stage='control', controlled=True)
    return entry, paths


class SemanticControls(unittest.TestCase):
    def analyze(self, **options):
        with tempfile.TemporaryDirectory() as root:
            entry, paths = fixture(Path(root), **options)
            return h.analyze_attempt(entry, paths, {})

    def test_original_clock_area_not_candidate_age_or_cpu_replay(self):
        summary, gaps, cuts = self.analyze()
        self.assertAlmostEqual(summary['metrics']['joint_gap_area_within_session_observation'], 4.0)
        self.assertAlmostEqual(summary['metrics']['joint_gap_wall_within_session_observation'], 2.0)
        self.assertEqual(gaps[0]['selected_job'], 'B')
        self.assertEqual(gaps[0]['category'], 'restore_originally_visible_same_node')
        self.assertAlmostEqual(gaps[0]['start_perf'], 106.4)
        self.assertAlmostEqual(gaps[0]['end_perf'], 108.4)

    def test_genesis_query_never_mutates_original_reference_projection(self):
        observed_uncommitted = []
        outer = self
        class InspectingView(EnvelopeView):
            def consume(self, event, observed=None):
                prior = self.states.get(event.get('session_id'))
                if event['kind'] == 'display' and prior and prior['version'] == 0:
                    observed_uncommitted.append(prior.get('Psha'))
                    outer.assertIsNone(prior.get('Psha'), 'query polluted the original baseline state')
                return super().consume(event, observed)
        with patch.object(h, 'EnvelopeView', InspectingView):
            self.analyze()
        self.assertGreaterEqual(len(observed_uncommitted), 2)

    def test_original_certified_identity_mismatch_still_fails(self):
        with tempfile.TemporaryDirectory() as root:
            entry, paths = fixture(Path(root))
            rows, _ = h.read_rows(paths['consumer.jsonl'])
            rows[0]['certified_P_sha256'] = 'a' * 64
            paths['consumer.jsonl'].write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaisesRegex(h.AuditFailure, 'identity/mode mismatch certified_P_sha256'):
                h.analyze_attempt(entry, paths, {})

    def test_final_zero_duration_Canonical_application_counts_for_deadline(self):
        summary, _, _ = self.analyze()
        self.assertEqual(summary['first_deadline_analysis']['actual_joint_D2_C8_audio_seconds'], 4.0)
        self.assertEqual(summary['counts']['zero_following_observation_duration_applications'], 1)

    def test_partial_EOS_uses_actual_tail_not_only_full_fine_grid(self):
        summary, _, _ = self.analyze(tail=56000)
        deadline = summary['first_deadline_analysis']
        self.assertEqual(deadline['partial_EOS_intervals'], 1)
        self.assertEqual(deadline['offered_audio_seconds'], 3.5)
        self.assertEqual(deadline['actual_joint_D2_C8_audio_seconds'], 3.5)

    def test_same_timestamp_applications_are_not_missing_first_times(self):
        summary, _, _ = self.analyze(same_last_time=True)
        self.assertEqual(summary['first_deadline_analysis']['actual_joint_D2_C8_audio_seconds'], 4.0)
        self.assertEqual(summary['metrics'].get('joint_gap_area_within_session_observation', 0), 0)

    def test_owner_generation_retirement_cuts_gap_before_queued_withdrawal(self):
        summary, gaps, _ = self.analyze(retirement=107.4)
        self.assertAlmostEqual(summary['metrics']['joint_gap_area_within_session_observation'], 2.0)
        self.assertAlmostEqual(gaps[0]['end_perf'], 107.4)

    def test_receive_to_apply_new_complete_parent_ambiguity_is_not_ignored(self):
        # Canonical application receives at106.35, applies106.4; the unpublished
        # duplicate arrives106.38 and must refute D's unique core-parent path.
        _, without, _ = self.analyze(deep=True)
        _, with_ambiguity, _ = self.analyze(deep=True, ambiguity_received=106.38)
        self.assertEqual(without[0]['selected_job'], 'D')
        self.assertEqual(with_ambiguity[0]['selected_job'], 'B')

    def test_unpublished_result_never_enters_registered_tip_universe(self):
        summary, gaps, _ = self.analyze(deep=True, ambiguity_received=109.0)
        self.assertEqual(gaps[0]['selected_job'], 'D')
        self.assertNotIn('B-unpublished-equal-state', {row['selected_job'] for row in gaps})

    def test_future_host_result_cannot_validate_earlier_publication(self):
        with tempfile.TemporaryDirectory() as root:
            entry, paths = fixture(Path(root))
            workers, _ = h.read_rows(paths['worker_records.jsonl'])
            workers[1]['result']['received_perf'] = 500.0
            paths['worker_records.jsonl'].write_text(''.join(json.dumps(row)+'\n' for row in workers))
            with self.assertRaisesRegex(h.AuditFailure, 'before host receipt'):
                h.analyze_attempt(entry, paths, {})

    def test_full_output_binding_tamper_is_a_failed_gate(self):
        with tempfile.TemporaryDirectory() as root:
            entry, paths = fixture(Path(root))
            workers, _ = h.read_rows(paths['worker_records.jsonl'])
            workers[1]['result']['text'] = 'tampered'
            paths['worker_records.jsonl'].write_text(''.join(json.dumps(row)+'\n' for row in workers))
            with self.assertRaisesRegex(h.AuditFailure, 'immutable result binding'):
                h.analyze_attempt(entry, paths, {})

    def test_missing_original_consumer_clock_fails_not_replay_time_substitution(self):
        with tempfile.TemporaryDirectory() as root:
            entry, paths = fixture(Path(root))
            rows, _ = h.read_rows(paths['consumer.jsonl'])
            rows[0].pop('consumer_received_perf')
            paths['consumer.jsonl'].write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaisesRegex(h.AuditFailure, 'original application/receive'):
                h.analyze_attempt(entry, paths, {})

    def test_equal_frontier_different_text_ties_are_exposed(self):
        state = dict(F=0, Psha=digest_tokens(()), epoch=7, nodes={})
        for number, text in [(1, 'one'), (2, 'two')]:
            state['nodes'][str(number)] = dict(job_id=str(number), chunk_id=0, end_window=1,
                input_projection_sha256=digest_tokens(()), output_projection_sha256='p',
                audio_end_sample=32000, display_revision=number, branch_generation=0,
                contract_epoch=7, contract_digest=CONTRACT, text=text)
        jobs = {key: dict(id=key, sid=0, role='proposal', rootF=0, inputP=digest_tokens(()), end=32000,
                         result=dict(P='p', textsha=text_sha(node['text'])))
                for key, node in state['nodes'].items()}
        _, selected, detail = h.select_views(state, CONTRACT, 'NORMAL', 0, set(), 0, 32000, jobs)
        self.assertEqual(selected['job_id'], '2')
        self.assertEqual(detail['best_frontier_distinct_texts'], 2)

    def test_mode_and_epoch_are_permission_fences(self):
        tip = dict(job_id='x', audio_end_sample=64000, display_revision=3,
                   branch_generation=0, contract_epoch=7, contract_digest=CONTRACT)
        state = dict(F=32000, epoch=7)
        self.assertFalse(h.allowed_tip(tip, state, CONTRACT, 'RECOVERY', 0, set(), 0))
        self.assertFalse(h.allowed_tip(tip, dict(state, epoch=8), CONTRACT, 'NORMAL', 0, set(), 0))
        self.assertFalse(h.allowed_tip(tip, state, CONTRACT, 'NORMAL', 0, {'x'}, 0))
        self.assertFalse(h.allowed_tip(tip, state, CONTRACT, 'NORMAL', 0, set(), 1))

    def test_distinct_audio_union_does_not_double_count_repeated_cut(self):
        self.assertEqual(h.interval_union_length([(10, 30), (20, 40), (10, 30)]), 30)

    def test_incomplete_tail_and_corrupt_complete_frame_are_separate(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'rows.jsonl'
            path.write_bytes(b'{"ok":1}\n{"partial"')
            rows, tail = h.read_rows(path)
            self.assertEqual(rows, [{'ok':1}])
            self.assertGreater(tail, 0)
            path.write_bytes(b'{"ok":1}\n{"partial"\n')
            with self.assertRaises(h.AuditFailure):
                h.read_rows(path)

    def test_actual_original_raw_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'config.json'
            path.write_bytes(b'{}')
            entry = dict(trace_identity=[dict(path=str(path), bytes=2, sha256='0'*64)])
            with self.assertRaisesRegex(h.AuditFailure, 'SHA mismatch'):
                h.verify_inputs(entry, {'config.json':path})


if __name__ == '__main__':
    unittest.main(verbosity=2)
