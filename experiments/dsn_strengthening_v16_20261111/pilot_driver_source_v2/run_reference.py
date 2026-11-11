"""Paid original continuous/restore short references; no serving claims.

Imports the complete clean newly frozenv3 runtime. Its long_reference MAIN,
long-stream receipt/recipe and service controller are never invoked.
"""
from __future__ import annotations
import argparse, collections, copy, datetime, hashlib, importlib.metadata, json, os
import pathlib, platform, random, subprocess, sys, time, traceback, wave
from ref_common import (NN4F, B, SUCCESS, need, read, put, sha, inventory,
    verify_inventory, verify_source, sources_from_receipt, expected_frontiers, disk, canonical)
from reference_logic import generate_source
from confirmation_common import validate_prelaunch


def gpu_precondition(gpu, uuid):
    owners = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid',
        '--format=csv,noheader,nounits'], text=True, timeout=15).strip()
    need(not owners, 'another CUDA owner exists; do not touch it or launch')
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.used,utilization.gpu',
        '--format=csv,noheader,nounits'], text=True, timeout=15)
    records = {int(row.split(',')[0]): [v.strip() for v in row.split(',')[1:]]
               for row in raw.splitlines() if row.strip()}
    need(gpu in records and records[gpu][0] == uuid, 'physical GPU identity differs')
    return dict(gpu=gpu, gpu_uuid=uuid, no_existing_compute_owners=True, original_query=raw)


def boot(args, plan):
    own = verify_source(pathlib.Path(__file__).parent, args.manifest)
    pre = read(args.prelaunch)
    base = verify_source(plan['base_source'], plan['base_manifest'], NN4F)
    validate_prelaunch(pre,args.plan,own,base)
    need(plan['generator']==own and plan['actual_NN']==base,'new reference generator/runtime identity drift')
    need(base['complete_files'] == 66 and plan['actual_NN_source_commit'] == NN4F, 'not complete actualv3 runtime')
    verify_inventory(plan['inputs'])
    need(sha(plan['asset_byte_gate']) == plan['asset_byte_gate_sha256'], 'asset-byte gate changed')
    assets = read(plan['asset_byte_gate'])
    need(assets['status'].startswith('PASS') and assets.get('all_asset_bytes_verified') is True,
         'Root actual model-byte prerequisite failed')
    receipt = read(plan['selection_receipt'])
    sources = sources_from_receipt(receipt)
    need(sha(plan['selection_receipt']) == plan['selection_receipt_sha256'] and
         sources == plan['sources'] and len(sources) == plan['expected_sources'], 'frozen metadata source set changed')
    need(plan['expected_original_steps'] == sum(len(expected_frontiers(s['frames'])) for s in sources),
         'reference source/step denominator changed')
    need(plan['continuous_no_between_step_restore'] is True and plan['restored_repeats_per_edge'] == 2
         and plan['first_failure_controls'] == dict(same_input_adapter_repeats=2,
             original_continuous_prefix_repeats=1, first_failed_boundary_per_source=True), 'reference control protocol changed')
    need(plan['original_seed'] == 1701 and plan['original_FP32'] is True and plan['original_TF32'] is False
         and plan['source_replacement_after_reference_forbidden'] is True
         and plan['reference_only'] is True and plan['actual_serving_runs'] == 0,
         'reference numerical/source-selection/accounting scope changed')
    env = read(plan['environment_record'])
    need(pathlib.Path(sys.executable).resolve() == pathlib.Path(plan['environment_python']).resolve(), 'wrong actual interpreter')
    packages = {name: importlib.metadata.version(name) for name in env['packages']}
    need(packages == env['packages'], 'frozen package versions differ')
    backend = plan['backend']; author = pathlib.Path(backend['author_root']).resolve()
    for name in ('author_root', 'asr_model', 'corrector_base', 'corrector_adapter',
                 'text_backbone', 'corrector_audio_processor'):
        disk(backend[name])
    head = subprocess.check_output(['git', '-C', str(author), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(author), 'status', '--porcelain', '--untracked-files=all'], text=True).strip()
    need(not dirty and head == backend['contract']['native_author_commit'], 'original author checkout changed')
    need(plan['runtime_environment'] == {'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True'}, 'allocator contract changed')
    gpu = gpu_precondition(plan['gpu'], plan['gpu_uuid'])
    return own, base, sources, packages, gpu


def load_audio(source, soundfile):
    path = disk(source['path']); need(sha(path) == source['audio_sha256'], 'immutable original WAV changed')
    with wave.open(str(path), 'rb') as f:
        need(f.getframerate() == 16000 and f.getnchannels() == 1 and f.getsampwidth() == 2
             and f.getnframes() == source['frames'] and f.getcomptype() == 'NONE', 'original WAV format/frames changed')
        pcm = f.readframes(f.getnframes())
    if 'header' in source:
        need(hashlib.sha256(pcm).hexdigest() == source['header']['PCM_sha256'], 'original PCM bytes changed')
    data, sr = soundfile.read(path, dtype='float32')
    need(sr == 16000 and data.ndim == 1 and len(data) == source['frames'], 'actual native float32 audio changed')
    return data


def energy_from_rows(rows, start, end):
    by = {}
    for gpu in ('0', '1'):
        pts = sorted((r['time'], r['watts'][gpu] if gpu in r['watts'] else r['watts'][int(gpu)]) for r in rows)
        need(len(pts) >= 2 and pts[0][0] <= start <= end <= pts[-1][0], 'reference power window lacks boundary observations')
        total = 0.0
        for (a, x), (b, y) in zip(pts, pts[1:]):
            need(b > a, 'reference power clock regressed')
            lo, hi = max(a, start), min(b, end)
            if hi > lo:
                low, high = x+(y-x)*(lo-a)/(b-a), x+(y-x)*(hi-a)/(b-a)
                total += .5*(low+high)*(hi-lo)
        by[gpu] = total
    return dict(begin_perf=start, end_perf=end, seconds=end-start, board_joules=by,
        total_joules=sum(by.values()), reference_only=True, actual_serving_runs=0,
        scope='both-board model/import/load/warmup/reference/diagnostic window; final process exit checked externally')


def run(args):
    plan = read(args.plan); own, base, sources, packages, gpu = boot(args, plan)
    out = disk(plan['raw_result_location']); need(not out.exists(), 'refusing to overwrite reference run')
    cache = disk(plan['cache_root']); out.mkdir(parents=True); (out/'sources').mkdir(); (out/'controls').mkdir()
    env_keys = [('HF_HOME', 'huggingface'), ('HF_MODULES_CACHE', 'huggingface/modules'), ('TORCH_HOME', 'torch'),
        ('XDG_CACHE_HOME', 'xdg'), ('TRITON_CACHE_DIR', 'triton'), ('TORCHINDUCTOR_CACHE_DIR', 'inductor'),
        ('CUDA_CACHE_PATH', 'cuda'), ('NUMBA_CACHE_DIR', 'numba'), ('TMPDIR', 'reference_tmp')]
    for key, leaf in env_keys:
        folder = cache/leaf; folder.mkdir(parents=True, exist_ok=True); os.environ[key] = str(folder)
    (cache/'xdg/torch/kernels').mkdir(parents=True, exist_ok=True)
    os.environ.pop('PYTORCH_ALLOC_CONF', None)
    os.environ.update(plan['runtime_environment'])
    os.environ.update(CUDA_VISIBLE_DEVICES=str(plan['gpu']), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
        CUBLAS_WORKSPACE_CONFIG=':4096:8', PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode = True
    put(out/'CONFIG.json', plan)
    put(out/'ENVIRONMENT.json', dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
        generator=own, actual_NN=base, packages=packages, physical_GPU=gpu,
        actual_serving_runs=0, reference_only=True, runtime_environment=plan['runtime_environment']))
    put(out/'RUN_RECORD.json', dict(experiment_id=plan['experiment_id'], code_commit=own['source_commit'],
        actual_NN_source_commit=NN4F, execution_roles=dict(generator=own, original_NN=base),
        frozen_config=str(out/'CONFIG.json'), config_sha256=sha(out/'CONFIG.json'),
        environment_record=str(out/'ENVIRONMENT.json'), environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out), aggregate_summary_location=str(out/'SUMMARY.json'),
        gate_decision_location=str(out/'GATE.json'), reference_only=True, actual_serving_runs=0,
        expected_sources=len(sources), expected_original_steps=plan['expected_original_steps'],
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    model = power = None; details = []; outcomes = []; ledger = collections.Counter(); energy = None
    input_hashes = dict(plan['inputs']); writers = []
    try:
        sys.path.insert(0, plan['base_source'])
        from long_reference import continuous_transitions, compare_edge, frontiers, JsonLines
        from feedback_contract import FeedbackCut
        from native_bridge import restore_cut, export_cut
        from resilience_trial import BoundedPower
        # Power begins before torch/CUDA/model initialization. This is paid
        # reference work; no service latency or throughput is measured.
        power = BoundedPower(out/'REFERENCE_POWER.jsonl')
        wait = time.perf_counter()+30
        while len(power.recent) < 2:
            need(power.error is None and power.t.is_alive() and time.perf_counter() < wait, 'reference power sampler failed at startup')
            time.sleep(.02)
        power_start = time.perf_counter()
        import numpy as np, soundfile as sf, torch
        torch.cuda.set_device(0); torch.set_num_threads(1); torch.manual_seed(1701)
        np.random.seed(1701); random.seed(1701)
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True
        audio = {}
        for source in [plan['warmup_source'], *sources]:
            audio[source['source_id']] = load_audio(source, sf)
            input_hashes[source['path']] = dict(bytes=pathlib.Path(source['path']).stat().st_size,
                                                sha256=source['audio_sha256'])
        from candidate_bridge import CandidateBridge
        load_start = time.perf_counter()
        model = CandidateBridge(stage_role='authority', source_commit=NN4F, corrector_dtype='float32', **plan['backend'])
        loaded = time.perf_counter()
        warm = plan['warmup']; warm_source = plan['warmup_source']
        warm_start = model.rebind_warm_cut(warm['original_reference_start_state'], warm_source['audio_sha256'])
        warm_record = model.warm_neural_ready(audio=audio[warm_source['source_id']], start=warm_start, end=32000)
        ledger['declared_fixed_warmup_full_step_calls'] += 1
        need(warm_record['neural_C_confirmed'] and warm_record['reset_to_genesis'], 'fixed original neural warmup was not executed')
        dtypes = {name: sorted({str(p.dtype) for p in module.parameters() if p.is_floating_point()})
                  for name, module in [('asr', model.engine.model), ('corrector', model.corrector_model)]}
        need(all(v == ['torch.float32'] for v in dtypes.values()) and not torch.is_autocast_enabled(), 'original FP32 execution contract changed')
        put(out/'MODEL_READY.json', dict(runtime_identity=model.runtime_identity, actual_NN_source_commit=NN4F,
            model_load_seconds=loaded-load_start, actual_parameter_dtypes=dtypes, original_warmup=warm_record,
            CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'], reference_only=True))
        genesis = {s['source_id']: model.initial_for(s['audio_sha256']).state for s in sources}
        put(out/'GENESIS.json', genesis)
        call_log = JsonLines(out/'REFERENCE_CALLS.jsonl', durable=True); writers.append(call_log)
        for source in sources:
            sid = source['source_id']; folder = out/'sources'/sid; folder.mkdir()
            need(frontiers(source['frames']) == expected_frontiers(source['frames']), 'original helper cadence differs')
            raw_log = JsonLines(folder/'RAW_REFERENCE_EVENTS.jsonl', durable=True); writers.append(raw_log)
            latest = {'row': None}
            def reset():
                initial = model.initial_for(source['audio_sha256'])
                restore_cut(model.engine, initial, audio=audio[sid], contract=initial.state['contract'])
                model.engine.first_token_generated = False; model.engine.first_token_latency = None
            def continuous(*, stop_at, phase):
                def checkpoint(row):
                    latest['row'] = copy.deepcopy(row)
                    ledger[phase+'_step_attempts'] += 1
                    put(folder/('LAST_ORIGINAL_INPUT_'+phase+'.json'), row, replace=True)
                for row in continuous_transitions(model, source, audio[sid], cut_export=export_cut,
                    to_tensor=lambda x: torch.from_numpy(np.asarray(x, dtype=np.float32).copy()),
                    sync=torch.cuda.synchronize, stop_at=stop_at, before_infer=checkpoint):
                    need(all(row[key]['contract']['stage_execution']['source_commit'] == NN4F
                         and row[key]['contract']['source_sha'] == source['audio_sha256']
                         for key in ('original_full_start_cut', 'original_full_cut')),
                         'original reference source/actual execution marker changed')
                    ledger[phase+'_step_completed'] += 1
                    ledger[phase+'_native_model_evaluated'] += int(row['original_full_result']['native_model_evaluated'])
                    call_log.write(dict(phase=phase, source_id=sid, end=row['end'],
                        start=row['original_full_start_cut']['frontier'], model_start=row['original_model_start'],
                        model_end=row['original_model_end'], native_model_evaluated=row['original_full_result']['native_model_evaluated']))
                    yield row
            def restored(reference, *, phase, repeat):
                ledger[phase+'_full_step_attempts'] += 1
                start = FeedbackCut(reference['original_full_start_cut']); begin = time.perf_counter()
                try:
                    cut, record = model.full_step(audio=audio[sid], start=start, end=reference['end'],
                                                  is_last=reference['end'] == source['frames'])
                except Exception:
                    call_log.write(dict(phase=phase, repeat=repeat, source_id=sid, end=reference['end'],
                        host_begin=begin, host_end=time.perf_counter(), exception=traceback.format_exc(),
                        native_model_evaluated='UNKNOWN_NO_COMPLETE_RECORD'))
                    raise
                ledger[phase+'_full_step_completed'] += 1
                ledger[phase+'_native_model_evaluated'] += int(record['native_model_evaluated'])
                call_log.write(dict(phase=phase, repeat=repeat, source_id=sid, end=reference['end'],
                    host_begin=begin, host_end=time.perf_counter(), native_model_evaluated=record['native_model_evaluated'],
                    original_record=record))
                return cut, record
            def compare(reference, cut, record):
                result = compare_edge(reference, cut, record)
                extra = dict(original_authority=record['role'] == 'authority' and record['candidate_handoff'] is False,
                    native_evaluation_flag=record['native_model_evaluated'] == reference['original_full_result']['native_model_evaluated'])
                result['checks'].update(extra); result['all_equal'] = all(result['checks'].values())
                return result
            def emit(kind, row): raw_log.write(dict(kind=kind, payload=row))
            result = generate_source(source, reset=reset, continuous=continuous, restored=restored,
                compare=compare, emit=emit, pending=lambda: latest['row'], restored_repeats=2)
            references = result.pop('references'); details.extend(references)
            need(not references or canonical(references[0]['original_full_start_cut']) == canonical(genesis[sid]),
                 'continuous original genesis differs from model initial state')
            put(folder/'CONTINUOUS_DETAILS.json', references)
            put(folder/'SOURCE_SUMMARY.json', result); outcomes.append(result)
            raw_log.close(); writers.remove(raw_log)
            put(out/'PROGRESS.json', dict(completed_sources=len(outcomes), expected_sources=len(sources),
                original_steps=len(details), ledger=dict(ledger), no_source_replacement=True), replace=True)
            if result['execution_exception'] is not None:
                break
        call_log.close(); writers.remove(call_log)
        power_end = time.perf_counter(); wait = time.perf_counter()+30
        while not power.recent or power.recent[-1]['time'] < power_end:
            need(power.error is None and power.t.is_alive() and time.perf_counter() < wait, 'reference power missing final boundary')
            time.sleep(.02)
        power.close(); need(power.error is None and not power.t.is_alive(), 'reference power sampler did not close')
        power = None
        energy = energy_from_rows([json.loads(line) for line in
            (out/'REFERENCE_POWER.jsonl').read_bytes().splitlines() if line.strip()], power_start, power_end)
        put(out/'REFERENCE_ENERGY.json', energy)
        put(out/'REFERENCE_DETAILS.json', details)
        put(out/'INPUTS.json', input_hashes); verify_inventory(input_hashes)
        # Recheck full executable identity after model use; archive HEAD is not
        # substituted for actualv3 runtime or this generator's execution commit.
        verify_source(plan['base_source'], plan['base_manifest'], NN4F)
        verify_source(pathlib.Path(__file__).parent, args.manifest, own['source_commit'])
        ok = (len(outcomes) == len(sources) and len(details) == plan['expected_original_steps']
              and all(row['all_equal'] for row in outcomes))
        status = SUCCESS if ok else 'FAIL_SHORT_REFERENCE_EQUIVALENCE_CONTROLS_PRESERVED'
        detail_meta = dict(path=str(out/'REFERENCE_DETAILS.json'), sha256=sha(out/'REFERENCE_DETAILS.json'),
                           bytes=(out/'REFERENCE_DETAILS.json').stat().st_size, expected_steps=plan['expected_original_steps'])
        gate = dict(status=status, actual_NN_source_commit=NN4F, generator_source_commit=own['source_commit'],
            expected_sources=len(sources), completed_sources=len(outcomes), expected_original_steps=plan['expected_original_steps'],
            original_continuous_steps=len(details), all_original_full_state_C_IDs_equal=ok,
            reference_only=True, actual_serving_runs=0, reference_details=detail_meta)
        put(out/'GATE.json', gate)
        if ok:
            receipt = dict(status=SUCCESS, actual_NN_source_commit=NN4F, generator_source_commit=own['source_commit'],
                reference_origin='measured_continuous_and_restored',
                selection_receipt=dict(path=plan['selection_receipt'], sha256=plan['selection_receipt_sha256']),
                sources=sources, source_ids=[s['source_id'] for s in sources], speaker_ids=[s['speaker_id'] for s in sources],
                reference_details=detail_meta, reference_gate=dict(path=str(out/'GATE.json'), sha256=sha(out/'GATE.json')),
                genesis=dict(path=str(out/'GENESIS.json'), sha256=sha(out/'GENESIS.json')),
                reference_kind='strict', original_continuous_no_between_step_restore=True,
                restored_repeats_per_edge=2, first_failure_controls=plan['first_failure_controls'],
                ledger=dict(ledger), reference_energy=dict(path=str(out/'REFERENCE_ENERGY.json'), sha256=sha(out/'REFERENCE_ENERGY.json')),
                reference_only=True, actual_serving_runs=0,
                physical_resource_closure='ROOT_EXTERNAL_PROCESS_EXIT_AND_CUDA_EMPTY_CHECK_REQUIRED')
            put(out/'REFERENCE_RECEIPT.json', receipt)
        summary = dict(**gate, ledger=dict(ledger), source_outcomes=outcomes,
            not_attempted_source_ids=[s['source_id'] for s in sources[len(outcomes):]], reference_energy=energy,
            loader_internal_neural_call_count='NOT_INSTRUMENTED; load/import/warmup charged in reference window',
            complete_reference_receipt=(dict(path=str(out/'REFERENCE_RECEIPT.json'), sha256=sha(out/'REFERENCE_RECEIPT.json')) if ok else None),
            scope='Paid offline original-task reference, restore and repeat checks; no serving latency/Goodput claim')
        put(out/'SUMMARY.json', summary)
        need(ok, 'reference gate failed; no selected source is replaced and no service uses a failed oracle')
    except BaseException:
        failure = dict(status='FAIL_SHORT_REFERENCE_SETUP_OR_EXECUTION_PRESERVED', failure=traceback.format_exc(),
            actual_NN_source_commit=NN4F, generator_source_commit=own['source_commit'], ledger=dict(ledger),
            completed_sources=len(outcomes), expected_sources=len(sources), reference_only=True, actual_serving_runs=0)
        put(out/'FAILURE.json', failure)
        if (out/'GATE.json').exists() and read(out/'GATE.json')['status'] == SUCCESS:
            # A late artifact/export failure must invalidate the just-produced
            # receipt; its former gate SHA then cannot authorize service.
            failure['comparison_gate_before_late_failure'] = read(out/'GATE.json')
            put(out/'GATE.json', failure, replace=True)
        elif not (out/'GATE.json').exists():
            put(out/'GATE.json', failure)
        if not (out/'SUMMARY.json').exists():
            put(out/'SUMMARY.json', dict(status='FAIL_SHORT_REFERENCE_SETUP_OR_EXECUTION_PRESERVED', ledger=dict(ledger),
                                        expected_sources=len(sources), completed_sources=len(outcomes)))
        raise
    finally:
        for writer in writers:
            try: writer.close()
            except Exception: pass
        if power is not None: power.close()
        model = None


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('plan', 'manifest', 'prelaunch'): p.add_argument('--'+name, required=True)
    run(p.parse_args())
