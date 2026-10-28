"""Small exclusions and clock-boundary controls; no model or runtime imports."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name('interaction_opportunities.py')
SPEC = importlib.util.spec_from_file_location('opportunity_recount', MODULE)
OP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OP)


def worker(jid, chunk, end, prompt, state, sid=0, received=1.):
    return dict(job=dict(job_id=jid, role='proposal', session_id=sid, source_id='source',
        contract_epoch=1, contract_digest='contract', branch_generation=0,
        chunk_id=chunk, end_window=end//100, audio_start_sample=0, audio_end_sample=end,
        prompt_tokens=prompt, enqueue_perf=received-.1), result=dict(
        token_ids=state+[999], state_tokens=state, text='ahead', received_perf=received,
        completed_perf=received, execution_context_audit=dict(executed_prompt_tokens=prompt)))


class OpportunityControls(unittest.TestCase):
    def test_actual_logical_feedback_boundary_not_old_canonical_audio_start(self):
        row = worker('p', 1, 200, [7], [8])
        self.assertEqual(OP.complete_chain('p', 100, [7], {'p':row}, {'p'}, 100)[0], True)

    def test_false_caller_flag_cannot_create_compatibility(self):
        row = worker('p', 1, 200, [6], [8])
        row['result']['compatible_provisional_retained'] = True
        self.assertEqual(OP.complete_chain('p', 100, [7], {'p':row}, {'p'}, 100)[0], False)

    def test_complete_multihop_chain_requires_actual_same_identity_ancestor(self):
        a = worker('a', 1, 200, [7], [8], received=1.)
        b = worker('b', 2, 300, [8], [9], received=2.)
        records = {'a':a, 'b':b}
        self.assertTrue(OP.complete_chain('b', 100, [7], records, set(records), 100)[0])
        a['job']['session_id'] = 1
        self.assertIsNone(OP.complete_chain('b', 100, [7], records, set(records), 100)[0])

    def test_missing_cancelled_partial_or_future_result_never_proves_chain(self):
        a = worker('a', 1, 200, [7], [8], received=3.)
        b = worker('b', 2, 300, [8], [9], received=2.)
        self.assertIsNone(OP.complete_chain('b', 100, [7], {'b':b}, {'a','b'}, 100)[0])
        self.assertIsNone(OP.complete_chain('b', 100, [7], {'a':a,'b':b}, {'a','b'}, 100)[0])
        del b['result']['token_ids']
        self.assertIsNone(OP.complete_chain('b', 100, [7], {'b':b}, {'b'}, 100)[0])

    def test_ambiguous_equal_token_ancestors_remain_unknown(self):
        records = {'a':worker('a', 1, 200, [7], [8]),
                   'alias':worker('alias', 1, 200, [7], [8]),
                   'b':worker('b', 2, 300, [8], [9], received=2.)}
        self.assertIsNone(OP.complete_chain('b', 100, [7], records, set(records), 100)[0])

    def test_published_before_install_observed_after_install_before_canonical(self):
        with tempfile.TemporaryDirectory(dir=MODULE.parent) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(MODULE.parent.resolve()))
            root = Path(temporary)/'attempt0'
            root.mkdir()
            private = worker('p', 1, 200, [7], [8])
            authority = worker('a', 0, 100, [], [7])
            authority['job']['role'] = 'authority'
            authority['result']['text'] = 'canonical'
            events = [dict(kind='run-start', t0_perf=0.),
                dict(private['job'], kind='enqueue'),
                dict(kind='view-mode', session_id=0, displayed=0.),
                dict(kind='display', session_id=0, job_id='p', displayed=1., text='ahead', audio_end_sample=200),
                dict(kind='commit', session_id=0, version=1, job_id='a', audio_start_sample=0,
                     audio_end_sample=100, installed=2., segment_tokens=[7,999], next_prompt_tokens=[7]),
                dict(kind='canonical-display', session_id=0, version=1, job_id='a', displayed=2.1)]
            consumers = [dict(session_id=0, source_kind='view-mode', server_time=0., observed_perf=.2,
                canonical_version=0, certified_frontier=0, valid_visible_frontier=0, visible_text=''),
                dict(session_id=0, source_kind='display', server_time=1., observed_perf=2.5,
                canonical_version=0, certified_frontier=0, valid_visible_frontier=200, visible_text='ahead'),
                dict(session_id=0, source_kind='canonical-display', server_time=2.1, observed_perf=3.,
                canonical_version=1, certified_frontier=100, certified_text='canonical',
                valid_visible_frontier=200, visible_text='ahead', compatible_provisional_retained=False)]
            payloads = {'config.json':dict(fine_seconds=1, sample_rate=100, rho=1, arrival='sync'),
                'sessions.json':[dict(session_id=0, source_id='source')], 'events.jsonl':events,
                'consumer.jsonl':consumers, 'worker_records.jsonl':[private, authority]}
            for name, value in payloads.items():
                (root/name).write_text('\n'.join(map(json.dumps,value)) if name.endswith('jsonl') else json.dumps(value))
            updates, sources = OP.recount(Path(temporary))
            by_clock = {row['clock_scope']:row for row in sources}
            self.assertEqual(by_clock['owner_install']['ahead_updates'], 0)
            self.assertEqual(by_clock['consumer_apply']['compatible_opportunities'], 1)
            self.assertEqual(by_clock['consumer_apply']['compatible_retained'], 1)
            self.assertEqual(len(updates), 2)
            # Removing the selected complete result must keep the Canonical
            # denominator, but can no longer prove a compatible opportunity.
            (root/'worker_records.jsonl').write_text(json.dumps(private)+'\n')
            _, sources = OP.recount(Path(temporary))
            applied = next(r for r in sources if r['clock_scope']=='consumer_apply')
            self.assertEqual(applied['canonical_updates'], 1)
            self.assertEqual(applied['compatible_opportunities'], 0)
            self.assertEqual(applied['unresolved_ahead_updates'], 1)
            self.assertIsNone(applied['canonical_history_sha256'])


if __name__ == '__main__':
    unittest.main()
