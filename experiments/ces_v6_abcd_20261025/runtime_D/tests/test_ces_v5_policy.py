"""CPU scheduling fixtures, never evidence of real GPU or service gains."""
from copy import deepcopy
from dataclasses import replace

import pytest

from revtrace.ces_v5_policy import (
    V5Target, choose_v5, predict_batch, residual_credit, _plan_metrics,
)


def calibration():
    return {
        'global_reject': 0.2,
        'causal_reject': {},
        'cost_seconds': {
            'generate': {'1': 1.0, '2': 2.0, '4': 4.0},
            'verify': {'1': 0.2, '2': 0.2, '4': 0.2},
            'fallback': {'1': 1.0, '2': 1.0, '4': 2.0},
            'proposal': {'1': 0.5, '2': 0.7, '4': 1.0},
        },
        'v5_risk_model': {
            'schema_version': 1, 'min_bucket_samples': 1, 'risk_quantile': .9,
            'generation_scenarios': {
                'global': [{'weight': 1, 'lease_ratio': 1, 'row_fraction': 1}],
            },
            'verification_scenarios': {
                'global': [{'weight': 1, 'original_rows': 1, 'failed_count': 0,
                            'verify_ratio': 1, 'fallback_ratio': 1,
                            'verify_row_fraction': 1, 'fallback_row_fraction': 1}],
            },
        },
    }


def target(sid=0, **kwargs):
    values = dict(sid=sid, window=1, ready=0.0, deadline=8.0,
                  candidate_ready=True, same_birth=False, previous_reject=False,
                  candidate_tokens=32, descendant_count=0, descendant_seconds=0,
                  candidate_eta=None, display_met=False, display_expired=False,
                  audio_weight=2.0)
    values.update(kwargs)
    return V5Target(**values)


@pytest.mark.parametrize('mode', ['risk_cost', 'progress', 'progress_joint'])
def test_never_verifies_unavailable_candidate(mode):
    result = choose_v5([target(candidate_ready=False, candidate_eta=.01)], now=0,
                       mode=mode, cal=calibration(), limit=16, wait_cap=.15)
    assert result['operation'] == 'generate'
    assert result['wait_seconds'] == 0
    assert result['common_cut_sids'] == [0]


def test_display_already_met_retains_pending_commit_credit():
    row = target(display_met=True)
    assert residual_credit(row, 7.9, 2) == 2
    assert residual_credit(row, 8.1, 2) == 0
    pending = replace(row, display_met=False)
    assert residual_credit(pending, 7.9, 2) == 0


def test_display_expired_predecessor_is_still_dispatched():
    row = target(display_expired=True)
    result = choose_v5([row], now=3, mode='progress', cal=calibration(), limit=16)
    assert result['operation'] in ('generate', 'verify')
    assert result['sids'] == [0]
    assert result['expected_credit_audio'] == 0
    assert result['common_cut_sids'] == [0]


def test_same_birth_is_not_required_for_successful_verification():
    result = choose_v5([target(same_birth=False)], now=0, mode='progress',
                       cal=calibration(), limit=16)
    assert result['operation'] == 'verify'


def test_progress_changes_order_using_actual_display_ack():
    rows = [target(0, ready=-1.5), target(1, candidate_ready=False, display_met=True)]
    cost_result = choose_v5(rows, now=0, mode='risk_cost', cal=calibration(), limit=16)
    progress = choose_v5(rows, now=0, mode='progress', cal=calibration(), limit=16)
    assert cost_result['operation'] == 'generate' and cost_result['sids'] == [1]
    assert progress['operation'] == 'verify' and progress['sids'] == [0]
    assert progress['expected_credit_audio'] == 4
    assert cost_result['expected_credit_audio'] == 2
    already_seen = [replace(rows[0], display_met=True), rows[1]]
    after_ack = choose_v5(already_seen, now=0, mode='progress', cal=calibration(), limit=16)
    assert after_ack['operation'] == 'generate'
    assert after_ack['expected_credit_audio'] == 4


def test_expired_display_not_resurrected_by_late_canonical_result():
    row = target(display_expired=True)
    assert residual_credit(row, .1, 2) == 0
    assert residual_credit(replace(row, display_expired=False), .1, 2) == 2


def test_accepted_verify_row_returns_before_failed_peer_but_lease_remains():
    cal = calibration()
    cal['v5_risk_model']['verification_scenarios'] = {
        '2': [{'weight': 1, 'original_rows': 2, 'failed_count': 1,
               'fallback_rows': 1, 'verify_ratio': 1, 'fallback_ratio': 1,
               'verify_row_fraction': .5, 'fallback_row_fraction': 1}],
    }
    a, b = target(0), target(1)
    c = target(2, candidate_ready=False, display_met=True, deadline=1.5)
    batch = predict_batch(cal, 'verify', [a, b])[0]
    assert batch.early_row == pytest.approx(.1)
    assert batch.late_row == pytest.approx(1.2)
    assert batch.lease == pytest.approx(1.2)
    assert batch.reject_fraction == .5
    metrics = _plan_metrics((('verify', [a, b]), ('generate', [c])), 0, cal, 2, {})
    assert metrics['row_predictions'][2]['predicted_finish_seconds'] == pytest.approx(2.2)
    assert metrics['expected_commit_late_audio'] == 2
    assert metrics['expected_lease_seconds'] == pytest.approx(2.2)


def test_joint_failed_count_is_not_independent_row_sampling():
    cal = calibration()
    cal['v5_risk_model']['verification_scenarios'] = {'2': [
        {'weight': .5, 'original_rows': 2, 'failed_count': 0},
        {'weight': .5, 'original_rows': 2, 'failed_count': 2},
    ]}
    outcomes = predict_batch(cal, 'verify', [target(0), target(1)])
    assert {o.reject_fraction for o in outcomes} == {0, 1}
    assert len(outcomes) == 2
    assert sum(o.weight for o in outcomes) == 1


def test_sparse_calibration_is_labelled_and_conservative():
    cal = calibration()
    cal['v5_risk_model']['min_bucket_samples'] = 8
    outcomes = predict_batch(cal, 'verify', [target(0), target(1)])
    assert all(o.source.startswith('sparse-conservative:') for o in outcomes)
    assert {o.reject_fraction for o in outcomes} == {0, 1}
    assert max(o.lease for o in outcomes) >= 1.2


def test_compressed_scenario_support_uses_original_count():
    cal = calibration()
    cal['v5_risk_model']['min_bucket_samples'] = 8
    cal['v5_risk_model']['verification_scenarios']['2'] = {
        'count': 100, 'scenarios': [{'weight': 1, 'original_rows': 2, 'failed_count': 0}],
    }
    outcomes = predict_batch(cal, 'verify', [target(0), target(1)])
    assert len(outcomes) == 1
    assert outcomes[0].source == 'empirical:verify:2'


def test_methods_receive_same_risk_model_and_joint_candidate_set():
    cal = calibration()
    rows = [target(0), target(1, candidate_ready=False, display_met=True)]
    results = [choose_v5(rows, now=0, mode=m, cal=cal, limit=16)
               for m in ('risk_cost', 'progress', 'progress_joint')]
    assert all(r['risk_model_shared'] for r in results)
    assert len({r['partitions_evaluated'] for r in results}) == 1
    assert results[1]['plan'] == results[2]['plan']


def test_full_common_cut_has_no_dropped_or_duplicate_target():
    rows = [target(i, candidate_ready=(i % 2 == 0), display_expired=(i % 3 == 0))
            for i in range(8)]
    result = choose_v5(rows, now=1, mode='progress', cal=calibration(), limit=16)
    plan_ids = [sid for batch in result['plan'] for sid in batch['sids']]
    assert sorted(plan_ids) == list(range(8))
    assert len(plan_ids) == len(set(plan_ids))
    for batch in result['plan']:
        if batch['operation'] == 'verify':
            assert all(rows[sid].candidate_ready for sid in batch['sids'])


@pytest.mark.parametrize('mutation', ['future', 'duplicate', 'ambiguous_display', 'weight'])
def test_invalid_online_targets_fail_closed(mutation):
    row = target()
    rows = [row]
    if mutation == 'future':
        rows = [replace(row, ready=1)]
    elif mutation == 'duplicate':
        rows.append(row)
    elif mutation == 'ambiguous_display':
        rows = [replace(row, display_met=True, display_expired=True)]
    else:
        rows = [replace(row, audio_weight=float('nan'))]
    with pytest.raises(ValueError):
        choose_v5(rows, now=0, mode='progress', cal=calibration(), limit=16)


def test_private_age_does_not_manufacture_progress_or_savings():
    rows = [target(0, display_expired=True), target(1, display_met=True)]
    base = choose_v5(rows, now=3, mode='progress', cal=calibration(), limit=16)
    exaggerated = [replace(t, descendant_count=10000, descendant_seconds=1e8) for t in rows]
    result = choose_v5(exaggerated, now=3, mode='progress', cal=calibration(), limit=16)
    assert result == base


def test_batch_model_does_not_accept_absent_candidates():
    with pytest.raises(ValueError, match='actually ready'):
        predict_batch(calibration(), 'verify', [target(candidate_ready=False)])


def test_prediction_does_not_change_input_objects_or_calibration():
    cal = calibration()
    before = deepcopy(cal)
    rows = [target()]
    choose_v5(rows, now=0, mode='progress', cal=cal, limit=16)
    assert cal == before
    assert rows == [target()]
