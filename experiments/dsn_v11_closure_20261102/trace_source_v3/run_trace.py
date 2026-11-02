"""Frozen, read-only CPU accounting of the original normal32 service traces."""
from __future__ import annotations
import argparse
import datetime
import importlib
import io
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import unittest
from trace_common import (BASE, NN4F, NN_MANIFEST_SHA, Inputs, close, csvout,
                          current_environment, disk, need, no_model_imports,
                          put, read, sha, verify_tree)
from trace_analysis import STATE_FIELDS, aggregate, analyze_cell, validate_scope


def binding(spec, expected_commit=None, expected_manifest_sha=None, expected_files=None):
    return verify_tree(spec['source_root'], spec['source_manifest'],
                       expected_commit or spec['source_commit'],
                       expected_manifest_sha or spec['source_manifest_sha256'], expected_files)


def control_snapshot(paths):
    return {str(disk(path).resolve()): dict(bytes=Path(path).stat().st_size, sha256=sha(path))
            for path in paths}


def indexed_inputs(config):
    spec = config['raw_index']
    path = disk(spec['path'])
    need(sha(path) == spec['sha256'], 'Root frozen raw index SHA differs')
    index = read(path)
    need(index['status'] == 'FROZEN_COMPLETE_ORIGINAL32_EVENT_INPUTS_NOT_ANALYSIS_RESULT'
         and index['source_producer'] == NN4F, 'wrong original32 input freeze')
    need(len(index['prior_C4_bindings']) == 32
         and {r['cell_id'] for r in index['prior_C4_bindings']} == {r['cell_id'] for r in index['cells']}
         and all(r['all_current_core_bytes_equal_original_completed_C4'] is True
                 for r in index['prior_C4_bindings']), 'original completed C4 raw bindings missing')
    items = []
    for name, item in index['inputs'].items():
        need(item.get('path', name) == name, 'raw index key/path differs')
        items.append(dict(item, path=name))
    report = config['verified_report']
    existing = next((item for item in items if item['path'] == report['path']), None)
    if existing is None:
        items.append(report)
    else:
        need(existing['bytes'] == report['bytes'] and existing['sha256'] == report['sha256'],
             'report identity conflicts with raw index')
    for label in ('original_service_summary', 'prior_C4_summary'):
        bound = index[label]
        need(bound['path'] in index['inputs'], 'original summary absent from input inventory')
        prior = index['inputs'][bound['path']]
        need(bound['bytes'] == prior['bytes'] and bound['sha256'] == prior['sha256'],
             'summary hash differs from raw input inventory')
    return index, items


def load_cell(cell, inputs, scanner):
    root = disk(cell['raw_root']).resolve()
    actual = {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith('owner_e')}
    owners = []
    for declared in cell['owner_directories']:
        path = Path(declared)
        path = path if path.is_absolute() else root / path
        need(path.resolve().parent == root, 'declared Owner directory escapes cell')
        owners.append(path.name)
    need(actual == set(owners) == {'owner_e0'}, 'normal32 physical Owner attempt scope differs')
    data = dict(config=inputs.json(root / 'CONFIG.json'), origin=inputs.json(root / 'ORIGIN.json'),
                summary=inputs.json(root / 'SUMMARY.json'), consumer=inputs.lines(root / 'consumer.jsonl'),
                publications=inputs.lines(root / 'publications.jsonl'), ingress=inputs.lines(root / 'ingress.jsonl'),
                frames=list(scanner(inputs.path(root / 'facts.wal'), repair_tail=False)),
                dispatch=[], results=[], events=[], audit=[])
    for owner in owners:
        epoch = int(owner.removeprefix('owner_e'))
        for key, file in (('dispatch', 'dispatch.jsonl'), ('results', 'worker_results.jsonl'),
                          ('events', 'owner_events.jsonl'), ('audit', 'policy_audit.jsonl')):
            for row in inputs.lines(root / owner / file):
                need('owner_epoch' not in row or row['owner_epoch'] == epoch, 'Owner directory/epoch differs')
                data[key].append(dict(row, owner_epoch=epoch))
    need(data['summary']['gate'] == 'PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT',
         'original trial task gate not PASS')
    source = data['config']['settings']['sources'][0]
    expected = list(range(8000, source['frames'], 8000)) + [source['frames']]
    ingress = data['ingress']
    need(len(ingress) == len(expected), 'original ingress/EOS count differs')
    for row, frontier in zip(ingress, expected):
        need(row['source_id'] == source['source_id'] and row['frontier'] == frontier,
             'original ingress frontier differs')
        close(row['original_offer'], data['origin']['origin_perf'] + frontier / 16000,
              'original ingress clock differs')
    return data


def controls(out):
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent),
                                              pattern='test_trace_controls.py')
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out / 'CONTROLS.txt').write_text(stream.getvalue(), encoding='utf8')
    need(result.testsRun == 9 and result.wasSuccessful() and not result.skipped,
         'nine frozen synthetic controls failed')
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=0)


def run(args):
    began = time.monotonic()
    source = Path(__file__).resolve().parent
    config_path, manifest_path, prelaunch_path = map(disk, (args.config, args.manifest, args.prelaunch))
    config, prelaunch = read(config_path), read(prelaunch_path)
    need(sha(config_path) == prelaunch['config_sha256'], 'prelaunch frozen config SHA differs')
    need(config['mode'] in ('controls', 'analysis'), 'unknown CPU analysis mode')
    own = config['analysis_source']
    need(Path(own['source_root']).resolve() == source
         and Path(own['source_manifest']).resolve() == manifest_path.resolve(), 'CLI/source paths differ')
    identity = binding(own)
    need(config['actual_NN']['source_commit'] == NN4F
         and config['actual_NN']['source_manifest_sha256'] == NN_MANIFEST_SHA,
         'wrong actual NN dependency identity')
    nn_identity = binding(config['actual_NN'], NN4F, NN_MANIFEST_SHA, 59)
    gate_path = disk(prelaunch['root_noarg_preflight'])
    need(sha(gate_path) == prelaunch['root_noarg_preflight_sha256'], 'Root CURRENT receipt differs')
    gate = read(gate_path)
    need(gate['gate'] == 'SOURCE_IDENTITY_PASS' and gate['code_commit'] == identity['source_commit']
         and gate['manifest_sha256'] == identity['source_manifest_sha256'], 'Root CURRENT does not identify this analysis source')
    env_path = disk(config['environment_record'])
    need(sha(env_path) == config['environment_record_sha256'], 'frozen CPU environment SHA differs')
    need(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and sys.dont_write_bytecode,
         'run CPU-only with CUDA_VISIBLE_DEVICES empty and -B')
    environment = current_environment()
    need(read(env_path) == environment, 'actual CPU environment differs from frozen record')
    no_model_imports()
    out = disk(args.out)
    disk(config['stdout_location']); disk(config['stderr_location']); disk(config['raw_base'])
    need(str(out) == config['raw_result_location']
         and str(out / 'SUMMARY.json') == config['aggregate_summary_location']
         and str(out / 'GATE.json') == config['gate_decision_location'], 'output paths differ from frozen config')
    need(0 < config['max_input_bytes'] <= 512 * 1024 * 1024
         and 0 < config['max_output_bytes'] <= 32 * 1024 * 1024
         and 0 < config['max_elapsed_seconds'] <= 3600, 'unbounded analysis budgets')
    need(out.parent.exists() and shutil.disk_usage(BASE).free >= config['minimum_free_bytes'],
         'output parent/free-space gate')
    need(os.stat(out.parent).st_dev == os.stat(BASE).st_dev, 'output not on designated experiment device')
    lease = disk(config['lease_path'])
    need(lease.parent.exists(), 'lease parent missing')
    handle = os.open(lease, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, 'w', encoding='utf8') as stream:
        stream.write(config['experiment_id'] + '\n')
    out.mkdir(exist_ok=False)
    control_paths = [config_path, manifest_path, prelaunch_path, gate_path, env_path,
                     config['actual_NN']['source_manifest'], config['raw_index']['path']]
    before_controls = control_snapshot(control_paths)
    record = dict(experiment_id=config['experiment_id'], started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  code_commit=identity['source_commit'], source_identity=identity,
                  actual_NN_dependency=nn_identity, own_config=str(config_path), config_sha256=sha(config_path),
                  prelaunch=str(prelaunch_path), prelaunch_sha256=sha(prelaunch_path),
                  root_noarg_preflight=str(gate_path), root_noarg_preflight_sha256=sha(gate_path),
                  environment_record=str(env_path), environment_record_sha256=sha(env_path),
                  raw_base=config['raw_base'], raw_index=config['raw_index'],
                  verified_report=config['verified_report'], frozen_input_inventory_bound_by_config=True,
                  raw_result_location=str(out), aggregate_summary_location=str(out / 'SUMMARY.json'),
                  gate_decision_location=str(out / 'GATE.json'), stdout_location=config['stdout_location'],
                  stderr_location=config['stderr_location'], model_calls=0,
                  source_device=os.stat(source).st_dev, output_device=os.stat(out).st_dev)
    put(out / 'RUN_RECORD_PRELAUNCH.json', record)
    put(out / 'CONFIG_FROZEN.json', config)
    put(out / 'PRELAUNCH_FROZEN.json', prelaunch)
    put(out / 'ENVIRONMENT.json', environment)
    try:
        put(out / 'CONTROL_HASHES_BEFORE.json', before_controls)
        checked = controls(out)
        if config['mode'] == 'controls':
            summary = dict(status='PASS_NINE_FROZEN_CPU_TRACE_CONTROLS_ONLY', controls=checked,
                           actual_raw_scanned=False, new_model_calls=0)
        else:
            index, items = indexed_inputs(config)
            inputs = Inputs(items, config['max_input_bytes'])
            before = inputs.verify()
            put(out / 'INPUT_HASHES_BEFORE.json', before)
            archive = inputs.json(index['original_service_summary']['path'])
            report = inputs.json(config['verified_report']['path'])
            archived = validate_scope(index['cells'], archive)
            need(report['status'] == 'PASS_COMPLETE_NEW8_CONFIRMATION_REPORT'
                 and report['actual_NN_source'] == NN4F and report['C4']['passed'] is True
                 and report['C4']['checked_cases'] == 32
                 and report['C4']['source_summary_sha256'] == index['prior_C4_summary']['sha256'],
                 'complete original C4/report receipt absent')
            nn_root = Path(nn_identity['source_root'])
            need('feedback_contract' not in sys.modules and 'resilience_storage' not in sys.modules,
                 'original helper was imported before dependency validation')
            sys.path.insert(0, str(nn_root))
            feedback = importlib.import_module('feedback_contract')
            storage = importlib.import_module('resilience_storage')
            need(Path(feedback.__file__).resolve() == nn_root / 'feedback_contract.py'
                 and Path(storage.__file__).resolve() == nn_root / 'resilience_storage.py'
                 and feedback.STATE_FIELDS == STATE_FIELDS, 'wrong original pure helper module')
            from trace_common import digest
            need(feedback.digest({'clock': 1.25, 'state': ['frozen', 2]})
                 == digest({'clock': 1.25, 'state': ['frozen', 2]}), 'original canonical digest differs')
            per_cell, jobs, endpoint_rows, miss_rows = [], [], [], []
            for cell in index['cells']:
                need(time.monotonic() - began <= config['max_elapsed_seconds'], 'bounded CPU time exceeded')
                need(disk(cell['raw_root']).resolve().is_relative_to(disk(config['raw_base']).resolve()),
                     'cell outside frozen R3 raw base')
                data = load_cell(cell, inputs, storage.scan)
                need(data['config']['settings']['sources'][0]['frames'] == cell['frames'],
                     'frozen index frame denominator differs')
                values = analyze_cell(cell, data, archived[cell['cell_id']])
                per_cell.append(values[0]); jobs.extend(values[1]); endpoint_rows.extend(values[2]); miss_rows.extend(values[3])
            summary = aggregate(per_cell)
            close(summary['selected_steps'], report['checked_original_steps'], 'all32 selected transitions')
            for policy, actual in summary['policies'].items():
                expected = report['policies'][policy]
                for own_key, expected_key in (('offered_audio_s', 'offered_audio_s'),
                                               ('original_credit_audio_s', 'credit_audio_s'),
                                               ('passes', 'D2_C8_passes')):
                    close(actual[own_key], expected[expected_key], 'frozen report policy.' + own_key)
            after = inputs.verify()
            need(before == after, 'raw inputs changed during CPU analysis')
            put(out / 'INPUT_HASHES_AFTER.json', after)
            put(out / 'ACCESSED_INPUTS.json', sorted(inputs.accessed))
            put(out / 'PER_CELL.json', per_cell)
            put(out / 'SOURCE_DEFICIT_LEDGER.json', summary['source_deficit_ledger'])
            csvout(out / 'SOURCE_DEFICIT_LEDGER.csv', summary['source_deficit_ledger'])
            csvout(out / 'JOB_TIMELINES.csv', jobs)
            csvout(out / 'ENDPOINTS.csv', endpoint_rows)
            csvout(out / 'MISS_TIMELINES.csv', miss_rows)
            summary.update(controls=checked, raw_input_files=len(before),
                           raw_input_bytes=sum(r['bytes'] for r in before.values()),
                           raw_inputs_before_after_unchanged=True, all32_original_endpoint_fields_conserved=True,
                           issued_job_timeline_rows=len(jobs), all_offered_endpoint_rows=len(endpoint_rows),
                           D2_miss_timeline_rows=len(miss_rows), original_C4_scope=report['C4'],
                           timestamp_scope='All times are original perf_counter host observations. Install fields are log observations; model intervals are host boundaries, not CUDA-kernel time. Publication receive-to-Consumer is not a pure guard tax.')
        need(time.monotonic() - began <= config['max_elapsed_seconds'], 'bounded CPU time exceeded')
        no_model_imports()
        need(binding(own) == identity and binding(config['actual_NN'], NN4F, NN_MANIFEST_SHA, 59) == nn_identity,
             'source identity changed during analysis')
        after_controls = control_snapshot(control_paths)
        need(before_controls == after_controls, 'frozen control bytes changed')
        put(out / 'CONTROL_HASHES_AFTER.json', after_controls)
        need(sum(p.stat().st_size for p in out.iterdir() if p.is_file())
             < config['max_output_bytes'] - 65536, 'output byte budget exceeded')
        put(out / 'SUMMARY.json', summary)
        put(out / 'GATE.json', dict(status=summary['status'], new_model_calls=0,
                                   accounting_only=True, desired_cause_or_S0915_value_not_a_pass_condition=True))
        put(out / 'RUN_RECORD_FINAL.json', dict(record, completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                               summary_sha256=sha(out / 'SUMMARY.json'), gate_sha256=sha(out / 'GATE.json'),
                                               elapsed_seconds=time.monotonic() - began, status=summary['status']))
        print(summary['status'])
        return 0
    except BaseException:
        failure = dict(status='FAIL_OR_INCOMPLETE_CPU_TRACE_ACCOUNTING_PRESERVED',
                       new_model_calls=0, failure=traceback.format_exc())
        if not (out / 'GATE.json').exists():
            put(out / 'GATE.json', failure)
        if not (out / 'SUMMARY.json').exists():
            put(out / 'SUMMARY.json', failure)
        if not (out / 'RUN_RECORD_FINAL.json').exists():
            put(out / 'RUN_RECORD_FINAL.json', dict(record, **failure))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('config', 'manifest', 'prelaunch', 'out'):
        parser.add_argument('--' + name, required=True)
    raise SystemExit(run(parser.parse_args()))
