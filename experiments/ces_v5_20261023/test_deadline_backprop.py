"""Pure CPU symbolic obligations, separate from model safety or GPU evidence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError,replace
import pytest

from deadline_backprop import CanonicalRoot,Obligation,build_symbolic_problem
from cpu_planning_oracle import Action,solve


def example():
    return build_symbolic_problem(now=10.05,
        roots=(CanonicalRoot(0,0),CanonicalRoot(1,0)), obligations=(
        Obligation(0,0,0,2,8.,10.,16.,.4),
        Obligation(1,0,2,4,10.,12.,18.,.9),
        Obligation(2,1,0,2,6.,8.,14.,.8,display_met=True)))


def test_expired_zero_credit_parent_inherits_released_child_deadline():
    p=example();a,b,c=p.priorities
    assert a.display_expired and a.own_finish_deadline==16.
    assert a.effective_finish_deadline==pytest.approx(11.1)
    assert a.latest_start==pytest.approx(10.7)
    assert a.inherited_from==(1,)
    assert b.requires_actual_future_parent and not b.structural_parent_at_root
    assert p.priority_order()==(0,2)
    assert p.priority_order((0,))==(1,2)
    assert not p.creates_execution_permission
    assert not p.creates_parent_tokens_or_candidate_outputs


def test_display_met_preserves_pending_commit_obligation():
    p=example();seen=p.priorities[2]
    assert seen.own_finish_deadline==14.
    assert not seen.display_expired
    task=p.to_oracle_tasks()[2]
    assert task.display_met and task.audio_weight==2.
    assert task.commit_deadline==14.


def test_symbolic_plan_links_to_exact_cpu_oracle_without_gpu_claim():
    p=example();actions=(Action('generate',(0,),.4,(.4,)),
        Action('generate',(1,),.9,(.9,)),Action('generate',(2,),.8,(.8,)),
        Action('generate',(0,2),1.2,(.8,1.2)))
    out=solve(p.to_oracle_tasks(),actions,now=p.now)
    assert out['new_credit_audio']==4.
    assert out['new_wall_seconds']==pytest.approx(2.1)
    assert tuple(step['tasks'][0] for step in out['steps'])==(0,1,2)
    assert not out['real_GPU_optimality_or_gain_claimed']
    full_batch_only=solve(p.to_oracle_tasks(),actions[1:2]+actions[3:],now=p.now)
    assert full_batch_only['new_credit_audio']==2.
    assert full_batch_only['new_wall_seconds']==pytest.approx(out['new_wall_seconds'])


def test_unreleased_successor_cannot_enter_snapshot():
    p=example();future=replace(p.obligations[1],release=p.now+.001)
    with pytest.raises(ValueError,match='unreleased'):
        build_symbolic_problem(now=p.now,roots=p.roots,
            obligations=(p.obligations[0],future,p.obligations[2]))


def test_committed_history_is_immutable_and_never_rescheduled():
    roots=[CanonicalRoot(0,2)]
    tasks=[Obligation(1,0,2,4,10.,12.,18.,.9)]
    before=deepcopy((roots,tasks))
    p=build_symbolic_problem(now=10.05,roots=roots,obligations=tasks)
    assert (roots,tasks)==before
    assert len(p.to_oracle_tasks())==1 and p.priorities[0].structural_parent_at_root
    with pytest.raises(FrozenInstanceError):p.roots[0].frontier=0
    with pytest.raises(ValueError,match='committed history'):
        build_symbolic_problem(now=10.05,roots=roots,
            obligations=[Obligation(9,0,0,2,8.,10.,16.,.4)])


@pytest.mark.parametrize('bad',[Obligation(1,0,1,4,10.,12.,18.,.9),
    Obligation(1,0,0,4,10.,12.,18.,.9)])
def test_gap_and_fork_are_not_symbolic_parent_permissions(bad):
    p=example()
    with pytest.raises(ValueError,match='gap-free'):
        build_symbolic_problem(now=p.now,roots=p.roots,
            obligations=(p.obligations[0],bad,p.obligations[2]))


def test_no_descendant_reduces_to_own_deadline_minus_declared_service():
    p=example()
    single=build_symbolic_problem(now=p.now,roots=p.roots,
        obligations=(p.obligations[0],p.obligations[2]))
    for o,priority in zip(single.obligations,single.priorities):
        assert priority.inherited_from==()
        assert priority.latest_start==pytest.approx(o.commit_deadline-o.service_seconds)


def test_display_satisfied_descendant_propagates_only_commit_deadline():
    p=example();child=replace(p.obligations[1],display_met=True)
    actual=build_symbolic_problem(now=p.now,roots=p.roots,
        obligations=(p.obligations[0],child,p.obligations[2]))
    assert actual.priorities[0].effective_finish_deadline==16.
    assert actual.priorities[0].inherited_from==()


def test_complete_set_cannot_skip_symbolic_predecessor():
    with pytest.raises(ValueError,match='predecessors'):
        example().priority_order((1,))


def test_declared_bound_remains_a_model_assumption_not_guarantee():
    p=example()
    bound=build_symbolic_problem(now=p.now,roots=p.roots,
        obligations=p.obligations,service_kind='declared_upper_bound')
    assert bound.service_kind=='declared_upper_bound'
    assert bound.evidence_tier=='symbolic_CPU_deadline_model_only'
    assert not bound.real_GPU_optimality_or_gain_claimed
