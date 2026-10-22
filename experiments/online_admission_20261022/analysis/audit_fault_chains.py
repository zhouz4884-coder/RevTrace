"""Rebuild actual online provenance/consumption, distinct from GPU counterfactuals."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import sys


def main():
    B = Path(sys.argv[1]); O = B / 'results/revtrace/online_admission_20261022'
    A = O / 'formal_v1_audit_v3'; D = O / 'FAULT_CHAINS_v1'; D.mkdir(exist_ok=False)
    def read(p): return json.loads(p.read_text())
    def lines(p): return [json.loads(x) for x in p.read_text().splitlines()]
    def table(name):
        with (A / name).open() as f: return list(csv.DictReader(f))
    def save(name, x): (D / name).write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')
    def out(name, data):
        if not data: return
        with (D / name).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    assert read(A / 'AUDIT_REPORT.json')['status'] == 'PASS_COMPLETE_FORMAL_RAW_REPLAY'
    replay = read(O / 'formal_v1_PROCESSOR_REPLAY_v4.json')
    assert replay['status'] == 'PASS_ACTUAL_F2_PROCESSOR_BATCH_REPLAY'
    proc = {}; effective = {}
    for b in replay['batches']:
        for jid in b['job_ids']: proc[b['cell'], jid] = b
        for r in b['actual_vs_correct_context']: effective[b['cell'], r['job_id']] = r['effective_processed_ID_change']
    label_data = read(O / 'formal_oracles_v1/SUMMARY.json')
    labels = {(r['cell'], r['job_id']): r for r in label_data['labels']}
    quality = {(r['cell'], r['source_id']): r for r in table('SOURCE_QUALITY.csv')}
    opportunities = []; chains = []; total_effects = []
    for method in ['fine', 'unprotected', 'score', 'strict', 'dgft', 'standard']:
        for load in ['sync16', 'cohort8']:
            for repeat in range(3):
                fn = f'{method}-{load}-F2-r{repeat}'; cn = f'{method}-{load}-clean-r{repeat}'
                fault = O / 'formal_v1' / fn; clean = O / 'formal_v1' / cn
                rows = lines(fault / 'worker_records.jsonl'); cr = lines(clean / 'worker_records.jsonl')
                es = lines(fault / 'events.jsonl'); by_job = {r['job']['job_id']: r for r in rows}
                committed = {e['job_id']: e for e in es if e['kind'] == 'commit'}
                source_rows = json.loads((fault / 'sessions.json').read_text())
                for s in source_rows:
                    sid, source = s['session_id'], s['source_id']
                    candidates = [r for r in rows if r['job']['session_id'] == sid and 'fault_actual_prompt_tokens' in r['job']]
                    assert len(candidates) <= 1
                    r = candidates[0] if candidates else None
                    match = []; same_processed = False
                    if r:
                        j = r['job']; p = proc[fn, j['job_id']]
                        match = [z for z in cr if z['job']['role'] == 'proposal' and z['job']['source_id'] == source
                                 and z['job']['chunk_id'] == j['chunk_id'] and z['job']['end_window'] == j['end_window']
                                 and z['job']['audio_start_sample'] == j['audio_start_sample']
                                 and z['job']['audio_end_sample'] == j['audio_end_sample']
                                 and z['job']['prompt_tokens'] == j['prompt_tokens']]
                        same_processed = any(p['counterfactual_no_override_batch_tensors'] == z['result']['model_input_audit']['batch_tensors'] for z in match)
                    opportunities.append({'cell': fn, 'method': method, 'load': load, 'repeat': repeat,
                                          'source_id': source, 'fault_issued_and_GPU_executed': bool(r),
                                          'fault_job_id': r['job']['job_id'] if r else None,
                                          'actual_processed_conditioning_changed': effective.get((fn, r['job']['job_id'])) if r else None,
                                          'matched_clean_parent_audio_chunk': bool(match),
                                          'matched_clean_full_counterfactual_processor_batch': same_processed,
                                          'not_natural_prevalence': True})
                    qf, qc = quality[fn, source], quality[cn, source]
                    total_effects.append({'method': method, 'load': load, 'repeat': repeat, 'source_id': source,
                                          'F2_cell': fn, 'clean_cell': cn,
                                          'matched_actual_preintervention_input': same_processed,
                                          'final_WER_error_delta': int(qf['WER_errors']) - int(qc['WER_errors']),
                                          'final_CER_error_delta': int(qf['CER_errors']) - int(qc['CER_errors']),
                                          'final_text_changed': qf['final_canonical_text'] != qc['final_canonical_text'],
                                          'scope': 'actual_serving_total_effect; pure_feedback_attribution_requires_matched_input_and_control'})
                    if not r: continue
                    attached = [z for z in rows if z['job'].get('candidate_origin_job_id') == r['job']['job_id']]
                    for target in attached:
                        j, v = target['job'], target['result']; proof = v['online_verification']
                        label = labels.get((fn, j['job_id']))
                        successors = [z for z in rows if z['job']['role'] == 'authority' and z['job']['session_id'] == sid
                                      and z['job']['audio_start_sample'] == j['audio_end_sample']]
                        next_consumed = bool(j['job_id'] in committed and successors and all(z['job']['prompt_tokens'] == v['state_tokens'] for z in successors))
                        chains.append({'cell': fn, 'method': method, 'source_id': source,
                                       'fault_origin_job_id': r['job']['job_id'], 'target_job_id': j['job_id'],
                                       'candidate_accepted': proof['candidate_accepted'], 'fallback': proof['fallback_used'],
                                       'target_installed': j['job_id'] in committed,
                                       'next_actual_authority_consumed_selected_P': next_consumed,
                                       'candidate_equal_correct_context_generated_oracle': label['candidate_equal_generated_FP32_oracle'] if label else None,
                                       'generated_oracle_label_executed': label is not None,
                                       'not_a_claim_every_token_change_is_semantic_damage': True})
    assert len(opportunities) == len(total_effects) == 6 * 2 * 3 * 16
    out('FAULT_OPPORTUNITIES.csv', opportunities); out('DIRECT_ADMISSION_CHAINS.csv', chains); out('CLEAN_F2_TOTAL_EFFECTS.csv', total_effects)
    protected_reference_failures = [r for r in chains if r['method'] in ['score', 'strict'] and r['candidate_accepted']
                                    and r['generated_oracle_label_executed'] and not r['candidate_equal_correct_context_generated_oracle']]
    result = {'status': 'COMPLETE_ACTUAL_ONLINE_FAULT_CHAIN_RECONSTRUCTION',
              'nominal_source_run_opportunities': len(opportunities),
              'unique_source_count_not_576': 16,
              'actual_fault_jobs': sum(r['fault_issued_and_GPU_executed'] for r in opportunities),
              'actual_processed_condition_changes': sum(r['actual_processed_conditioning_changed'] is True for r in opportunities),
              'direct_attached_candidate_targets': len(chains),
              'protected_generated_reference_failures_in_labelled_subset': protected_reference_failures,
              'unlabelled_generated_oracle_cases_remain_unknown': sum(not r['generated_oracle_label_executed'] for r in chains),
              'future_damage_labels_scope': 'separate formal_oracles_v1 controlled GPU continuation, not inferred from these counts',
              'natural_fault_incidence_claim': False,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save('SUMMARY.json', result); print(json.dumps(result))
    assert not protected_reference_failures, 'Protected acceptance contradicted measured independent generated reference'


if __name__ == '__main__': main()
