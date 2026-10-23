"""Symbolic deadline inheritance for released canonical obligations.

CPU research model only.  This module never constructs an execution Job, Parent
tokens, candidate Z, a certificate, or a WAL transition.  A future canonical
Parent remains unknown until actual trusted execution and admission complete.
The returned priorities are scheduling estimates, not execution permission or
an SLO theorem.  All unfinished obligations, including zero-credit parents,
remain in the common cut.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CanonicalRoot:
    session_id: int
    frontier: int


@dataclass(frozen=True)
class Obligation:
    task_id: int
    session_id: int
    parent_frontier: int
    frontier: int
    release: float
    display_deadline: float
    commit_deadline: float
    service_seconds: float
    audio_weight: float = 2.0
    display_met: bool = False


@dataclass(frozen=True)
class Priority:
    task_id: int
    dependencies: tuple[int, ...]
    own_finish_deadline: float
    effective_finish_deadline: float
    latest_start: float
    inherited_from: tuple[int, ...]
    display_expired: bool
    structural_parent_at_root: bool
    requires_actual_future_parent: bool


@dataclass(frozen=True)
class SymbolicProblem:
    now: float
    roots: tuple[CanonicalRoot, ...]
    obligations: tuple[Obligation, ...]
    priorities: tuple[Priority, ...]
    service_kind: str
    evidence_tier: str = 'symbolic_CPU_deadline_model_only'
    creates_execution_permission: bool = False
    creates_parent_tokens_or_candidate_outputs: bool = False
    real_GPU_optimality_or_gain_claimed: bool = False

    def priority_order(self, completed=()):
        """Structurally available IDs only; actual Parent must still be read.

        ``completed`` is a CPU-model dependency set, never a substitute for
        trusted installation in the runtime. No caller input is modified.
        """
        completed = frozenset(completed)
        by_id = {p.task_id: p for p in self.priorities}
        if not completed <= set(by_id):
            raise ValueError('unknown symbolic completed obligation')
        for task_id in completed:
            if not set(by_id[task_id].dependencies) <= completed:
                raise ValueError('symbolic completion requires its predecessors')
        eligible = [p for p in self.priorities if p.task_id not in completed
                    and set(p.dependencies) <= completed]
        return tuple(p.task_id for p in sorted(eligible,
            key=lambda p: (p.latest_start, p.effective_finish_deadline, p.task_id)))

    def to_oracle_tasks(self):
        """Bridge to the finite CPU oracle without inventing model outcomes."""
        from cpu_planning_oracle import Work
        priorities = {p.task_id: p for p in self.priorities}
        return tuple(Work(o.task_id, o.display_deadline, o.commit_deadline,
            audio_weight=o.audio_weight, display_met=o.display_met,
            display_expired=priorities[o.task_id].display_expired,
            candidate_ready=False, dependencies=priorities[o.task_id].dependencies)
            for o in self.obligations)


def build_symbolic_problem(*, now, roots, obligations, service_kind='estimate'):
    """Propagate descendant finish deadlines backwards through session chains.

    For an unfinished Display obligation, its own useful finish deadline is
    min(Display, Commit). Already displayed or Display-expired obligations keep
    their Commit deadline. For a structural edge parent -> child:

        effective_finish(parent) <= effective_finish(child) - service(child).

    Service values describe a declared serial CPU path. In batched execution,
    physical lease availability and row completion must be separately modeled;
    this recursion alone never guarantees that a real GPU deadline is met.
    Only already-released audio obligations may enter this bounded snapshot.
    """
    if not math.isfinite(now):
        raise ValueError('finite decision time required')
    if service_kind not in ('estimate', 'declared_upper_bound'):
        raise ValueError('service_kind must declare estimate or upper bound')
    roots = tuple(roots)
    obligations = tuple(obligations)
    root_by_session = {r.session_id: r for r in roots}
    if len(root_by_session) != len(roots):
        raise ValueError('one immutable canonical root per session required')
    if any(not isinstance(r.frontier, int) or r.frontier < 0 for r in roots):
        raise ValueError('invalid committed frontier')
    by_id = {o.task_id: o for o in obligations}
    if len(by_id) != len(obligations):
        raise ValueError('duplicate obligation identity')
    sessions = {}
    for o in obligations:
        if o.session_id not in root_by_session:
            raise ValueError('missing immutable canonical root')
        if not all(math.isfinite(x) for x in (o.release, o.display_deadline,
                o.commit_deadline, o.service_seconds, o.audio_weight)):
            raise ValueError('finite declared clocks and service required')
        if o.release > now:
            raise ValueError('unreleased audio cannot enter symbolic planning')
        if min(o.display_deadline, o.commit_deadline) < o.release:
            raise ValueError('deadline precedes audio release')
        if o.service_seconds <= 0 or o.audio_weight < 0:
            raise ValueError('positive service and nonnegative audio required')
        if (not isinstance(o.parent_frontier, int) or not isinstance(o.frontier, int)
                or o.parent_frontier < 0 or o.frontier <= o.parent_frontier):
            raise ValueError('invalid causal frontier interval')
        if (o.frontier <= root_by_session[o.session_id].frontier or
                o.parent_frontier < root_by_session[o.session_id].frontier):
            raise ValueError('committed history cannot be rewritten or rolled back')
        sessions.setdefault(o.session_id, []).append(o)

    dependencies = {}
    own = {}
    effective = {}
    inherited = {}
    expired = {}
    for sid, chain in sessions.items():
        chain.sort(key=lambda o: (o.frontier, o.task_id))
        cursor = root_by_session[sid].frontier
        previous = None
        for o in chain:
            if o.parent_frontier != cursor:
                raise ValueError('canonical obligations require a gap-free nonforking chain')
            if previous is not None and o.release < previous.release:
                raise ValueError('successor audio cannot release before its prefix')
            dependencies[o.task_id] = () if previous is None else (previous.task_id,)
            expired[o.task_id] = not o.display_met and now > o.display_deadline
            own[o.task_id] = (o.commit_deadline if o.display_met or expired[o.task_id]
                              else min(o.display_deadline, o.commit_deadline))
            effective[o.task_id] = own[o.task_id]
            inherited[o.task_id] = ()
            cursor, previous = o.frontier, o
        for parent, child in zip(reversed(chain[:-1]), reversed(chain[1:])):
            inherited_deadline = effective[child.task_id] - child.service_seconds
            if inherited_deadline < effective[parent.task_id]:
                effective[parent.task_id] = inherited_deadline
                inherited[parent.task_id] = (child.task_id,) + inherited[child.task_id]

    priorities = tuple(Priority(o.task_id, dependencies[o.task_id], own[o.task_id],
        effective[o.task_id], effective[o.task_id] - o.service_seconds,
        inherited[o.task_id], expired[o.task_id], not dependencies[o.task_id],
        bool(dependencies[o.task_id])) for o in sorted(obligations, key=lambda x: x.task_id))
    return SymbolicProblem(float(now), roots, tuple(sorted(obligations,
        key=lambda o: o.task_id)), priorities, service_kind)
