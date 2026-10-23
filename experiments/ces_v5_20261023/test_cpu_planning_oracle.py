"""Counterexamples compare complete finite models, never mixed GPU traces."""
import itertools

import pytest

from cpu_planning_oracle import Work, Action, solve, counterexamples


def test_split_generation_exposes_current_action_search_gap():
    example = counterexamples()['generation_split']
    assert example['single_batch']['new_credit_audio'] == 2
    assert example['full_action_set']['new_credit_audio'] == 4
    assert example['full_action_set']['new_wall_seconds'] == pytest.approx(.4)
    assert [s['tasks'] for s in example['full_action_set']['steps']] == [[0], [1]]


def test_split_verification_can_improve_urgent_row_without_free_gpu_time():
    example = counterexamples()['verification_split']
    assert example['single_batch']['new_credit_audio'] == 2
    assert example['full_action_set']['new_credit_audio'] == 4
    assert example['full_action_set']['new_wall_seconds'] == pytest.approx(.7)
    assert example['full_action_set']['steps'][1]['start'] == pytest.approx(.1)


def test_commit_first_is_not_equivalent_to_dual_deadline_goodput():
    example = counterexamples()['commit_priority']
    assert example['commit_first']['new_credit_audio'] == 0
    assert example['commit_first']['commit_late_audio'] == 0
    assert example['goodput_first']['new_credit_audio'] == 2
    assert example['goodput_first']['commit_late_audio'] == 2


def test_commit_priority_counterexample_matches_fixed_2s_8s_contract():
    # Actual 2/8-second deadlines from release=-6.5 and release=-1.5.
    a = Work(0, -4.5, 1.5, display_expired=True)
    b = Work(1, .5, 6.5, candidate_ready=True)
    actions = [Action('generate', (0,), 1.4, (1.4,)),
               Action('verify', (1,), .2, (.2,))]
    old_rule = solve([a, b], actions, objective='commit_first')
    corrected_objective = solve([a, b], actions, objective='goodput')
    assert old_rule['steps'][0]['tasks'] == [0]
    assert old_rule['new_credit_audio'] == 0
    assert corrected_objective['steps'][0]['tasks'] == [1]
    assert corrected_objective['new_credit_audio'] == 2


def test_parent_unlock_complementarity_requires_zero_credit_work():
    example = counterexamples()['parent_unlock']
    assert example['new_credit_audio'] == 4
    assert [s['tasks'] for s in example['steps']] == [[0, 2], [1, 3], [4]]
    assert example['new_wall_seconds'] == pytest.approx(2.2)
    # Immediate-positive-credit greedy starts E, earns 2, then loses B and D.
    greedy_finish = {4: .6, 0: 1.4, 2: 1.4, 1: 2.2, 3: 2.2}
    assert sum(2 for i, deadline in ((1, 1.9), (3, 1.9), (4, .6))
               if greedy_finish[i] <= deadline) == 2


def test_prefix_ratio_and_expectation_ratio_choose_different_plans():
    data = counterexamples()
    prefix = data['prefix_ratio_counterexample']
    assert prefix['A_local_rate'] > prefix['B_local_rate']
    assert prefix['A_completed_rate'] < prefix['B_completed_rate']
    expectation = data['ratio_of_expectations_counterexample']
    assert expectation['A_Ecredit_over_Ewall'] < expectation['B_both_objectives']
    assert expectation['A_Ecredit_over_wall'] > expectation['B_both_objectives']


def test_pareto_matches_full_enumeration_on_fixed_small_model():
    tasks = [Work(i, .4 + .1 * i, 1.0 + .2 * i, candidate_ready=i % 2 == 0)
             for i in range(5)]
    actions = []
    for k in range(1, 4):
        for ids in itertools.combinations(range(5), k):
            g = .12 + .07 * k
            actions.append(Action('generate', ids, g, tuple(g for _ in ids)))
            if all(tasks[i].candidate_ready for i in ids):
                v = .05 + .03 * k
                actions.append(Action('verify', ids, v, tuple(v for _ in ids)))
    for objective in ('goodput', 'commit_first'):
        pruned = solve(tasks, actions, objective=objective, pareto=True)
        unpruned = solve(tasks, actions, objective=objective, pareto=False)
        assert pruned['finite_run_rate'] == unpruned['finite_run_rate']
        assert pruned['commit_late_audio'] == unpruned['commit_late_audio']
        assert pruned['candidate_transitions_evaluated'] < unpruned['candidate_transitions_evaluated']


def test_lease_remains_occupied_after_early_row_return():
    tasks = [Work(0, 1, 8, display_met=True), Work(1, .4, 8)]
    actions = [Action('generate', (0,), 1.0, (.1,)),
               Action('generate', (1,), .1, (.1,))]
    result = solve(tasks, actions)
    assert result['new_credit_audio'] == 4
    assert result['steps'][0]['tasks'] == [1]
    assert result['steps'][1]['start'] == .1
    assert result['new_wall_seconds'] == 1.1


def test_same_batch_parent_child_is_not_legal():
    tasks = [Work(0, 2, 8), Work(1, 2, 8, dependencies=(0,))]
    with pytest.raises(ValueError, match='no complete schedule'):
        solve(tasks, [Action('generate', (0, 1), .1, (.1, .1))])


def test_unready_verification_is_never_a_legal_action():
    with pytest.raises(ValueError, match='no complete schedule'):
        solve([Work(0, 2, 8)], [Action('verify', (0,), .1, (.1,))])


@pytest.mark.parametrize('action', [
    Action('generate', (0,), .1, (.2,)),
    Action('mixed', (0,), .1, (.1,)),
    Action('generate', (0, 0), .1, (.1, .1)),
])
def test_invalid_physical_action_rejected(action):
    with pytest.raises(ValueError):
        solve([Work(0, 2, 8)], [action])


def test_zero_credit_tasks_cannot_be_dropped_from_common_cut():
    tasks = [Work(i, -1, 8, display_expired=True) for i in range(3)]
    actions = [Action('generate', (i,), .1, (.1,)) for i in range(3)]
    result = solve(tasks, actions)
    assert result['new_credit_audio'] == 0
    assert sorted(i for step in result['steps'] for i in step['tasks']) == [0, 1, 2]


def test_oracle_scope_is_bounded_and_explicit():
    with pytest.raises(ValueError, match='eight'):
        solve([Work(i, 2, 8) for i in range(9)], [])
    result = solve([Work(0, 2, 8)], [Action('generate', (0,), .1, (.1,))])
    assert result['model_optimal']
    assert not result['real_GPU_optimality_or_gain_claimed']
    assert result['evidence_tier'] == 'deterministic_CPU_scheduling_model_only'
