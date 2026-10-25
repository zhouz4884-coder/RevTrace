"""Planner-author CPU controls. Explicit fixture costs are not GPU evidence."""
from dataclasses import replace
from copy import deepcopy
import math

import pytest

from revtrace.ces_closed_loop import (Identity, TargetContext,
    SuccessorObligation, ClosedLoopState, PlannerConfig, choose_closed_loop,
    effective_deadlines, _draws, _private_probability, _private_survival_probability,
    AncestorPrediction)
from revtrace.ces_v5_policy import V5Target, BatchOutcome


def row(sid=0, ready=0., **kw):
    values = dict(sid=sid, window=1, ready=ready, deadline=ready+8,
        candidate_ready=False, same_birth=False, previous_reject=False,
        candidate_tokens=16, descendant_count=0, descendant_seconds=0.,
        candidate_eta=None, audio_seconds=2., interval_seconds=2.)
    values.update(kw)
    return V5Target(**values)


def ctx(t):
    return TargetContext(Identity(t.sid, 1, 0, 'actual-P', 0, 32000, 'contract'))


def calibration():
    return {'global_reject': 0., 'causal_reject': {}, 'cost_seconds': {
        'generate': {'1': .4, '2': 1.2, '16': 4.},
        'verify': {'1': .1, '2': .7, '16': 1.},
        'fallback': {'1': .4, '2': 1.2, '16': 4.}},
        'v5_risk_model': {'min_bucket_samples': 1, 'owner_delivery_seconds': .08,
        'generation_scenarios': {'global': [{'weight': 1., 'lease_ratio': 1., 'row_fraction': 1.}]},
        'verification_scenarios': {'global': [{'weight': 1., 'original_rows': 1,
            'failed_count': 0, 'verify_ratio': 1., 'verify_row_fraction': 1.}]}}}


def choose(rows, contexts=None, state=None, **kw):
    defaults = dict(now=0., mode='causal', cal=calibration(), limit=16,
        observed_credit_audio=0., elapsed_seconds=.01,
        state=state or ClosedLoopState('fixture'))
    defaults.update(kw)
    return choose_closed_loop(rows, contexts or {t.sid: ctx(t) for t in rows}, **defaults)


def test_real_enqueue_not_replan_changes_service_age():
    ts = [row(0, ready=-3., display_expired=True), row(1, candidate_ready=True)]
    cs = {t.sid: ctx(t) for t in ts}
    state = ClosedLoopState('x')
    decision = choose(ts, cs, state)
    for _ in range(3):
        choose(ts, cs, state)
    assert all(r.deferrals == 0 for r in state.records.values())
    state.record_dispatch(decision, cs, now=0.)
    assert state.dispatches == 1
    assert sum(r.deferrals for r in state.records.values()) == len(ts)-len(decision['sids'])
    with pytest.raises(ValueError, match='duplicate'):
        state.record_dispatch(decision, cs, now=0.)


def test_temporary_eligibility_absence_does_not_claim_wal_completion():
    t = row()
    state = ClosedLoopState()
    choose([t], state=state)
    key = ctx(t).identity
    state.records[key].deferrals = 2
    state.observe({}, 1.)
    assert state.records[key].deferrals == 2
    state.admitted(0, epoch=1, frontier=32000)
    assert not state.records


def test_symbolic_continuation_binds_only_new_actual_parent():
    t = row(ready=0., display_expired=True)
    u = SuccessorObligation(2, 64000, 2., 4., 10., 2., .4,
        parent_frontier_start=32000)
    context = replace(ctx(t), successors=(u,))
    state = ClosedLoopState()
    result = choose([t], {0: context}, state, now=2.1)
    assert result['symbolic_successors'][0]['requires_actual_parent']
    state.record_dispatch(result, {0: context}, now=2.1)
    assert state.continuation_intents
    state.admitted(0, epoch=1, frontier=32000)
    actual_child = replace(t, window=2, ready=2., deadline=10.)
    actual_context = TargetContext(Identity(0, 1, 1, 'real-new-P', 32000, 64000, 'contract'))
    state.observe({0: actual_context}, 2.6)
    record = state.records[actual_context.identity]
    assert record.promised_finish is not None
    assert actual_context.identity.parent_digest == 'real-new-P'


def test_known_verify_success_is_not_applied_to_unknown_direct():
    t = row(candidate_ready=True)
    outcome = BatchOutcome(1., 1., .2, 1., .25, 'fixture')
    c = replace(ctx(t), direct_private_probability=.4, fallback_private_probability=.2)
    assert _private_probability(c, 'verify', outcome, True, None) == (.8, True)
    assert _private_probability(c, 'generate', outcome, True, None) == (.4, True)
    unknown = replace(c, direct_private_probability=None)
    assert _private_probability(unknown, 'verify', outcome, True, None) == (0., False)
    assert unknown.direct_private_probability is None


def test_successor_direct_and_fallback_rates_are_not_collapsed():
    t = row(candidate_ready=True)
    rejected = BatchOutcome(1., 1., .2, 1., 1., 'all-failed-fixture')
    c = replace(ctx(t), direct_private_probability=.8, fallback_private_probability=.1)
    assert _private_probability(c, 'verify', rejected, True, direct=.8,
        fallback=.1, inherit_current=False) == (.1, True)
    assert _private_probability(c, 'generate', rejected, True, direct=.8,
        fallback=.1, inherit_current=False) == (.8, True)
    # A genuinely new symbolic Parent class has no measured transition rate.
    assert _private_probability(c, 'generate', rejected, True, direct=None,
        fallback=None, inherit_current=False) == (0., False)


def test_private_free_interval_is_not_reset_at_each_unknown_ancestor():
    # Actual branch is legal now, but root update at 6.6 certainly invalidates
    # it. A later child update at 7.1 cannot revive the old row finishing 6.9.
    probability = _private_survival_probability(((1., .8),), None,
        now=6.1, delivery=0., display_deadline=8.,
        ancestor_updates=((6.6, 0.), (7.1, None)), currently_legal=True)
    assert probability == 0.
    early = _private_survival_probability(((1., .2),), None,
        now=6.1, delivery=0., display_deadline=8.,
        ancestor_updates=((6.6, 0.), (7.1, None)), currently_legal=True)
    assert early == 1.  # Actual legal observation before the first root change.
    both = _private_survival_probability(((1., 1.2),), None,
        now=6.1, delivery=0., display_deadline=8.,
        ancestor_updates=((6.6, .8), (7.1, .1)), currently_legal=True)
    assert both == pytest.approx(.08)


def test_early_parent_row_does_not_get_envelope_free_survival():
    # Half of Generate rows install at .1, half at 1.0. This old branch is
    # never retained. A Private row at .5 survives only the late-parent half;
    # using the 1.0 envelope as a free interval would incorrectly reward all.
    outcome = BatchOutcome(1., 1., .55, .55, 0., 'fixture', (.1, 1.), (.1, 1.))
    parent = AncestorPrediction('generate', outcome, 0., 0., 0., 0., 0., True)
    p = _private_survival_probability(((1., .5),), None, now=0., delivery=0.,
        display_deadline=2., ancestor_updates=(parent,), currently_legal=True)
    assert p == .5


def test_verify_accept_early_and_fallback_late_joint_survival():
    # Accepted half installs at .1 and preserves; rejected half has not yet
    # installed at .5 (Fallback ends 1.0), so both halves are still legal at .5.
    # Multiplying mixed row-CDF by aggregate keep=.5 would produce only .75.
    outcome = BatchOutcome(1., 1., .1, 1., .5, 'fixture', (.1,), (1.,))
    parent = AncestorPrediction('verify', outcome, 0., 0., 1., .8, 0., True)
    p = _private_survival_probability(((1., .5),), None, now=0., delivery=0.,
        display_deadline=2., ancestor_updates=(parent,), currently_legal=True)
    assert p == 1.


def test_private_consumer_delay_clock_does_not_pay_delivery_twice():
    # Remaining .95 already includes Consumer delivery; adding allowance .1
    # again would incorrectly miss the absolute deadline 1.0.
    p = _private_survival_probability(((1., .95),), None, now=0., delivery=.1,
        display_deadline=1., ancestor_updates=(), currently_legal=True,
        private_delay_includes_delivery=True)
    assert p == 1.
    terminal_clock = _private_survival_probability(((1., .95),), None,
        now=0., delivery=.1, display_deadline=1., ancestor_updates=(),
        currently_legal=True, private_delay_includes_delivery=False)
    assert terminal_clock == 0.


def test_released_child_backpropagates_cumulative_service():
    t = row(ready=8., display_expired=True)
    cs = {0: replace(ctx(t), successors=(
        SuccessorObligation(2, 64000, 10., 12., 18., 2., .9),))}
    due = effective_deadlines([t], cs, now=10.05)[0]
    assert due['own_finish_deadline'] == 16.
    assert due['effective_finish_deadline'] == pytest.approx(11.1)
    assert due['inherited_from_windows'] == [2]


def test_shared_full_cut_still_pays_all_released_work():
    ts = [row(0), row(1, candidate_ready=True)]
    cs = {t.sid: ctx(t) for t in ts}
    base = choose(ts, cs, mode='service_cost')
    successor = SuccessorObligation(2, 64000, 0., 2., 8., 2., .4)
    future = choose(ts, {sid: replace(c, successors=(successor,)) for sid, c in cs.items()},
        mode='service_cost')
    assert future['expected_lease_seconds'] > base['expected_lease_seconds']
    assert sum(len(p['sids']) for p in future['plan']) == 2
    assert sum(len(p['sids']) for p in future['symbolic_steps'] if p['prediction_only']) == 2


def test_scenario_budget_has_explicit_approximation_label():
    d = [BatchOutcome(.5, 1., .2, .9, 0., 'a'), BatchOutcome(.5, 3., 1., 2., 0., 'b')]
    draws, label = _draws([d]*6, 16)
    assert len(draws) == 16 and sum(w for _, w in draws) == 1.
    assert 'quadrature' in label
    exact, label = _draws([d]*2, 16)
    assert len(exact) == 4 and 'exact_product' in label


def test_common_prefix_and_inputs_remain_actual_and_immutable():
    ts = [row(0), row(1, candidate_ready=True)]
    cs = {t.sid: ctx(t) for t in ts}
    before = deepcopy((ts, cs))
    a = choose(ts, cs, observed_credit_audio=0., elapsed_seconds=10.)
    b = choose(ts, cs, observed_credit_audio=40., elapsed_seconds=10.)
    assert (ts, cs) == before
    assert b['finite_prefix_goodput'] > a['finite_prefix_goodput']
    assert b['prediction_only_not_authorization']


@pytest.mark.parametrize('field', ['observed_credit_audio', 'elapsed_seconds'])
def test_invalid_actual_prefix_not_allowed(field):
    with pytest.raises(ValueError):
        choose([row()], **{field: math.nan})


def test_no_private_causal_degenerates_to_inheritance():
    ts = [row(0), row(1, candidate_ready=True)]
    cs = {t.sid: ctx(t) for t in ts}
    a = choose(ts, cs, mode='inherit')
    b = choose(ts, cs, mode='causal')
    assert (a['operation'], a['sids'], a['finite_prefix_goodput']) == (
        b['operation'], b['sids'], b['finite_prefix_goodput'])


def test_no_successor_inheritance_degenerates_to_reserved_progress():
    ts = [row(0), row(1, candidate_ready=True)]
    a = choose(ts, mode='inherit')
    b = choose(ts, mode='reserved_progress')
    assert (a['operation'], a['sids'], a['finite_prefix_goodput']) == (
        b['operation'], b['sids'], b['finite_prefix_goodput'])


def test_reserved_progress_does_not_backpropagate_or_promise_symbolic_children():
    t = row(ready=8., display_expired=True)
    child = SuccessorObligation(2, 64000, 10., 12., 18., 2., .9)
    cs = {0: replace(ctx(t), successors=(child,))}
    result = choose([t], cs, now=10.05, mode='reserved_progress')
    assert not result['successor_reward_used']
    assert not result['private_path_prediction_used']
    assert not result['symbolic_service_promises']
    assert result['effective_deadlines'][0]['inherited_from_windows'] == []
    assert result['expected_cut_wall_seconds'] > result['expected_lease_seconds']
