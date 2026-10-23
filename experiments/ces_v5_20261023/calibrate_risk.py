"""Development-only calibration from actual V4 physical batches.

This is historical cost modelling, not new GPU inference or a policy speedup.
The whole failed count is retained per physical batch; row failure identities
are exchangeable predictions, never reconstructed labels for unchosen actions.
"""
from pathlib import Path
from collections import defaultdict
import csv, gzip, hashlib, json, math, statistics, sys

W = Path(__file__).resolve().parent
OLD = W.parent / 'causal_evidence_scheduling_20261023'
S = W / 'runtime'
sys.path.insert(0, str(S / 'src'))
from revtrace.ces_policy import Target, cost, verify_cost

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def quantile(xs, p):
    xs = sorted(xs)
    if len(xs) == 1: return xs[0]
    x = (len(xs) - 1) * p
    lo, hi = int(math.floor(x)), int(math.ceil(x))
    return xs[lo] + (xs[hi] - xs[lo]) * (x - lo)
def stats(xs):
    return {'count': len(xs), 'median': statistics.median(xs),
            'mean': statistics.mean(xs), 'p90': quantile(xs, .90),
            'p95': quantile(xs, .95), 'minimum': min(xs), 'maximum': max(xs)}
def target(j):
    return Target(j['session_id'], j['end_window'], 0., 8.,
                  'candidate_token_ids' in j, False, False,
                  len(j.get('candidate_token_ids', [])), 0, 0., None,
                  audio_seconds=j['audio_end_sample'] / 16000,
                  interval_seconds=(j['audio_end_sample'] - j['audio_start_sample']) / 16000,
                  prompt_tokens=len(j['prompt_tokens']))

out = W / 'calibration_v2'
assert not out.exists(), 'Never overwrite calibration evidence'
out.mkdir()
base = read(OLD / 'CALIBRATION_v5.json')
diag = OLD / 'collected/evidence/formal_diagnosis_v1'
targets = {}
with (diag / 'TARGETS.csv').open(encoding='utf-8', newline='') as f:
    for r in csv.DictReader(f):
        if r['cell'].startswith('development-'):
            targets[(r['cell'], int(r['session']), int(r['window']))] = r
observed = {}
with (diag / 'BATCH_PREDICTION_VS_ACTUAL.csv').open(encoding='utf-8', newline='') as f:
    for r in csv.DictReader(f):
        if r['cell'].startswith('development-'):
            observed[(r['cell'], r['batch_id'])] = r
groups = defaultdict(list)
sources = []
for p in sorted((OLD / 'collected/canonical_witnesses').glob('development-*.jsonl.gz')):
    sources.append({'path': str(p.relative_to(OLD)), 'sha256': sha(p)})
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            receipt = x['selected']['_row_receipt']
            groups[(p.name[:-9], receipt['binding']['batch_id'])].append(x)
rows = []
for key, witnesses in sorted(groups.items()):
    raw = observed[key]
    n = len(witnesses)
    assert n == int(raw['rows']), 'Incomplete physical batch in Canonical witnesses'
    jobs = [x['job'] for x in witnesses]
    ts = [target(j) for j in jobs]
    op = jobs[0]['ces_operation']
    assert all(j['ces_operation'] == op for j in jobs)
    lease = float(raw['actual_batch_occupancy_s'])
    row_times = [float(targets[(key[0], j['session_id'], j['end_window'])]['row_result_after_start_s']) for j in jobs]
    pred = verify_cost(base, ts, False) if op == 'verify' else cost(base, 'generate', n, ts)
    if op == 'generate':
        scenario = {'original_rows': n, 'lease_ratio': lease / pred,
                    'row_fraction': min(1., max(.001, statistics.mean(row_times) / lease)),
                    'row_fractions': [min(1., max(0., t / lease)) for t in row_times], 'weight': 1.}
    else:
        proofs = [x['verification'] for x in witnesses]
        failed = [i for i, p in enumerate(proofs) if p['fallback_used']]
        k = len(failed)
        vsecs = max(p['verify_batch_seconds'] for p in proofs)
        fsecs = max(0., float(raw['actual_model_seconds']) - vsecs)
        assert (k > 0) == (int(raw['actual_fallback_calls']) > 0)
        # All observed CPU/preprocessing/drain overhead is paid. Allocating it
        # before fallback is a declared prediction approximation, not a phase
        # measurement. Raw row/lease observations remain in COST_ROWS.jsonl.
        vpaid = lease - fsecs
        assert vpaid > 0
        accepted_times = [row_times[i] for i in range(n) if i not in failed]
        fallback_times = [row_times[i] for i in failed]
        vf = min(1., max(.001, statistics.mean(accepted_times) / vpaid)) if accepted_times else 1.
        ff = min(1., max(.001, statistics.mean([(t - vpaid) / max(fsecs, .001) for t in fallback_times]))) if fallback_times else 1.
        scenario = {'original_rows': n, 'failed_count': k,
                    'verify_ratio': vpaid / cost(base, 'verify', n, ts),
                    'fallback_ratio': fsecs / cost(base, 'fallback', k, ts) if k else 1.,
                    'verify_row_fraction': vf, 'fallback_row_fraction': ff,
                    'verify_row_fractions': [min(1., max(0., t / vpaid)) for t in accepted_times],
                    'fallback_row_fractions': [min(1., max(0., (t - vpaid) / max(fsecs, .001))) for t in fallback_times],
                    'weight': 1.}
    rows.append({'cell': key[0], 'batch_id': key[1], 'operation': op, 'rows': n,
                 'actual_lease_s': lease, 'actual_row_s': row_times,
                 'old_global_prediction_s': pred, 'ratio': lease / pred, 'scenario': scenario})
assert len(rows) == len(observed)

def compress(samples):
    """Eight weighted medoids, retaining exact no-fallback/fallback mass.

    Each representative is one real batch, including its complete row CDF.
    Within each failure/no-failure class, stratify normalized physical cost.
    Compression approximates the detailed K and duration distribution; its
    distortion is reported and never claimed to be an exact empirical tail.
    """
    classes = defaultdict(list)
    for r in samples:
        classes[int(r['scenario'].get('failed_count', 0) > 0)].append(r)
    budget = min(8, len(samples))
    seats = {k: 1 for k in classes}
    while sum(seats.values()) < budget:
        candidates = [k for k in classes if seats[k] < len(classes[k])]
        k = max(candidates, key=lambda k: (len(classes[k]) / (seats[k] + 1), -k))
        seats[k] += 1
    reps = []
    for k, group in sorted(classes.items()):
        ordered = sorted(group, key=lambda r: (r['ratio'], r['cell'], r['batch_id']))
        count = seats[k]
        for i in range(count):
            chunk = ordered[i * len(ordered) // count:(i + 1) * len(ordered) // count]
            selected = chunk[(len(chunk) - 1) // 2]
            reps.append(dict(selected['scenario'], weight=len(chunk),
                             representative_cell=selected['cell'],
                             representative_batch_id=selected['batch_id'],
                             represented_physical_batches=len(chunk)))
    assert len(reps) <= 8 and sum(r['weight'] for r in reps) == len(samples)
    raw_failed = sum(r['scenario'].get('failed_count', 0) > 0 for r in samples) / len(samples)
    represented_failed = sum(r['weight'] for r in reps if r.get('failed_count', 0) > 0) / len(samples)
    assert abs(raw_failed - represented_failed) < 1e-12
    return reps

def fit(samples):
    ratios = {'generate': {}, 'verify': {}}
    gs, vs = {}, {}
    for op in ratios:
        selected = [r for r in samples if r['operation'] == op]
        for size in ['global'] + sorted({str(r['rows']) for r in selected}, key=lambda v: int(v)):
            sub = selected if size == 'global' else [r for r in selected if str(r['rows']) == size]
            ratios[op][size] = stats([r['ratio'] for r in sub])
            dest = vs if op == 'verify' else gs
            dest[size] = {'count': len(sub), 'scenarios': compress(sub)}
    return {'schema_version': 2, 'min_bucket_samples': 8, 'risk_quantile': .90,
            'ratio_buckets': ratios, 'verification_scenarios': vs, 'generation_scenarios': gs,
            'scenario_limit': 8,
            'compression': 'Failure/no-failure mass preserved exactly; normalized-cost strata use weighted real-batch medoids; detailed K and tail approximated',
            'scope': 'Actual development physical-batch samples; exchanged row identities are cost predictions only',
            'phase_overhead_allocation': 'Observed non-model overhead allocated to verify stage; row fractions estimated separately',
            'not_a_deterministic_SLO_bound': True}

hold = [r for r in rows if int(hashlib.sha256(r['cell'].encode()).hexdigest()[:8], 16) % 5 == 0]
train = [r for r in rows if r not in hold]
train_model = fit(train)
diagnostics = {}
for op in ['generate', 'verify']:
    errors, covered = [], []
    for r in hold:
        if r['operation'] != op: continue
        buckets = train_model['ratio_buckets'][op]
        b = buckets.get(str(r['rows']))
        if b is None or b['count'] < 8: b = buckets['global']
        errors.append(abs(r['actual_lease_s'] - r['old_global_prediction_s'] * b['median']))
        covered.append(r['actual_lease_s'] <= r['old_global_prediction_s'] * b['p90'])
    diagnostics[op] = {'held_cell_batches': len(errors), 'median_absolute_error_s': statistics.median(errors),
                       'empirical_p90_coverage': sum(covered) / len(covered),
                       'scope': 'Cell-held-out historical calibration check; not new-source or serving performance'}

base['v5_risk_model'] = fit(rows)
base['schema'] = 'CES-V5-shared-physical-risk-v2'
base['v5_calibration_provenance'] = {
    'baseline_archive': '01f6e04aa88cf704c129242e6bbdaf42de159525',
    'base_calibration_sha256': sha(OLD / 'CALIBRATION_v5.json'),
    'code_sha256': sha(Path(__file__)), 'sources': sources,
    'source_pool': 'V4 development only; V4 validation omitted from fitting',
    'batch_csv_sha256': sha(diag / 'BATCH_PREDICTION_VS_ACTUAL.csv'),
    'targets_csv_sha256': sha(diag / 'TARGETS.csv'),
    'physical_batches': len(rows), 'cells': len({r['cell'] for r in rows}),
    'diagnostics': diagnostics, 'fresh_GPU_calls': 0,
    'unselected_verification_outcomes_used': False}
(out / 'CALIBRATION.json').write_text(json.dumps(base, indent=2) + '\n', encoding='utf-8')
with (out / 'COST_ROWS.jsonl').open('w', encoding='utf-8') as f:
    for r in rows: f.write(json.dumps(r) + '\n')
summary = dict(base['v5_calibration_provenance'], calibration_sha256=sha(out / 'CALIBRATION.json'))
(out / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k != 'sources'}, indent=2))
