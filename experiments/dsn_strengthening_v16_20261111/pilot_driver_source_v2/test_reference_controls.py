"""Prepared CPU contract/orchestration controls. No model or raw GPU run."""
from __future__ import annotations
import copy, unittest
from ref_common import (ReferenceError, SELECTION_STATUS, SPLIT_NAMESPACE, SPLIT_DIRECTORY,
                        sources_from_receipt, expected_frontiers)
from reference_logic import generate_source, reference_chain


def source(sid='s', speaker='p', frames=128000):
    return dict(source_id=sid, speaker_id=speaker, frames=frames, duration=frames/16000,
        path='/owned/'+sid+'.wav', audio_sha256='1'*64, reference='text',
        original_split=SPLIT_NAMESPACE, split_directory=SPLIT_DIRECTORY,
        archive_member=dict(path=SPLIT_DIRECTORY+'/'+sid+'.wav'),
        header=dict(sample_rate=16000, channels=1, sample_width=2, frames=frames, PCM_sha256='2'*64))


def receipt(sources=None):
    return dict(status=SELECTION_STATUS, sources=sources or [source()], metadata_first=True,
                model_calls=0, no_concat=True, no_trim=True, no_resample=True)


def scripted_rows(frames=16001):
    old = dict(frontier=0, transcript='')
    rows = []
    for i, end in enumerate(expected_frontiers(frames)):
        new = dict(frontier=end, transcript=old['transcript']+str(i))
        rows.append(dict(source_id='s', end=end, original_full_start_cut=copy.deepcopy(old),
            original_full_cut=new, original_full_result=dict(token_ids=[i], selected_correction=dict(selected=i)),
            continuous_original_no_between_step_restore=True))
        old = new
    return rows


class Cut:
    def __init__(self, state): self.state = state


def fake_compare(reference, cut, record):
    checks = dict(end=cut.state == reference['original_full_cut'],
                  C=record['C'] == reference['original_full_result']['selected_correction'],
                  IDs=record['IDs'] == reference['original_full_result']['token_ids'])
    return dict(source_id='s', end=reference['end'], checks=checks, all_equal=all(checks.values()))


def rig(mismatch=False, restore_exception=False, continuous_exception=False):
    rows, calls, resets, emitted = scripted_rows(), [], [], []
    pending = {'value': None}
    def reset(): resets.append('genesis')
    def continuous(*, stop_at, phase):
        calls.append(('continuous_begin', phase, stop_at))
        for row in rows:
            if stop_at is not None and row['end'] > stop_at: break
            pending['value'] = dict(end=row['end'], original_full_start_cut=copy.deepcopy(row['original_full_start_cut']))
            if continuous_exception and row['end'] == 16000:
                raise RuntimeError('scripted original failure')
            yield copy.deepcopy(row)
    def restored(reference, *, phase, repeat):
        calls.append(('restore', phase, repeat, reference['end']))
        if restore_exception and phase == 'restored_original_input': raise RuntimeError('scripted restore failure')
        row = next(row for row in rows if row['end'] == reference['end'])
        record = dict(C=copy.deepcopy(row['original_full_result']['selected_correction']),
                      IDs=list(row['original_full_result']['token_ids']))
        if mismatch and phase == 'restored_original_input' and repeat == 0 and row['end'] == 8000:
            record['C'] = dict(selected='bad')
        return Cut(copy.deepcopy(row['original_full_cut'])), record
    result = generate_source(dict(source_id='s', frames=16001), reset=reset, continuous=continuous,
        restored=restored, compare=fake_compare, emit=lambda k, v: emitted.append((k, copy.deepcopy(v))),
        pending=lambda: pending['value'])
    return result, calls, resets, emitted


class Controls(unittest.TestCase):
    def test_original_cadence_keeps_exact_and_partial_EOS(self):
        self.assertEqual(expected_frontiers(16001), [8000, 16000, 16001])
        self.assertEqual(expected_frontiers(16000), [8000, 16000])

    def test_invalid_frames_cannot_create_reference(self):
        for value in (0, -1, 1.1, True, None):
            with self.assertRaises(ReferenceError): expected_frontiers(value)

    def test_source_count_is_actual_not_forced_to_twelve(self):
        self.assertEqual(len(sources_from_receipt(receipt())), 1)

    def test_missing_model_call_proof_is_not_zero(self):
        r = receipt(); r.pop('model_calls')
        with self.assertRaisesRegex(ReferenceError, 'precede every model call'): sources_from_receipt(r)

    def test_duplicate_speaker_rejected_even_with_new_clip(self):
        with self.assertRaisesRegex(ReferenceError, 'duplicate source or speaker'):
            sources_from_receipt(receipt([source('a'), source('b')]))

    def test_duration_scope_and_whole_utterance_are_preserved(self):
        r = receipt([source(frames=320001)])
        with self.assertRaisesRegex(ReferenceError, '6--20s'): sources_from_receipt(r)
        r = receipt(); r['no_trim'] = False
        with self.assertRaisesRegex(ReferenceError, 'whole-utterance'): sources_from_receipt(r)

    def test_exact_split_namespace_is_distinct_from_directory_and_member_path(self):
        self.assertEqual(sources_from_receipt(receipt())[0]['original_split'], SPLIT_NAMESPACE)
        for field, value in [('original_split', SPLIT_DIRECTORY),
                             ('original_split', SPLIT_NAMESPACE[:-1]+'7'),
                             ('split_directory', SPLIT_NAMESPACE)]:
            changed = receipt(); changed['sources'][0][field] = value
            with self.assertRaises(ReferenceError): sources_from_receipt(changed)
        changed = receipt()
        changed['sources'][0]['archive_member']['path'] = SPLIT_NAMESPACE+'/s.wav'
        with self.assertRaisesRegex(ReferenceError, 'archive member'): sources_from_receipt(changed)

    def test_normal_path_is_continuous_once_then_two_restores_per_edge(self):
        result, calls, resets, emitted = rig()
        self.assertTrue(result['all_equal']); self.assertEqual(len(result['references']), 3)
        self.assertEqual(len(result['comparisons']), 6); self.assertEqual(resets, ['genesis', 'genesis'])
        self.assertEqual(sum(c[0] == 'continuous_begin' for c in calls), 1)
        self.assertEqual(sum(c[0] == 'restore' for c in calls), 6)

    def test_mismatch_preserves_reference_and_runs_first_failure_controls(self):
        result, calls, resets, emitted = rig(mismatch=True)
        self.assertFalse(result['all_equal']); self.assertEqual(result['references'], scripted_rows())
        control = result['first_failure_controls']
        self.assertEqual(control['first_failed_end'], 8000)
        self.assertEqual(len(control['same_input_adapter_repeats']), 2)
        self.assertIn(('continuous_begin', 'first_failure_original_prefix', 8000), calls)
        self.assertEqual(len(resets), 3)

    def test_original_prefix_stop_does_not_change_source_EOS(self):
        result, calls, resets, emitted = rig(mismatch=True)
        prefix = [v for k, v in emitted if k == 'diagnostic_original_prefix_edge']
        self.assertEqual([r['end'] for r in prefix], [8000])
        self.assertEqual(result['references'][-1]['end'], 16001)

    def test_restore_exception_is_retained_not_used_as_reference(self):
        result, calls, resets, emitted = rig(restore_exception=True)
        self.assertFalse(result['all_equal']); self.assertIsNotNone(result['execution_exception'])
        self.assertEqual(result['references'], scripted_rows())
        self.assertEqual(len(result['first_failure_controls']['same_input_adapter_repeats']), 2)

    def test_continuous_failure_keeps_pending_original_start(self):
        result, calls, resets, emitted = rig(continuous_exception=True)
        self.assertFalse(result['all_equal']); self.assertEqual(len(result['references']), 1)
        self.assertEqual(result['first_failure_controls']['first_failed_end'], 16000)
        self.assertTrue(any(k == 'continuous_exception' for k, _ in emitted))

    def test_reference_chain_cannot_skip_or_relabel_an_edge(self):
        rows = scripted_rows(); rows[1]['original_full_start_cut']['transcript'] = 'wrong'
        with self.assertRaisesRegex(ReferenceError, 'state chain broke'):
            reference_chain(dict(source_id='s', frames=16001), rows)

    def test_same_input_control_bounds_not_silently_relaxed(self):
        with self.assertRaisesRegex(ReferenceError, 'frozen repeat controls'):
            generate_source({}, reset=None, continuous=None, restored=None, compare=None,
                emit=None, pending=None, restored_repeats=1)


if __name__ == '__main__': unittest.main(verbosity=2)
