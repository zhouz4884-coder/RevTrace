"""Frozen scalar plan-metric reference from runtime commit 0cc42df.

CPU equivalence/performance tests only. This preserves the original statistical
definition while the production implementation changes its computation order.
Unchanged cost/scenario/quantile helpers are imported from the runtime module.
"""
from bisect import bisect_right
from functools import lru_cache
import itertools
import math

from revtrace.ces_v5_policy import predict_batch, _finite, _fraction, _weighted_quantile

REFERENCE_COMMIT = '0cc42dfa18e291a84b1b89e20fdd04f08fa15c37'


@lru_cache(maxsize=8192)
def _row_cdf(outcome):
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


def scalar_plan_metrics(plan, now, cal, display_slo, cache):
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
