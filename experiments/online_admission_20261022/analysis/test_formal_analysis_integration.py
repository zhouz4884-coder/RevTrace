"""Synthetic report-schema tests ONLY: no model, audio or GPU measurement."""
import csv
import json
from pathlib import Path
import pytest
import analysis_core
import summarize_formal


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def fake_audit(root, incomplete=False):
    """Upstream reports are deliberate test stubs, never study evidence."""
    O = root / 'results/revtrace/online_admission_20261022'
    A = O / 'formal_v1_audit_v3'; A.mkdir(parents=True)
    (O / 'CPU_FIXTURE_NOT_GPU.txt').write_text('Synthetic downstream-schema test. NOT actual formal audit or GPU evidence.\n')
    (A / 'AUDIT_REPORT.json').write_text(json.dumps({'status': 'PASS_COMPLETE_FORMAL_RAW_REPLAY', 'cells': 72}))
    (O / 'formal_v1_PROCESSOR_REPLAY_v4.json').write_text(json.dumps({'status': 'PASS_ACTUAL_F2_PROCESSOR_BATCH_REPLAY'}))
    (O / 'formal_oracles_v1').mkdir()
    (O / 'formal_oracles_v1/SUMMARY.json').write_text(json.dumps({'status': 'COMPLETE_FORMAL_REFERENCE_AND_FUTURE_LABELS', 'labels': [], 'synthetic_not_GPU': True}))
    cells, fs, qs = [], [], []
    for method in ['fine', 'unprotected', 'score', 'strict', 'dgft', 'standard']:
        for load in ['sync16', 'cohort8']:
            for traffic in ['clean', 'F2']:
                for repeat in range(3):
                    name = f'{method}-{load}-{traffic}-r{repeat}'
                    missing = incomplete and method == 'dgft'
                    cells.append({'cell': name, 'Audio_Goodput_2_8': 3. if missing else 3.2,
                                  'display_P99': '' if missing else 1., 'commit_P99': '' if missing else 4. if method in ['dgft', 'standard'] else 2.,
                                  'GPU_strict_J_audio_s': 80. if method in ['dgft', 'standard'] else 100.,
                                  'WER': .1, 'CER': 1 / 30, 'wall_seconds': 10.,
                                  'false_acceptance_against_complete_forward': 0, 'false_rejection_against_complete_forward': 0,
                                  'candidate_accepts': 16, 'fallback_rows': 0, 'unfinished_sources': int(missing)})
                    for source in range(16):
                        sid = f'fixture-source-{source}'
                        fs.append({'cell': name, 'source_id': sid, 'display': '' if missing and source == 15 else 1.,
                                   'commit': '' if missing and source == 15 else 4. if method in ['dgft', 'standard'] else 2.,
                                   'certified_consumer': '' if missing and source == 15 else 4., 'audio_seconds': 2.})
                        qs.append({'cell': name, 'source_id': sid, 'WER_errors': 1, 'reference_words': 10,
                                   'CER_errors': 1, 'reference_characters': 30})
    write_csv(A / 'SERVICE_CELLS.csv', cells); write_csv(A / 'COMMON_FRONTIERS.csv', fs); write_csv(A / 'SOURCE_QUALITY.csv', qs)
    return O


@pytest.mark.parametrize('incomplete', [False, True])
def test_complete_reporting_pipeline_cannot_hide_slo_or_source_failures(tmp_path, monkeypatch, incomplete):
    O = fake_audit(tmp_path, incomplete)
    monkeypatch.setattr('sys.argv', ['synthetic-report-test', str(tmp_path)])
    def fast_fixture_bootstrap(arms):
        return analysis_core.paired_bootstrap(arms, samples=8)
    monkeypatch.setattr(summarize_formal, 'paired_bootstrap', fast_fixture_bootstrap)
    summarize_formal.main()
    decision = json.loads((O / 'FORMAL_RESULTS_v1/GONOGO.json').read_text())
    assert decision['formal_cells'] == 72 and decision['comparison_count'] == 16
    assert len(list(csv.DictReader((O / 'FORMAL_RESULTS_v1/DEADLINE_GRID.csv').open()))) == 864
    assert all(not d['best_legal_primary_goodput_GO'] for d in decision['decisions'])
    assert all(not d['best_legal_strict_pareto_GO'] for d in decision['decisions'])
    assert all(d['best_legal_shared_contract_cost_GO'] is (not incomplete) for d in decision['decisions'])
    # Equivalent conventional positive control cannot become a claimed win.
    comparisons = json.loads((O / 'FORMAL_RESULTS_v1/PAIRED_COMPARISONS.json').read_text())
    assert all(not d['gates']['shared_service_contract_cost_gate'] for d in comparisons if d['baseline'] == 'standard')
