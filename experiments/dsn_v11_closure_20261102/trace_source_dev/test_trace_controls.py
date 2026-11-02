"""Eight synthetic controls. No real trace/model/source helper is opened."""
from __future__ import annotations
import copy
import unittest
from trace_common import TraceError, NN4F, digest
from trace_analysis import (aggregate, analyze_cell, build_context, canonical_binding,
                            compare_endpoints, cut, delta, display_chain, endpoints,
                            job_timelines, same, validate_scope, view_bindings)


def state(frontier, text='', cursor=0):
    return dict(audio_segments=[], tokens=[], context=[], last_attend_frame=cursor,
                detected_language='zh', initial_tokens=[], initial_token_length=0,
                sot_index=0, decoder_type='test', contract={'source_sha': 'audio', 'model': 'fixture'},
                frontier=frontier, transcript=text)


def fixture():
    sid = 'source'
    initial, projected, final = state(0), state(8000, 'draft'), state(8000, 'selected')
    source = dict(source_id=sid, frames=8000, audio_sha256='audio', reference='selected')
    config = dict(cell_id='cell', arm='fullcall', repeat=0, fault={'kind': 'none'},
                  settings=dict(source_commit=NN4F, sources=[source]))
    job = dict(job_id='e0-j000000001', source_id=sid, start=initial, end=8000,
               worker='full0', worker_incarnation=0, dispatch_epoch=0, kind='full',
               started_on_canonical=True, dispatched_perf=100.5)
    identity = dict(job_id=job['job_id'], source_id=sid, worker='full0',
                    worker_incarnation=0, dispatch_epoch=0)
    asr = dict(identity, kind='asr_early', start_state=initial, start_state_sha=cut(initial),
               end_frontier=8000, produced_perf=100.9, sent_perf=100.91,
               projection=dict(end=projected, end_state_sha=cut(projected)))
    record = dict(start_state=cut(initial), end_state=cut(final), model_start=100.6,
                  model_end=101.2, worker_job_begin_perf=100.55, worker_job_end_perf=101.21,
                  native_model_evaluated=True, selection_changed=False,
                  role='authority', candidate_handoff=False, token_ids=[1], selected_correction=None)
    complete = dict(identity, kind='completed', start=initial, end=final, record=record, sent_perf=101.22)
    body = dict(source_id=sid, owner_epoch=0, session_epoch=0, job=job, parent_state=initial,
                parent_state_sha256=cut(initial), next_state=final, next_state_sha256=cut(final),
                transition_id='transition-1', record=record)
    receipt = dict(sequence=2, record_sha256='1' * 64, synced_perf=101.3)
    pubs = [dict(bound_owner_epoch=0, received_perf=100.95,
                 event=dict(kind='private', source_id=sid, publication_id=1, canonical_sha=cut(initial),
                            steps=[dict(job_id=job['job_id'], start=initial, end=projected)])),
            dict(bound_owner_epoch=0, received_perf=101.35,
                 event=dict(kind='canonical', source_id=sid, publication_id=2, state=final,
                            durable_receipt=receipt))]
    rows = [dict(kind='private', source_id=sid, owner_epoch=0, observed=101.,
                 visible_frontier=8000, certified_frontier=0, text='draft',
                 canonical_sha=cut(initial), private_job=job['job_id'], publication_id=1),
            dict(kind='canonical', source_id=sid, owner_epoch=0, observed=101.36,
                 visible_frontier=8000, certified_frontier=8000, text='selected',
                 canonical_sha=cut(final), private_job=None, publication_id=2,
                 journal_sequence=2, transition_id='transition-1')]
    primary, fs = endpoints(rows, source, 100.)
    quality = [dict(source_id=sid, character_edits=0, reference_characters=8, CER=0.)]
    data = dict(config=config, origin=dict(origin_perf=100., original_D=2., original_C=8.),
                summary=dict(primary=primary, content={'original_dual_credit_audio_seconds': .5}, quality=quality),
                consumer=rows, publications=pubs,
                dispatch=[dict(owner_epoch=0, job=job)],
                results=[dict(owner_epoch=0, event=asr), dict(owner_epoch=0, event=complete)],
                events=[dict(kind='durable_sync', owner_epoch=0, job_id=job['job_id'], receipt=receipt,
                             observed=101.31),
                        dict(kind='canonical_install', owner_epoch=0, job_id=job['job_id'], receipt=receipt,
                             observed=101.32, parent_state_sha=cut(initial), next_state_sha=cut(final))],
                audit=[], frames=[(dict(kind='genesis', body=dict(initials={sid: initial},
                                                                  metadata={'config_sha256': digest(config)})),
                                   {'sequence': 1}),
                                  (dict(kind='canonical', body=body), receipt)])
    cell = dict(cell_id='cell', source_id=sid, speaker_id='speaker', policy='fullcall', repeat=0)
    archived = dict(primary=dict(primary, frontiers=fs), semantic={'checked_steps': 1})
    return cell, data, archived


class TraceControls(unittest.TestCase):
    def test_01_actual_G_exceeds_F_and_original_clock_path_is_conserved(self):
        source = dict(source_id='s', frames=16000)
        row = dict(kind='private', source_id='s', owner_epoch=0, observed=101.25,
                   visible_frontier=16000, certified_frontier=16000, private_job='j', publication_id=7)
        _, fs = endpoints([row], source, 100.)
        self.assertEqual(fs[0]['first_D_actual_G'], 16000)
        self.assertAlmostEqual(fs[0]['D'], .75)
        pub = dict(received_perf=101.2, bound_owner_epoch=0, event={'publication_id': 7})
        binding = dict(kind='actual_private_job', identity=(0, 'j'), actual_publication=pub,
                       view_publication=pub, view_publication_id=7, view_publication_owner_epoch=0)
        chain = display_chain(fs[0], row, binding,
                              dict(dispatched_perf=101.01, ASR_produced_perf=101.1))
        self.assertAlmostEqual(chain['decomposition_sum_seconds'], .75)
        self.assertAlmostEqual(chain['Consumer_minus_publication_receive_seconds'], .05)
        self.assertEqual(chain['view_job_id'], 'j')

    def test_02_canonical_fallback_requires_bound_fact_not_a_fabricated_private_ASR(self):
        _, data, _ = fixture()
        context = build_context(data)
        row, pub = data['consumer'][1], data['publications'][1]
        fact = canonical_binding(row, pub, context)
        self.assertEqual(fact['body']['transition_id'], 'transition-1')
        binding = view_bindings(data['consumer'], context)[1]
        frontier = dict(offer=100.5, D=.86)
        out = display_chain(frontier, row, binding, dict(dispatched_perf=100.5, ASR_produced_perf=100.9))
        self.assertEqual(out['decomposition_status'], 'NOT_APPLICABLE_CANONICAL_FACT_FALLBACK')
        self.assertIsNone(out['ASR_minus_dispatch_seconds'])
        bad = dict(row, journal_sequence=999)
        with self.assertRaises(TraceError):
            canonical_binding(bad, pub, context)

    def test_03_missing_phase_time_remains_NA_and_signed_intervals_are_not_zeroed(self):
        cell, data, archived = fixture()
        del data['results'][1]['event']['record']['worker_job_begin_perf']
        # The synthetic durable record is an alias to the same original record.
        context = build_context(data)
        timeline = job_timelines(data, context)[0]
        self.assertIsNone(timeline['worker_job_begin_perf'])
        self.assertIsNone(timeline['worker_begin_minus_dispatch_seconds'])
        binding = view_bindings(data['consumer'], context)[0]
        out = display_chain(dict(offer=100.5, D=.5), data['consumer'][0], binding,
                            dict(dispatched_perf=100.5, ASR_produced_perf=None))
        self.assertTrue(out['decomposition_status'].startswith('NOT_APPLICABLE_MISSING'))
        self.assertIsNone(out['decomposition_sum_seconds'])
        self.assertEqual(delta(2., 3.), -1.)

    def test_04_partial_EOS_all_offered_credit_and_archived_endpoints_are_conserved(self):
        source = dict(source_id='s', frames=9000)
        rows = [dict(source_id='s', observed=101., visible_frontier=8000, certified_frontier=8000),
                dict(source_id='s', observed=102.7, visible_frontier=9000, certified_frontier=9000)]
        primary, fs = endpoints(rows, source, 100.)
        self.assertEqual(len(fs), 2)
        self.assertAlmostEqual(primary['offered_audio_seconds'], .5625)
        self.assertAlmostEqual(primary['dual_deadline_audio_credit_seconds'], .5)
        self.assertFalse(fs[-1]['D2'])
        archive = dict(primary, frontiers=copy.deepcopy(fs))
        compare_endpoints(primary, fs, primary, archive)
        archive['frontiers'][-1]['offer'] += .1
        with self.assertRaises(TraceError):
            compare_endpoints(primary, fs, primary, archive)
        with self.assertRaises(TraceError):
            compare_endpoints(primary, fs, dict(primary, dual_deadline_audio_credit_seconds=0.),
                              dict(primary, frontiers=fs))

    def test_05_only_complete_paired_32_scope_with_eight_distinct_speakers_is_accepted(self):
        cells = [dict(cell_id=f'{sid}-{p}-{r}', source_id=str(sid), speaker_id=f's{sid}',
                      policy=p, repeat=r) for sid in range(8)
                 for p in ('conservative', 'fullcall') for r in (0, 1)]
        archive = dict(status='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS',
                       completed_trials=32, independent_speakers=8, cells=cells)
        self.assertEqual(len(validate_scope(cells, archive)), 32)
        with self.assertRaises(TraceError):
            validate_scope(cells[:-1], archive)
        changed = copy.deepcopy(cells)
        for row in changed:
            if row['source_id'] == '1':
                row['speaker_id'] = 's0'
        with self.assertRaises(TraceError):
            validate_scope(changed, archive)

    def test_06_duplicate_dispatch_UID_and_foreign_completion_fail_closed(self):
        _, data, _ = fixture()
        duplicate = copy.deepcopy(data)
        duplicate['dispatch'].append(copy.deepcopy(duplicate['dispatch'][0]))
        with self.assertRaises(TraceError):
            build_context(duplicate)
        foreign = copy.deepcopy(data)
        foreign['results'][-1]['event']['worker_incarnation'] = 1
        with self.assertRaises(TraceError):
            build_context(foreign)

    def test_07_full_state_equality_is_not_text_or_python_numeric_coercion(self):
        a = state(8000, 'same', 0)
        b = state(8000, 'same', 1)
        self.assertFalse(same(a, b))
        b = copy.deepcopy(a)
        b['context'] = [True]
        a['context'] = [1]
        self.assertFalse(same(a, b))
        with self.assertRaises(TraceError):
            cut(dict(a, extra='not declared'))
        _, data, _ = fixture()
        timeline = job_timelines(data, build_context(data))[0]
        self.assertFalse(timeline['own_projection_vs_complete_full_state_equal'])
        self.assertFalse(timeline['selection_changed'])
        self.assertTrue(timeline['actual_parent_full_state_equal'])

    def test_08_retained_view_keeps_its_actual_publication_and_source_deficits_are_not_hardcoded(self):
        _, data, _ = fixture()
        # Same actual view persists through another applied private publication
        # whose empty path cannot replace the ahead tip. Bind to original pub1.
        context = build_context(data)
        context['publications'][(0, 9)] = dict(bound_owner_epoch=0, received_perf=101.05,
                                              event=dict(kind='private', publication_id=9,
                                                         source_id='source', canonical_sha=cut(state(0)), steps=[]))
        held = dict(data['consumer'][0], observed=101.1, publication_id=9)
        bindings = view_bindings([data['consumer'][0], held], context)
        self.assertEqual(bindings[1]['view_publication_id'], 1)
        self.assertEqual(bindings[1]['actual_publication']['event']['publication_id'], 9)
        self.assertEqual(bindings[1]['kind'], 'retained_actual_private_job')
        cells = []
        for sid in range(8):
            for policy in ('conservative', 'fullcall'):
                for repeat in (0, 1):
                    deficit = .2 if policy == 'fullcall' and sid == 3 else .1 if policy == 'conservative' else 0.
                    cells.append(dict(cell_id=f'{sid}-{policy}-{repeat}', source_id=str(sid), speaker_id=str(sid),
                                      policy=policy, repeat=repeat, selected_steps=1,
                                      primary=dict(offered_audio_seconds=1., dual_deadline_audio_credit_seconds=1.-deficit,
                                                   complete_coverage_and_original_quantile_pass=deficit == 0.),
                                      D2_missed_audio_s=deficit, dual_deadline_missed_audio_s=deficit,
                                      quality=[dict(character_edits=0, reference_characters=1, CER=0.)]))
        out = aggregate(cells)
        own = next(r for r in out['source_deficit_ledger'] if r['source_id'] == '3')
        self.assertAlmostEqual(own['fullcall_dual_deadline_missed_audio_s'], .4)
        self.assertAlmostEqual(own['share_of_fullcall_missed_audio'], 1.)
        self.assertEqual(len(out['failed_fullcall_cell_ids']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
