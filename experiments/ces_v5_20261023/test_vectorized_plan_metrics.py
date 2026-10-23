"""Shared statistical model equivalence, CPU only, against frozen 0cc42df."""
from dataclasses import replace
from pathlib import Path
import ast
import hashlib
import inspect
import json
import random
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runtime' / 'src'))
import revtrace.ces_v5_policy as policy
from scalar_reference import scalar_plan_metrics, REFERENCE_COMMIT


def calibration(rng):
    tables = {name: {str(n): rng.uniform(.05, .4) + n * coefficient for n in range(1, 17)}
              for name, coefficient in [('generate', .12), ('verify', .018),
                                         ('fallback', .11), ('proposal', .08)]}
    model = {'schema_version': 1, 'min_bucket_samples': 1, 'risk_quantile': rng.choice([.5, .9, .95]),
             'owner_delivery_seconds': rng.choice([0, .005, .05, .4]),
             'generation_scenarios': {}, 'verification_scenarios': {}}
    for n in range(1, 17):
        generate, verify = [], []
        for _ in range(rng.choice([1, 2, 4, 8])):
            fractions = [rng.uniform(.05, 1) for _ in range(n)]
            generate.append({'weight': rng.uniform(.01, 2), 'original_rows': n,
                             'lease_ratio': rng.uniform(.3, 2), 'row_fraction': sum(fractions) / n,
                             'row_fractions': fractions})
            failed = rng.randrange(n + 1)
            successful_fractions = [rng.uniform(.05, 1) for _ in range(n - failed)]
            failed_fractions = [rng.uniform(.05, 1) for _ in range(failed)]
            verify.append({'weight': rng.uniform(.01, 2), 'original_rows': n,
                           'failed_count': failed, 'fallback_rows': failed,
                           'verify_ratio': rng.uniform(.3, 2), 'fallback_ratio': rng.uniform(.3, 2),
                           'verify_row_fraction': .5, 'fallback_row_fraction': .7,
                           'verify_row_fractions': successful_fractions,
                           'fallback_row_fractions': failed_fractions,
                           'lease_overhead_s': rng.choice([0, .005, .02])})
        model['generation_scenarios'][str(n)] = {'count': 40, 'scenarios': generate}
        model['verification_scenarios'][str(n)] = {'count': 40, 'scenarios': verify}
    return {'global_reject': rng.uniform(0, 1), 'causal_reject': {},
            'cost_seconds': tables, 'v5_risk_model': model}


def fixture(rng, case):
    n = rng.randrange(1, 9)
    # Include both near-zero and nonzero monotonic clocks; extreme clock-scale
    # precision is separately tested at exact row deadline boundaries.
    now = rng.uniform(0, 100)
    cal = calibration(rng)
    rows = []
    for sid in range(n):
        status = rng.randrange(3)
        rows.append(policy.V5Target(
            sid, rng.randrange(1, 20), now - rng.uniform(0, 8), now + rng.uniform(-1, 8),
            rng.random() < .7, rng.random() < .5, rng.random() < .25,
            rng.randrange(1, 257), 0, 0, None,
            audio_seconds=rng.uniform(2, 60), interval_seconds=2, prompt_tokens=rng.randrange(257),
            display_met=status == 1, display_expired=status == 2,
            audio_weight=rng.uniform(.1, 2)))
    cut = rng.randrange(1, n + 1)
    groups = [rows[:cut]] + ([rows[cut:]] if cut < n else [])
    plan = []
    for group in groups:
        operation = rng.choice(['verify', 'generate'])
        if operation == 'verify':
            group = [replace(t, candidate_ready=True) for t in group]
        plan.append((operation, tuple(group)))
    return tuple(plan), rows, now, cal


def compare(left, right, path='root', tolerance=1e-10):
    if isinstance(left, dict):
        assert left.keys() == right.keys(), path
        return max((compare(left[k], right[k], path + '.' + str(k), tolerance) for k in left), default=0)
    if isinstance(left, list):
        assert len(left) == len(right), path
        return max((compare(a, b, path, tolerance) for a, b in zip(left, right)), default=0)
    if isinstance(left, (float, int)) and not isinstance(left, bool):
        error = abs(float(left) - float(right))
        assert error <= tolerance, (path, left, right, error)
        return error
    assert left == right, (path, left, right)
    return 0


def equivalence_audit(cases=240):
    rng = random.Random(2026102305)
    fast = policy._plan_metrics
    max_error = 0.0
    modes = ['risk_cost', 'progress', 'progress_joint']
    for i in range(cases):
        plan, rows, now, cal = fixture(rng, i)
        expected = scalar_plan_metrics(plan, now, cal, 2.0, {})
        actual = fast(plan, now, cal, 2.0, {})
        max_error = max(max_error, compare(actual, expected, 'metrics.' + str(i)))
        mode = modes[i % 3]
        try:
            policy._plan_metrics = scalar_plan_metrics
            scalar_decision = policy.choose_v5(rows, now=now, mode=mode, cal=cal, limit=16)
        finally:
            policy._plan_metrics = fast
        decision = policy.choose_v5(rows, now=now, mode=mode, cal=cal, limit=16)
        max_error = max(max_error, compare(decision, scalar_decision, 'decision.' + str(i)))
    return {'evidence': 'CPU statistical model equivalence only',
            'reference_commit': REFERENCE_COMMIT, 'cases': cases,
            'decision_modes': modes, 'maximum_absolute_numeric_error': max_error,
            'tolerance': 1e-10, 'all_metrics_and_decisions_equal_within_tolerance': True}


def test_frozen_reference_matches_commit_ast():
    archived = ROOT / 'reference_source' / 'ces_v5_policy_0cc42df.py'
    if archived.exists():
        raw = archived.read_bytes()
    else:
        raw = subprocess.check_output(['git','show',REFERENCE_COMMIT+':src/revtrace/ces_v5_policy.py'],cwd=ROOT/'runtime')
    assert hashlib.sha256(raw).hexdigest() == '0a92ac9015908731d1ecd8217aba8d2771740e4d33fc812bdff77871c7bff986'
    original = raw.decode('utf-8')
    source_ast = next(n for n in ast.parse(original).body
                      if isinstance(n, ast.FunctionDef) and n.name == '_plan_metrics')
    reference_ast = ast.parse(inspect.getsource(scalar_plan_metrics)).body[0]
    source_ast.name = reference_ast.name
    assert ast.dump(source_ast, include_attributes=False) == ast.dump(reference_ast, include_attributes=False)


def test_240_random_complete_plan_metrics_and_decisions():
    result = equivalence_audit()
    assert result['cases'] >= 200
    assert result['all_metrics_and_decisions_equal_within_tolerance']


def test_model_bound_pruning_matches_unpruned_complete_search():
    rng = random.Random(2026102319)
    for i in range(160):
        _, rows, now, cal = fixture(rng, i)
        if i % 4 == 0:
            delta = 4_000_000.
            now += delta
            rows = [replace(t, ready=t.ready+delta, deadline=t.deadline+delta) for t in rows]
        mode = ['risk_cost', 'progress', 'progress_joint'][i % 3]
        full = policy.choose_v5(rows,now=now,mode=mode,cal=cal,limit=16,bound_pruning=False)
        bounded = policy.choose_v5(rows,now=now,mode=mode,cal=cal,limit=16,bound_pruning=True)
        for d in [full,bounded]:
            d.pop('plans_fully_evaluated')
            d.pop('plans_pruned_by_model_bound')
        compare(full,bounded,'bound-pruning.'+str(i),tolerance=1e-10)


@pytest.mark.parametrize('now', [0.0, 1.0, 10000.0, 1000000.0])
@pytest.mark.parametrize('delivery', [0.0, .001, .1])
def test_exact_deadline_boundaries(now, delivery):
    rng = random.Random(21)
    cal = calibration(rng)
    cal['v5_risk_model']['owner_delivery_seconds'] = delivery
    a = policy.V5Target(0, 1, now - 1, now + 8, True, False, False, 20, 0, 0, None)
    b = replace(a, sid=1)
    first = policy.predict_batch(cal, 'verify', [a])[0]
    second = policy.predict_batch(cal, 'generate', [b])[0]
    boundary = now + first.lease + second.early_row_times[0] + delivery
    b = replace(b, deadline=boundary, display_met=True)
    plan = (('verify', [a]), ('generate', [b]))
    compare(policy._plan_metrics(plan, now, cal, 2, {}),
            scalar_plan_metrics(plan, now, cal, 2, {}), 'exact-boundary',
            tolerance=1e-10)


if __name__ == '__main__':
    print(json.dumps(equivalence_audit(), indent=2))
