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


def _plan_metrics(plan, now, cal, display_slo, cache):
    batches = [(op, tuple(rows)) for op, rows in plan if rows]
    distributions = []
    for operation, rows in batches:
        key = operation, tuple(t.sid for t in rows)
        if key not in cache:
            cache[key] = predict_batch(cal, operation, rows)
        distributions.append(cache[key])
    credit = late_audio = tardy_audio_seconds = expected_lease = expected_wall = 0.0
    lease_distribution = []
    per_row = {t.sid: {'predicted_finish_seconds': 0.0, 'predicted_credit_audio': 0.0}
               for _, rows in batches for t in rows}
    delivery = max(0.0, _finite(cal.get('v5_risk_model', {}).get('owner_delivery_seconds', 0.0)))
    for outcomes in itertools.product(*distributions):
        probability = math.prod(o.weight for o in outcomes)
        cursor = now
        latest_delivery = now
        scenario_credit = scenario_late = scenario_tardy = 0.0
        for (_, rows), outcome in zip(batches, outcomes):
            for target in rows:
                commit_probability, tardy, mean_row = _row_moments(
                    outcome, target.deadline - cursor - delivery)
                if target.display_expired:
                    earned = 0.
                else:
                    due = target.deadline if target.display_met else min(target.deadline, target.ready + display_slo)
                    earned = target.audio_weight * _row_moments(outcome, due - cursor - delivery)[0]
                scenario_credit += earned
                scenario_late += target.audio_weight * (1. - commit_probability)
                scenario_tardy += target.audio_weight * tardy
                per_row[target.sid]['predicted_finish_seconds'] += probability * (cursor + mean_row + delivery)
                per_row[target.sid]['predicted_credit_audio'] += probability * earned
            latest_delivery = max(latest_delivery, cursor + max(_row_cdf(outcome)[0]) + delivery)
            # An early receipt never releases the still-running physical batch.
            cursor += outcome.lease
        elapsed = cursor - now
        expected_lease += probability * elapsed
        expected_wall += probability * (max(cursor, latest_delivery) - now)
        credit += probability * scenario_credit
        late_audio += probability * scenario_late
        tardy_audio_seconds += probability * scenario_tardy
        lease_distribution.append((elapsed, probability))
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


def choose_v5(targets, *, now, mode, cal, limit, display_slo=2.0, wait_cap=0.0):
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
    cache = {}
    for plan in _plans(targets, cal, now, display_slo):
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
    key, plan, metrics = min(evaluated, key=lambda item: item[0])
    operation, rows = plan[0]
    return {
        'operation': operation,
        'sids': [t.sid for t in rows],
        'reason': 'v5-shared-risk-cost' if mode == 'risk_cost' else 'v5-residual-legal-progress',
        'score': key[0],
        'planned_seconds': metrics['expected_lease_seconds'],
        'partitions_evaluated': len(evaluated),
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
