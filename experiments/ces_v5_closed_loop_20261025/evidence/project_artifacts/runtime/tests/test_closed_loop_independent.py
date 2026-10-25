"""Independent closed-loop CPU fixtures, not GPU or SLO performance evidence.

The costs below are explicitly constructed. All deadlines use the real study's
release+2 / release+8 relationship. Neural outputs are never fabricated for a
future Parent; symbolic successors have no executable job identity.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace

import pytest

from revtrace.ces_v5_policy import V5Target, residual_credit
from revtrace.ces_closed_loop import (
    Identity, SuccessorObligation, TargetContext, ClosedLoopState,
    PlannerConfig, choose_closed_loop, _evaluate,
)


def calibration(single=1.2, two=3.0):
    return {
        'global_reject': 0.0, 'causal_reject': {},
        'cost_seconds': {
            'generate': {'1': single, '2': two, '4': two * 2},
            'verify': {'1': .2, '2': .3, '4': .4},
            'fallback': {'1': single, '2': two, '4': two * 2},
            'proposal': {'1': .5, '2': .7, '4': 1.0},
        },
        'v5_risk_model': {
            'schema_version': 1, 'min_bucket_samples': 1,
            'risk_quantile': .9, 'owner_delivery_seconds': .08,
            'generation_scenarios': {'global': [
                {'weight': 1., 'lease_ratio': 1., 'row_fraction': 1.}]},
            'verification_scenarios': {'global': [
                {'weight': 1., 'original_rows': 1, 'failed_count': 0,
                 'verify_ratio': 1., 'fallback_ratio': 1.,
                 'verify_row_fraction': 1., 'fallback_row_fraction': 1.}]},
        },
    }


def target(sid=0, release=2., **changes):
    values = dict(sid=sid, window=1, ready=release, deadline=release+8,
        candidate_ready=False, same_birth=False, previous_reject=False,
        candidate_tokens=32, descendant_count=0, descendant_seconds=0.,
        candidate_eta=None, display_met=False, display_expired=True,
        audio_weight=2.)
    values.update(changes)
    return V5Target(**values)


def context(row, **changes):
    identity = dict(sid=row.sid, epoch=1, parent_version=0,
        parent_digest='actual-parent-'+str(row.sid), frontier_start=0,
        frontier_end=32000*row.window, contract_digest='actual-contract')
    identity.update(changes)
    return TargetContext(Identity(**identity))


def choose(rows, *, now, mode='causal', state=None, contexts=None, cal=None):
    return choose_closed_loop(rows, contexts or {r.sid: context(r) for r in rows},
        now=now, mode=mode, cal=cal or calibration(), limit=16,
        observed_credit_audio=0., elapsed_seconds=max(now, .01),
        state=ClosedLoopState() if state is None else state,
        display_slo=2., config=PlannerConfig(max_deferrals=2, promise_quantile=.9))


def test_real_2s_8s_commit_first_counterexample_is_not_restored():
    a = target(0, release=-6.5, display_expired=True)
    b = target(1, release=-1.5, display_expired=False, candidate_ready=True)
    result = choose([a, b], now=0., cal=calibration(single=1.4, two=4.))
    assert result['operation'] == 'verify'
    assert result['sids'] == [1]
    assert a.deadline == 1.5 and b.ready+2 == .5


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_old_common_cut_suffix_gets_real_service_within_bound(mode):
    old = target(0)
    state = ClosedLoopState()
    decisions = []
    for step in range(8):
        now = 5. + step*1.2
        fresh = target(step+1, release=now, display_expired=False)
        contexts = {r.sid: context(r) for r in (old, fresh)}
        result = choose([old, fresh], now=now, mode=mode, state=state,
                        contexts=contexts)
        decisions.append(result)
        if 0 in result['sids']:
            break
        state.record_dispatch(result, contexts, now=now)
    assert any(0 in r['sids'] for r in decisions), 'old suffix starved in every replan'
    assert len(decisions) <= 4, 'declared two-deferral service bound was not enforced'
    for row in decisions:
        cut = [sid for batch in row['plan'] for sid in batch['sids']]
        assert 0 in cut and len(cut) == len(set(cut))


def test_already_observed_display_retains_commit_credit():
    row = target(0, release=0., display_met=True, display_expired=False)
    assert residual_credit(row, 7.9, 2.) == 2.
    assert residual_credit(row, 8.1, 2.) == 0.
    result = choose([row], now=2.1)
    assert result['sids'] == [0]
    assert result['operation'] == 'generate'


def test_not_ready_candidate_never_becomes_verify_permission():
    row = target(candidate_ready=False, candidate_eta=.001)
    result = choose([row], now=5.)
    assert result['operation'] == 'generate' and result['wait_seconds'] == 0


@pytest.mark.parametrize('changes', [
    {'ready': float('nan')}, {'deadline': float('nan')},
    {'deadline': float('inf')}, {'audio_weight': float('nan')},
    {'audio_weight': -1.}, {'candidate_eta': float('inf')},
])
def test_invalid_current_accounting_inputs_fail_closed(changes):
    with pytest.raises(ValueError):
        choose([target(**changes)], now=5.)


@pytest.mark.parametrize('changes', [
    {'audio_weight': -1.}, {'audio_weight': float('nan')},
    {'remaining_service_s': -1.}, {'private_ready_delay_s': float('nan')},
])
def test_invalid_symbolic_accounting_inputs_fail_closed(changes):
    parent = target(0, release=8., display_expired=True)
    values = dict(window=2, frontier_end=64000, release=10.,
        display_deadline=12., commit_deadline=18., audio_weight=2.,
        remaining_service_s=.5)
    values.update(changes)
    ctx = replace(context(parent), successors=(SuccessorObligation(**values),))
    with pytest.raises(ValueError):
        choose([parent], now=10.05, contexts={0: ctx})


def test_birth_mismatch_is_not_hard_rejection_of_legal_verification():
    row = target(candidate_ready=True, same_birth=False, display_met=True,
                 display_expired=False)
    result = choose([row], now=5.)
    assert result['operation'] == 'verify'


def test_polling_without_actual_dispatch_cannot_create_deferrals():
    rows = [target(0), target(1, release=5., display_expired=False)]
    state = ClosedLoopState()
    decisions = [choose(rows, now=5., state=state) for _ in range(6)]
    assert all(d['sids'] == decisions[0]['sids'] for d in decisions)
    assert all(record.deferrals == 0 for record in state.records.values())


@pytest.mark.parametrize('change', [
    {'epoch': 2}, {'parent_version': 1}, {'parent_digest': 'new-parent'},
    {'frontier_start': 32000, 'frontier_end': 64000},
    {'contract_digest': 'new-contract'},
])
def test_changed_actual_identity_does_not_inherit_old_service_debt(change):
    rows = [target(0), target(1, release=5., display_expired=False)]
    contexts = {r.sid: context(r) for r in rows}
    old_identity = contexts[0].identity
    state = ClosedLoopState()
    first = choose(rows, now=5., state=state, contexts=contexts)
    state.record_dispatch(first, contexts, now=5.)
    contexts[0] = context(rows[0], **change)
    choose(rows, now=5.1, state=state, contexts=contexts)
    assert old_identity not in state.records
    record = state.records.get(contexts[0].identity)
    assert record is None or record.deferrals == 0


def test_explicit_restart_scope_resets_only_scheduling_obligations():
    rows = [target(0), target(1, release=5., display_expired=False)]
    contexts = {r.sid: context(r) for r in rows}
    state = ClosedLoopState()
    result = choose(rows, now=5., state=state, contexts=contexts)
    state.record_dispatch(result, contexts, now=5.)
    assert state.records
    state.reset(scope='independent-cpu-restart-test')
    assert not state.records
    # Reset never manufactures a success or changes trusted execution inputs.
    assert rows[0] == target(0)


def test_infeasible_old_promise_is_reported_without_dropping_work():
    row = target(0)
    contexts = {0: context(row)}
    state = ClosedLoopState()
    state.observe(contexts, 0.)
    key = contexts[0].identity
    state.records[key].promised_finish = 1.
    result = choose([row], now=5., state=state, contexts=contexts)
    assert result['sids'] == [0] and result['common_cut_sids'] == [0]
    assert result['promise_violation_mass'] > 0.
    state.record_dispatch(result, contexts, now=5.)
    assert state.records[key].promise_breaches == 1
    assert state.records[key].promised_finish == 1.
    retired = state.admitted(0, epoch=key.epoch, frontier=key.frontier_end, now=6.3)
    assert len(retired) == 1 and retired[0]['actual_promise_late']
    assert retired[0]['actual_install_time'] == 6.3
    assert key not in state.records


def test_new_session_cannot_take_old_session_service_debt():
    rows = [target(0), target(1, release=5., display_expired=False)]
    contexts = {r.sid: context(r) for r in rows}
    old_identity = contexts[0].identity
    state = ClosedLoopState()
    first = choose(rows, now=5., state=state, contexts=contexts)
    state.record_dispatch(first, contexts, now=5.)
    replacement = target(2)
    new_contexts = {2: context(replacement), 1: contexts[1]}
    choose([replacement, rows[1]], now=5.1, state=state, contexts=new_contexts)
    record = state.records.get(new_contexts[2].identity)
    assert record is None or record.deferrals == 0
    assert record is None or record.promised_finish is None
    # A missing eligible Session may still be in-flight; only actual admission
    # or its own new identity retires its debt. It must not move to sid=2.
    assert old_identity in state.records


def test_temporary_absence_from_ready_list_does_not_erase_owed_service():
    rows = [target(0), target(1, release=5., display_expired=False)]
    contexts = {r.sid: context(r) for r in rows}
    state = ClosedLoopState()
    first = choose(rows, now=5., state=state, contexts=contexts)
    state.record_dispatch(first, contexts, now=5.)
    key = contexts[0].identity
    prior = deepcopy(state.records[key])
    state.observe({1: contexts[1]}, now=5.1)
    assert state.records[key] == prior
    state.admitted(0, epoch=key.epoch, frontier=key.frontier_end)
    assert key not in state.records


def test_expired_parent_with_released_symbolic_successor_is_legal_input():
    parent = target(0, release=8., display_expired=True)
    child = SuccessorObligation(window=2, frontier_end=64000, release=10.,
        display_deadline=12., commit_deadline=18., audio_weight=2.,
        remaining_service_s=.5)
    ctx = replace(context(parent), successors=(child,))
    result = choose([parent], now=10.05, contexts={0: ctx})
    assert result['sids'] == [0]
    assert all(sid == 0 for batch in result['plan'] for sid in batch['sids'])
    assert not hasattr(child, 'prompt_tokens') and not hasattr(child, 'token_ids')
    assert not hasattr(child, 'certificate') and not hasattr(child, 'job_id')


def test_released_successor_value_changes_real_first_parent_batch():
    a = target(0, release=2., display_expired=True)
    c = target(1, release=2., display_expired=True)
    e = target(2, release=3.5, display_expired=False, candidate_ready=True)
    contexts = {t.sid: context(t) for t in (a, c, e)}
    for row in (a, c):
        child = SuccessorObligation(window=2, frontier_end=64000, release=4.,
            display_deadline=6., commit_deadline=12., audio_weight=2.,
            remaining_service_s=.8)
        contexts[row.sid] = replace(contexts[row.sid], successors=(child,))
    cal = calibration(single=.8, two=.8)
    cal['cost_seconds']['generate']['3'] = 2.2
    cal['cost_seconds']['verify']['1'] = .6
    result = choose([a, c, e], now=4.05, mode='inherit', contexts=contexts, cal=cal)
    assert result['operation'] == 'generate'
    assert set(result['sids']) == {0, 1}
    assert result['expected_successor_credit_audio'] == 4.
    assert result['effective_deadlines'][0]['inherited_from_windows'] == [2]
    # The first operation contains current actual targets only, not their
    # valuable but still unknown-Parent children.
    assert len(result['sids']) == 2 and set(result['sids']) <= {0, 1, 2}


def test_unreleased_successor_fails_closed_without_changing_context():
    parent = target(0, release=8., display_expired=True)
    child = SuccessorObligation(window=2, frontier_end=64000, release=10.051,
        display_deadline=12.051, commit_deadline=18.051, audio_weight=2.,
        remaining_service_s=.5)
    ctx = replace(context(parent), successors=(child,))
    before = deepcopy(ctx)
    with pytest.raises(ValueError):
        choose([parent], now=10.05, contexts={0: ctx})
    assert ctx == before


def test_identity_and_symbolic_obligations_are_immutable():
    row = target()
    identity = context(row).identity
    with pytest.raises(FrozenInstanceError):
        identity.parent_version = 77
    child = SuccessorObligation(window=2, frontier_end=64000, release=4.,
        display_deadline=6., commit_deadline=12., audio_weight=2.,
        remaining_service_s=.5)
    with pytest.raises(FrozenInstanceError):
        child.frontier_end = 999999


def test_planning_does_not_mutate_actual_targets_or_calibration():
    rows = [target(0), target(1, release=5., display_expired=False)]
    contexts = {r.sid: context(r) for r in rows}
    cal = calibration()
    original = deepcopy((rows, contexts, cal))
    choose(rows, now=5., contexts=contexts, cal=cal)
    assert (rows, contexts, cal) == original


def evaluate_one(plan, contexts, now, cal, state=None):
    state = ClosedLoopState() if state is None else state
    state.observe(contexts, now)
    return _evaluate(plan, contexts, now=now, mode='causal', cal=cal,
        display_slo=2., observed_credit_audio=0., elapsed_seconds=1.,
        state=state, config=PlannerConfig(), interleave=False, cache={})


def test_two_gpu_parallel_paths_use_min_display_and_max_wall_not_sum():
    row = target(release=0., display_expired=False)
    ctx = replace(context(row), private_ready_delay_s=.5,
        direct_private_probability=1., fallback_private_probability=1.,
        private_path_currently_legal=True)
    metrics = evaluate_one((('generate', (row,)),), {row.sid: ctx}, 0.,
                           calibration(single=3.))
    assert metrics['expected_credit_audio'] == 2.
    assert metrics['expected_private_additional_credit_audio'] == 2.
    assert metrics['expected_cut_wall_seconds'] == pytest.approx(3.08)
    assert metrics['expected_lease_seconds'] == pytest.approx(3.)


def test_private_and_canonical_both_on_time_cannot_double_count_audio():
    row = target(release=0., display_expired=False)
    ctx = replace(context(row), private_ready_delay_s=.1,
        direct_private_probability=1., fallback_private_probability=1.,
        private_path_currently_legal=True)
    metrics = evaluate_one((('generate', (row,)),), {row.sid: ctx}, 0.,
                           calibration(single=.2))
    assert metrics['expected_credit_audio'] == 2.
    assert metrics['expected_private_additional_credit_audio'] == 0.


def test_private_cdf_integrates_deadline_probability_not_average_completion():
    row = target(release=0., display_expired=False)
    ctx = replace(context(row), private_ready_delay_s=1.55,
        private_delay_distribution=((.5, .1), (.5, 3.)),
        private_path_currently_legal=True)
    metrics = evaluate_one((('generate', (row,)),), {row.sid: ctx}, 0.,
                           calibration(single=3.))
    # Mean remaining time 1.55s is before D=2, but only half the modeled rows
    # actually finish before D. A mean-before-deadline shortcut would earn 2.
    assert metrics['expected_credit_audio'] == 1.
    assert metrics['expected_private_additional_credit_audio'] == 1.


def test_unproven_current_private_path_is_not_a_display_shortcut():
    row = target(release=0., display_expired=False)
    ctx = replace(context(row), private_ready_delay_s=.1,
        direct_private_probability=1., fallback_private_probability=1.,
        private_path_currently_legal=False)
    metrics = evaluate_one((('generate', (row,)),), {row.sid: ctx}, 0.,
                           calibration(single=3.))
    assert metrics['expected_credit_audio'] == 0.


def test_root_verify_equality_does_not_survive_unknown_generated_grandparent():
    row = target(release=0., candidate_ready=True, display_expired=True)
    first = SuccessorObligation(window=2, frontier_end=64000, release=2.,
        display_deadline=4., commit_deadline=10., audio_weight=2.,
        remaining_service_s=3., private_ready_delay_s=.1,
        verify_private_compatible=True, unknown_private_probability=0.)
    second = SuccessorObligation(window=3, frontier_end=96000, release=4.,
        display_deadline=6., commit_deadline=12., audio_weight=2.,
        remaining_service_s=3., private_ready_delay_s=.1,
        verify_private_compatible=True, unknown_private_probability=0.)
    ctx = replace(context(row), successors=(first, second),
        direct_private_probability=0., fallback_private_probability=0.)
    cal = calibration(single=3.)
    cal['v5_risk_model']['generation_scenarios']['global'][0]['row_fraction'] = .1
    metrics = evaluate_one((('verify', (row,)),), {row.sid: ctx}, 4.05, cal)
    # The root Verify could select a known P, but the first future Generation
    # makes the second child's Parent unknown again. Its old Private branch is
    # not silently granted the root's compatibility witness.
    assert metrics['expected_private_additional_credit_audio'] == 0.


def test_uncalibrated_direct_parent_is_unknown_not_false_with_verify_bonus():
    row = target(release=0., candidate_ready=True, display_expired=False)
    ctx = replace(context(row), private_ready_delay_s=.1,
        verify_private_compatible=True, direct_private_probability=None,
        fallback_private_probability=None)
    result = evaluate_one((('verify', (row,)),), {row.sid: ctx}, 0.,
                          calibration(single=3.))
    assert not result['conditional_private_prediction_enabled']
    assert result['expected_private_additional_credit_audio'] == 0.
    assert ctx.direct_private_probability is None


def test_no_private_forecast_causal_reduces_to_inherited_plan():
    rows = [target(0), target(1, release=5., display_expired=False)]
    inherited = choose(rows, now=5., mode='inherit')
    causal = choose(rows, now=5., mode='causal')
    for key in ('operation', 'sids', 'plan', 'expected_credit_audio',
                'finite_prefix_goodput', 'expected_cut_wall_seconds'):
        assert causal[key] == inherited[key]


def test_finite_prefix_ratio_contains_observed_credit_and_elapsed_wall():
    row = target(release=0., display_met=True, display_expired=False)
    contexts = {row.sid: context(row)}
    state = ClosedLoopState()
    state.observe(contexts, 0.)
    metrics = _evaluate((('generate', (row,)),), contexts, now=0.,
        mode='causal', cal=calibration(single=3.), display_slo=2.,
        observed_credit_audio=100., elapsed_seconds=10., state=state,
        config=PlannerConfig(), interleave=False, cache={})
    assert metrics['finite_prefix_goodput'] == pytest.approx(102./13.08)
    assert metrics['finite_prefix_goodput'] != pytest.approx(2./3.08)


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_actual_ack_d1_wal_and_resume(mode, tmp_path):
    from test_ces_v5_integration import v5_owner
    path = tmp_path/'closed-history.wal'
    owner = v5_owner(mode, path)
    result = owner.run()
    assert result['certified_commits'] == 6
    assert result['fine_window_accounting_complete']
    assert owner.ack_counts['accepted'] > 0
    assert all(e['certificate_consumed'] for e in owner.events
               if e['kind'] == 'commit')
    assert not owner.inflight
    owner.close()
    resumed = v5_owner(mode, path)
    assert all(s.done for s in resumed.sessions.values())
    assert not resumed.jobs
    assert resumed.run()['certified_commits'] == 0
    resumed.close()


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_stale_parent_never_installs(mode):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode)
    owner.clock.sleep(2.1)
    owner._dispatch()
    owner.clock.sleep(.01)
    worker = owner.executors['authority'][0]
    original = worker.poll

    def wrong_parent():
        rows = original()
        for row in rows or []:
            owner.jobs[row['job_id']]['parent'] = -1
        return rows

    worker.poll = wrong_parent
    try:
        with pytest.raises(AssertionError, match='stale result'):
            owner._receive()
        assert all(s.state.checkpoint_id == 0 for s in owner.sessions.values())
    finally:
        owner.close()


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_failed_group_wal_does_not_publish_success(mode, tmp_path):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode, tmp_path/'failed-closed.wal')

    def fail(_frame):
        raise OSError('independent injected fsync failure')

    owner._journal._write_frame = fail
    try:
        with pytest.raises(OSError, match='injected fsync failure'):
            owner.run()
        assert not any(e['kind'] == 'commit' for e in owner.events)
        assert all(s.state.checkpoint_id == 0 for s in owner.sessions.values())
    finally:
        owner.close()


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_service_debt_tracks_dispatch_then_actual_wal_install(mode, tmp_path):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode, tmp_path/'dispatch-install.wal')
    owner.clock.sleep(2.1)
    owner._dispatch()
    assert owner.closed_state.dispatches == 1
    assert len([e for e in owner.events if e['kind'] == 'closed-loop-service-dispatch']) == 1
    owner._dispatch()  # Both physical Workers still busy: no new actual enqueue.
    assert owner.closed_state.dispatches == 1
    assert owner.closed_state.records
    owner.clock.sleep(.01)
    owner._receive()
    assert owner.closed_state.records  # Row arrival is not durable installation.
    assert not any(e['kind'] == 'closed-loop-service-retired' for e in owner.events)
    owner._commit_ready()
    retired = [e for e in owner.events if e['kind'] == 'closed-loop-service-retired']
    assert retired and all(e['actual_durable_install_observed'] for e in retired)
    assert not owner.closed_state.records
    for event in retired:
        assert all(item['actual_install_time'] == event['installed_perf']
                   for item in event['retired'])
    owner.close()


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_submit_rejected_before_issue_cannot_age_service(mode):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode)

    def reject_before_issue(_jobs):
        raise RuntimeError('CPU fake worker rejected before issue')

    owner.executors['authority'][0].submit = reject_before_issue
    owner.clock.sleep(2.1)
    with pytest.raises(RuntimeError, match='rejected before issue'):
        owner._dispatch()
    assert owner.closed_state.dispatches == 0
    assert all(record.deferrals == 0 for record in owner.closed_state.records.values())
    assert not any(e['kind'] == 'closed-loop-service-dispatch' for e in owner.events)
    assert not any(e['kind'] == 'commit' for e in owner.events)
    owner.close()


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_closed_owner_valid_group_prefix_and_torn_tail_resume(mode, tmp_path):
    """CPU truncation fixture, not SIGKILL, power loss or GPU recovery evidence."""
    import json
    import struct
    from test_ces_v5_integration import v5_owner

    path = tmp_path/'partial-group.wal'
    owner = v5_owner(mode, path)
    owner.clock.sleep(2.1)  # Both original, unchanged audio releases are ready.
    owner.run()
    commits = [e for e in owner.events if e['kind'] == 'commit']
    assert commits[0]['journal_group_size'] == 2
    owner.close()

    raw = path.read_bytes()
    cursor = 0
    retained_end = None
    while cursor < len(raw):
        n = struct.unpack('>I', raw[cursor:cursor+4])[0]
        record = json.loads(raw[cursor+4:cursor+4+n])
        frame_end = cursor+4+n+32
        if record['sequence'] == 1:
            retained_end = frame_end
            break
        cursor = frame_end
    assert retained_end is not None
    # Retain one complete valid transition from the group and an incomplete
    # second frame. This models the declared recoverable per-transition prefix,
    # not an all-or-nothing transaction across Sessions.
    path.write_bytes(raw[:retained_end+8])
    resumed = v5_owner(mode, path)
    assert sorted(s.state.checkpoint_id for s in resumed.sessions.values()) == [0, 1]
    assert resumed._journal.truncated_tail_bytes == 8
    result = resumed.run()
    assert result['certified_commits'] == 5
    assert all(s.state.checkpoint_id == 3 for s in resumed.sessions.values())
    resumed.close()


def test_closed_owner_shadow_planning_does_not_create_future_jobs_or_wal(tmp_path):
    from test_ces_v5_integration import v5_owner
    path = tmp_path/'shadow-purity.wal'
    owner = v5_owner('causal', path)
    owner.clock.sleep(2.1)
    owner._dispatch()
    owner.clock.sleep(.01)
    owner._receive()  # Real CPU fixture receipts, but no Canonical install yet.
    owner.clock.sleep(4.)
    owner._drain_consumer_acks(owner.clock())
    features = [owner._features(s, owner.clock()) for s in owner.sessions.values()]
    before_sessions = deepcopy({sid: vars(s) for sid, s in owner.sessions.items()})
    before_jobs = deepcopy(owner.jobs)
    before_results = deepcopy(owner._proposal_results)
    before_wal = path.read_bytes()
    first = owner._closed_build_contexts(features, owner.clock())
    second = owner._closed_build_contexts(features, owner.clock())
    assert first == second
    assert all(len(c.successors) == 2 for c in first.values())
    assert {sid: vars(s) for sid, s in owner.sessions.items()} == before_sessions
    assert owner.jobs == before_jobs and owner._proposal_results == before_results
    assert path.read_bytes() == before_wal
    assert all(c.identity.frontier_end == 32000 for c in first.values())
    assert not any(e['kind'] == 'commit' for e in owner.events)
    owner.close()


def test_retained_frozen_private_edge_may_name_older_birth_and_audio_root():
    from test_ces_v5_integration import v5_owner
    from revtrace.continuity_proof import eligible_chain
    owner = v5_owner('causal')
    s = owner.sessions[0]
    s.state = replace(s.state, checkpoint_id=1, prompt_tokens=(7,),
                      audio_frontier_window=32000)
    s.segment_start = s.segment_end = s.branch_chunk = 1
    s.branch_parent = 1
    s.branch_root_frontier = 32000
    s.branch_root_tokens = s.branch_tokens = (7,)
    s.fine_window = 2
    s.fine_busy = True
    boundary = dict(job_id='private-boundary', role='proposal', session_id=0,
        parent=0, branch_generation=s.branch_generation, chunk_id=0,
        prompt_tokens=[], audio_start_sample=0, audio_end_sample=32000,
        end_window=1)
    pending = dict(job_id='private-pending', role='proposal', session_id=0,
        parent=0, branch_generation=s.branch_generation, chunk_id=1,
        prompt_tokens=[7], audio_start_sample=0, audio_end_sample=64000,
        end_window=2)
    owner.jobs.update({boundary['job_id']: boundary, pending['job_id']: pending})
    owner._proposal_results[0, 1] = dict(job_id=boundary['job_id'], state_tokens=[7])
    assert eligible_chain(s, owner.jobs, owner._proposal_results)[0]
    # A legitimate retained edge keeps its immutable original birth metadata;
    # it must not be rewritten to claim it was generated under a newer Parent.
    assert pending['parent'] < s.state.checkpoint_id
    assert pending['audio_start_sample'] < s.branch_root_frontier
    assert owner._private_branch_currently_legal(s, pending)
    pending['prompt_tokens'] = [8]
    assert not owner._private_branch_currently_legal(s, pending)
    owner.close()


def test_cached_completed_private_node_is_not_future_publication():
    from test_ces_v5_integration import v5_owner
    owner = v5_owner('causal')
    s = owner.sessions[0]
    node = dict(job_id='completed-old-private', role='proposal', session_id=0,
        parent=0, branch_generation=s.branch_generation, chunk_id=0,
        prompt_tokens=[], audio_start_sample=0, audio_end_sample=64000,
        end_window=2)
    owner.jobs[node['job_id']] = node
    owner._proposal_results[0, 2] = dict(job_id=node['job_id'], state_tokens=[7])
    owner._row_completed.add(node['job_id'])
    distribution, pending, legal, audit = owner._pending_private_distribution(s, 64000,
                                                                           owner.clock())
    assert distribution == () and pending is None and not legal
    assert audit['status'] == 'no-uncompleted-frozen-private-job'
    assert not owner.inflight
    owner.close()


def profile_bucket(fraction, rows=8, batches=8):
    return {'support': rows, 'physical_batches': batches,
            'fractions': [fraction]*rows}


@pytest.mark.parametrize('audio_rows,audio_batches,n_rows,n_batches,expected,value', [
    (8, 8, 8, 8, '2/0-8', .25),
    (7, 8, 8, 8, '2', .5),
    (8, 7, 8, 8, '2', .5),
    (7, 7, 8, 7, 'global', .9),
    (7, 7, 7, 8, 'global', .9),
])
def test_supported_audio_n_global_backoff_uses_both_sample_units(
        audio_rows, audio_batches, n_rows, n_batches, expected, value):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner('causal')
    owner.cal['closed_loop_profiles'] = {'proposal': {
        'row_fraction_by_n': {'2': profile_bucket(.5, n_rows, n_batches),
                              'global': profile_bucket(.9)},
        'row_fraction_by_n_audio': {'2': {'0-8': profile_bucket(.25, audio_rows,
                                                             audio_batches)}}}}
    fractions, label = owner._proposal_fractions(2, 8.)
    assert label == expected and set(fractions) == {value}
    # A neighbouring n bucket is not a same-shape observation.
    fractions, label = owner._proposal_fractions(3, 8.)
    assert label == 'global' and set(fractions) == {.9}
    owner.close()


def pending_owner_with_fractions(fractions):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner('causal')
    owner.cal['cost_seconds']['proposal'] = {'1': 1., '2': 1.}
    owner.cal.setdefault('v5_risk_model', {})['owner_delivery_seconds'] = .08
    owner.cal['closed_loop_profiles'] = {'proposal': {'row_fraction_by_n': {
        '2': {'support': len(fractions), 'physical_batches': 8,
              'fractions': list(fractions)}}}}
    owner.clock.sleep(2.1)
    owner._dispatch()
    return owner


def test_private_remaining_clock_uses_observed_start_not_enqueue():
    owner = pending_owner_with_fractions([.1]*3+[.5]*3+[1.]*3)
    owner.clock.sleep(.2)
    s = owner.sessions[0]
    dist, pending, legal, audit = owner._pending_private_distribution(s, 32000,
                                                                      owner.clock())
    assert audit['age_clock'] == 'start-not-yet-observed-age-zero'
    assert audit['actual_lease_age_s'] == 0.
    assert audit['private_delay_includes_delivery']
    assert max(delay for _, delay in dist) == pytest.approx(1.08)
    # A real worker-start observation arrives after the enqueue clock.
    ids = owner.inflight['p'][1]
    owner._event('worker-status', worker='p', status='batch-started',
                 job_ids=ids, started_perf=owner.clock()-.1)
    dist, pending, legal, audit = owner._pending_private_distribution(s, 32000,
                                                                      owner.clock())
    assert audit['age_clock'] == 'observed-worker-start'
    assert audit['actual_lease_age_s'] == pytest.approx(.1)
    # The .1 terminal component can already have ended, yet its Consumer
    # delivery has not happened. Do not drop it by conditioning on EOS time.
    assert audit['survival_conditioned_samples'] == 9
    assert min(delay for _, delay in dist) == pytest.approx(.08)
    owner.close()


@pytest.mark.parametrize('samples', [33, 64, 100, 101, 1000])
def test_upper_endpoint_private_cdf_retains_mass_with_declared_bound(samples):
    fractions = [(i+1)/samples for i in range(samples)]
    owner = pending_owner_with_fractions(fractions)
    dist, pending, legal, audit = owner._pending_private_distribution(owner.sessions[0],
        32000, owner.clock())
    assert len(dist) <= 32
    assert sum(weight for weight, _ in dist) == pytest.approx(1.)
    width = __import__('math').ceil(samples/32)
    bound = (width-1)/samples
    assert audit['CDF_one_sided_error_bound'] == pytest.approx(bound)
    raw = [f+.08 for f in fractions]
    for threshold in raw:
        actual_cdf = sum(value <= threshold for value in raw)/samples
        compressed_cdf = sum(weight for weight, delay in dist if delay <= threshold)
        assert compressed_cdf <= actual_cdf+1e-12
        assert actual_cdf-compressed_cdf <= bound+1e-12
    owner.close()


def test_consumer_remaining_delay_included_exactly_once_in_full_score():
    row = target(release=0., display_expired=False)
    ctx = replace(context(row), private_delay_distribution=((1., .95),),
        private_path_currently_legal=True, private_delay_includes_delivery=True)
    cal = calibration(single=3.)
    cal['v5_risk_model']['owner_delivery_seconds'] = .1
    included = evaluate_one((('generate', (row,)),), {0: ctx}, 1., cal)
    terminal = evaluate_one((('generate', (row,)),),
        {0: replace(ctx, private_delay_includes_delivery=False)}, 1., cal)
    assert included['expected_credit_audio'] == 2.
    assert terminal['expected_credit_audio'] == 0.


def test_successor_root_rates_are_explicit_and_not_inherited_through_generation():
    from test_ces_v5_integration import v5_owner
    owner = v5_owner('causal')
    owner.clock.sleep(6.1)
    features = [owner._features(s, owner.clock()) for s in owner.sessions.values()]
    owner._conditional_chain = lambda _s, _end: (True, True, {'status': 'CPU-known-chain'})
    owner._unknown_retention = lambda _s, mode, _structural: (
        (.8 if mode == 'direct' else .2), {'status': 'CPU-declared-distinct-rates'})
    contexts = owner._closed_build_contexts(features, owner.clock())
    for ctx in contexts.values():
        first, second = ctx.successors
        assert (first.direct_private_probability, first.fallback_private_probability) == (.8, .2)
        assert first.inherit_current_transition_model
        assert first.verify_private_compatible is True
        assert second.direct_private_probability is None
        assert second.fallback_private_probability is None
        assert second.verify_private_compatible is None
        assert not second.inherit_current_transition_model
    owner.close()


@pytest.mark.parametrize('mode', ['fine', 'standard', 'cost', 'service_cost', 'causal'])
def test_all_methods_can_price_full_proposer_cut_including_unselected_suffix(mode):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode)
    owner.ces['proposer_policy'] = 'shared_progress'
    owner.cal['cost_seconds']['proposal'] = {'1': .2, '2': .7}
    owner.clock.sleep(2.1)
    ready = list(owner.sessions.values())
    owner._closed_proposal_selection(ready, owner.clock())
    event = [e for e in owner.events if e['kind'] == 'closed-loop-proposer-choice'][-1]
    assert set(event['common_cut_sids']) == {0, 1}
    for candidate in event['candidates']:
        paid = candidate['paid_plan']
        assert sorted(sid for batch in paid for sid in batch['sids']) == [0, 1]
        assert candidate['lease'] == pytest.approx(sum(batch['lease_s'] for batch in paid))
        if len(candidate['sids']) == 1:
            assert candidate['lease'] == pytest.approx(.4), 'the second .2s batch is not free'
    assert not event['authority_occupied_lease_observed']
    assert event['predicted_evidence_value'] == 0.
    owner.close()


@pytest.mark.parametrize('mode', ['cost', 'service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_candidate_value_requires_actual_busy_authority_and_unissued_target(mode):
    from test_ces_v5_integration import v5_owner
    owner = v5_owner(mode)
    owner.ces['proposer_policy'] = 'causal_joint'
    owner.cal['global_reject'] = 0.
    for op, value in [('generate', 1.), ('verify', .1), ('fallback', 1.), ('proposal', .1)]:
        owner.cal['cost_seconds'][op] = {'1': value, '2': value}
    owner.cal['closed_loop_profiles'] = {'proposal': {
        'median_generated_tokens_by_audio_bin': {'0-8': {'median_generated_tokens': 16.}}}}
    owner._closed_credit['constructed-prior-audio'] = 2.
    owner.clock.sleep(2.1)
    target_session = owner.sessions[1]
    owner._closed_proposal_selection([target_session], owner.clock())
    event = [e for e in owner.events if e['kind'] == 'closed-loop-proposer-choice'][-1]
    assert event['predicted_evidence_value'] == 0.
    assert not event['authority_occupied_lease_observed']

    # Actual CPU fake-worker submit creates a real tracked lease for another
    # Session, not a hypothetical wait added to make candidates valuable.
    busy_session = owner.sessions[0]
    owner.selected[0] = 'generate'
    job = owner._make_job(busy_session, 'authority')
    worker = owner.executors['authority'][0]
    worker.submit([job])
    owner.inflight[worker.name] = (worker, [job['job_id']])
    busy_session.auth_busy = True
    owner._closed_proposal_selection([target_session], owner.clock())
    event = [e for e in owner.events if e['kind'] == 'closed-loop-proposer-choice'][-1]
    assert event['authority_occupied_lease_observed']
    assert event['predicted_evidence_value'] > 0.
    assert len(owner.jobs) == 1, 'forecast cannot build a future candidate job'
    target_session.auth_busy = True
    owner._closed_proposal_selection([target_session], owner.clock())
    event = [e for e in owner.events if e['kind'] == 'closed-loop-proposer-choice'][-1]
    assert event['predicted_evidence_value'] == 0.
    owner.close()


@pytest.mark.parametrize('mode', ['fine', 'standard', 'cost'])
def test_shared_baseline_accumulates_real_committed_ack_credit_without_service_book(
        mode, monkeypatch, tmp_path):
    import test_ces_v5_integration as fixtures
    constructor = fixtures.CESScheduler

    def freeze_shared_capability_before_owner_init(**kwargs):
        kwargs['contract']['ces_study']['proposer_policy'] = 'causal_joint'
        return constructor(**kwargs)

    # Freeze the actual capability into the CPU fixture contract before owner
    # initialization/WAL genesis; do not mutate a running declared contract.
    with monkeypatch.context() as patch:
        patch.setattr(fixtures, 'CESScheduler', freeze_shared_capability_before_owner_init)
        owner = fixtures.v5_owner(mode, tmp_path/'baseline-observed-credit.wal')
    result = owner.run()
    commits = [e for e in owner.events if e['kind'] == 'commit']
    assert result['certified_commits'] == 6 and len(commits) == 6
    expected = 0.
    for event in commits:
        job = owner.jobs[event['job_id']]
        key = job['session_id'], job['end_window']
        observed = owner._first_visible.get(key)
        installed = owner.t0+event['installed']
        if (observed is not None and observed <= job['audio_ready_perf']+2.
                and installed <= job['audio_ready_perf']+8.):
            expected += (job['audio_end_sample']-job['audio_start_sample'])/owner.sample_rate
    assert expected > 0.
    assert len(owner._closed_committed) == 6
    assert owner._closed_observed_credit() == pytest.approx(expected)
    assert not owner.closed_state.records
    assert owner.closed_state.dispatches == 0
    assert not any(e['kind'] in ('closed-loop-service-retired',
                                 'closed-loop-service-dispatch') for e in owner.events)
    owner.close()
