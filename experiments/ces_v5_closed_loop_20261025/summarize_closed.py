"""Independent closed-loop pilot summaries; no frontier is treated as an IID run.

This module also supplies small, model-free analysis helpers to audit_v5.py.
Bootstrap intervals are descriptive paired-run intervals for a bounded pilot.
Source-cluster resampling is explicitly conditional on observed schedules.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import random
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path


def quantile(values, q):
    if not values:
        return math.inf
    xs = sorted(math.inf if v is None else float(v) for v in values)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    frac = pos - lo
    if frac == 0 or lo == len(xs) - 1:
        return xs[lo]
    if math.isinf(xs[lo + 1]):
        return math.inf
    return xs[lo] + frac * (xs[lo + 1] - xs[lo])


def quality_counts(reference, text):
    def units(t, word):
        t = unicodedata.normalize('NFKC', t).lower()
        return re.findall(r"[a-z0-9']+", t) if word else [c for c in t if c.isalnum()]
    def distance(a, b):
        row = list(range(len(b) + 1))
        for i, x in enumerate(a, 1):
            nxt = [i]
            for j, y in enumerate(b, 1):
                nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
            row = nxt
        return row[-1]
    rw, tw = units(reference, True), units(text, True)
    rc, tc = units(reference, False), units(text, False)
    return {'WER_errors': distance(rw, tw), 'reference_words': len(rw),
            'CER_errors': distance(rc, tc), 'reference_characters': len(rc)}


def good_audio(frontiers, display=2., commit=8., display_key='display', commit_key='commit'):
    return sum(float(q['audio_seconds']) for q in frontiers
               if q.get(display_key) is not None and q.get(commit_key) is not None
               and float(q[display_key]) <= display and float(q[commit_key]) <= commit)


def visibility_sensitivity(views, frontier, release, owner_install):
    """Actual FIFO observations, not a prediction of an alternative schedule.

    stable_display is the start of the last uninterrupted coverage interval
    ending at first certified Consumer coverage. It is separately labelled
    because the original metric rewards first legal visibility.
    """
    ordered = sorted(enumerate(views), key=lambda x: (x[1]['observed'], x[0]))
    rows = [r for _, r in ordered]
    cover = [r for r in rows if r['valid_visible_frontier'] >= frontier]
    certified = next((r for r in rows if r['certified_frontier'] >= frontier), None)
    first = cover[0]['observed'] if cover else None
    cert_time = certified['observed'] if certified else None
    stable_start = None
    withdrawn = False
    seen = False
    for row in rows:
        if cert_time is not None and row['observed'] > cert_time:
            break
        if row['valid_visible_frontier'] >= frontier:
            if stable_start is None:
                stable_start = row['observed']
            seen = True
        else:
            if seen:
                withdrawn = True
            stable_start = None
    if cert_time is None:
        stable_start = None
    at_install = [r for r in rows if owner_install is not None and r['observed'] <= owner_install]
    return {
        'stable_display': None if stable_start is None else stable_start - release,
        'first_visible_withdrawn_before_certified': withdrawn,
        'visible_at_owner_install': bool(at_install and at_install[-1]['valid_visible_frontier'] >= frontier),
        'first_visible_to_certified_s': None if first is None or cert_time is None else cert_time - first,
    }


def clean_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    return value


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for k, v in row.items():
            if v == '':
                row[k] = None
            elif v in ('True', 'False'):
                row[k] = v == 'True'
            else:
                try:
                    row[k] = float(v)
                except (ValueError, TypeError):
                    pass
    return rows


def identity(cell):
    # Method names may contain underscores; the final -rN identifies repeats.
    prefix, repeat = cell.rsplit('-r', 1)
    parts = prefix.split('-')
    return parts[0], parts[1], parts[2], int(repeat)


def paired_effect(a, b, key, draws=10000, seed=20261023):
    assert set(a) == set(b)
    repeats = sorted(a)
    values = [(b[r][key] - a[r][key]) if key in ('WER', 'CER') else
              ((b[r][key] / a[r][key] - 1) if a[r][key] else
               (0. if b[r][key] == 0 else math.inf)) for r in repeats]
    if any(not math.isfinite(x) for x in values):
        return {'paired_values': clean_json(values), 'paired_median': None,
                'paired_run_95_interval': None, 'status': 'NONFINITE_NO_SUPERIORITY_CLAIM'}
    rng = random.Random(seed)
    samples = [statistics.median(rng.choices(values, k=len(values))) for _ in range(draws)]
    return {'paired_values': values, 'paired_median': statistics.median(values),
            'paired_run_95_interval': [quantile(samples, .025), quantile(samples, .975)],
            'all_repeats_positive': all(v > 0 for v in values), 'runs': len(repeats)}


def source_effect(base, new, fronts, qualities, draws=2000, seed=20261023):
    """Paired repeat/source clusters; wall/energy remain actual whole-run values."""
    repeats = sorted(base)
    assert set(base) == set(new)
    byfront = defaultdict(lambda: defaultdict(list))
    byquality = defaultdict(dict)
    for row in fronts:
        byfront[row['cell']][row['source_id']].append(row)
    for row in qualities:
        byquality[row['cell']][row['source_id']] = row
    sources = sorted(byfront[base[repeats[0]]['cell']])
    for arm in (base, new):
        for r in repeats:
            assert sorted(byfront[arm[r]['cell']]) == sources
    keys = ['goodput', 'stable_goodput', 'WER', 'CER']
    def compare(rs, ss):
        effects = defaultdict(list)
        for r in rs:
            values = []
            for arm in (base, new):
                row = arm[r]
                fs = [f for s in ss for f in byfront[row['cell']][s]]
                qs = [byquality[row['cell']][s] for s in ss]
                values.append({'goodput': good_audio(fs) / row['wall_seconds'],
                    'stable_goodput': good_audio(fs, display_key='stable_display', commit_key='certified_consumer') / row['wall_seconds'],
                    'WER': sum(q['WER_errors'] for q in qs) / sum(q['reference_words'] for q in qs),
                    'CER': sum(q['CER_errors'] for q in qs) / sum(q['reference_characters'] for q in qs)})
            for key in keys:
                a, b = values[0][key], values[1][key]
                effects[key].append(b-a if key in ('WER', 'CER') else b/a-1 if a else 0. if b == 0 else math.inf)
        return {k: statistics.median(v) for k,v in effects.items()}
    observed = compare(repeats, sources)
    rng = random.Random(seed)
    boot = defaultdict(list)
    for _ in range(draws):
        effect = compare(rng.choices(repeats, k=len(repeats)), rng.choices(sources, k=len(sources)))
        for k,v in effect.items():
            boot[k].append(v)
    return clean_json({'paired_median': observed,
        'paired_source_run_95_interval': {k: [quantile(v,.025),quantile(v,.975)] for k,v in boot.items()},
        'unique_sources': len(sources), 'repeats': len(repeats), 'draws': draws,
        'interpretation': 'Conditional on actual schedules. Resampled audio is not model/queue re-execution.'})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--samples', type=int, default=2000)
    ap.add_argument('--expected-repeats', type=int, default=3)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.audit/'SUMMARY.json').read_text())
    rows = read_csv(args.audit/'SERVICE_CELLS.csv')
    fronts = read_csv(args.audit/'COMMON_FRONTIERS.csv')
    qualities = read_csv(args.audit/'SOURCE_QUALITY.csv')
    groups = defaultdict(dict)
    for row in rows:
        pool, arrival, traffic, repeat = identity(row['cell'])
        groups[pool,arrival,traffic,row['method']][repeat] = row
    comparisons = []
    for key, treatment in sorted(groups.items()):
        pool, arrival, traffic, method = key
        if method in ('fine', 'standard', 'cost'):
            continue
        for baseline in ('fine', 'standard', 'cost', 'strict', 'service_cost', 'reserved_progress', 'inherit', 'causal', 'causal_joint'):
            if baseline == method:
                continue
            control = groups.get((pool,arrival,traffic,baseline), {})
            meta = {'pool': pool, 'arrival': arrival, 'traffic': traffic, 'method': method, 'baseline': baseline}
            if (len(control) != args.expected_repeats or len(treatment) != args.expected_repeats
                    or set(control) != set(treatment)):
                comparisons.append(dict(meta, status='INCOMPLETE_NO_COMPARATIVE_CLAIM',
                    baseline_repeats=sorted(control), treatment_repeats=sorted(treatment)))
                continue
            metrics = {k: paired_effect(control,treatment,k) for k in
                ['Audio_Goodput_2_8','Audio_Goodput_certified_consumer_2_8','Audio_Goodput_stable_2_8',
                 'display_P99','commit_P99','GPU_J_audio_s','WER','CER']}
            comparisons.append(dict(meta, status='DESCRIPTIVE_PAIRED_PILOT' if args.expected_repeats >= 3 else
                'SMOKE_SINGLE_REPEAT_POINT_ESTIMATES_NO_SUPERIORITY_CLAIM', metrics=metrics,
                source_clusters=source_effect(control,treatment,fronts,qualities,draws=args.samples),
                baseline_dual_P99_passes=sum(r['dual_P99_2_8_pass'] for r in control.values()),
                treatment_dual_P99_passes=sum(r['dual_P99_2_8_pass'] for r in treatment.values())))
    report = {'scope': summary.get('source_scope', 'Reused sources: diagnostic pilot, not independent confirmatory superiority'),
        'expected_cells': summary['expected_cells'], 'audited_pass_cells': len(rows),
        'failed_or_missing_cells': summary['failures'], 'all_requested_cells_retained': True,
        'performance_decision_eligible': not summary['failures'] and args.expected_repeats >= 3,
        'performance_point_estimates_available': not summary['failures'],
        'paired_repeat_minimum_for_inference': args.expected_repeats,
        'one_repeat_smoke_is_safety_feasibility_not_superiority': args.expected_repeats < 3,
        'shared_model_and_execution_capabilities_required': True,
        'sampling_unit': 'Fresh-process paired run; shared source clusters separately resampled, never individual frontiers',
        'comparisons': comparisons}
    (args.output/'PAIRED_SUMMARY.json').write_text(json.dumps(clean_json(report),indent=2,allow_nan=False)+'\n')
    group_rows=[]
    for key,group in sorted(groups.items()):
        pool,arrival,traffic,method=key
        available=list(group.values())
        row={'pool':pool,'arrival':arrival,'traffic':traffic,'method':method,
             'runs':len(group),'repeat_indices':';'.join(str(x) for x in sorted(group)),
             'whole_run_dual_P99_passes':sum(r['dual_P99_2_8_pass'] for r in available),
             'not_frontier_IID':True,'source_scope':report['scope']}
        for metric in ['Audio_Goodput_2_8','Audio_Goodput_certified_consumer_2_8','Audio_Goodput_stable_2_8',
                       'display_P50','display_P95','display_P99','commit_P50','commit_P95','commit_P99',
                       'GPU_J_audio_s','WER','CER','wall_seconds','audio_seconds','planner_wall_s',
                       'feature_wall_s','decision_count','verified_rows','accepted_rows','rejected_rows',
                       'fallback_rows','physical_fsyncs','unfinished_sources','capped_authority_admissions',
                       'visible_audio_rollback_samples','erased_characters']:
            values=[r[metric] for r in available if r.get(metric) is not None]
            row[metric+'_median']=statistics.median(values) if values else None
        group_rows.append(row)
    with (args.output/'GROUPS.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(group_rows[0]) if group_rows else [])
        writer.writeheader();writer.writerows(group_rows)
    print(json.dumps({'expected_cells': summary['expected_cells'], 'audited_cells': len(rows),
                      'comparisons': len(comparisons), 'performance_decision_eligible': not summary['failures']}))


if __name__ == '__main__':
    main()


