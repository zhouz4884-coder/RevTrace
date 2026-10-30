"""SYNTHETIC CPU CONTROLS ONLY: no native models, serving claims or paper data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from export_bounded import export, lines, put, read
from render_evidence import aggregate

RUNTIME = Path(__file__).resolve().parents[1] / 'source_v2'


def jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf8')


def wal(path, rows):
    previous = '0'*64
    with Path(path).open('wb') as stream:
        for sequence, (kind, body) in enumerate(rows, 1):
            obj = dict(sequence=sequence, previous=previous, kind=kind, body=body)
            payload = json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                 ensure_ascii=False, allow_nan=False).encode('utf8')
            digest = hashlib.sha256(payload).digest()
            stream.write(b'RVN1' + struct.pack('>I', len(payload)) + payload + digest)
            previous = digest.hex()


def fixture(root, *, missing=False, unpinned=64):
    root.mkdir()
    commit = 'a'*40
    config = dict(cell_id='SYNTHETIC_CPU_FIXTURE_NOT_SERVING', source_commit=commit,
                  settings=dict(sources=[dict(source_id='s', frames=16000)]))
    put(root/'CONFIG.json', config)
    put(root/'ORIGIN.json', dict(origin_perf=0., original_D=2., original_C=8.))
    put(root/'SERVICE_END.json', dict(service_end_perf=2.))
    cuts = [dict(frontier=8000, transcript='different-at-F'),
            dict(frontier=16000, transcript='actual-G-text')]
    wal(root/'facts.wal', [('genesis', {})] + [('canonical', dict(
        owner_epoch=0, source_id='s', job=dict(job_id=f'e0-j{i+1:09d}'),
        next_state=cut, record=dict(model_end=1., token_ids=[1], selection_changed=False)))
        for i, cut in enumerate(cuts)])
    jsonl(root/'owner_e0'/'worker_results.jsonl', [dict(event=dict(kind='asr_early',
        job_id=f'e0-j{i+1:09d}', projection=dict(end=cut))) for i, cut in enumerate(cuts)])
    counts = dict(audio_buffer_samples=16000, context_token_count=1,
        current_token_count=1, total_decoder_input_tokens=2, max_text_len=448,
        max_context_tokens=224, context_trim_triggered=False)
    jsonl(root/'owner_e0'/'policy_audit.jsonl', [dict(kind='native_state',
        boundary='context_trim', physical_slot='full0', physical_incarnation=0,
        job_id='e0-j000000001', source_id='s', start_frontier=0, end_frontier=8000,
        observed_perf=1., before=counts, after=counts, context_changed=False)])
    jsonl(root/'owner_e0'/'state_sizes.jsonl', [dict(observed=1., owner_epoch=0,
        history=dict(inbox=dict(active=1, terminal=unpinned+3, pinned_terminals=3,
                               terminal_limit=64, issued_highwater=1000),
                     audit_retained=dict(promotions=64), history_limit=64,
                     audit_total=dict(promotions=1000)),
        consumer_pins=3, pending_publications=1, current_cut_bytes=10,
        current_text_bytes=3, immutable_audio_bytes=64000, owner_RSS_bytes=None)])
    if missing:
        consumer = [dict(source_id='s', observed=1., visible_frontier=0,
                         certified_frontier=0, text='')]
    else:
        consumer = [dict(source_id='s', observed=1., visible_frontier=16000,
                         certified_frontier=8000, text='actual-G-text'),
                    dict(source_id='s', observed=1.2, visible_frontier=16000,
                         certified_frontier=16000, text='actual-G-text')]
    jsonl(root/'consumer.jsonl', consumer)
    support = dict(original_credit_supported_seconds=0. if missing else 1.,
                   original_credit_mismatching_seconds=0., original_credit_unknown_seconds=0.,
                   all_offered_frontier_counts={'unknown' if missing else 'supported': 2})
    put(root/'METRICS_SUMMARY.json', dict(analysis_phase='offline_after_trial',
        source_commit=commit, primary=dict(dual_deadline_audio_credit_seconds=0. if missing else 1.,
            offered_frontiers=2, missing_D_frontiers=2 if missing else 0,
            missing_C_frontiers=2 if missing else 0),
        posterior_whole_text_support=dict(raw=support, whitespace_stripped=support)))


class EvidenceControls(unittest.TestCase):
    def test_actual_G_not_offered_F_and_complete_series(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d)/'raw', Path(d)/'out'
            fixture(raw)
            result = export(raw, RUNTIME, out)
            rows = list(lines(out/'frontiers.jsonl'))
            self.assertEqual(rows[0]['frontier'], 8000)
            self.assertEqual(rows[0]['first_visible_actual_G'], 16000)
            self.assertEqual(rows[0]['actual_G_whole_text_posterior_support']['raw'], 'supported')
            self.assertEqual(result['counts']['frontiers'], 2)
            self.assertEqual(result['counts']['canonical_edges'], 2)
            self.assertTrue(result['all_observed_rows_retained'])

    def test_missing_endpoint_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d)/'raw', Path(d)/'out'
            fixture(raw, missing=True)
            export(raw, RUNTIME, out)
            rows = list(lines(out/'frontiers.jsonl'))
            self.assertTrue(all(r['D'] is None and r['C'] is None for r in rows))
            self.assertTrue(all(r['actual_G_whole_text_posterior_support']['raw'] == 'unknown' for r in rows))

    def test_total_terminal_may_exceed_64_but_unpinned_may_not(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d)/'raw', Path(d)/'out'
            fixture(raw, unpinned=64)
            export(raw, RUNTIME, out)
            row = next(lines(out/'history.jsonl'))
            self.assertEqual(row['history']['inbox']['terminal'], 67)
            self.assertEqual(row['derived_unpinned_terminals'], 64)
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d)/'raw', Path(d)/'out'
            fixture(raw, unpinned=65)
            with self.assertRaisesRegex(ValueError, 'unpinned terminal bound'):
                export(raw, RUNTIME, out)

    def test_aggregate_cannot_infer_illegal_zero_or_zero_recovery(self):
        rows = []
        from render_evidence import CONDITIONS, ARMS
        for condition in CONDITIONS:
            for arm in ARMS:
                for repeat in (0, 1):
                    applicable = condition not in ('none', 'duplicate_late')
                    rows.append(dict(cohort='short_main', condition=condition, arm=arm,
                        illegal_installs=None, complete_original_task=True,
                        local_reject_records=0, local_reject_canonical_mutations=0,
                        recovery_clock_applicable=applicable,
                        new_model_completed_after_fault_and_certified_consume_seconds=None,
                        old_durable_replay_seconds=None, original_D2_C8_pass=False,
                        EOS_D2_misses=1, energy_joules=1.))
        groups = aggregate(rows)
        self.assertTrue(all(g['illegal_installs'] is None for g in groups))
        self.assertTrue(all(g['new_certified_result_seconds'] == 'NA'
                            for g in groups if g['condition'] in ('none', 'duplicate_late')))
        self.assertTrue(all(g['new_certified_result_seconds'] is None
                            for g in groups if g['condition'] not in ('none', 'duplicate_late')))


if __name__ == '__main__':
    unittest.main()
