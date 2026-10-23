"""Exact finite deterministic scheduling-model oracle (CPU fixtures only).

The input supplies a finite set of *hypothetical legal* evidence actions and
their row/lease costs. It does not execute a model, certify token outputs, infer
new-parent generation from old traces, or predict real GPU Goodput. Exactness
holds only inside this declared, deterministic model with at most eight tasks.

The solver may split homogeneous generation or verification batches, retains
the entire common completion cut, respects structural Parent dependencies, and
never dispatches before the preceding physical Worker lease has drained.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Work:
    task_id: int
    display_deadline: float
    commit_deadline: float
    audio_weight: float = 2.0
    display_met: bool = False
    display_expired: bool = False
    candidate_ready: bool = False
    dependencies: tuple[int, ...] = ()


@dataclass(frozen=True)
class Action:
    operation: str
    tasks: tuple[int, ...]
    lease: float
    row_times: tuple[float, ...]
    # The fixture is responsible for including any verify/fallback sequence
    # within these paid costs. This value is a descriptive audit field only.
    evidence_note: str = 'declared deterministic CPU scheduling fixture'


@dataclass(frozen=True)
class Label:
    time: float
    credit: float
    commit_late_audio: float
    steps: tuple[dict, ...]


def _dominates(a, b):
    """Safe under time-independent costs and monotone completion deadlines."""
    return (a.time <= b.time and a.credit >= b.credit
            and a.commit_late_audio <= b.commit_late_audio)


def _insert_frontier(labels, incoming):
    if any(_dominates(old, incoming) for old in labels):
        return False
    labels[:] = [old for old in labels if not _dominates(incoming, old)]
    labels.append(incoming)
    return True


def solve(tasks, actions, *, now=0.0, base_credit=0.0, base_wall=0.0,
          objective='goodput', pareto=True):
    """Enumerate all complete legal schedules in the supplied finite action set.

    ``goodput`` maximizes (base_credit + new_credit)/(base_wall + new_wall).
    ``commit_first`` first minimizes Commit-late audio, then the same ratio.
    The latter is useful to expose why Commit SLO is not an admission safety
    predicate. All tasks must complete for either objective.

    Pareto pruning is exact only for this model: future actions depend on the
    completed-task set; costs, candidate availability and transition outcomes
    do not change with dispatch history or clock. Real model histories need
    additional state and cannot inherit this dominance proof automatically.
    """
    tasks = tuple(tasks)
    actions = tuple(actions)
    if not 1 <= len(tasks) <= 8:
        raise ValueError('bounded finite oracle requires one through eight tasks')
    if objective not in ('goodput', 'commit_first'):
        raise ValueError('unknown oracle objective')
    if base_credit < 0 or base_wall < 0:
        raise ValueError('prefix credit and wall must be nonnegative')
    by_id = {t.task_id: t for t in tasks}
    if len(by_id) != len(tasks):
        raise ValueError('duplicate task identity')
    index = {t.task_id: i for i, t in enumerate(tasks)}
    for task in tasks:
        if not math.isfinite(task.audio_weight) or task.audio_weight < 0:
            raise ValueError('invalid audio weight')
        if task.display_met and task.display_expired:
            raise ValueError('ambiguous display observation')
        if task.task_id in task.dependencies or not set(task.dependencies) <= set(by_id):
            raise ValueError('invalid Parent dependency')
    encoded = []
    for action in actions:
        if action.operation not in ('generate', 'verify'):
            raise ValueError('heterogeneous/unknown action is not allowed')
        if not action.tasks or len(action.tasks) != len(set(action.tasks)):
            raise ValueError('empty or duplicate batch row')
        if not set(action.tasks) <= set(by_id):
            raise ValueError('unknown batch task')
        if not math.isfinite(action.lease) or action.lease <= 0:
            raise ValueError('positive finite physical lease required')
        if len(action.row_times) != len(action.tasks):
            raise ValueError('one completion time per row required')
        if any(not math.isfinite(t) or t < 0 or t > action.lease for t in action.row_times):
            raise ValueError('row completion must lie inside physical lease')
        if action.operation == 'verify' and any(not by_id[i].candidate_ready for i in action.tasks):
            continue
        mask = sum(1 << index[i] for i in action.tasks)
        dependency_mask = 0
        for i in action.tasks:
            for parent in by_id[i].dependencies:
                dependency_mask |= 1 << index[parent]
        # A Parent must already be durably installed before this batch begins;
        # a same-batch row is not an available Parent for another row.
        if mask & dependency_mask:
            continue
        encoded.append((action, mask, dependency_mask))

    full = (1 << len(tasks)) - 1
    frontiers = {0: [Label(now, 0.0, 0.0, ())]}
    evaluated = rejected_dominated = peak_labels = 0
    for completed in range(full + 1):
        current_labels = tuple(frontiers.get(completed, ()))
        peak_labels = max(peak_labels, len(current_labels))
        for label in current_labels:
            for action, mask, dependencies in encoded:
                if completed & mask or completed & dependencies != dependencies:
                    continue
                evaluated += 1
                credit, late_audio = label.credit, label.commit_late_audio
                finishes = {}
                for task_id, row_time in zip(action.tasks, action.row_times):
                    task = by_id[task_id]
                    finish = label.time + row_time
                    finishes[task_id] = finish
                    commit_ok = finish <= task.commit_deadline
                    display_ok = task.display_met or (
                        not task.display_expired and finish <= task.display_deadline)
                    if commit_ok and display_ok:
                        credit += task.audio_weight
                    if not commit_ok:
                        late_audio += task.audio_weight
                step = {
                    'operation': action.operation, 'tasks': list(action.tasks),
                    'start': label.time, 'lease_end': label.time + action.lease,
                    'row_finishes': finishes, 'evidence_note': action.evidence_note,
                }
                incoming = Label(label.time + action.lease, credit, late_audio,
                                 label.steps + (step,))
                next_labels = frontiers.setdefault(completed | mask, [])
                if pareto:
                    if not _insert_frontier(next_labels, incoming):
                        rejected_dominated += 1
                else:
                    next_labels.append(incoming)
    if not frontiers.get(full):
        raise ValueError('no complete schedule in the declared legal action set')

    def key(label):
        rate = (base_credit + label.credit) / (base_wall + label.time - now)
        suffix = (-rate, label.time, label.commit_late_audio)
        return ((label.commit_late_audio,) + suffix) if objective == 'commit_first' else suffix

    best = min(frontiers[full], key=key)
    return {
        'evidence_tier': 'deterministic_CPU_scheduling_model_only',
        'model_optimal': True,
        'real_GPU_optimality_or_gain_claimed': False,
        'objective': objective,
        'new_credit_audio': best.credit,
        'new_wall_seconds': best.time - now,
        'commit_late_audio': best.commit_late_audio,
        'finite_run_rate': (base_credit + best.credit) / (base_wall + best.time - now),
        'common_cut': sorted(by_id),
        'steps': list(best.steps),
        'candidate_transitions_evaluated': evaluated,
        'dominated_labels_rejected': rejected_dominated,
        'peak_labels_per_completed_set': peak_labels,
        'final_labels': len(frontiers[full]),
        'assumptions': [
            'finite declared homogeneous actions', 'deterministic time-independent costs',
            'fixed legal transition outcomes', 'all tasks in common cut complete',
            'no additional Worker dispatch before physical lease drains',
            'candidate availability fixed in fixture',
        ],
    }


def counterexamples():
    """Mechanistic counterexamples, deliberately synthetic and reproducible."""
    early = Work(0, .5, 8.0)
    seen = Work(1, .5, 8.0, display_met=True)
    gg = [Action('generate', (0,), .2, (.2,)),
          Action('generate', (1,), .2, (.2,)),
          Action('generate', (0, 1), 1.0, (1.0, 1.0))]
    generation_split = {
        'single_batch': solve([early, seen], [gg[-1]]),
        'full_action_set': solve([early, seen], gg),
    }
    vv_tasks = [Work(0, .5, 8, candidate_ready=True),
                Work(1, .5, 8, display_met=True, candidate_ready=True)]
    vv = [Action('verify', (0,), .1, (.1,)),
          Action('verify', (1,), .6, (.6,)),
          Action('verify', (0, 1), .7, (.7, .7))]
    verification_split = {
        'single_batch': solve(vv_tasks, [vv[-1]]),
        'full_action_set': solve(vv_tasks, vv),
    }
    expired_parent = Work(0, -1.0, 1.1, display_expired=True, candidate_ready=True)
    live = Work(1, .5, 8.0)
    priority_actions = [Action('verify', (0,), 1.0, (1.0,)),
                        Action('generate', (1,), .2, (.2,))]
    commit_priority = {
        'commit_first': solve([expired_parent, live], priority_actions, objective='commit_first'),
        'goodput_first': solve([expired_parent, live], priority_actions, objective='goodput'),
    }
    # Two session chains A->B and C->D, plus independent E. Every audio
    # frontier is already released: release = display deadline - 2 seconds.
    # Same-session releases are exactly two seconds apart; Commit is release+8.
    unlock_tasks = [Work(0, -.1, 5.9, display_expired=True),
                    Work(1, 1.9, 7.9, dependencies=(0,)),
                    Work(2, -.1, 5.9, display_expired=True),
                    Work(3, 1.9, 7.9, dependencies=(2,)),
                    Work(4, .6, 6.6)]
    unlock_actions = [Action('generate', (0, 2), .8, (.8, .8)),
                      Action('generate', (1, 3), .8, (.8, .8)),
                      Action('generate', (4,), .6, (.6,))]
    unlock = solve(unlock_tasks, unlock_actions)
    return {
        'generation_split': generation_split,
        'verification_split': verification_split,
        'commit_priority': commit_priority,
        'parent_unlock': unlock,
        'ratio_of_expectations_counterexample': {
            'A_outcomes_equal_probability': [[2, 1], [8, 10]],
            'A_Ecredit_over_Ewall': 5 / 5.5,
            'A_Ecredit_over_wall': (2 / 1 + 8 / 10) / 2,
            'B_constant_credit_wall': [1, 1],
            'B_both_objectives': 1.0,
        },
        'prefix_ratio_counterexample': {
            'prefix_credit': 0, 'prefix_wall': 10,
            'A_delta_credit_wall': [2, 1], 'B_delta_credit_wall': [3, 2],
            'A_local_rate': 2.0, 'B_local_rate': 1.5,
            'A_completed_rate': 2 / 11, 'B_completed_rate': 3 / 12,
        },
    }


if __name__ == '__main__':
    import json
    print(json.dumps(counterexamples(), indent=2, ensure_ascii=False))
