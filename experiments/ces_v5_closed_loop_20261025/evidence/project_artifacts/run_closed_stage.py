"""Frozen, bounded closed-loop GPU stages; no implicit matrix expansion.

This file prepares/runs only the cells explicitly present in a hashed PLAN.
It does not choose audio by observed performance, tune parameters, or start
the formal stage after smoke automatically. Run each stage explicitly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


METHODS = {'fine', 'standard', 'cost', 'strict', 'service_cost',
           'reserved_progress', 'inherit', 'causal', 'risk_cost', 'progress'}
CLOSED = {'service_cost', 'reserved_progress', 'inherit', 'causal'}
STUDY = 'REVTRACE-CES-V5-CLOSED-LOOP-20261025'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value, *, replace=False):
    path = Path(path)
    if path.exists() and not replace:
        raise FileExistsError(f'Frozen or existing artifact is not overwritten: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.partial')
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')
    temporary.replace(path)


def confined(base, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('PLAN paths must be confined relative paths')
    target = (base/relative).resolve()
    target.relative_to(base.resolve())
    return target


def validate_plan(plan, stage):
    if plan.get('study_id') != STUDY:
        raise ValueError('Wrong study identity; historical studies are immutable')
    if plan.get('implementation_gates_complete') is not True:
        raise ValueError('CPU implementation/independent audit gate not explicitly complete')
    if not plan.get('cpu_gate_files'):
        raise ValueError('CPU gate evidence hashes required')
    if plan.get('independent_confirmation') is not False:
        raise ValueError('This bounded reused-source study is diagnostic, not confirmatory')
    if not str(plan.get('output_relative', '')).startswith('results/revtrace/ces_v5_closed_loop_20261025'):
        raise ValueError('Output must be a new closed-loop study path')
    for name in ('runtime_commit', 'runtime_manifest_sha256', 'manifest_sha256',
                 'calibration_sha256', 'closed_config_sha256', 'protocol_sha256',
                 'donors_sha256'):
        if not plan.get(name):
            raise ValueError('Missing frozen identity: '+name)
    spec = plan.get('stages', {}).get(stage)
    if not spec or not spec.get('cells'):
        raise ValueError('No explicitly frozen cells for stage '+stage)
    names = []
    for item in spec.get('oracles', []) + spec['cells']:
        if item['method'] not in METHODS or item['arrival'] not in ('sync', 'staggered'):
            raise ValueError('Undeclared method/arrival')
        if item['traffic'] not in ('clean', 'mixed', 'high'):
            raise ValueError('Undeclared traffic condition')
        if not isinstance(item['sessions'], int) or not 1 <= item['sessions'] <= 16:
            raise ValueError('Bounded single-study concurrency required')
        if item.get('proposer_policy', 'ready') not in ('ready', 'shared_progress', 'causal_joint'):
            raise ValueError('Undeclared physical Proposer policy')
        if not isinstance(item.get('repeat'), int) or item['repeat'] < 0:
            raise ValueError('Explicit nonnegative repeat index required')
        if 'seed' not in item:
            raise ValueError('Every cell requires an explicit frozen source/fault seed')
        if item.get('oracle'):
            if item['method'] != 'strict' or item['sessions'] > 4:
                raise ValueError('Paid Oracle is a separately labelled small Strict control')
        names.append(cell_name(item))
    if len(set(names)) != len(names):
        raise ValueError('Duplicate frozen cell identity')
    if stage == 'smoke':
        performance = spec['cells']
        if len(performance) != 4 or {(x['method'], x['arrival']) for x in performance} != {
                ('fine', 'sync'), ('fine', 'staggered'), ('causal', 'sync'), ('causal', 'staggered')}:
            raise ValueError('Initial smoke must contain exactly Fine/Causal × sync/staggered')
        if any(x['sessions'] != 8 or x.get('oracle') for x in performance):
            raise ValueError('Initial smoke is four actual eight-session serving controls')
        if any(x.get('proposer_policy', 'ready') != 'shared_progress' for x in performance):
            raise ValueError('Safety smoke must cover the shared physical Proposer subbatch path')
        oracles = spec.get('oracles', [])
        if len(oracles) != 2 or {x['traffic'] for x in oracles} != {'clean', 'mixed'}:
            raise ValueError('Initial smoke requires separate Clean/Mixed paid Strict Oracles')
        if any(not x.get('oracle') or x['sessions'] != 4 for x in oracles):
            raise ValueError('Oracle controls must have explicit separate four-session identity')
        if any(x.get('proposer_policy', 'ready') != 'ready' for x in oracles):
            raise ValueError('Small paid Strict Oracle preserves the ready Proposer reference')
    else:
        if plan.get('formal_approved_after_smoke') is not True:
            raise ValueError('Formal matrix requires an explicit new post-smoke freeze')
    # Matched methods within a source/arrival/traffic/repeat group share source
    # seed/concurrency and all common executor capabilities. An explicit joint
    # side-arm may differ only in the declared Proposer policy.
    matched = {}
    common_policies = {}
    for item in spec['cells']:
        key = item.get('pool', 'validation'), item['arrival'], item['traffic'], item['repeat']
        identity = item['sessions'], item['seed']
        if key in matched and matched[key] != identity:
            raise ValueError('Unfair paired source/concurrency/seed group')
        matched[key] = identity
        if not item.get('side_arm', False):
            common_policies.setdefault(key, set()).add(item.get('proposer_policy', 'ready'))
        else:
            main = [x for x in spec['cells'] if not x.get('side_arm', False)
                and (x.get('pool', 'validation'), x['arrival'], x['traffic'], x['repeat'], x['method']) ==
                    (item.get('pool', 'validation'), item['arrival'], item['traffic'], item['repeat'], item['method'])]
            if len(main) != 1:
                raise ValueError('Each optional GPU0 side-arm needs one same-method matched main arm')
            if item.get('proposer_policy', 'ready') == main[0].get('proposer_policy', 'ready'):
                raise ValueError('A declared single-factor side-arm must change the Proposer policy')
            if item.get('proposer_policy') not in ('shared_progress', 'causal_joint'):
                raise ValueError('Side-arm must declare one of the shared new GPU0 capabilities')
            def common_fields(cell):
                value = {k: v for k, v in cell.items() if k not in ('label', 'proposer_policy', 'side_arm')}
                value.setdefault('pool', 'validation')
                value.setdefault('oracle', False)
                return value
            if common_fields(item) != common_fields(main[0]):
                raise ValueError('A GPU0 side-arm may differ only in label and Proposer policy')
    if any(len(policies) != 1 for policies in common_policies.values()):
        raise ValueError('Main methods must share the same GPU0 physical dispatch capability/policy')
    if stage == 'formal' and any(policies != {'ready'} for policies in common_policies.values()):
        raise ValueError('Formal main matrix preserves original ready Fine/Standard/cost references')
    return spec


def cell_name(item):
    name = '-'.join((item.get('pool', 'validation'), item['arrival'], item['traffic'],
                     item['label'], 'r'+str(item['repeat'])))
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise ValueError('Unsafe cell name')
    return name


def verify_inputs(base, project, plan, plan_path):
    source = project/'runtime'
    manifest_path = source/'SOURCE_MANIFEST.json'
    if sha(manifest_path) != plan['runtime_manifest_sha256']:
        raise AssertionError('Runtime manifest differs from frozen PLAN')
    manifest = read(manifest_path)
    if manifest['code_commit'] != plan['runtime_commit']:
        raise AssertionError('Runtime commit mismatch')
    for row in manifest['files']:
        if sha(confined(source, row['path'])) != row['sha256']:
            raise AssertionError('Changed runtime source: '+row['path'])
    files = {
        'manifest': (confined(base, plan['manifest_relative']), plan['manifest_sha256']),
        'donors': (confined(base, plan['donors_relative']), plan['donors_sha256']),
        'calibration': (confined(project, plan.get('calibration_file', 'CALIBRATION.json')), plan['calibration_sha256']),
        'closed_config': (confined(project, plan.get('closed_config_file', 'CLOSED_CONFIG.json')), plan['closed_config_sha256']),
        'protocol': (project/'PROTOCOL.md', plan['protocol_sha256']),
    }
    for item in plan['cpu_gate_files']:
        files['cpu_gate:'+item['path']] = (confined(project, item['path']), item['sha256'])
    for item in plan.get('profile_files', []):
        files['profile:'+item['path']] = (confined(project, item['path']), item['sha256'])
    for name, (path, expected) in files.items():
        if sha(path) != expected:
            raise AssertionError('Frozen input hash mismatch: '+name)
    model = confined(base, plan.get('model_relative', 'models/Qwen3-ASR-1.7B'))
    if not plan.get('model_files'):
        raise AssertionError('Frozen actual model hashes required')
    for name, expected in plan['model_files'].items():
        if sha(confined(model, name)) != expected:
            raise AssertionError('Model hash mismatch: '+name)
    return source, manifest, files, model


def free_gpu():
    return not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
        '--format=csv,noheader'], text=True).strip()


def owned_workers_exited(directory):
    handles = read(directory/'OWNED_WORKER_HANDLES.json')
    checks = []
    for handle in handles:
        stat = Path('/proc')/str(handle['pid'])/'stat'
        alive = False
        actual_ticks = None
        if stat.exists():
            actual_ticks = stat.read_text().rsplit(')', 1)[1].split()[19]
            alive = actual_ticks == handle['linux_start_ticks']
        checks.append({'pid': handle['pid'], 'worker': handle['name'],
            'expected_start_ticks': handle['linux_start_ticks'],
            'observed_start_ticks': actual_ticks, 'same_owned_process_alive': alive})
    if any(row['same_owned_process_alive'] for row in checks):
        raise AssertionError('Owned Worker process did not exit at the fresh-process boundary')
    return checks


def run(command, log, cwd):
    if log.exists():
        raise FileExistsError(log)
    with log.open('w', encoding='utf8') as stream:
        result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if result.returncode:
        raise RuntimeError('Stage failed; preserve raw and do not silently retry: '+str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--stage', required=True, choices=('smoke', 'formal'))
    parser.add_argument('--plan', type=Path, default=Path(__file__).with_name('PLAN.json'))
    parser.add_argument('--validate-only', action='store_true', help='No GPU/model execution; verify frozen identities only')
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    base = args.base.resolve()
    plan_path = args.plan.resolve()
    plan = read(plan_path)
    spec = validate_plan(plan, args.stage)
    source, source_manifest, files, model = verify_inputs(base, project, plan, plan_path)
    output = confined(base, plan['output_relative'])
    expected_plan_sha = sha(plan_path)
    if args.validate_only:
        print(json.dumps({'status': 'PASS_FROZEN_PLAN_AND_SOURCE_IDENTITY_ONLY',
            'stage': args.stage, 'plan_sha256': expected_plan_sha,
            'cells': len(spec['cells']), 'oracles': len(spec.get('oracles', [])),
            'GPU_started': False}))
        return 0
    output.mkdir(parents=True, exist_ok=True)
    marker = output/(args.stage+'_GPU_STARTED.json')
    if marker.exists() or (output/(args.stage+'_STOP.json')).exists():
        raise FileExistsError('Never duplicate or silently retry this frozen stage')
    if args.stage == 'formal':
        previous = read(output/'smoke_SUMMARY.json')
        if previous['status'] != 'COMPLETE_FROZEN_CLOSED_LOOP_STAGE_AND_AUDIT' or previous['source_commit'] != plan['runtime_commit']:
            raise AssertionError('The same-source safety smoke must pass before formal freeze')
        previous_freeze = read(output/'smoke_FREEZE.json')
        for key in ('runtime_manifest_sha256', 'calibration_sha256', 'closed_config_sha256'):
            if previous_freeze[key] != plan[key]:
                raise AssertionError('Implementation/calibration changed after smoke; requires a new smoke study')
    if not free_gpu():
        raise RuntimeError('Foreign GPU ownership present; do not terminate or replace it')
    controllers = {n: sha(project/n) for n in ('run_closed_stage.py', 'audit_closed.py',
        'audit_closed_helpers.py', 'summarize_closed.py')}
    freeze = {'experiment_id': STUDY, 'stage': args.stage, 'plan': plan,
        'plan_sha256': expected_plan_sha, 'runtime_commit': plan['runtime_commit'],
        'runtime_manifest_sha256': plan['runtime_manifest_sha256'],
        'calibration_sha256': plan['calibration_sha256'],
        'closed_config_sha256': plan['closed_config_sha256'], 'controllers': controllers,
        'independent_confirmation': False, 'all_unfinished_frontiers_retained': True,
        'primary_SLO_seconds': [2., 8.], 'formal_is_separate_explicit_invocation': True}
    save(output/(args.stage+'_FREEZE.json'), freeze)
    save(output/(args.stage+'_ENVIRONMENT.json'), {'python': sys.version,
        'packages': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True),
        'uname': subprocess.check_output(['uname', '-a'], text=True),
        'hardware': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,uuid,driver_version,memory.total', '--format=csv,noheader'], text=True),
        'model_files_sha256': plan['model_files'], 'source_commit': plan['runtime_commit']})
    save(marker, {'pid': os.getpid(), 'time_unix': time.time(), 'source_commit': plan['runtime_commit'],
                  'stage': args.stage, 'plan_sha256': expected_plan_sha})
    completed = []
    oracle_completed = []
    active_substage = args.stage+'_oracle'

    def cell(item, substage):
        if not free_gpu():
            raise RuntimeError('GPU lease occupied at fresh-process cell boundary')
        if sha(plan_path) != expected_plan_sha:
            raise AssertionError('Frozen PLAN changed during execution')
        for row in source_manifest['files']:
            if sha(confined(source, row['path'])) != row['sha256']:
                raise AssertionError('Source changed during execution')
        for path, expected in files.values():
            if sha(path) != expected:
                raise AssertionError('Frozen config/profile/data identity changed during execution')
        name = cell_name(item)
        directory = output/substage
        directory.mkdir(exist_ok=True)
        (directory/'journals').mkdir(exist_ok=True)
        if (directory/name).exists():
            raise FileExistsError('Existing cell is not overwritten: '+name)
        command = [sys.executable, '-u', str(source/'scripts/run_tc_live_qwen.py'),
            '--model', str(model), '--manifest', str(files['manifest'][0]),
            '--output', str(directory/name), '--code-commit', plan['runtime_commit'],
            '--study-id', STUDY, '--sessions', str(item['sessions']), '--arrival', item['arrival'],
            '--seed', str(item['seed']), '--trusted-text-binding',
            '--display-protocol', 'canonical-snapshot-v1', '--publish-canonical-display',
            '--consumer-policy', 'two_lane', '--retain-verified-private-prefix',
            '--phase-n-instrumentation', '--capture-model-inputs',
            '--ces-method', item['method'], '--ces-traffic', item['traffic'],
            '--ces-calibration', str(files['calibration'][0]),
            '--ces-closed-config', str(files['closed_config'][0]),
            '--ces-proposer-policy', item.get('proposer_policy', 'ready'),
            '--online-donors', str(files['donors'][0]), '--online-fallback-layout', 'selective',
            '--durable-journal-path', str(directory/'journals'/(name+'.wal')),
            '--journal-sync-mode', 'group_ready', '--result-delivery', 'row']
        if item.get('oracle'):
            command.append('--online-oracle-diagnostic')
        save(directory/(name+'.COMMAND.json'), {'item': item, 'argv': command,
            'code_commit': plan['runtime_commit'], 'plan_sha256': expected_plan_sha,
            'fresh_process': True, 'all_completed_or_failed_raw_retained': True})
        run(['/usr/bin/time', '-v', '-o', str(directory/(name+'.CPU_IO.txt'))]+command,
            directory/(name+'.log'), source)
        result = read(directory/name/'result.json')
        if not result.get('fine_window_accounting_complete'):
            raise AssertionError('Incomplete actual frontier accounting retained, no gain claim')
        checks = owned_workers_exited(directory/name)
        save(directory/(name+'.RESOURCE_RELEASE.json'), {'owned_worker_checks': checks,
            'our_workers_exited': True, 'time_unix': time.time(),
            'current_GPU_processes': subprocess.check_output(['nvidia-smi',
                '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader'], text=True),
            'foreign_tasks_not_modified': True})
        return name

    def audit(substage, names):
        expected = output/(substage+'_EXPECTED.json')
        save(expected, {'cells': names})
        audited = output/(substage+'_audit')
        command = [sys.executable, str(project/'audit_closed.py'), '--root', str(output),
            '--stage', substage, '--source', str(source), '--output', str(audited),
            '--model', str(model), '--references', str(files['manifest'][0]),
            '--expected-cells', str(expected)]
        run(command, output/(substage+'_audit.log'), project)
        summary = read(audited/'SUMMARY.json')
        if summary['failures'] or summary['cells'] != len(names):
            raise AssertionError('Independent safety/denominator audit did not pass')
        return audited

    try:
        for item in spec.get('oracles', []):
            oracle_completed.append(cell(item, active_substage))
            save(output/(args.stage+'_PROGRESS.json'), {'stage': active_substage,
                'status': 'RUNNING', 'oracle_completed': oracle_completed,
                'performance_completed': completed, 'expected_performance': len(spec['cells'])}, replace=True)
        if oracle_completed:
            audit(active_substage, oracle_completed)
        active_substage = args.stage
        for item in spec['cells']:
            completed.append(cell(item, active_substage))
            save(output/(args.stage+'_PROGRESS.json'), {'stage': active_substage,
                'status': 'RUNNING', 'oracle_completed': oracle_completed,
                'performance_completed': completed, 'expected_performance': len(spec['cells'])}, replace=True)
            print('CELL_COMPLETE', len(completed), completed[-1], flush=True)
        audited = audit(active_substage, completed)
        repeats = int(spec.get('expected_repeats', 1 if args.stage == 'smoke' else 3))
        run([sys.executable, str(project/'summarize_closed.py'), '--audit', str(audited),
            '--output', str(output/(args.stage+'_summary')), '--samples', str(spec.get('bootstrap_samples', 2000)),
            '--expected-repeats', str(repeats)], output/(args.stage+'_summary.log'), project)
        save(output/(args.stage+'_SUMMARY.json'), {'status': 'COMPLETE_FROZEN_CLOSED_LOOP_STAGE_AND_AUDIT',
            'stage': args.stage, 'performance_cells': len(completed), 'oracle_cells': len(oracle_completed),
            'completed_performance': completed, 'completed_oracles': oracle_completed,
            'source_commit': plan['runtime_commit'], 'GPU_queue_closed': True,
            'current_GPU_free': free_gpu(), 'foreign_tasks_not_modified': True,
            'formal_not_automatically_started': True, 'independent_confirmation': False,
            'no_automatic_tuning': True})
    except BaseException as error:
        save(output/(args.stage+'_STOP.json'), {'error': repr(error), 'active_substage': active_substage,
            'performance_completed': completed, 'oracle_completed': oracle_completed,
            'all_raw_retained': True, 'no_silent_retry': True})
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
