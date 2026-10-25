"""Independent CSV/profile arithmetic audit; no fitter imports or GPU calls.

This checks the bounded extracted evidence, not the full remote worker-record
extraction or new inference. Input hashes preserve the link to original logs.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding='utf8', newline='') as handle:
        return list(csv.DictReader(handle))


def integer(value):
    return int(value)


def number(value):
    out = float(value)
    assert math.isfinite(out), ('nonfinite extracted value', value)
    return out


def boolean(value):
    assert value in ('True', 'False'), ('nonboolean field', value)
    return value == 'True'


def equal(a, b, tolerance=1e-9):
    assert math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance), (a, b)


def bin_audio(seconds):
    if seconds <= 8.:
        return '0-8'
    return '8-16' if seconds <= 16. else '16+'


def independent_fit(rows):
    """Independent transcription of the declared 15-step robust ridge math."""
    import numpy as np
    x = np.array([[number(r[f'x{i}']) for i in range(7)] for r in rows])
    y = np.array([number(r['physical_lease_s']) for r in rows])
    assert len(y) and np.isfinite(x).all() and np.isfinite(y).all() and (y > 0).all()
    weights = np.ones(len(y))
    ridge = np.diag([0.] + [.1]*6)
    for _ in range(15):
        gram = sum(w*np.outer(a, a) for w, a in zip(weights, x))
        rhs = sum(w*b*a for w, b, a in zip(weights, y, x))
        beta = np.linalg.solve(gram+ridge, rhs)
        errors = y-x@beta
        scale = max(1e-6, 1.4826*float(np.median(np.abs(errors-np.median(errors)))))
        weights = np.minimum(1., 1.345*scale/np.maximum(np.abs(errors), 1e-12))
    return beta, min(y), max(y)


def audit(profile_dir, old_calibration, repeat_dir=None):
    summary = read(profile_dir/'SUMMARY.json')
    assert summary['status'] == 'PASS_ACTUAL_SELECTED_EXECUTION_PROFILES'
    assert summary['online_cells'] == 48 and summary['new_GPU_calls'] == 0
    assert summary['capped_complete_runs_retained'] is True
    assert summary['script_sha256'] == sha(Path(__file__).with_name('fit_execution_profiles.py'))
    for name, record in summary['outputs'].items():
        assert Path(name).name == name
        path = profile_dir/name
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']

    cal = read(profile_dir/'CALIBRATION.json')
    profiles = cal['closed_loop_profiles']
    rows = csv_rows(profile_dir/'PROPOSAL_ROWS.csv')
    batches = csv_rows(profile_dir/'PROPOSAL_BATCHES.csv')
    roots = csv_rows(profile_dir/'ROOT_COMPATIBILITY.csv')
    cells = csv_rows(profile_dir/'CELL_STATUS.csv')
    assert len(cells) == 48 and len({r['cell'] for r in cells}) == 48
    assert all(boolean(r['fine_window_accounting_complete']) for r in cells)
    counts = Counter(r['decision'] for r in cells)
    assert set(counts) <= {'PASS_PROTOCOL_COMPLETENESS', 'TOKEN_LIMIT_BOUNDARY'}
    assert dict(counts) == summary['cell_status_counts']
    assert sum(integer(r['proposal_capped_rows']) for r in cells) == summary['proposal_capped_rows']
    assert sum(integer(r['authority_capped_rows']) for r in cells) == summary['authority_capped_rows']
    assert len(rows) == summary['actual_proposal_rows']
    assert len(batches) == summary['actual_proposal_physical_batches']
    assert len(roots) == summary['actual_direct_fallback_transitions']
    assert sum(r['hit_token_limit'] == 'True' for r in rows) == summary['proposal_capped_rows']
    inputs = read(profile_dir/'INPUT_MANIFEST.json')
    assert len(inputs) == 4+48*6
    assert len({r['path'] for r in inputs}) == len(inputs)
    for entry in inputs:
        assert not Path(entry['path']).is_absolute() and '..' not in Path(entry['path']).parts
        assert len(entry['sha256']) == 64 and entry['bytes'] > 0

    keyed = {(r['cell'], r['batch_id']): r for r in batches}
    assert len(keyed) == len(batches)
    assert len({r['cell'] for r in batches}) == 48
    row_count = Counter()
    assert len({(r['cell'], r['job_id']) for r in rows}) == len(rows)
    for r in rows:
        key = r['cell'], r['batch_id']
        batch = keyed[key]
        row_count[key] += 1
        lease = number(r['physical_lease_s'])
        equal(lease, batch['physical_lease_s'])
        assert lease > 0. and integer(r['rows']) == integer(batch['rows'])
        fraction = number(r['row_fraction'])
        assert 0. <= fraction <= 1.
        equal(fraction, number(r['terminal_after_start_s'])/lease)
        assert r['audio_bin'] == bin_audio(number(r['audio_seconds']))
    for key, batch in keyed.items():
        assert row_count[key] == integer(batch['rows'])
        equal(number(batch['batch_drained_perf'])-number(batch['worker_started_perf']),
              batch['physical_lease_s'])

    proposal = profiles['proposal']
    for n, fitted in proposal['row_fraction_by_n'].items():
        subset = rows if n == 'global' else [r for r in rows if integer(r['rows']) == integer(n)]
        assert fitted['support'] == len(subset)
        assert fitted['physical_batches'] == len({(r['cell'], r['batch_id']) for r in subset})
        assert Counter(fitted['fractions']) == Counter(number(r['row_fraction']) for r in subset)
        for audio, item in proposal['row_fraction_by_n_audio'].get(n, {}).items():
            selected = [r for r in subset if r['audio_bin'] == audio]
            assert item['support'] == len(selected)
            assert item['physical_batches'] == len({(r['cell'], r['batch_id']) for r in selected})
            assert Counter(item['fractions']) == Counter(number(r['row_fraction']) for r in selected)
    for audio, item in proposal['median_generated_tokens_by_audio_bin'].items():
        selected = [integer(r['generated_tokens']) for r in rows if r['audio_bin'] == audio]
        assert item['support'] == len(selected)
        equal(item['median_generated_tokens'], statistics.median(selected))
    for n, lease in cal['cost_seconds']['proposal'].items():
        equal(lease, statistics.median(number(r['physical_lease_s']) for r in batches
                                     if integer(r['rows']) == integer(n)))

    available = [r for r in roots if r['birth_group']]
    no_nodes = [r for r in roots if not r['birth_group']]
    for r in available:
        assert r['operation'] in ('direct', 'fallback')
        assert r['birth_group'] in ('same', 'mismatch')
        assert integer(r['available_nodes_at_enqueue']) > 0
        assert r['node_job_id'] and not r['no_node_reason']
        assert number(r['node_received_perf']) <= number(r['authority_enqueue_perf'])
        boolean(r['root_equal'])
    for r in no_nodes:
        assert not r['node_job_id'] and not r['root_equal']
        assert integer(r['available_nodes_at_enqueue']) == 0 and r['no_node_reason']
    independently_derived = {}
    for operation in ('direct', 'fallback'):
        independently_derived[operation] = {}
        for birth in ('same', 'mismatch'):
            group = [r for r in available if r['operation'] == operation and r['birth_group'] == birth]
            n = len(group)
            k = sum(boolean(r['root_equal']) for r in group)
            report = profiles['compatibility'][operation][birth]
            assert (report['support'], report['matches']) == (n, k)
            assert report['unique_cells'] == len({r['cell'] for r in group})
            assert report['unique_source_frontiers'] == len({(r['source_id'], r['frontier_sample']) for r in group})
            if n >= 8:
                equal(report['probability'], (k+.5)/(n+1.))
            else:
                assert report['probability'] is None
            if n:
                z = 1.959963984540054
                p = k/n
                den = 1.+z*z/n
                half = z*math.sqrt(p*(1.-p)/n+z*z/(4.*n*n))/den
                middle = (p+z*z/(2.*n))/den
                low, high = max(0., middle-half), min(1., middle+half)
            else:
                low, high = 0., 1.
            equal(report['lower'], low)
            equal(report['upper'], high)
            independently_derived[operation][birth] = dict(support=n, matches=k,
                probability=report['probability'], lower=low, upper=high)

    coefficients, floor, ceiling = independent_fit(batches)
    fitted = proposal['contextual_cost_fit']
    for a, b in zip(coefficients, fitted['coefficients']):
        equal(a, b, 1e-6)
    equal(floor, fitted['prediction_floor_s'])
    equal(ceiling, fitted['prediction_ceiling_s'])
    assert fitted['support_physical_batches'] == len(batches)
    held = [r for r in batches if int(hashlib.sha256(r['cell'].encode()).hexdigest()[:8], 16)%5 == 0]
    train = [r for r in batches if r not in held]
    beta, lo, hi = independent_fit(train)
    errors = []
    for r in held:
        prediction = sum(number(r[f'x{i}'])*beta[i] for i in range(7))
        prediction = min(hi, max(lo, prediction))
        errors.append(abs(prediction-number(r['physical_lease_s'])))
    diagnostic = proposal['held_cell_diagnostic']
    assert diagnostic['physical_batches'] == len(held)
    assert diagnostic['cells'] == len({r['cell'] for r in held})
    equal(statistics.median(errors), diagnostic['median_absolute_error_s'], 1e-6)
    equal(statistics.mean(errors), diagnostic['mean_absolute_error_s'], 1e-6)

    original = read(old_calibration)
    restored = deepcopy(cal)
    restored.pop('closed_loop_profiles')
    restored['cost_seconds']['proposal'] = original['cost_seconds']['proposal']
    if 'proposal' in original.get('contextual_cost_models', {}):
        restored['contextual_cost_models']['proposal'] = original['contextual_cost_models']['proposal']
    else:
        restored.get('contextual_cost_models', {}).pop('proposal', None)
        if not restored.get('contextual_cost_models') and 'contextual_cost_models' not in original:
            restored.pop('contextual_cost_models', None)
    assert restored == original, 'Non-proposal old calibration unexpectedly changed'
    assert sha(old_calibration) == summary['source_calibration_sha256']
    repeat_match = None
    if repeat_dir is not None:
        repeat_match = (profile_dir/'CALIBRATION.json').read_bytes() == (repeat_dir/'CALIBRATION.json').read_bytes()
        assert repeat_match, 'Same-source repeated profile calibration differs'
        for name in ('PROPOSAL_ROWS.csv', 'PROPOSAL_BATCHES.csv', 'ROOT_COMPATIBILITY.csv',
                     'CELL_STATUS.csv', 'INPUT_MANIFEST.json'):
            assert (profile_dir/name).read_bytes() == (repeat_dir/name).read_bytes(), name
    return dict(status='PASS_INDEPENDENT_EXTRACTED_PROFILE_ARITHMETIC_AND_FIT_AUDIT',
        evidence_tier='CPU_recomputation_of_actual_old48_extracted_records_no_GPU',
        actual_cells=48, actual_proposal_rows=len(rows), actual_proposal_batches=len(batches),
        actual_selected_direct_fallback=len(roots), available_root_denominator=len(available),
        excluded_no_node=len(no_nodes), cell_status_counts=dict(counts),
        compatibility=independently_derived, same_input_repeat_byte_identical=repeat_match,
        authority_calibration_unchanged=True, held_cell_diagnostic=diagnostic,
        profiles_sha256=sha(profile_dir/'CALIBRATION.json'),
        script_sha256=sha(Path(__file__)),
        limitation='Extracted CSV arithmetic and fit only; not fresh inference, full raw extraction rerun, source-independent validation or a retention/SLO theorem.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profiles', type=Path, required=True)
    parser.add_argument('--old-calibration', type=Path, required=True)
    parser.add_argument('--repeat-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Independent audit evidence must not be overwritten')
    result = audit(args.profiles, args.old_calibration, args.repeat_dir)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
