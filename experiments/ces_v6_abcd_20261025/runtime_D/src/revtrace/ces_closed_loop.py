"""Bounded closed-loop evidence scheduling; predictions are not permissions.

This module carries durable-*service* obligations across replanning, not durable
state or authorization.  It never constructs a Job, token, certificate or WAL
record.  A symbolic successor is costed with the shared physical batch model;
its real Parent/input must be reconstructed by the owner after actual admission.
Only the first currently executable homogeneous batch is returned for dispatch.

Commit lateness is a reported performance result, never a hard admission or
scheduling permission. ``promise_quantile`` controls an empirical service
promise, not a distribution-free SLO guarantee or a Commit-late risk budget.
"""
from dataclasses import dataclass, replace, asdict
import itertools
import math
import random
from bisect import bisect_right
from functools import lru_cache

from .ces_v5_policy import V5Target, BatchOutcome, predict_batch, _plans, _weighted_quantile, _row_moments, _row_cdf


@dataclass(frozen=True)
class Identity:
    sid: int
    epoch: int
    parent_version: int
    parent_digest: str
    frontier_start: int
    frontier_end: int
    contract_digest: str


@dataclass(frozen=True)
class SuccessorObligation:
    window: int
    frontier_end: int
    release: float
    display_deadline: float
    commit_deadline: float
    audio_weight: float
    remaining_service_s: float
    display_met: bool = False
    private_ready_delay_s: float | None = None
    verify_private_compatible: bool | None = None
    unknown_private_probability: float | None = None
    direct_private_probability: float | None = None
    fallback_private_probability: float | None = None
    inherit_current_transition_model: bool = False
    parent_frontier_start: int | None = None
    audio_seconds: float | None = None
    estimated_prompt_tokens: int | None = None
    interval_seconds: float | None = None
    private_delay_distribution: tuple[tuple[float, float], ...] = ()
    private_path_currently_legal: bool = False
    private_delay_includes_delivery: bool = False


@dataclass(frozen=True)
class TargetContext:
    identity: Identity
    successors: tuple[SuccessorObligation, ...] = ()
    private_ready_delay_s: float | None = None
    verify_private_compatible: bool | None = None
    direct_private_probability: float | None = None
    fallback_private_probability: float | None = None
    private_path_currently_legal: bool = False
    private_delay_distribution: tuple[tuple[float, float], ...] = ()
    private_delay_includes_delivery: bool = False


@dataclass(frozen=True)
class PlannerConfig:
    max_deferrals: int = 2
    promise_quantile: float = .9
    max_successors_per_session: int = 2
    max_scenario_combinations: int = 16
    max_candidate_plans: int = 8
    promise_tolerance_s: float = 1e-6
    cache_mode: str = 'reference'
    guard_mode: str = 'hard'


@dataclass
class ServiceRecord:
    first_seen: float
    deferrals: int = 0
    promised_finish: float | None = None
    continuation_rank: int | None = None
    promise_breaches: int = 0


@dataclass(frozen=True)
class AncestorPrediction:
    operation: str
    outcome: BatchOutcome
    started: float
    delivery: float
    accept_compatible_probability: float
    direct_compatible_probability: float
    fallback_compatible_probability: float
    compatibility_identified: bool


class ClosedLoopState:
    """Owner-local service book. Increment only after real enqueue succeeds.

    The owner must call ``record_dispatch`` exactly once per issued batch and
    use a new scope/reset after restart. Polling ``choose_closed_loop`` does not
    age the decision counter. Real Parent/epoch/contract changes remove the old
    bound identity. Symbolic continuation intent can bind the newly *observed*
    child identity, but it supplies neither that identity nor execution input.
    """
    def __init__(self, scope=None):
        self.scope = scope
        self.records = {}
        self.continuation_intents = {}
        self.dispatches = 0
        self._recorded_tokens = set()

    def reset(self, scope=None):
        self.__init__(scope)

    def to_audit(self):
        """JSON-safe real service state; contains no speculative Parent value."""
        return {'scope': self.scope, 'actual_dispatches': self.dispatches,
            'records': [{'identity': asdict(k), **asdict(v)} for k, v in sorted(
                self.records.items(), key=lambda kv: (kv[0].sid, kv[0].epoch, kv[0].frontier_end))],
            'symbolic_continuation_intents': list(self.continuation_intents.values()),
            'authorization_state': False}

    def observe(self, contexts, now):
        live = {c.identity for c in contexts.values()}
        observed_sids = {k.sid for k in live}
        # Temporary absence from an eligible list is not service completion.
        # A newly observed actual identity replaces that Session's old binding.
        self.records = {k: v for k, v in self.records.items()
                        if k.sid not in observed_sids or k in live}
        epochs = {(k.sid, k.epoch, k.contract_digest) for k in live}
        self.continuation_intents = {k: v for k, v in self.continuation_intents.items()
            if k[0] not in observed_sids or k[:3] in epochs}
        for key in live:
            if key not in self.records:
                intent = self.continuation_intents.pop(
                    (key.sid, key.epoch, key.contract_digest, key.frontier_end), None)
                self.records[key] = ServiceRecord(float(now))
                if intent is not None:
                    self.records[key].promised_finish = intent['promised_finish']
                    self.records[key].continuation_rank = intent['rank']

    def admitted(self, sid, *, epoch, frontier, now=None):
        """Retire service debt only after the owner observes real WAL install."""
        retired = [{'identity': asdict(k), **asdict(v),
            'actual_install_time': now,
            'actual_promise_late': bool(now is not None and v.promised_finish is not None
                                       and now > v.promised_finish)}
            for k, v in self.records.items()
            if k.sid == sid and k.epoch == epoch and k.frontier_end <= frontier]
        self.records = {k: v for k, v in self.records.items()
            if not (k.sid == sid and k.epoch == epoch and k.frontier_end <= frontier)}
        self.continuation_intents = {k: v for k, v in self.continuation_intents.items()
            if not (k[0] == sid and k[1] == epoch and k[3] <= frontier)}
        return retired

    def record_dispatch(self, decision, contexts, *, now):
        if not decision.get('operation'):
            raise ValueError('only an actually issued physical batch ages service obligations')
        token = decision.get('decision_token')
        if token is None or token in self._recorded_tokens:
            raise ValueError('missing or duplicate closed-loop dispatch receipt')
        self._recorded_tokens.add(token)
        self.dispatches += 1
        selected = set(decision['sids'])
        for sid in decision['common_cut_sids']:
            key = contexts[sid].identity
            record = self.records[key]
            if record.promised_finish is not None and now > record.promised_finish:
                record.promise_breaches += 1
            if sid in selected:
                record.deferrals = 0
                continue
            record.deferrals += 1
            predicted = decision['service_promises'].get(str(sid))
            if predicted is not None:
                record.promised_finish = (predicted if record.promised_finish is None
                    else min(record.promised_finish, predicted))
            record.continuation_rank = decision['continuation_ranks'].get(str(sid))
        # These are service intentions only. No future Parent value is stored.
        for item in decision.get('symbolic_service_promises', []):
            key = (item['sid'], item['epoch'], item['contract_digest'], item['frontier_end'])
            previous = self.continuation_intents.get(key)
            if previous is None or item['promised_finish'] < previous['promised_finish']:
                self.continuation_intents[key] = dict(item)
        return self.to_audit()


def _probability(value):
    if value is None:
        return None
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('private compatibility probability must be declared in [0,1]')
    return float(value)


def _validate_private_distribution(distribution):
    if not distribution:
        return
    if any(len(pair) != 2 or not all(math.isfinite(x) for x in pair)
           or pair[0] < 0 or pair[1] < 0 for pair in distribution):
        raise ValueError('finite nonnegative Private row-CDF weights and delays required')
    if sum(weight for weight, _ in distribution) <= 0:
        raise ValueError('Private row-CDF requires positive probability mass')


@lru_cache(maxsize=4096)
def _private_cdf(distribution, scalar):
    if not distribution:
        distribution = () if scalar is None else ((1., scalar),)
    total = sum(w for w, _ in distribution)
    times = []
    cumulative = [0.]
    for weight, delay in sorted(distribution, key=lambda pair: pair[1]):
        if weight <= 0:
            continue
        times.append(delay)
        cumulative.append(cumulative[-1]+weight/total)
    return tuple(times), tuple(cumulative)


def _private_cdf_at(distribution, scalar, remaining):
    times, cumulative = _private_cdf(tuple(distribution), scalar)
    return cumulative[bisect_right(times, remaining)]


@lru_cache(maxsize=8192)
def _ancestor_phase_times(outcome, phase):
    return tuple(sorted((outcome.early_row_times or (outcome.early_row,)) if phase == 'early'
                        else (outcome.late_row_times or (outcome.late_row,))))


def _ancestor_survival_factor(ancestor, observed_at, *, require_installed=False):
    if not isinstance(ancestor, AncestorPrediction):
        # Deterministic transition fixture. Production uses the full physical
        # outcome/phase CDF below, never its envelope or mean as a free cutoff.
        update_time, keep = ancestor
        installed = float(update_time <= observed_at)
        compatible = 0. if keep is None else keep
        return installed*compatible if require_installed else 1-installed*(1-compatible)
    relative = observed_at-ancestor.started-ancestor.delivery
    outcome = ancestor.outcome
    early = _ancestor_phase_times(outcome, 'early')
    early_p = bisect_right(early, relative)/len(early)
    if ancestor.operation == 'generate':
        preserved = early_p*ancestor.direct_compatible_probability
        return preserved if require_installed else 1-early_p+preserved
    late = _ancestor_phase_times(outcome, 'late')
    late_p = bisect_right(late, relative)/len(late)
    rejected = outcome.reject_fraction
    preserved = ((1-rejected)*early_p*ancestor.accept_compatible_probability
                 +rejected*late_p*ancestor.fallback_compatible_probability)
    installed = (1-rejected)*early_p+rejected*late_p
    return preserved if require_installed else 1-installed+preserved


def _private_survival_probability(distribution, scalar, *, now, delivery,
                                   display_deadline, ancestor_updates,
                                   currently_legal, private_delay_includes_delivery=False):
    """Integrate a pending row through *all* possible invalidating updates.

    An actual legal branch is free of retention conditions only before its
    first root update. Later symbolic updates never reset this free interval.
    ``None`` is an uncalibrated transition: no post-update preservation credit
    is asserted there, without declaring the actual Parent incompatible.
    """
    if not distribution:
        distribution = () if scalar is None else ((1., scalar),)
    total = sum(w for w, _ in distribution)
    if total <= 0:
        return 0.
    credit = 0.
    for weight, delay in distribution:
        observed = now+delay+(0. if private_delay_includes_delivery else delivery)
        if observed > display_deadline or weight <= 0:
            continue
        if not ancestor_updates:
            survival = float(currently_legal)
        else:
            survival = 1.
            for index, ancestor in enumerate(ancestor_updates):
                survival *= _ancestor_survival_factor(ancestor, observed,
                    require_installed=index == 0 and not currently_legal)
        credit += weight/total*survival
    return min(1., max(0., credit))


def _validate(targets, contexts, now, config):
    if not math.isfinite(now) or config.max_deferrals < 1:
        raise ValueError('finite time and positive finite-service deferral budget required')
    if not 0 < config.promise_quantile <= 1:
        raise ValueError('invalid empirical promise quantile')
    if not 1 <= config.max_scenario_combinations <= 256:
        raise ValueError('bounded scenario count required')
    if not 1 <= config.max_candidate_plans or not 1 <= config.max_successors_per_session <= 2:
        raise ValueError('positive candidate beam and at most two released successor layers required')
    if len({t.sid for t in targets}) != len(targets):
        raise ValueError('one current transition per session required')
    for t in targets:
        c = contexts[t.sid]
        k = c.identity
        if k.sid != t.sid or k.frontier_start < 0 or k.frontier_end <= k.frontier_start:
            raise ValueError('actual Parent/frontier identity does not bind current target')
        if not k.parent_digest or not k.contract_digest or k.epoch < 0 or k.parent_version < 0:
            raise ValueError('actual Parent/epoch/contract identity required')
        if t.ready > now or t.display_met and t.display_expired:
            raise ValueError('unreleased or ambiguous current target')
        if not all(math.isfinite(x) for x in (t.ready, t.deadline, t.audio_weight,
                t.audio_seconds, t.interval_seconds)) or t.audio_weight < 0:
            raise ValueError('finite nonnegative current accounting fields required')
        if t.candidate_eta is not None and (not math.isfinite(t.candidate_eta) or t.candidate_eta < 0):
            raise ValueError('finite nonnegative current candidate ETA required')
        if c.private_ready_delay_s is not None and (not math.isfinite(c.private_ready_delay_s) or c.private_ready_delay_s < 0):
            raise ValueError('finite nonnegative current private ETA required')
        _validate_private_distribution(c.private_delay_distribution)
        if not isinstance(c.private_delay_includes_delivery, bool):
            raise ValueError('Private delay clock must explicitly declare delivery inclusion')
        _probability(c.direct_private_probability)
        _probability(c.fallback_private_probability)
        end = k.frontier_end
        prior_release = t.ready
        prior_window = t.window
        for u in c.successors:
            if not all(math.isfinite(x) for x in (u.release, u.display_deadline,
                    u.commit_deadline, u.audio_weight, u.remaining_service_s)):
                raise ValueError('finite released successor estimates required')
            if u.release > now:
                raise ValueError('unreleased successor cannot enter planning cut')
            if u.release < prior_release or u.window <= prior_window or u.frontier_end <= end:
                raise ValueError('successor must advance a gap-free monotone chain')
            if u.parent_frontier_start is not None and u.parent_frontier_start != end:
                raise ValueError('successor frontier gap or fork')
            if min(u.display_deadline, u.commit_deadline) < u.release or u.remaining_service_s <= 0 or u.audio_weight < 0:
                raise ValueError('invalid successor deadlines or service estimate')
            if u.private_ready_delay_s is not None and (not math.isfinite(u.private_ready_delay_s) or u.private_ready_delay_s < 0):
                raise ValueError('finite nonnegative successor private ETA required')
            _validate_private_distribution(u.private_delay_distribution)
            if not isinstance(u.private_delay_includes_delivery, bool):
                raise ValueError('Successor Private delay clock must explicitly declare delivery inclusion')
            _probability(u.unknown_private_probability)
            _probability(u.direct_private_probability)
            _probability(u.fallback_private_probability)
            end, prior_release, prior_window = u.frontier_end, u.release, u.window


def effective_deadlines(targets, contexts, *, now, display_slo=2.):
    """Prediction-only backward propagation; all nodes refer to released audio."""
    result = {}
    for t in targets:
        own = t.deadline if t.display_met or t.display_expired else min(t.deadline, t.ready + display_slo)
        effective = own
        inherited = []
        for u in contexts[t.sid].successors:
            due = u.commit_deadline if u.display_met or u.display_deadline < now else min(u.display_deadline, u.commit_deadline)
            estimate = due - u.remaining_service_s
            if estimate < effective:
                effective = estimate
                inherited.append(u.window)
        result[t.sid] = {'own_finish_deadline': own, 'effective_finish_deadline': effective,
                         'inherited_from_windows': inherited}
    return result


def _candidate_plans(targets, contexts, cal, now, display_slo, state, config, mode, shared_cache=None):
    """Shared operation family, with declared predecessor/promise priority lists."""
    candidates = list(_plans(targets, cal, now, display_slo))
    use_successors = mode in ('inherit', 'causal')
    priority_contexts = contexts if use_successors else {sid: replace(c, successors=()) for sid, c in contexts.items()}
    dues = effective_deadlines(targets, priority_contexts, now=now, display_slo=display_slo)
    orders = [sorted(targets, key=lambda t: (dues[t.sid]['effective_finish_deadline'], t.deadline, t.sid)),
              sorted(targets, key=lambda t: (state.records[contexts[t.sid].identity].promised_finish
                  if state.records[contexts[t.sid].identity].promised_finish is not None else math.inf,
                  state.records[contexts[t.sid].identity].first_seen, t.sid))]
    extras = []
    for order in orders:
        for n in sorted({1, 2, 4, 8, len(targets) // 2, len(targets)}):
            if not 0 < n <= len(targets):
                continue
            ids = {t.sid for t in order[:n]}
            first = tuple(t for t in targets if t.sid in ids)
            rest = tuple(t for t in targets if t.sid not in ids)
            for op in ('generate', 'verify'):
                if op == 'verify' and not all(t.candidate_ready for t in first):
                    continue
                extras.append(tuple((o, rs) for o, rs in ((op, first), ('generate', rest)) if rs))
    # Bounded cheap beam formation, not a model-optimality claim. Preserve a
    # full-G reference, cheapest physical work, earliest inherited priorities
    # and service promises. Complete row-CDF scenarios are evaluated *after*
    # this prefilter. The cheap point estimate never becomes a reported CDF.
    unique = {}
    for p in candidates + extras:
        key = tuple((op, tuple(t.sid for t in rs)) for op, rs in p)
        unique[key] = p
    full = list(unique.values())
    if len(full) <= config.max_candidate_plans:
        return full, len(full)
    cost_cache = {}
    def cheap(plan):
        cursor = now
        credit = inherited_credit = promise_risk = total = 0.
        for op, rows in plan:
            key = op, tuple(t.sid for t in rows)
            if key not in cost_cache:
                distribution_key = op, tuple((t.sid,t.window,t.audio_seconds,t.prompt_tokens,t.candidate_tokens) for t in rows)
                if shared_cache is None:
                    ds = predict_batch(cal, op, rows)
                else:
                    if distribution_key not in shared_cache:
                        shared_cache[distribution_key] = predict_batch(cal,op,rows)
                    ds = shared_cache[distribution_key]
                cost_cache[key] = (sum(o.weight*o.lease for o in ds),
                    sum(o.weight*((1-o.reject_fraction)*o.early_row+o.reject_fraction*o.late_row) for o in ds))
            lease, row = cost_cache[key]
            finish = cursor+row
            for t in rows:
                due = t.deadline if t.display_met else min(t.deadline, t.ready+display_slo)
                if not t.display_expired and finish <= due:
                    credit += t.audio_weight
                for u in (contexts[t.sid].successors[:config.max_successors_per_session] if use_successors else ()):
                    if (u.display_met or now <= u.display_deadline) and finish+u.remaining_service_s <= min(u.display_deadline if not u.display_met else u.commit_deadline, u.commit_deadline):
                        inherited_credit += u.audio_weight
                promise = state.records[contexts[t.sid].identity].promised_finish
                if promise is not None:
                    promise_risk += max(0., finish-promise)
            cursor += lease
            total += lease
        return total, credit/max(total,1e-9), (credit+inherited_credit)/max(total,1e-9), promise_risk
    summaries = [(p, cheap(p)) for p in full]
    selected = []
    def retain(p):
        if p not in selected and len(selected) < config.max_candidate_plans:
            selected.append(p)
    retain(next(p for p in full if len(p)==1 and p[0][0]=='generate' and len(p[0][1])==len(targets)))
    retain(min(summaries, key=lambda x: (x[1][0], -x[1][1]))[0])
    retain(min(summaries, key=lambda x: (x[1][3], x[1][0], -x[1][1]))[0])
    forced = {t.sid for t in targets if state.records[contexts[t.sid].identity].deferrals >= config.max_deferrals}
    if forced:
        retain(min(summaries, key=lambda x: (len(forced-{t.sid for t in x[0][0][1]}), x[1][0]))[0])
    for index in range(config.max_candidate_plans):
        for column in (2, 1):
            ranked = sorted(summaries, key=lambda x: (-x[1][column], x[1][3], x[1][0]))
            if index < len(ranked):
                retain(ranked[index][0])
        if len(selected) >= config.max_candidate_plans:
            break
    return selected, len(full)


def _proxy(t, u):
    """Historical feature estimate only, not a Job or processed model input."""
    return replace(t, window=u.window, ready=u.release, deadline=u.commit_deadline,
        candidate_ready=False, candidate_tokens=0, display_met=u.display_met,
        display_expired=False, audio_weight=u.audio_weight,
        audio_seconds=u.audio_seconds if u.audio_seconds is not None else t.audio_seconds + (u.window-t.window)*t.interval_seconds,
        prompt_tokens=u.estimated_prompt_tokens if u.estimated_prompt_tokens is not None else t.prompt_tokens,
        interval_seconds=u.interval_seconds if u.interval_seconds is not None else t.interval_seconds)


def _expanded(plan, contexts, config, interleave):
    """All current rows and bounded released successors appear exactly once."""
    steps = []
    pending = []
    for index, (op, rows) in enumerate(plan):
        steps.append((op, rows, False, None))
        pending.extend(rows)
        if not interleave and index + 1 < len(plan):
            continue
        for depth in range(config.max_successors_per_session):
            descendants = [(t, contexts[t.sid].successors[depth]) for t in pending
                           if depth < len(contexts[t.sid].successors)]
            if descendants:
                steps.append(('generate', tuple(_proxy(t, u) for t, u in descendants),
                              True, {t.sid: u for t, u in descendants}))
        pending = []
    return steps


def _draws(distributions, budget):
    n = math.prod(len(d) for d in distributions)
    if n <= budget:
        return [(tuple(outcomes), math.prod(o.weight for o in outcomes))
                for outcomes in itertools.product(*distributions)], 'exact_product_within_budget'
    # Fixed weighted stratified quadrature; never outcome/fault labels. The
    # same frozen draws are used for every compared policy. Not exact Monte
    # Carlo confidence or a complete dependent-outcome distribution.
    generator = random.Random(20261025)
    strata = []
    for _ in distributions:
        order = list(range(budget))
        generator.shuffle(order)
        strata.append(order)
    draws = []
    for i in range(budget):
        outcomes = []
        for j, distribution in enumerate(distributions):
            u = (strata[j][i] + .5) / budget
            cumulative = 0.
            for outcome in distribution:
                cumulative += outcome.weight
                if u <= cumulative + 1e-12:
                    outcomes.append(outcome)
                    break
            else:
                outcomes.append(distribution[-1])
        draws.append((tuple(outcomes), 1. / budget))
    return draws, 'bounded_weighted_stratified_scenario_quadrature'


def _row_probability(outcome, finish_by, start, delivery, cache=None):
    remaining = finish_by-start-delivery
    if cache is None:
        return _row_moments(outcome, remaining)[0]
    # A cache is scoped to one choose call and retains the actual Outcome.
    # Identity keys avoid repeatedly hashing its entire empirical row tuple.
    # The arithmetic and bisect boundary are identical to _row_moments.
    identity = id(outcome)
    compiled = cache.setdefault('row_CDF_by_identity', {})
    if identity not in compiled:
        times,cumulative,_ = _row_cdf(outcome)
        compiled[identity] = (outcome,times,cumulative)
    stored,times,cumulative = compiled[identity]
    assert stored is outcome
    queries = cache.setdefault('row_probability_queries', {})
    key = (identity,remaining)
    if key not in queries:
        queries[key] = min(1.,max(0.,cumulative[bisect_right(times,remaining)]))
    return queries[key]


def _scenario_audit(distributions, draws):
    audits = []
    for j, distribution in enumerate(distributions):
        counts = [sum(w for outcomes, w in draws if outcomes[j] is outcome) for outcome in distribution]
        tv = .5*sum(abs(p-outcome.weight) for p, outcome in zip(counts, distribution))
        expected_failed = sum(o.weight for o in distribution if o.reject_fraction > 0)
        drawn_failed = sum(p for p, o in zip(counts, distribution) if o.reject_fraction > 0)
        largest = max(o.lease for o in distribution)
        omitted_tail = sum(o.weight for p, o in zip(counts, distribution) if p == 0 and o.lease == largest)
        audits.append({'marginal_total_variation': tv,
            'fallback_mass_original': expected_failed, 'fallback_mass_quadrature': drawn_failed,
            'largest_lease_outcome_mass_omitted': omitted_tail,
            'original_scenarios': len(distribution), 'represented_scenarios': sum(p > 0 for p in counts)})
    return audits


def _private_probability(c, op, outcome, known, unknown=None, *,
                         direct=None, fallback=None, inherit_current=True):
    """No unexplained Verify bonus when Direct/Fallback is uncalibrated."""
    # ``unknown`` is a backwards-compatible *declared equal-rate fixture*
    # parameter. Production successor contexts use the two explicit rates;
    # an unknown later Parent must not silently inherit the root transition.
    if unknown is not None:
        direct = fallback = unknown
    elif inherit_current:
        direct = c.direct_private_probability if direct is None else direct
        fallback = c.fallback_private_probability if fallback is None else fallback
    if direct is None or fallback is None:
        return 0., False  # Common conservative no-differential-credit forecast.
    if op != 'verify':
        return direct, True
    if known is None:
        return direct, True  # Unknown conditional equality is not incompatibility.
    return (1-outcome.reject_fraction)*float(known) + outcome.reject_fraction*fallback, True


def _ancestor_prediction(c, operation, outcome, started, delivery, known,
                         unknown=None, *, direct=None, fallback=None,
                         inherit_current=True):
    if unknown is not None:
        direct = fallback = unknown
    elif inherit_current:
        direct = c.direct_private_probability if direct is None else direct
        fallback = c.fallback_private_probability if fallback is None else fallback
    identified = direct is not None and fallback is not None
    # Shared conservative post-update forecast when compatibility is sparse;
    # not an assertion that any actual unknown Parent is incompatible.
    if not identified:
        direct = fallback = accepted = 0.
    else:
        accepted = direct if known is None else float(known)
    return AncestorPrediction(operation, outcome, started, delivery,
        accepted, direct, fallback, identified)


def _evaluate(plan, contexts, *, now, mode, cal, display_slo, observed_credit_audio,
              elapsed_seconds, state, config, interleave, cache):
    steps = _expanded(plan, contexts, config, interleave)
    distributions = []
    for op, rows, symbolic, _ in steps:
        key = op, tuple((t.sid, t.window, t.audio_seconds, t.prompt_tokens, t.candidate_tokens) for t in rows)
        if key not in cache:
            cache[key] = predict_batch(cal, op, rows)
        distributions.append(cache[key])
    draws, draw_kind = _draws(distributions, config.max_scenario_combinations)
    scenario_audit = _scenario_audit(distributions, draws)
    delivery = max(0., float(cal.get('v5_risk_model', {}).get('owner_delivery_seconds', 0.)))
    expected_credit = current_credit = successor_credit = expected_late = 0.
    expected_wall = prefix_rate = expected_private = expected_lease = 0.
    promise_violation = promise_tardy = 0.
    per_sid = {t.sid: [] for _, rs in plan for t in rs}
    successor_finishes = {}
    conditional_enabled = False
    row_query_cache = cache if config.cache_mode == 'memoized' else None
    for outcomes, mass in draws:
        cursor = now
        paid_gpu_lease = 0.
        latest_delivery = now
        q = cq = sq = late = private_q = 0.
        parent_times = {}
        parent_ops = {}
        parent_outcomes = {}
        ancestor_survival = {}
        for (op, rows, symbolic, successor_map), outcome in zip(steps, outcomes):
            # Actual future inputs can only be made after installed Parent;
            # forecast also pays wait for the parent's complete Owner delivery.
            if symbolic:
                cursor = max(cursor, max(parent_times[t.sid] for t in rows))
            started = cursor
            row_finish = started + max(outcome.early_row_times + outcome.late_row_times
                if outcome.early_row_times or outcome.late_row_times else (outcome.early_row, outcome.late_row)) + delivery
            for t in rows:
                c = contexts[t.sid]
                # Each constituent row's exact exchangeable CDF, not its mean.
                commit_p = _row_probability(outcome, t.deadline, started, delivery, row_query_cache)
                u = successor_map[t.sid] if symbolic else None
                d_due = u.display_deadline if symbolic else t.ready + display_slo
                expired = (not t.display_met and now > d_due)
                canonical_p = _row_probability(outcome, min(d_due, t.deadline), started, delivery, row_query_cache)
                credit_p = commit_p if t.display_met else (0. if expired else canonical_p)
                private_delay = u.private_ready_delay_s if symbolic else c.private_ready_delay_s
                private_distribution = u.private_delay_distribution if symbolic else c.private_delay_distribution
                private_compat = u.verify_private_compatible if symbolic else c.verify_private_compatible
                if mode == 'causal' and (private_delay is not None or private_distribution) and not t.display_met and not expired:
                    # Integrate the *conditional remaining* actual Private-row
                    # CDF supplied by the owner. Never threshold its mean ETA.
                    private_has_delivery = u.private_delay_includes_delivery if symbolic else c.private_delay_includes_delivery
                    on_time_private = _private_cdf_at(private_distribution, private_delay,
                        d_due-now-(0. if private_has_delivery else delivery))
                    if not symbolic:
                        # The extra mass has D < C, so a currently legal row
                        # observed by D necessarily precedes this late C. If
                        # not currently legal it cannot gain its own D only
                        # after late C. C-first/on-time is already credited.
                        available = on_time_private if c.private_path_currently_legal else 0.
                    else:
                        available = _private_survival_probability(private_distribution, private_delay,
                            now=now, delivery=delivery, display_deadline=d_due,
                            ancestor_updates=ancestor_survival[t.sid],
                            currently_legal=u.private_path_currently_legal,
                            private_delay_includes_delivery=private_has_delivery)
                    addition = max(0., commit_p-canonical_p) * available
                    credit_p = min(commit_p, credit_p + addition)
                    private_q += t.audio_weight * addition
                weight = max(0., t.audio_weight)
                earned = weight * credit_p
                q += earned
                late += weight * (1-commit_p)
                if symbolic:
                    sq += earned
                    successor_finishes.setdefault((t.sid, t.window), []).append((row_finish, mass))
                else:
                    cq += earned
                    per_sid[t.sid].append((row_finish, mass))
                    record = state.records[c.identity]
                    if record.promised_finish is not None:
                        miss = 1-_row_probability(outcome, record.promised_finish, started, delivery, row_query_cache)
                        promise_violation += mass * miss
                        promise_tardy += mass * max(0., row_finish-record.promised_finish)
                # A further symbolic Generate creates another unknown Parent;
                # do not reuse root Verify-success provenance at depth two.
                parent_ops[t.sid] = op
                parent_outcomes[t.sid] = outcome
                if not symbolic:
                    predicted_ancestor = _ancestor_prediction(c, op, outcome, started, delivery,
                        c.verify_private_compatible)
                    identified = predicted_ancestor.compatibility_identified
                    ancestor_survival[t.sid] = [predicted_ancestor]
                else:
                    subsequent = next((v for v in c.successors if v.window == t.window+1), None)
                    if subsequent is not None:
                        predicted_ancestor = _ancestor_prediction(c, op, outcome, started, delivery,
                            subsequent.verify_private_compatible, subsequent.unknown_private_probability,
                            direct=subsequent.direct_private_probability,
                            fallback=subsequent.fallback_private_probability,
                            inherit_current=subsequent.inherit_current_transition_model)
                        identified = predicted_ancestor.compatibility_identified
                        ancestor_survival[t.sid].append(predicted_ancestor)
                    else:
                        identified = False
                conditional_enabled |= identified
                parent_times[t.sid] = row_finish
                latest_delivery = max(latest_delivery, row_finish)
            cursor += outcome.lease
            paid_gpu_lease += outcome.lease
        wall = max(cursor, latest_delivery) - now
        selected_credit = cq if mode in ('service_cost', 'reserved_progress') else q
        expected_credit += mass*q
        current_credit += mass*cq
        successor_credit += mass*sq
        expected_private += mass*private_q
        expected_late += mass*late
        expected_wall += mass*wall
        expected_lease += mass*paid_gpu_lease
        prefix_rate += mass * (observed_credit_audio+selected_credit) / max(elapsed_seconds+wall, 1e-9)
    return {'expected_credit_audio': expected_credit, 'expected_current_credit_audio': current_credit,
        'expected_successor_credit_audio': successor_credit, 'expected_private_additional_credit_audio': expected_private,
        'expected_commit_late_audio': expected_late, 'expected_cut_wall_seconds': expected_wall,
        'expected_lease_seconds': expected_lease, 'finite_prefix_goodput': prefix_rate,
        'promise_violation_mass': promise_violation, 'promise_tardy_seconds': promise_tardy,
        'service_promises': {str(sid): _weighted_quantile(values, config.promise_quantile) for sid, values in per_sid.items()},
        'successor_finishes': successor_finishes, 'scenario_combinations': len(draws), 'scenario_model': draw_kind,
        'scenario_marginal_audit': scenario_audit,
        'conditional_private_prediction_enabled': conditional_enabled,
        'symbolic_steps': [{'operation': op, 'sids': [t.sid for t in rs], 'windows': [t.window for t in rs],
            'prediction_only': symbolic} for op, rs, symbolic, _ in steps]}


def choose_closed_loop(targets, contexts, *, now, mode, cal, limit,
                       observed_credit_audio, elapsed_seconds, state,
                       display_slo=2., config=None):
    """Return a currently legal first batch plus a fully paid forecast suffix.

    ``service_cost`` uses the same executor, risk model, future-work cost and
    service protection, preferring low complete-cut work with current-credit
    tie-breaking. ``inherit`` adds released-successor canonical deadline value.
    ``reserved_progress`` uses finite-prefix current credit without successor
    backpropagation or Private prediction, isolating the objective change.
    ``causal`` additionally forecasts the two legitimate Display paths when
    actual compatibility estimates exist. None is an online optimum.
    """
    config = config or PlannerConfig()
    if config.cache_mode not in ('reference','memoized') or config.guard_mode not in ('hard','soft','aging'):
        raise ValueError('undeclared planner implementation or service-guard variant')
    if mode not in ('service_cost', 'reserved_progress', 'inherit', 'causal'):
        raise ValueError('undeclared closed-loop policy')
    if limit < 1 or not all(math.isfinite(x) and x >= 0 for x in (observed_credit_audio, elapsed_seconds)):
        raise ValueError('positive limit and actual nonnegative prefix accounting required')
    targets = sorted(targets, key=lambda t: (t.deadline, t.ready, t.sid))[:limit]
    if not targets:
        return {'operation': None, 'sids': [], 'reason': 'closed-loop-no-released-target'}
    _validate(targets, contexts, now, config)
    contexts = {t.sid: replace(contexts[t.sid], successors=contexts[t.sid].successors[:config.max_successors_per_session])
                for t in targets}
    state.observe(contexts, now)
    forced = {t.sid for t in targets if state.records[contexts[t.sid].identity].deferrals >= config.max_deferrals}
    cache = {}
    plans, raw_count = _candidate_plans(targets, contexts, cal, now, display_slo, state, config, mode,
        cache if config.cache_mode == 'memoized' else None)
    evaluated = []
    for plan in plans:
        for interleave in ((False, True) if len(plan) > 1 and any(c.successors for c in contexts.values()) else (False,)):
            metrics = _evaluate(plan, contexts, now=now, mode=mode, cal=cal, display_slo=display_slo,
                observed_credit_audio=observed_credit_audio, elapsed_seconds=elapsed_seconds,
                state=state, config=config, interleave=interleave, cache=cache)
            first_ids = {t.sid for t in plan[0][1]}
            unpaid_forced = len(forced-first_ids)
            # A suffix promise is a *previously chosen* service commitment,
            # not a new Commit-first constraint imposed on a fresh decision.
            allowed_mass = (1-config.promise_quantile) * sum(
                state.records[c.identity].promised_finish is not None for c in contexts.values())
            promise_excess = max(0., metrics['promise_violation_mass']-allowed_mass-1e-12)
            common = (metrics['expected_commit_late_audio'], metrics['expected_cut_wall_seconds'],
                      plan[0][0] != 'generate', tuple(t.sid for t in plan[0][1]))
            perf = ((metrics['expected_cut_wall_seconds'], -metrics['finite_prefix_goodput'])
                    if mode == 'service_cost' else (-metrics['finite_prefix_goodput'],))
            promises = (round(promise_excess, 12), round(metrics['promise_tardy_seconds'], 12))
            if config.guard_mode == 'hard':
                key = (unpaid_forced,) + promises + perf + common
            elif config.guard_mode == 'soft':
                key = (unpaid_forced,) + perf + promises + common
            else:
                key = (unpaid_forced,) + perf + common
            evaluated.append((key, plan, metrics))
    key, plan, metrics = min(evaluated, key=lambda x: x[0])
    ranks = {str(t.sid): index for index, (_, rs) in enumerate(plan) for t in rs}
    symbolic = []
    for sid, c in contexts.items():
        for u in (c.successors[:config.max_successors_per_session] if mode in ('inherit', 'causal') else ()):
            values = metrics['successor_finishes'].get((sid, u.window), [])
            if values:
                symbolic.append({'sid': sid, 'epoch': c.identity.epoch,
                    'contract_digest': c.identity.contract_digest, 'frontier_end': u.frontier_end,
                    'promised_finish': _weighted_quantile(values, config.promise_quantile), 'rank': u.window,
                    'actual_parent_not_created': True})
    metrics.pop('successor_finishes')
    return {'operation': plan[0][0], 'sids': [t.sid for t in plan[0][1]],
        'reason': 'closed-loop-'+mode, 'decision_token': f'{state.scope}:{state.dispatches}:{now:.12f}',
        'score': metrics['finite_prefix_goodput'], 'planned_seconds': metrics['expected_lease_seconds'],
        'mode': mode, 'common_cut_sids': [t.sid for t in targets],
        'plan': [{'operation': op, 'sids': [t.sid for t in rs]} for op, rs in plan],
        'continuation_ranks': ranks, 'symbolic_service_promises': symbolic,
        'service_guard_active': bool(forced or any(state.records[c.identity].promised_finish is not None for c in contexts.values())),
        'forced_sids': sorted(forced), 'max_deferrals': config.max_deferrals,
        'service_obligations': [{'identity': asdict(c.identity), **asdict(state.records[c.identity])} for c in contexts.values()],
        'effective_deadlines': effective_deadlines(targets, contexts if mode in ('inherit', 'causal') else
            {sid: replace(c, successors=()) for sid, c in contexts.items()}, now=now, display_slo=display_slo),
        'symbolic_successors': [{'sid': sid, **asdict(u), 'requires_actual_parent': True,
            'creates_execution_permission': False} for sid, c in contexts.items() for u in c.successors[:config.max_successors_per_session]],
        'plans_considered_before_bound': raw_count, 'plans_evaluated': len(evaluated),
        'promise_quantile': config.promise_quantile,
        'service_promise_model': 'scenario_quantile_of_physical_outcome_row_time_envelope_plus_owner_delivery',
        'successor_cost_model': 'shared_calibrated_homogeneous_generation_batches_with_historical_prompt_feature_estimates',
        'prediction_only_not_authorization': True,
        'objective_scope': 'bounded finite-prefix scenario estimate with paid common released cut; not global GPU optimality',
        'future_parent_model': 'abstract_unknown_until_actual_trusted_admission',
        'successor_reward_used': mode in ('inherit', 'causal'),
        'private_path_prediction_used': mode == 'causal',
        'private_authority_joint_model': 'remaining_private_row_CDF_independent_of_Authority_scenarios_without_joint_calibration',
        'private_ancestor_survival_model': 'joint_accepted_early_fallback_late_row_CDF_survival_through_all_ancestors_not_envelope_free_intervals',
        'risk_model_shared': True, 'wait_seconds': 0., **metrics}
