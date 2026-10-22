"""Independent post-audit formal tables and predeclared statistical decisions."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import sys
from analysis_core import median, quantile, good_audio, paired_bootstrap, classify_gates


def main():
    B = Path(sys.argv[1]); O = B / 'results/revtrace/online_admission_20261022'
    A = O / 'formal_v1_audit_v3'; D = O / 'FORMAL_RESULTS_v1'
    report = json.loads((A / 'AUDIT_REPORT.json').read_text())
    assert report['status'] == 'PASS_COMPLETE_FORMAL_RAW_REPLAY' and report['cells'] == 72
    assert json.loads((O / 'formal_v1_PROCESSOR_REPLAY_v4.json').read_text())['status'] == 'PASS_ACTUAL_F2_PROCESSOR_BATCH_REPLAY'
    assert json.loads((O / 'formal_oracles_v1/SUMMARY.json').read_text())['status'] == 'COMPLETE_FORMAL_REFERENCE_AND_FUTURE_LABELS'
    D.mkdir(exist_ok=False)

    def rows(name):
        with (A / name).open() as f: return list(csv.DictReader(f))
    def number(x): return None if x in [None, '', 'None'] else float(x)
    def truth(x): return x == 'True'
    def clean(x):
        if isinstance(x, float) and not math.isfinite(x): return None
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)): return [clean(v) for v in x]
        return x
    def save(name, x): (D / name).write_text(json.dumps(clean(x), indent=2, allow_nan=False) + '\n')
    def csvsave(name, data):
        with (D / name).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)

    cells = rows('SERVICE_CELLS.csv'); F = defaultdict(list); Q = defaultdict(dict)
    for r in rows('COMMON_FRONTIERS.csv'):
        F[r['cell']].append({**r, **{k: number(r[k]) for k in ['display', 'commit', 'certified_consumer', 'audio_seconds']}})
    for r in rows('SOURCE_QUALITY.csv'):
        Q[r['cell']][r['source_id']] = {k: int(r[k]) for k in ['WER_errors', 'reference_words', 'CER_errors', 'reference_characters']}
    indexed = {}; grouped = defaultdict(list)
    for c in cells:
        method, load, traffic, rep = c['cell'].split('-'); repeat = int(rep[1:])
        indexed[method, load, traffic, repeat] = c; grouped[load, traffic, method].append(c)
    assert len(indexed) == 72
    metrics = ['Audio_Goodput_2_8', 'display_P99', 'commit_P99', 'GPU_strict_J_audio_s', 'WER', 'CER', 'wall_seconds']
    table = []; deadline_table = []
    for (load, traffic, method), cs in sorted(grouped.items()):
        assert len(cs) == 3
        out = {'load': load, 'traffic': traffic, 'method': method, 'repeats': 3}
        for k in metrics:
            values = [number(c[k]) for c in cs]
            out[k + '_median'] = median(values); out[k + '_min'] = min(math.inf if v is None else v for v in values); out[k + '_max'] = max(math.inf if v is None else v for v in values)
        out['dual_P99_passes_2_8'] = sum(number(c['display_P99']) is not None and number(c['commit_P99']) is not None and number(c['display_P99']) <= 2 and number(c['commit_P99']) <= 8 for c in cs)
        out['forward_false_acceptances'] = sum(int(c['false_acceptance_against_complete_forward']) for c in cs)
        out['forward_false_rejections'] = sum(int(c['false_rejection_against_complete_forward']) for c in cs)
        out['candidate_accepts'] = sum(int(c['candidate_accepts']) for c in cs)
        out['fallback_rows'] = sum(int(c['fallback_rows']) for c in cs)
        out['unfinished_sources'] = sum(int(c['unfinished_sources']) for c in cs)
        table.append(clean(out))
        for c in cs:
            for d in [2., 5., 8.]:
                for t in [4., 8., 12., 16.]:
                    deadline_table.append({'cell': c['cell'], 'load': load, 'traffic': traffic, 'method': method,
                                           'display_deadline_s': d, 'commit_deadline_s': t,
                                           'Audio_Goodput': good_audio(F[c['cell']], d, t) / float(c['wall_seconds']),
                                           'all_population_P99_pass': number(c['display_P99']) is not None and number(c['commit_P99']) is not None and number(c['display_P99']) <= d and number(c['commit_P99']) <= t})
    csvsave('GROUPS.csv', table); csvsave('DEADLINE_GRID.csv', deadline_table)

    def arm(method, load, traffic):
        runs = {}
        for repeat in range(3):
            c = indexed[method, load, traffic, repeat]; name = c['cell']; sources = {}
            for sid, q in Q[name].items(): sources[sid] = dict(q, frontiers=[f for f in F[name] if f['source_id'] == sid])
            runs[repeat] = {'wall': float(c['wall_seconds']), 'energy': float(c['GPU_strict_J_audio_s']), 'sources': sources}
        return runs

    comparisons = []; gate_rows = []
    for load in ['sync16', 'cohort8']:
        for traffic in ['clean', 'F2']:
            for baseline in ['fine', 'score', 'strict', 'standard']:
                a, b = arm(baseline, load, traffic), arm('dgft', load, traffic)
                print('bootstrap', load, traffic, baseline, flush=True)
                effect = paired_bootstrap((a, b))
                ac = [indexed[baseline, load, traffic, r] for r in range(3)]
                bc = [indexed['dgft', load, traffic, r] for r in range(3)]
                positive = all(float(y['Audio_Goodput_2_8']) > float(x['Audio_Goodput_2_8']) for x, y in zip(ac, bc))
                slo = all(number(c['display_P99']) is not None and number(c['commit_P99']) is not None and number(c['display_P99']) <= 2 and number(c['commit_P99']) <= 8 for c in ac + bc)
                safe = all(int(c['false_acceptance_against_complete_forward']) == 0 for c in ac + bc)
                complete = all(int(c['unfinished_sources']) == 0 for c in ac + bc)
                gates = classify_gates(effect, all_paired_goodput_positive=positive, both_all_slo_pass=slo, safety_pass=safe, samples_complete=complete)
                result = {'load': load, 'traffic': traffic, 'baseline': baseline, 'new': 'dgft', 'effect': effect, 'gates': gates,
                          'all_three_paired_goodput_deltas_positive': positive, 'both_all_three_dual_SLO_pass': slo,
                          'source_identity_and_raw_replay_pass': True, 'independent_generated_oracle_scope_is_sampled_not_every_admission': True}
                comparisons.append(result)
                gate_rows.append({'load': load, 'traffic': traffic, 'baseline': baseline, **gates,
                                  **{k + '_paired_change': v for k, v in effect['paired_median'].items()}})
    save('PAIRED_COMPARISONS.json', comparisons); csvsave('GATE_DECISIONS.csv', clean(gate_rows))
    labels = json.loads((O / 'formal_oracles_v1/SUMMARY.json').read_text())
    save('REFERENCE_AND_FUTURE_LABELS.json', labels)
    decisions = []
    for load in ['sync16', 'cohort8']:
        for traffic in ['clean', 'F2']:
            relevant = [x for x in comparisons if x['load'] == load and x['traffic'] == traffic and x['baseline'] != 'standard']
            decisions.append({'load': load, 'traffic': traffic,
                              'best_legal_primary_goodput_GO': all(x['gates']['primary_goodput_gate'] for x in relevant),
                              'best_legal_strict_pareto_GO': all(x['gates']['strict_energy_latency_pareto_gate'] for x in relevant),
                              'best_legal_shared_contract_cost_GO': all(x['gates']['shared_service_contract_cost_gate'] for x in relevant),
                              'literal_no_quality_loss_point_against_all': all(x['gates']['literal_quality_no_loss_point'] for x in relevant),
                              'no_claim_of_global_or_exclusive_optimality': True})
    save('GONOGO.json', {'status': 'COMPLETE_PREDECLARED_FORMAL_COMPARISONS', 'decisions': decisions,
                         'all_negative_results_retained': True,
                         'null_latency_interval_endpoint_means_unbounded_or_missing_not_zero': True,
                         'comparison_count': len(comparisons), 'formal_cells': len(cells),
                         'not_final_goal_completion': 'cross-campaign interpretation, archive and full completion audit still required'})
    save('INPUT_HASHES.json', {str(p.relative_to(O)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(A.iterdir()) if p.is_file()})
    print('COMPLETE_PREDECLARED_FORMAL_COMPARISONS', flush=True)


if __name__ == '__main__': main()
