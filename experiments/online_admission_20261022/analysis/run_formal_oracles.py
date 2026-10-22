"""Post-serving real GPU reference labels; never a serving performance result."""
from pathlib import Path
from collections import defaultdict
import copy
import hashlib
import json
import math
import subprocess
import sys
import time


def main():
    B = Path(sys.argv[1]); P = B / 'projects/revtrace_online_admission_20261022'
    O = B / 'results/revtrace/online_admission_20261022'; S = P / 'pilot_sdk_v3'
    D = O / 'formal_oracles_v1'
    assert json.loads((O / 'FORMAL_SUMMARY.json').read_text())['status'] == 'COMPLETE_72_FRESH_ONLINE_FORMAL_CELLS'
    assert not (O / 'STOP_FORMAL_v1.json').exists()
    assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip(), 'Do not interfere with any GPU task'
    D.mkdir(exist_ok=False)
    sys.path[:0] = [str(S / 'src'), str(S / 'scripts'), str(S / 'scripts/v100'), str(P)]
    import numpy as np
    import soundfile as sf
    from tc_live_worker import GPUExecutor
    from revtrace.live_qwen import fingerprint
    from revtrace.dgft import digest_tokens
    from run_v100_matrix import PowerSampler
    from analysis_core import quality_counts

    def read(p): return json.loads(p.read_text())
    def save(p, data): p.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    def sha(p):
        with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

    frozen = read(O / 'FORMAL_FREEZE.json'); source = read(S / 'SOURCE_MANIFEST.json')
    assert source['code_commit'] == frozen['runtime_code_commit'] == '55cd52dfdbab71298cdb7eae3b0c08c9424020c6'
    for r in source['files']: assert sha(S / r['path']) == r['sha256']
    plan = read(O / 'FORMAL_ORACLE_INPUT_PLAN.json')
    assert not any(x['status'] == 'not_complete_yet' for x in plan['opportunities'])
    protocol = {'experiment': 'FORMAL-TRACE-ORACLE-v1', 'source_commit': source['code_commit'],
                'input_plan_sha256': sha(O / 'FORMAL_ORACLE_INPUT_PLAN.json'),
                'protocol_sha256': sha(P / 'FORMAL_ORACLE_EXTENSION_FREEZE.md'),
                'driver_sha256': sha(Path(__file__)), 'targets': plan['opportunities'],
                'not_serving_performance': True, 'no_outcome_selection': True}
    save(D / 'RUN.json', protocol)
    digest = fingerprint(protocol)
    records = {}; groups = {}; summaries = []; future_roots = []; phases = []
    for batch in plan['batches']:
        name = batch['cell']
        if name not in records:
            rows = [json.loads(l) for l in (O / 'formal_v1' / name / 'worker_records.jsonl').read_text().splitlines()]
            records[name] = {r['job']['job_id']: r for r in rows}
        groups[name, batch['batch_index']] = [records[name][j] for j in batch['whole_peer_job_ids']]
    cfg = read(O / 'formal_v1/strict-sync16-clean-r0/config.json')
    manifest_path = B / 'datasets/revtrace/phaseD_20261021/manifest.json'
    sources = {r['source_id']: r for r in read(manifest_path)['sessions']}
    worker = None; sampler = None

    def run(name, original):
        jobs = copy.deepcopy(original)
        for i, j in enumerate(jobs):
            j['origin_job_id'] = j['job_id']; j['job_id'] = name + '-' + str(i)
            j['runtime_digest'] = digest; j['contract_digest'] = fingerprint(protocol)
            j['audio_ready_perf'] = 0.; j['enqueue_perf'] = time.perf_counter()
            j.pop('fault_actual_prompt_tokens', None)
        worker.submit(jobs); started = time.perf_counter(); telemetry = []
        while True:
            result = worker.poll(); telemetry += worker.drain_telemetry()
            if result is not None: break
            if time.perf_counter() - started > 600: raise TimeoutError('bounded diagnostic batch exceeded600s')
            time.sleep(.001)
        save(D / (name + '.json'), {'phase': name, 'jobs': jobs, 'results': result,
                                   'telemetry': telemetry, 'operator_wall_seconds': time.perf_counter() - started})
        phases.append(name); print(name, flush=True)
        return result

    def make_worker(mode):
        rt = copy.deepcopy(cfg['authority_runtime'])
        rt.update(online_selection_mode=mode, online_oracle_diagnostic=bool(mode), fallback_layout='selective')
        config = {**rt, 'gpu': 1, 'model': str(B / 'models/Qwen3-ASR-1.7B'),
                  'manifest': str(manifest_path), 'runtime_digest': digest,
                  'capture_model_inputs': True, 'lifecycle_instrumentation': True,
                  'allow_execution_context_override': False}
        w = GPUExecutor('formal-diagnostic-' + str(mode), config)
        try: w.wait_ready()
        except BaseException:
            w.close()
            raise
        save(D / ('WORKER-' + str(mode) + '.json'), {'config': config, 'ready': w.ready})
        return w

    try:
        sampler = PowerSampler([1], interval=.2); sampler.start()
        for mode in ['score', 'strict']:
            worker = make_worker(mode)
            for bi, batch in enumerate(plan['batches']):
                if ('score' if batch['method'] == 'score' else 'strict') != mode: continue
                old = groups[batch['cell'], batch['batch_index']]
                result = run('target-' + str(bi), [r['job'] for r in old])
                for i, (origin, new) in enumerate(zip(old, result)):
                    assert new['model_input_audit']['batch_tensors'] == origin['result']['model_input_audit']['batch_tensors']
                    assert new['model_input_audit']['input_ids'] == origin['result']['model_input_audit']['input_ids']
                    proof = new['online_verification']; oracle = proof['pilot_oracle']
                    assert oracle['same_input_repeat_equal'] and all(oracle['oracle_selfchecks']) and all(oracle['accepted_equal_independent_greedy'])
                    if origin['job']['job_id'] not in batch['target_job_ids']: continue
                    candidate = origin['job']['candidate_token_ids']; expected = oracle['oracle_token_ids'][i]
                    old_proof = origin['result']['online_verification']
                    if batch['method'] != 'unprotected':
                        assert old_proof['candidate_accepted'] == proof['candidate_accepted'], 'same target decision changed on exact input replay'
                    # The diagnostic result's selected P may be a selective
                    # fallback realization. Reconstruct full-layout oracle P
                    # from its actual target generation tokens, not old Z.
                    from qwen_asr import parse_asr_output
                    from transformers import AutoProcessor
                    # Loaded lazily once for the entire campaign.
                    if not hasattr(main, 'tokenizer'):
                        main.tokenizer = AutoProcessor.from_pretrained(B / 'models/Qwen3-ASR-1.7B', local_files_only=True).tokenizer
                    tok = main.tokenizer
                    raw = new['model_input_audit']['rollback_prefix'] + tok.decode(expected, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                    expected_P = tok.encode(raw); _, expected_text = parse_asr_output(raw, user_language=origin['job']['language'])
                    source_id = origin['job']['source_id']
                    summaries.append({'cell': batch['cell'], 'job_id': origin['job']['job_id'], 'source_id': source_id,
                                      'method': batch['method'], 'candidate_equal_generated_FP32_oracle': candidate == expected,
                                      'candidate_accepted_online': old_proof['candidate_accepted'],
                                      'correct_context_full_forward_pass': proof['candidate_accepted'] if mode == 'strict' else None,
                                      'accepted_but_generated_reference_differs': old_proof['candidate_accepted'] and candidate != expected,
                                      'fallback_selected_online': old_proof['fallback_used'],
                                      'exact_original_processor_input': True, 'same_input_reference_repeat': True})
                    if batch['method'] == 'unprotected':
                        future_roots.append({'cell': batch['cell'], 'origin': origin,
                                             'oracle_Z': expected, 'oracle_P': expected_P, 'oracle_text': expected_text})
            worker.close(); worker = None
        worker = make_worker(None); futures = []
        for i, root in enumerate(future_roots):
            old = root['origin']; j = old['job']; name = root['cell']; source = sources[j['source_id']]
            later = sorted([r['job'] for r in records[name].values() if r['job']['role'] == 'authority'
                            and r['job']['session_id'] == j['session_id']
                            and r['job']['audio_start_sample'] == j['audio_end_sample']], key=lambda r: r['audio_end_sample'])
            if not later:
                futures.append({'cell': name, 'source_id': j['source_id'], 'status': 'no_later_interval_retained_in_denominator'})
                continue
            wav, rate = sf.read(source['path'], dtype='float32'); assert rate == 16000
            wav = np.asarray(wav, dtype='<f4'); base = copy.deepcopy(later[0]); total = len(wav)
            base.update(audio_end_sample=total, end_window=math.ceil(total / 32000),
                        chunk_advance=math.ceil(total / 32000) - base['chunk_id'],
                        prefix_audio_sha256=hashlib.sha256(wav.tobytes()).hexdigest(),
                        interval_audio_sha256=hashlib.sha256(wav[base['audio_start_sample']:].tobytes()).hexdigest())
            for k in list(base):
                if k.startswith('candidate_') or k.startswith('online_'): base.pop(k)
            bad, good = copy.deepcopy(base), copy.deepcopy(base)
            bad['prompt_tokens'] = old['result']['state_tokens']; good['prompt_tokens'] = root['oracle_P']
            for x in [bad, good]: x['parent_prompt_digest'] = digest_tokens(x['prompt_tokens'])
            a = run('future-' + str(i), [bad, good]); b = run('future-repeat-' + str(i), [bad, good])
            assert all(x['token_ids'] == y['token_ids'] and x['state_tokens'] == y['state_tokens']
                       and x['text'] == y['text'] for x, y in zip(a, b)), 'same future input repeat changed'
            futures.append({'cell': name, 'source_id': j['source_id'], 'status': 'complete_fixed_future_GPU_control',
                            'candidate_Z_differs_reference': old['result']['token_ids'] != root['oracle_Z'],
                            'admitted_P_differs_reference': old['result']['state_tokens'] != root['oracle_P'],
                            'actual_live_next_authority_consumed_admitted_P': later[0]['prompt_tokens'] == old['result']['state_tokens'],
                            'future_effective_unpadded_input_ids_diff': a[0]['model_input_audit']['unpadded_input_ids'] != a[1]['model_input_audit']['unpadded_input_ids'],
                            'future_rollback_prefix_diff': a[0]['model_input_audit']['rollback_prefix'] != a[1]['model_input_audit']['rollback_prefix'],
                            'new_Z_differs': a[0]['token_ids'] != a[1]['token_ids'],
                            'final_P_differs': a[0]['state_tokens'] != a[1]['state_tokens'],
                            'final_text_differs': a[0]['text'] != a[1]['text'],
                            'unsafe_quality': quality_counts(source['reference'], a[0]['text']),
                            'reference_quality': quality_counts(source['reference'], a[1]['text']),
                            'unsafe_hit_limit': a[0]['hit_token_limit'], 'reference_hit_limit': a[1]['hit_token_limit'],
                            'scope': 'trace-derived controlled continuation, not live incidence or serving latency'})
        power = sampler.stop(); save(D / 'POWER.json', {'operator_campaign': power, 'samples': sampler.rows, 'not_serving_energy': True})
        save(D / 'SUMMARY.json', {'status': 'COMPLETE_FORMAL_REFERENCE_AND_FUTURE_LABELS',
                                  'labels': summaries, 'future_controls': futures, 'phases': phases,
                                  'missing_opportunities': [x for x in plan['opportunities'] if x['status'] != 'selected_by_input_time'],
                                  'not_a_serving_performance_claim': True})
    except BaseException as e:
        save(D / 'STOP.json', {'error': repr(e), 'completed_phases': phases, 'no_silent_retry': True})
        raise
    finally:
        if sampler is not None: sampler.stop()
        if worker is not None: worker.close()


if __name__ == '__main__': main()
