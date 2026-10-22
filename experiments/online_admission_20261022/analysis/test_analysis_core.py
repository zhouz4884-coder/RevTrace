"""CPU synthetic denominator/estimator controls; zero model invocations."""
import math
from analysis_core import (quantile, quality_counts, good_audio, relative_change,
                           paired_bootstrap, classify_gates)


def test_incomplete_population_not_dropped():
    assert math.isinf(quantile([.1, .2, None], .99))
    assert quantile([1, 2, 3], .5) == 2
    assert quantile([math.inf, math.inf], .99) == math.inf
    assert good_audio([{'display': None, 'commit': .1, 'audio_seconds': 2},
                       {'display': .1, 'commit': .1, 'audio_seconds': 2}]) == 2


def test_quality_integer_denominators():
    q = quality_counts('one two three', 'one four three')
    assert q['WER_errors'] == 1 and q['reference_words'] == 3
    assert quality_counts('A b', 'a b')['WER_errors'] == 0


def fixture_arms():
    baseline, new = {}, {}
    for r in range(3):
        baseline[r] = {'wall': 10., 'energy': 100., 'sources': {}}
        new[r] = {'wall': 10., 'energy': 80., 'sources': {}}
        for s in range(16):
            q = {'WER_errors': 1, 'reference_words': 10,
                 'CER_errors': 1, 'reference_characters': 30}
            baseline[r]['sources'][str(s)] = dict(q, frontiers=[
                {'display': 1., 'commit': 2., 'audio_seconds': 2.}])
            new[r]['sources'][str(s)] = dict(q, frontiers=[
                {'display': 1., 'commit': 4., 'audio_seconds': 2.}])
    return baseline, new


def test_energy_win_not_mislabeled_latency_pareto():
    e = paired_bootstrap(fixture_arms(), samples=40)
    g = classify_gates(e, all_paired_goodput_positive=False,
                       both_all_slo_pass=True, safety_pass=True)
    assert g['shared_service_contract_cost_gate']
    assert not g['strict_energy_latency_pareto_gate']
    assert not g['primary_goodput_gate']
    assert g['literal_quality_no_loss_point']
    assert abs(e['paired_median']['energy'] + .2) < 1e-12


def test_quality_tolerance_is_not_no_loss():
    a, b = fixture_arms()
    for r in b:
        for s in b[r]['sources']:
            for arm in [a, b]:
                arm[r]['sources'][s]['reference_words'] = 1000
            b[r]['sources'][s]['WER_errors'] = 2
    e = paired_bootstrap((a, b), samples=20)
    g = classify_gates(e, all_paired_goodput_positive=False,
                       both_all_slo_pass=True, safety_pass=True)
    assert g['quality_tolerance_noninferiority']
    assert not g['literal_quality_no_loss_point']
    assert g['not_an_unqualified_quality_preserving_claim']


def test_missing_slo_and_safety_cannot_be_rescued_by_energy():
    e = paired_bootstrap(fixture_arms(), samples=20)
    g = classify_gates(e, all_paired_goodput_positive=True,
                       both_all_slo_pass=False, safety_pass=False)
    assert not any(g[k] for k in ['primary_goodput_gate',
               'strict_energy_latency_pareto_gate', 'shared_service_contract_cost_gate'])
    assert relative_change(0, 0) == 0
    assert math.isinf(relative_change(1, 0))


def test_repeated_bootstrap_is_frozen():
    assert paired_bootstrap(fixture_arms(), samples=20) == paired_bootstrap(fixture_arms(), samples=20)


def test_raw_auditor_p99_keeps_missing_without_changing_quantile():
    import ast
    from pathlib import Path
    source = ast.parse(Path(__file__).with_name('audit_online.py').read_text(encoding='utf-8'))
    fn = next(x for x in source.body if isinstance(x, ast.FunctionDef) and x.name == 'q99')
    ns = {'math': math}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<auditor-p99>', 'exec'), ns)
    for values in [[1, 2, 3], [1, 2, None], [1] * 199 + [None], [None], [None, None]]:
        expected = quantile(values, .99)
        assert ns['q99'](values) == (None if math.isinf(expected) else expected)
