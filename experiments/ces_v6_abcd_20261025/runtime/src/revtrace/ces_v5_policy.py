"""Small, shared-risk CES policy over actual residual deadline obligations.

This module only selects which trusted evidence computation to request.  It
cannot issue a certificate, install state, release a Worker lease, or predict a
future token.  The owner retains all existing admission and recovery checks.

The empirical scenarios are physical-batch observations.  A failed-row count
is retained jointly; unknown current failed-row identity is exchangeable.  This
is a cost approximation, not a prediction of which candidate will be accepted.
Different planned batches use independent historical scenario draws; temporal
correlation between serial batches is not represented by this minimal model.
Quantiles are empirical risk estimates and never deadline guarantees.
"""
from dataclasses import dataclass
from bisect import bisect_right
from functools import lru_cache
import itertools
import math
import numpy as np

from .ces_policy import Target, cost, rejection, choose as choose_legacy


@dataclass(frozen=True)
class V5Target(Target):
    display_met: bool = False
    display_expired: bool = False
    audio_weight: float = 2.0
    reject_age_seconds: float | None = None


@dataclass(frozen=True)
class BatchOutcome:
    weight: float
    lease: float
    early_row: float
    late_row: float
    reject_fraction: float
    source: str
    early_row_times: tuple = ()
    late_row_times: tuple = ()


def _finite(value, default=0.0):
    value = float(value)
    return value if math.isfinite(value) else float(default)


def _positive(value, default=1.0):
    return max(1e-6, _finite(value, default))


def _fraction(value, default=1.0):
    return min(1.0, max(0.0, _finite(value, default)))


def _bucket(table, n, minimum):
    """Nearest sufficiently supported size bucket, with explicit backoff.

    Buckets accept either a scenario list or {count: N, scenarios: [...]}; the
    latter keeps original sample support after representative compression.
    A global/default bucket is supported. Sparse empirical buckets are not
    silently called a tail calibration.
    """
    good = []
    for key, item in (table or {}).items():
        records = item.get('scenarios', []) if isinstance(item, dict) else item
        if not isinstance(records, list) or not records:
            continue
        count = item.get('count', len(records)) if isinstance(item, dict) else len(records)
        if count < minimum:
            continue
        try:
            size = int(key)
        except (TypeError, ValueError):
            size = n if key in ('global', 'default') else None
        if size is not None:
            # An exact bucket precedes global; a distant supported bucket is
            # a documented size transfer, not a same-shape observation.
            distance = abs(size - n) if key not in ('global', 'default') else 1e6
            good.append((distance, str(key), records, int(size)))
    if not good:
        return None, [], n
    _, key, records, size = min(good, key=lambda x: (x[0], x[1]))
    return key, records, size


def _ratio(model, operation, n):
    table = model.get('ratio_buckets', {}).get(operation, {})
    minimum = int(model.get('min_bucket_samples', 8))
    valid = []
    for key, item in table.items():
        if not isinstance(item, dict) or int(item.get('count', 0)) < minimum:
            continue
        try:
            distance = abs(int(key) - n)
        except (TypeError, ValueError):
            if key not in ('global', 'default'):
                continue
            distance = 1e6
        valid.append((distance, str(key), item))
    if not valid:
        return 1.0, 'uncalibrated'
    _, key, item = min(valid, key=lambda x: (x[0], x[1]))
    # Sparse backoff uses a conservative measured multiplier; no confidence
    # guarantee is inferred from a reported empirical p90/p95.
    factor = max(1.0, _positive(item.get('p90', item.get('median', 1.0))))
    return factor, 'ratio-backoff:' + key


def _weighted_quantile(values, q):
    values = sorted((float(v), float(w)) for v, w in values if w > 0)
    if not values:
        return 0.0
    total = sum(w for _, w in values)
    threshold = _fraction(q) * total
    accumulated = 0.0
    for value, weight in values:
        accumulated += weight
        if accumulated + 1e-12 >= threshold:
            return value
    return values[-1][0]


def _normalise(outcomes):
    outcomes = [o for o in outcomes if o.weight > 0 and math.isfinite(o.weight)]
    if not outcomes:
        raise ValueError('V5 risk calibration has no positive scenario weight')
    total = sum(o.weight for o in outcomes)
    return [BatchOutcome(o.weight / total, o.lease, o.early_row,
                         o.late_row, o.reject_fraction, o.source,
                         o.early_row_times, o.late_row_times)
            for o in outcomes]


def predict_batch(cal, operation, rows):
    """Return bounded weighted row/lease scenarios using shared calibration.

    verification_scenarios[n] records:
      weight, original_rows, failed_count, fallback_rows (optional),
      verify_ratio, fallback_ratio, verify_row_fraction,
      fallback_row_fraction, lease_overhead_s (optional).
    Ratios multiply the existing context-dependent phase cost prediction.
    generation_scenarios[n]: weight, lease_ratio, row_fraction.
    The owner must still observe actual Batch-drained before dispatching again.
    """
    if not rows:
        return []
    if operation not in ('generate', 'verify'):
        raise ValueError('unknown physical evidence operation')
    if operation == 'verify' and not all(t.candidate_ready for t in rows):
        raise ValueError('verification requires an actually ready candidate')
    n = len(rows)
    model = cal.get('v5_risk_model', {})
    minimum = int(model.get('min_bucket_samples', 8))
    table_name = 'generation_scenarios' if operation == 'generate' else 'verification_scenarios'
    key, records, bucket_size = _bucket(model.get(table_name, {}), n, minimum)
    # The calibration producer freezes no more than eight representative
    # records. Refuse an accidental large expansion in the online scheduler.
    if len(records) > 8:
        raise ValueError('V5 requires at most eight frozen scenarios per size bucket')
    outcomes = []
    if records:
        source = 'empirical:' + operation + ':' + str(key)
        for record in records:
            weight = max(0.0, _finite(record.get('weight', 1.0)))
            if operation == 'generate':
                lease = cost(cal, 'generate', n, rows) * _positive(record.get('lease_ratio', 1.0))
                finish = lease * _fraction(record.get('row_fraction', 1.0))
                times = tuple(lease * _fraction(f) for f in record.get('row_fractions', []))
                outcomes.append(BatchOutcome(weight, lease, finish, finish, 0.0, source, times, times))
                continue
            original_n = max(1, int(record.get('original_rows', bucket_size)))
            original_k = min(original_n, max(0, int(record.get('failed_count', 0))))
            # Do not transfer historical Session IDs or a future failure label.
            # Counts may transfer across size only as an explicit approximation.
            k = min(n, max(0, round(original_k * n / original_n)))
            if original_k and not k:
                k = 1
            fallback_original = int(record.get('fallback_rows', original_k))
            fallback_n = min(n, max(k, math.ceil(fallback_original * n / original_n))) if k else 0
            verify_phase = cost(cal, 'verify', n, rows) * _positive(record.get('verify_ratio', 1.0))
            fallback_phase = (cost(cal, 'fallback', fallback_n, rows)
                              * _positive(record.get('fallback_ratio', 1.0))) if k else 0.0
            overhead = max(0.0, _finite(record.get('lease_overhead_s', 0.0)))
            lease = verify_phase + fallback_phase + overhead
            early = verify_phase * _fraction(record.get('verify_row_fraction', 1.0))
            late = verify_phase + fallback_phase * _fraction(record.get('fallback_row_fraction', 1.0))
            early_times = tuple(verify_phase * _fraction(f)
                                for f in record.get('verify_row_fractions', []))
            late_times = tuple(verify_phase + fallback_phase * _fraction(f)
                               for f in record.get('fallback_row_fractions', []))
            outcomes.append(BatchOutcome(weight, lease, min(early, lease),
                                         min(late, lease), k / n, source,
                                         early_times, late_times))
        return _normalise(outcomes)

    multiplier, ratio_source = _ratio(model, operation, n)
    source = 'sparse-conservative:' + operation + ':' + ratio_source
    if operation == 'generate':
        lease = cost(cal, 'generate', n, rows) * multiplier
        # With insufficient actual row evidence, charge the final batch time.
        return [BatchOutcome(1.0, lease, lease, lease, 0.0, source)]
    p = _fraction(cal.get('global_reject', 1.0))
    verify_phase = cost(cal, 'verify', n, rows) * multiplier
    fallback_phase = cost(cal, 'fallback', n, rows) * multiplier
    # Perfectly correlated all/none failure is a declared sparse-risk model,
    # not an empirical claim and not the independent Bernoulli approximation.
    return _normalise([
        BatchOutcome(1.0 - p, verify_phase, verify_phase, verify_phase, 0.0, source),
        BatchOutcome(p, verify_phase + fallback_phase, verify_phase,
                     verify_phase + fallback_phase, 1.0, source),
    ])


def residual_credit(target, finish, display_slo):
    """Credit a pending admission once, using the actual display observation.

    A displayed target retains its Commit obligation. An irrecoverably late
    Display target gets zero immediate credit but remains in every full plan.
    Canonical publication may supply first display for an uncovered target;
    this forecast uses row completion and a shared owner-delivery allowance.
    """
    if finish > target.deadline:
        return 0.0
    if target.display_met:
        return max(0.0, target.audio_weight)
    if target.display_expired or finish > target.ready + display_slo:
        return 0.0
    return max(0.0, target.audio_weight)


@lru_cache(maxsize=8192)
def _row_cdf(outcome):
    """Exchangeable row CDF conditional on one whole physical-batch outcome.

    Keeping all observed row times preserves deadline indicator expectations;
    replacing these times with their mean would not. Current row identities
    remain unknown, so this is not an exact current-row completion forecast.
    """
    pairs = []
    for mass, values, fallback in (
        (1. - outcome.reject_fraction, outcome.early_row_times, outcome.early_row),
        (outcome.reject_fraction, outcome.late_row_times, outcome.late_row),
    ):
        if mass <= 0: continue
        values = values or (fallback,)
        for value in values: pairs.append((value, mass / len(values)))
    pairs.sort()
    times, cumulative, moments = [], [0.], [0.]
    for value, probability in pairs:
        times.append(value)
        cumulative.append(cumulative[-1] + probability)
        moments.append(moments[-1] + value * probability)
    return tuple(times), tuple(cumulative), tuple(moments)


def _row_moments(outcome, remaining):
    times, cumulative, moments = _row_cdf(outcome)
    k = bisect_right(times, remaining)
    on_time = min(1., max(0., cumulative[k]))
    tardy = max(0., moments[-1] - moments[k] - remaining * (1. - on_time))
    return on_time, tardy, moments[-1]


def _mixture_cdf(distribution):
    """Compile the marginal row distribution once per physical batch.

    Whole-outcome lease/row correlation is retained in the input. Linearity of
    expected per-row credit permits marginalizing this batch's row times before
    querying deadlines. The preceding batch's lease is separately convolved
    below, so this does not release a Worker at an early row completion.
    """
    times, masses = [], []
    mean = 0.0
    max_rows = []
    mean_rows = []
    for outcome in distribution:
        outcome_times, _, outcome_moments = _row_cdf(outcome)
        mean += outcome.weight * outcome_moments[-1]
        max_rows.append(max(outcome_times))
        mean_rows.append(outcome_moments[-1])
        for fraction, values, fallback in (
            (1.0 - outcome.reject_fraction, outcome.early_row_times, outcome.early_row),
            (outcome.reject_fraction, outcome.late_row_times, outcome.late_row),
        ):
            if fraction <= 0:
                continue
            values = values or (fallback,)
            probability = outcome.weight * fraction / len(values)
            times.extend(values)
            masses.extend([probability] * len(values))
    order = np.argsort(times, kind='stable')
    times = np.asarray(times, dtype=np.float64)[order]
    masses = np.asarray(masses, dtype=np.float64)[order]
    return {
        'times': times,
        'cumulative': np.concatenate(([0.0], np.cumsum(masses))),
        'moments': np.concatenate(([0.0], np.cumsum(masses * times))),
        'mass': sum(o.weight for o in distribution),
        'mean': mean,
        'max_rows': max_rows,
        'mean_rows': mean_rows,
    }


def _mixture_queries(cdf, remaining):
    """Vectorized weighted on-time probability and positive lateness moment."""
    k = np.searchsorted(cdf['times'], remaining, side='right')
    on_time = np.clip(cdf['cumulative'][k], 0.0, cdf['mass'])
    tardy = np.maximum(0.0, cdf['mean'] - cdf['moments'][k]
                       - remaining * (cdf['mass'] - on_time))
    # Every constituent scalar positive-part moment is exactly zero past the
    # largest row time. Enforce that identity before reduction to avoid tiny
    # cancellation residuals changing a later deterministic tie break.
    tardy = np.where(remaining >= cdf['times'][-1], 0.0, tardy)
    return on_time, tardy


def _plan_metrics(plan, now, cal, display_slo, cache):
    batches = [(op, tuple(rows)) for op, rows in plan if rows]
    distributions, cdfs = [], []
    for operation, rows in batches:
        key = operation, tuple(t.sid for t in rows)
        if key not in cache:
            cache[key] = predict_batch(cal, operation, rows)
        distribution = cache[key]
        cdf_key = ('__v5_row_mixture__',) + key
        if cdf_key not in cache:
            cache[cdf_key] = _mixture_cdf(distribution)
        distributions.append(distribution)
        cdfs.append(cache[cdf_key])
    credit = late_audio = tardy_audio_seconds = expected_lease = expected_wall = 0.0
    lease_distribution = []
    per_row = {t.sid: {'predicted_finish_seconds': 0.0, 'predicted_credit_audio': 0.0}
               for _, rows in batches for t in rows}
    delivery = max(0.0, _finite(cal.get('v5_risk_model', {}).get('owner_delivery_seconds', 0.0)))

    # At most two batches are currently enumerated. Prefix start times retain
    # each complete preceding physical lease; row expectations are linear and
    # need not be recomputed for every unrelated later outcome and target.
    starts = np.asarray([now], dtype=np.float64)
    start_weights = np.asarray([1.0], dtype=np.float64)
    for batch_index, ((_, rows), distribution, cdf) in enumerate(zip(batches, distributions, cdfs)):
        deadlines = np.asarray([t.deadline for t in rows], dtype=np.float64)
        dues = np.asarray([t.deadline if t.display_met else min(t.deadline, t.ready + display_slo)
                           for t in rows], dtype=np.float64)
        weights = np.asarray([t.audio_weight for t in rows], dtype=np.float64)
        expired = np.asarray([t.display_expired for t in rows], dtype=bool)
        # The subtraction order matches the scalar deadline test even when
        # now is a large monotonic timestamp and deadlines lie on a boundary.
        remaining = (deadlines[None, :] - starts[:, None]) - delivery
        commit_probability, tardy = _mixture_queries(cdf, remaining)
        display_remaining = (dues[None, :] - starts[:, None]) - delivery
        earned_probability = _mixture_queries(cdf, display_remaining)[0]
        earned_probability[:, expired] = 0.0
        future_mass = math.prod(sum(o.weight for o in later)
                                for later in distributions[batch_index + 1:])
        expected_earned = (start_weights @ earned_probability) * weights * future_mass
        expected_late = (start_weights @ (cdf['mass'] - commit_probability)) * weights * future_mass
        expected_tardy = (start_weights @ tardy) * weights * future_mass
        credit += float(np.sum(expected_earned))
        late_audio += float(np.sum(expected_late))
        tardy_audio_seconds += float(np.sum(expected_tardy))
        for i, target in enumerate(rows):
            per_row[target.sid]['predicted_credit_audio'] = float(expected_earned[i])
        if batch_index + 1 < len(batches):
            starts = np.asarray([float(start) + outcome.lease for start in starts
                                 for outcome in distribution], dtype=np.float64)
            start_weights = np.asarray([float(weight) * outcome.weight for weight in start_weights
                                        for outcome in distribution], dtype=np.float64)

    # The complete joint scenarios are retained for physical lease quantiles
    # and common-cut wall (including the latest owner delivery). These maxima
    # are nonlinear; replacing them with marginal means would change the model.
    indexed = [tuple(enumerate(ds)) for ds in distributions]
    batch_finish_means = [0.0] * len(batches)
    for indexed_outcomes in itertools.product(*indexed):
        outcomes = [outcome for _, outcome in indexed_outcomes]
        probability = math.prod(o.weight for o in outcomes)
        cursor = now
        latest_delivery = now
        for batch_index, (cdf, (outcome_index, outcome)) in enumerate(zip(cdfs, indexed_outcomes)):
            latest_delivery = max(latest_delivery, cursor + cdf['max_rows'][outcome_index] + delivery)
            # Keep this cheap scalar reduction in its original arithmetic
            # order. Reassociating a large absolute monotonic clock can lose
            # an ulp even though all relative deadline probabilities agree.
            batch_finish_means[batch_index] += probability * (cursor + cdf['mean_rows'][outcome_index] + delivery)
            cursor += outcome.lease
        elapsed = cursor - now
        expected_lease += probability * elapsed
        expected_wall += probability * (max(cursor, latest_delivery) - now)
        lease_distribution.append((elapsed, probability))
    for (_, rows), finish in zip(batches, batch_finish_means):
        for target in rows:
            per_row[target.sid]['predicted_finish_seconds'] = finish
    risk_q = _fraction(cal.get('v5_risk_model', {}).get('risk_quantile', 0.9), .9)
    return {
        'expected_credit_audio': credit,
        'expected_commit_late_audio': late_audio,
        'expected_commit_tardy_audio_seconds': tardy_audio_seconds,
        'expected_lease_seconds': expected_lease,
        'expected_cut_wall_seconds': expected_wall,
        'risk_lease_seconds': _weighted_quantile(lease_distribution, risk_q),
        'risk_quantile': risk_q,
        'credit_per_lease_second': credit / max(expected_lease, 1e-9),
        'credit_per_cut_wall_second': credit / max(expected_wall, 1e-9),
        'row_predictions': per_row,
        'scenario_combinations': len(lease_distribution),
        'risk_sources': sorted({o.source for ds in distributions for o in ds}),
    }


def _plans(targets, cal, now, display_slo):
    ready = [t for t in targets if t.candidate_ready]
    ranked_orders = [
        sorted(ready, key=lambda t: (t.deadline, t.sid)),
        sorted(ready, key=lambda t: (rejection(cal, t, True), t.deadline, t.sid)),
        sorted(ready, key=lambda t: (t.candidate_tokens, t.deadline, t.sid)),
    ]
    seen = set()

    def make(verify_sids):
        verification = [t for t in targets if t.sid in verify_sids]
        generation = [t for t in targets if t.sid not in verify_sids]
        orders = [(('verify', verification), ('generate', generation))]
        if verification and generation:
            orders.append((('generate', generation), ('verify', verification)))
        return orders

    raw_plans = []
    for ranked in ranked_orders:
        for k in range(len(ranked) + 1):
            raw_plans.extend(make({t.sid for t in ranked[:k]}))
    # Real alternative dispatch sets: homogeneous G/G (or V/V) splitting.
    # Merely permuting a full n-row batch cannot create an earlier lease release.
    # All policies receive this same bounded candidate-action family.
    cuts = sorted({k for k in (1, 2, 4, 8, len(targets) // 2) if 0 < k < len(targets)})
    split_orders = [
        sorted(targets, key=lambda t: (t.deadline, t.sid)),
        sorted(targets, key=lambda t: (t.display_expired, t.display_met,
                                       t.ready + display_slo, t.deadline, t.sid)),
        sorted(targets, key=lambda t: (t.audio_seconds, t.prompt_tokens, t.sid)),
    ]
    for ordered in split_orders:
        for k in cuts:
            first_ids = {t.sid for t in ordered[:k]}
            # Preserve the original within-batch ordering. Alternative physical
            # layouts still require their own actual input/output GPU audit.
            first = [t for t in targets if t.sid in first_ids]
            rest = [t for t in targets if t.sid not in first_ids]
            raw_plans.append((('generate', first), ('generate', rest)))
            raw_plans.append((('generate', rest), ('generate', first)))
            if len(ready) == len(targets):
                raw_plans.append((('verify', first), ('verify', rest)))
                raw_plans.append((('verify', rest), ('verify', first)))
    # Preserve the exact old joint-cost action as a feasible prefix, paying for
    # all remaining current targets. Any legacy candidate wait becomes direct
    # work here because the minimal v5 does not idle for new candidates.
    legacy_targets = [Target(**{name: getattr(t, name) for name in Target.__dataclass_fields__})
                      for t in targets]
    old = choose_legacy(legacy_targets, now=now, mode='cost', cal=cal,
                        limit=len(targets), display_slo=display_slo, wait_cap=0.0)
    if old['operation']:
        selected = set(old['sids'])
        first = [t for t in targets if t.sid in selected]
        rest = [t for t in targets if t.sid not in selected]
        raw_plans.append(((old['operation'], first), ('generate', rest)))
    for plan in raw_plans:
        plan = tuple((op, tuple(rows)) for op, rows in plan if rows)
        key = tuple((op, tuple(t.sid for t in rows)) for op, rows in plan)
        if key not in seen:
            seen.add(key)
            yield plan


def choose_v5(targets, *, now, mode, cal, limit, display_slo=2.0, wait_cap=0.0,
              bound_pruning=True):
    """Select a homogeneous first operation of a complete common-cut plan.

    ``risk_cost`` first minimizes predicted Commit-late audio and then physical
    tail/mean cost. ``progress`` first maximizes residual joint deadline credit
    per predicted common-cut wall, with Commit lateness as a secondary metric.
    A Commit deadline is a performance obligation, not a safety permission.
    ``progress_joint`` has the same GPU1 policy; GPU0
    selection is separately controlled and measured by its owner.

    All current selected targets appear exactly once in every plan, including
    zero-credit overdue predecessors. No future child/output is simulated.
    ``wait_cap`` is accepted for API compatibility; this version never waits.
    """
    if mode not in ('risk_cost', 'progress', 'progress_joint'):
        raise ValueError('undeclared V5 policy')
    if limit < 1:
        raise ValueError('batch limit must be positive')
    targets = sorted(targets, key=lambda t: (t.deadline, t.ready, t.sid))[:limit]
    if not targets:
        return {'operation': None, 'sids': [], 'reason': 'v5-no-released-target'}
    if len({t.sid for t in targets}) != len(targets):
        raise ValueError('at most one pending target per session')
    for target in targets:
        if target.ready > now:
            raise ValueError('unreleased target cannot enter V5 scheduling')
        if target.display_met and target.display_expired:
            raise ValueError('display status must be unambiguous')
        if target.audio_weight < 0 or not math.isfinite(target.audio_weight):
            raise ValueError('audio weight must be finite and nonnegative')
    evaluated = []
    total_plans = pruned_plans = 0
    incumbent = None
    cache = {}
    for plan in _plans(targets, cal, now, display_slo):
        total_plans += 1
        # Safe bounds inside this *same* frozen cost model, not a real-time
        # guarantee: credit cannot exceed all still-creditable audio, and
        # common-cut wall cannot be shorter than paid physical lease time.
        # Prune only strict inferiority with a numerical margin; ties still
        # receive full row-CDF evaluation and deterministic secondary ordering.
        if bound_pruning and incumbent is not None:
            ds = []
            for op, rs in plan:
                cache_key = op, tuple(t.sid for t in rs)
                if cache_key not in cache:
                    cache[cache_key] = predict_batch(cal, op, rs)
                ds.append(cache[cache_key])
            if mode != 'risk_cost':
                lower_wall = sum(sum(o.weight * o.lease for o in d) for d in ds)
                # Actual scenario wall uses additions to a monotonic clock;
                # allow their floating-point cancellation before using a bound.
                lower_wall -= 4. * math.ulp(float(now)) * len(ds) + 1e-12
                max_credit = sum(t.audio_weight for t in targets if not t.display_expired) + 1e-10
                upper_rate = max_credit / max(lower_wall, 1e-9)
                if upper_rate < -incumbent[0] - 1e-10:
                    pruned_plans += 1
                    continue
            elif incumbent[0] == 0.0:
                costs = []
                for outcomes in itertools.product(*ds):
                    cursor = now
                    for outcome in outcomes: cursor += outcome.lease
                    costs.append((cursor - now, math.prod(o.weight for o in outcomes)))
                tail = _weighted_quantile(costs, _fraction(cal.get('v5_risk_model', {}).get('risk_quantile', .9)))
                if tail > incumbent[1] + 1e-10:
                    pruned_plans += 1
                    continue
        metrics = _plan_metrics(plan, now, cal, display_slo, cache)
        first_op, first_rows = plan[0]
        # Quantize only floating arithmetic noise in comparisons, not model
        # measurements. The empirical scenario metrics remain unrounded logs.
        commit_risk = round(metrics['expected_commit_late_audio'], 12)
        common_tail = (metrics['risk_lease_seconds'], metrics['expected_cut_wall_seconds'],
                       metrics['expected_commit_tardy_audio_seconds'],
                       first_op != 'generate', tuple(t.sid for t in first_rows))
        key = ((commit_risk,) + common_tail if mode == 'risk_cost' else
               (-round(metrics['credit_per_cut_wall_second'], 12), commit_risk) + common_tail)
        evaluated.append((key, plan, metrics))
        if incumbent is None or key < incumbent: incumbent = key
    key, plan, metrics = min(evaluated, key=lambda item: item[0])
    operation, rows = plan[0]
    return {
        'operation': operation,
        'sids': [t.sid for t in rows],
        'reason': 'v5-shared-risk-cost' if mode == 'risk_cost' else 'v5-residual-legal-progress',
        'score': key[0],
        'planned_seconds': metrics['expected_lease_seconds'],
        'partitions_evaluated': total_plans,
        'plans_fully_evaluated': len(evaluated),
        'plans_pruned_by_model_bound': pruned_plans,
        'common_cut_sids': [t.sid for t in targets],
        'plan': [{'operation': op, 'sids': [t.sid for t in rs]} for op, rs in plan],
        'risk_model_shared': True,
        'zero_residual_credit': metrics['expected_credit_audio'] <= 1e-12,
        'actual_display_met_targets': sum(t.display_met for t in targets),
        'display_expired_targets': sum(t.display_expired for t in targets),
        'display_pending_targets': sum(not t.display_met and not t.display_expired for t in targets),
        'failure_identity_model': 'exchangeable_count_not_state_conditioned',
        'between_batch_scenario_model': 'independent_historical_draws',
        'prediction_only_not_authorization': True,
        'objective_scope': 'local ratio of expected residual credit to expected common-cut wall; not global finite-run optimality',
        'row_completion_model': 'empirical_row_CDF_conditional_on_physical_batch_outcome',
        'wait_seconds': 0.0,
        **metrics,
    }
