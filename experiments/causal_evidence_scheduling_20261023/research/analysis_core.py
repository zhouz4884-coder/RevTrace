"""Pure analysis helpers. Synthetic tests are CPU evidence, not serving runs."""
from __future__ import annotations
import math
import random
import re
import unicodedata


def quantile(values, q):
    if not values:
        raise ValueError('empty population')
    xs = sorted(math.inf if v is None else float(v) for v in values)
    p = (len(xs) - 1) * q
    i = int(p)
    f = p - i
    if not f or i == len(xs) - 1:
        return xs[i]
    if math.isinf(xs[i + 1]):
        return math.inf
    return xs[i] + f * (xs[i + 1] - xs[i])


def median(values):
    return quantile(values, .5)


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def normalized_units(text, words=True):
    text = unicodedata.normalize('NFKC', text).lower()
    return re.findall(r"[a-z0-9']+", text) if words else [c for c in text if c.isalnum()]


def quality_counts(reference, text):
    rw, tw = normalized_units(reference), normalized_units(text)
    rc, tc = normalized_units(reference, False), normalized_units(text, False)
    return {'WER_errors': edit_distance(rw, tw), 'reference_words': len(rw),
            'CER_errors': edit_distance(rc, tc), 'reference_characters': len(rc)}


def good_audio(frontiers, display=2., commit=8.):
    return sum(q['audio_seconds'] for q in frontiers
               if q['display'] is not None and q['commit'] is not None
               and q['display'] <= display and q['commit'] <= commit)


def source_error_ratio(rows, prefix):
    denominator = sum(r['reference_words' if prefix == 'WER' else 'reference_characters'] for r in rows)
    if denominator <= 0:
        raise ValueError('empty quality reference')
    return sum(r[prefix + '_errors'] for r in rows) / denominator


def relative_change(new, old):
    if old == 0:
        return 0. if new == 0 else math.inf
    if not math.isfinite(new) or not math.isfinite(old):
        return 0. if new == old else math.inf if new > old else -1.
    return new / old - 1.


def percentile_interval(values):
    return [quantile(values, .025), quantile(values, .975)]


def paired_bootstrap(arms, *, samples=10000, seed=20261022):
    """arms=(baseline,dgft), each repeat -> wall, energy, sources -> records.

    Source record contains frontiers and quality integer counts. Source draw
    shared across arms/repeats. No schedule re-execution is implied.
    """
    baseline, new = arms
    repeats = sorted(baseline)
    assert len(repeats) == 3 and repeats == sorted(new)
    sources = sorted(baseline[repeats[0]]['sources'])
    assert len(sources) == 16
    for arm in arms:
        for r in repeats:
            assert sorted(arm[r]['sources']) == sources

    def metric(arm, r, selected):
        run = arm[r]
        data = [run['sources'][s] for s in selected]
        fs = [f for d in data for f in d['frontiers']]
        return {'goodput': good_audio(fs) / run['wall'],
                'display': quantile([f['display'] for f in fs], .99),
                'commit': quantile([f['commit'] for f in fs], .99),
                'WER': source_error_ratio(data, 'WER'),
                'CER': source_error_ratio(data, 'CER'),
                'energy': run['energy']}

    def effect(ri, si):
        delta = {k: [] for k in ['goodput', 'display', 'commit', 'WER', 'CER', 'energy']}
        for r in ri:
            a, b = metric(baseline, r, si), metric(new, r, si)
            for key in delta:
                value = b[key] - a[key] if key in ['WER', 'CER'] else relative_change(b[key], a[key])
                delta[key].append(value)
        return {k: median(v) for k, v in delta.items()}

    observed = effect(repeats, sources)
    rng = random.Random(seed)
    draws = {k: [] for k in observed}
    for _ in range(samples):
        ri = rng.choices(repeats, k=3)
        si = rng.choices(sources, k=len(sources))
        value = effect(ri, si)
        for key in draws:
            draws[key].append(value[key])
    return {'paired_median': observed,
            'paired_95_interval': {k: percentile_interval(v) for k, v in draws.items()},
            'samples': samples, 'seed': seed,
            'energy_resampling': 'paired repeats only',
            'schedule_interpretation': 'conditional on observed per-source frontiers'}


def classify_gates(effect, *, all_paired_goodput_positive, both_all_slo_pass,
                   safety_pass, samples_complete=True):
    p, ci = effect['paired_median'], effect['paired_95_interval']
    quality = ci['WER'][1] <= .005 and ci['CER'][1] <= .005
    literal_point = p['WER'] <= 0 and p['CER'] <= 0
    literal_confidence = ci['WER'][1] <= 0 and ci['CER'][1] <= 0
    eligible = safety_pass and samples_complete and quality
    energy = p['energy'] <= -.10 and ci['energy'][1] < 0
    goodput_ni = ci['goodput'][0] >= -.02
    latency = p['display'] <= .02 and p['commit'] <= .02
    return {'quality_tolerance_noninferiority': quality,
            'literal_quality_no_loss_point': literal_point,
            'literal_quality_no_loss_95': literal_confidence,
            'primary_goodput_gate': bool(eligible and p['goodput'] >= .05
                and ci['goodput'][0] > 0 and all_paired_goodput_positive),
            'strict_energy_latency_pareto_gate': bool(eligible and energy and goodput_ni and latency),
            'shared_service_contract_cost_gate': bool(eligible and energy and goodput_ni and both_all_slo_pass),
            'not_an_unqualified_quality_preserving_claim': not literal_point}
