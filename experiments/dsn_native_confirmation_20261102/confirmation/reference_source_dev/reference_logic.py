"""Pure orchestration over injected ORIGINAL engine helpers; no GPU imports."""
from __future__ import annotations
import copy, traceback
from ref_common import canonical, expected_frontiers, need


def reference_chain(source, references, *, allow_prefix=False):
    expected = expected_frontiers(source['frames'])
    need([r['end'] for r in references] == (expected[:len(references)] if allow_prefix else expected),
         'continuous original cadence/EOS incomplete')
    prior = None
    for row in references:
        need(row['source_id'] == source['source_id'] and row['continuous_original_no_between_step_restore'] is True,
             'reference source or continuous path changed')
        start, end = row['original_full_start_cut'], row['original_full_cut']
        need(start['frontier'] == (prior['frontier'] if prior else 0) and end['frontier'] == row['end'],
             'reference edge frontier changed')
        need(prior is None or canonical(start) == canonical(prior), 'continuous reference state chain broke')
        prior = end


def generate_source(source, *, reset, continuous, restored, compare, emit, pending,
                    restored_repeats=2, diagnostic_adapter_repeats=2):
    """Normal: one continuous path, two exact-start restored calls per edge.

    After the first bad boundary, two further same-input calls and one ORIGINAL
    continuous prefix are diagnostics, never replacement reference candidates.
    """
    need(restored_repeats == 2 and diagnostic_adapter_repeats == 2, 'frozen repeat controls changed')
    references, comparisons, first_bad, exception = [], [], None, None
    reset()
    try:
        for row in continuous(stop_at=None, phase='continuous_original'):
            references.append(copy.deepcopy(row)); emit('continuous_edge', row)
            reference_chain(source, references, allow_prefix=True)
        reference_chain(source, references)
    except Exception:
        exception = traceback.format_exc()
        last = copy.deepcopy(pending())
        emit('continuous_exception', dict(exception=exception, last_original_input=last))
        if last is not None:
            first_bad = dict(last, source_id=source['source_id'])
    if exception is None:
        # Match the original long_reference phase boundary. This is one reset
        # AFTER continuous generation, never a restore between original steps.
        reset()
        for index, reference in enumerate(references):
            for repeat in range(restored_repeats):
                try:
                    cut, record = restored(reference, phase='restored_original_input', repeat=repeat)
                    checked = compare(reference, cut, record)
                    comparisons.append(dict(index=index, repeat=repeat, **checked))
                    emit('restored_edge', dict(index=index, repeat=repeat, reference_end=reference['end'],
                        actual_cut=cut.state, actual_record=record, comparison=checked))
                    if not checked['all_equal'] and first_bad is None:
                        first_bad = copy.deepcopy(reference)
                except Exception:
                    exception = traceback.format_exc()
                    emit('restored_exception', dict(index=index, repeat=repeat, end=reference['end'], exception=exception))
                    first_bad = first_bad or copy.deepcopy(reference)
                    break
            if exception is not None:
                break
    control = None
    if first_bad is not None:
        control = dict(source_id=source['source_id'], first_failed_end=first_bad['end'],
                       same_input_adapter_repeats=[], original_continuous_prefix_repeat=[],
                       original_continuous_prefix_exception=None, diagnostics_do_not_replace_reference=True)
        for repeat in range(diagnostic_adapter_repeats):
            try:
                cut, record = restored(first_bad, phase='first_failure_same_input', repeat=repeat)
                comparison = compare(first_bad, cut, record) if 'original_full_cut' in first_bad else None
                row = dict(repeat=repeat, actual_cut=cut.state, actual_record=record,
                           comparison_to_original_completed_reference=comparison)
            except Exception:
                row = dict(repeat=repeat, exception=traceback.format_exc())
            control['same_input_adapter_repeats'].append(row)
            emit('diagnostic_same_input', row)
        repeated = []
        try:
            reset()
            for row in continuous(stop_at=first_bad['end'], phase='first_failure_original_prefix'):
                repeated.append(copy.deepcopy(row)); emit('diagnostic_original_prefix_edge', row)
        except Exception:
            control['original_continuous_prefix_exception'] = traceback.format_exc()
        originals = {r['end']: r for r in references}
        for row in repeated:
            old = originals.get(row['end'])
            control['original_continuous_prefix_repeat'].append(dict(end=row['end'],
                has_original_completed_reference=old is not None,
                complete_start_equal=(canonical(old['original_full_start_cut']) == canonical(row['original_full_start_cut'])) if old else None,
                complete_end_equal=(canonical(old['original_full_cut']) == canonical(row['original_full_cut'])) if old else None,
                original_C_equal=(canonical(old['original_full_result']['selected_correction']) == canonical(row['original_full_result']['selected_correction'])) if old else None,
                returned_IDs_equal=(old['original_full_result']['token_ids'] == row['original_full_result']['token_ids']) if old else None))
        emit('first_failure_controls', control)
    expected = len(expected_frontiers(source['frames']))
    ok = (exception is None and len(references) == expected and len(comparisons) == expected*2
          and all(r['all_equal'] for r in comparisons))
    return dict(source_id=source['source_id'], expected_original_steps=expected,
        references=references, comparisons=comparisons, first_failure_controls=control,
        execution_exception=exception, all_equal=ok,
        original_continuous_no_between_step_restore=True, reference_only=True)
