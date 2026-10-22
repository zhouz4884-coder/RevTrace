"""Actual post-admission neural work, separated from processing-only targets."""
from pathlib import Path
import csv
import hashlib
import json
import sys
from neural_feedback_core import actually_ran_neural_model, canonical_root_chain, token_digest


def main():
    B = Path(sys.argv[1]); O = B / 'results/revtrace/online_admission_20261022'
    assert json.loads((O / 'POSTPROCESS_SUMMARY.json').read_text())['status'] == 'COMPLETE_FORMAL_ORACLE_AND_CPU_AUDITS'
    D = O / 'NEURAL_FEEDBACK_CHAINS_v1'; D.mkdir(exist_ok=False)
    def read(p): return json.loads(p.read_text())
    def lines(p): return [json.loads(x) for x in p.read_text().splitlines()]
    def save(name, x): (D / name).write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')
    def table(name, rows):
        if not rows: return
        with (D / name).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    diagnostic = read(O / 'formal_oracles_v1/SUMMARY.json')
    labels = {(r['cell'], r['job_id']): r for r in diagnostic['labels']}
    future = {(r['cell'], r['source_id']): r for r in diagnostic['future_controls']}
    roots = []; witnesses = []; witness_ids = set(); processing_only = []
    try:
        for method in ['unprotected', 'score', 'strict']:
            for load in ['sync16', 'cohort8']:
                for repeat in range(3):
                    name = f'{method}-{load}-F2-r{repeat}'; c = O / 'formal_v1' / name
                    rows = lines(c / 'worker_records.jsonl'); events = lines(c / 'events.jsonl')
                    by_job = {r['job']['job_id']: r for r in rows}
                    commits = {e['job_id']: e for e in events if e['kind'] == 'commit'}
                    t0 = next(e['t0_perf'] for e in events if e['kind'] == 'run-start')
                    for target in rows:
                        j, r = target['job'], target['result']
                        origin_id = j.get('candidate_origin_job_id')
                        if origin_id is None or j['job_id'] not in commits: continue
                        origin = by_job[origin_id]
                        if 'fault_actual_prompt_tokens' not in origin['job']: continue
                        assert actually_ran_neural_model(origin), 'F2 source was not actually generated'
                        e = commits[j['job_id']]; label = labels.get((name, j['job_id']))
                        fo = future.get((name, j['source_id']), {})
                        root = {'session_id': j['session_id'], 'version': e['version'], 'P': r['state_tokens'],
                                'frontier': e['audio_end_sample'], 'installed_perf': t0 + e['installed']}
                        assert token_digest(root['P']) == e['certificate']['feedback_state_sha256']
                        post = []; preissued = []; direct_count = 0
                        for call in rows:
                            q = call['job']
                            if q['session_id'] != j['session_id'] or q['audio_end_sample'] <= root['frontier']: continue
                            if q['role'] == 'authority' and q['audio_start_sample'] == root['frontier']:
                                processing_only.append({'cell': name, 'root_job_id': j['job_id'], 'later_target_job_id': q['job_id'],
                                    'target_processed_selected_P': q['prompt_tokens'] == root['P'],
                                    'actual_model_call': actually_ran_neural_model(call),
                                    'not_automatically_a_new_generation': True})
                            if q['role'] != 'proposal' or not actually_ran_neural_model(call): continue
                            chain, reason = canonical_root_chain(call, root, rows)
                            if chain:
                                post.append(q['job_id']); direct_count += reason == 'direct_root'
                                key = (name, j['job_id'], q['job_id']); assert key not in witness_ids; witness_ids.add(key)
                                witnesses.append({'cell': name, 'root_job_id': j['job_id'], 'source_id': j['source_id'],
                                    'root_version': root['version'], 'root_frontier': root['frontier'],
                                    'root_installed_perf': root['installed_perf'], 'neural_job_id': q['job_id'],
                                    'neural_enqueue_perf': q['enqueue_perf'], 'model_started_perf': call['result']['model_started_perf'],
                                    'model_completed_perf': call['result']['model_completed_perf'],
                                    'actual_conditioning_prefix_sha256': call['result']['execution_context_audit']['conditioning_prefix_sha256'],
                                    'kind': reason, 'witness_jobs': chain})
                            elif reason == 'issued_before_installation' and q['prompt_tokens'] == root['P']:
                                preissued.append(q['job_id'])
                        roots.append({'cell': name, 'method': method, 'load': load, 'repeat': repeat,
                            'source_id': j['source_id'], 'fault_origin_job_id': origin_id, 'root_job_id': j['job_id'],
                            'fault_candidate_accepted': r['online_verification']['candidate_accepted'],
                            'legal_fallback_used': r['online_verification']['fallback_used'],
                            'candidate_equal_generated_correct_context_oracle': label['candidate_equal_generated_FP32_oracle'] if label else None,
                            'selected_P_known_different_generated_reference': fo.get('admitted_P_differs_reference') if method == 'unprotected' else None,
                            'post_install_real_neural_row_jobs': len(post), 'direct_root_neural_row_jobs': direct_count,
                            'preissued_private_equal_P_calls_not_counted': len(preissued),
                            'new_neural_output_difference_not_inferred_from_identity': True})
        table('ADMITTED_ROOTS.csv', roots); table('POST_INSTALL_NEURAL_WITNESSES.csv', witnesses); table('LATER_TARGET_PROCESSING.csv', processing_only)
        save('SUMMARY.json', {'status': 'COMPLETE_POST_INSTALL_NEURAL_CONSUMPTION_AUDIT',
            'roots_from_actual_F2_origin_candidates': len(roots),
            'root_count_with_post_install_neural_consumption': sum(r['post_install_real_neural_row_jobs'] > 0 for r in roots),
            'unsafe_accepted_root_count_with_post_install_neural_consumption': sum(r['method'] == 'unprotected' and r['fault_candidate_accepted'] and r['post_install_real_neural_row_jobs'] > 0 for r in roots),
            'known_bad_projection_root_count_with_post_install_neural_consumption': sum(r['method'] == 'unprotected' and r['selected_P_known_different_generated_reference'] is True and r['post_install_real_neural_row_jobs'] > 0 for r in roots),
            'post_install_neural_witnesses': len(witnesses),
            'physical_model_batches_for_witnesses': len({(r['cell'], r['model_started_perf'], r['model_completed_perf']) for r in witnesses}),
            'row_job_witnesses_not_independent_sources_or_physical_batches': True,
            'unique_sources': len({r['source_id'] for r in roots}),
            'processing_only_later_targets_not_neural_calls': sum(not r['actual_model_call'] for r in processing_only),
            'preissued_equal_P_calls_not_claimed_as_post_admission': sum(r['preissued_private_equal_P_calls_not_counted'] for r in roots),
            'generated_oracle_unknowns_not_filled': sum(r['candidate_equal_generated_correct_context_oracle'] is None for r in roots),
            'scope': 'read-only provenance/timestamps of actual GPU records; not CPU regeneration, not proof each divergence harms quality, not natural incidence',
            'quality_damage_source': 'separate paired fixed-future GPU controls and qualified clean/F2 serving contrasts',
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        print(json.dumps(read(D / 'SUMMARY.json')))
    except BaseException as e:
        save('STOP.json', {'error': repr(e), 'no_GPU_or_measurement_changes': True})
        raise


if __name__ == '__main__': main()
