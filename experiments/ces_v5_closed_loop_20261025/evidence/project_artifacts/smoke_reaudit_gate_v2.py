"""Read-only gate for an audit-only, same-raw smoke correction.

No original STOP, raw result or frozen source is rewritten. This gate verifies
the exact six recorded cells and v2 audit outputs before a separate formal
stage may start. It never invokes a model or SSH.
"""
from pathlib import Path
import hashlib
import json


STATUS = 'PASS_SMOKE_SAME_RAW_V2_REAUDIT'
REQUIRED_RAW = ('config.json', 'provenance.json', 'events.jsonl', 'consumer.jsonl',
    'worker_records.jsonl', 'worker_batch_accounting.jsonl', 'initial_states.json',
    'sessions.json', 'result.json', 'OWNED_WORKER_HANDLES.json', 'power_samples.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def within(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Reaudit paths must stay within this result study')
    path = (root/relative).resolve()
    path.relative_to(root.resolve())
    return path


def expected_smoke(freeze):
    spec = freeze['plan']['stages']['smoke']
    def name(item):
        return '-'.join((item.get('pool', 'validation'), item['arrival'], item['traffic'],
                         item['label'], 'r'+str(item['repeat'])))
    performance = [name(x) for x in spec['cells']]
    oracle = [name(x) for x in spec['oracles']]
    assert len(performance) == 4 and len(oracle) == 2
    return performance, oracle


def verify_smoke_reaudit(output, plan, project):
    output, project = Path(output).resolve(), Path(project).resolve()
    summary_path = output/'smoke_REAUDITED_SUMMARY.json'
    summary = read(summary_path)
    assert summary['status'] == STATUS
    assert summary['no_GPU_rerun'] is True and summary['GPU_model_calls_performed_by_reaudit'] == 0
    freeze_path = output/'smoke_FREEZE.json'
    assert summary['original_smoke_freeze_sha256'] == sha(freeze_path)
    freeze = read(freeze_path)
    for key in ('runtime_commit', 'runtime_manifest_sha256', 'calibration_sha256', 'closed_config_sha256'):
        assert summary[key] == freeze[key] == plan[key], 'Runtime/config changed after actual smoke: '+key
    assert summary['source_commit'] == plan['runtime_commit']
    # Source data/model identity is the same; the formal cell order and its
    # explicit approval can change only in the later newly frozen PLAN.
    for key in ('manifest_sha256', 'donors_sha256', 'model_files'):
        assert freeze['plan'][key] == plan[key], 'Execution input changed after smoke: '+key
    declared_formal = freeze['plan']['stages']['formal']['cells']
    assert len(declared_formal) == 72
    assert sum(not x.get('side_arm', False) for x in declared_formal) == 48
    assert sum(x.get('side_arm', False) for x in declared_formal) == 24
    assert plan['stages']['formal']['cells'] == declared_formal, 'Predeclared formal cells/order changed after smoke'
    performance, oracle = expected_smoke(freeze)
    assert summary['completed_performance_cells'] == performance
    assert summary['completed_oracle_cells'] == oracle
    assert summary['v2_audit_sha256'] == sha(project/'audit_closed_v2.py')
    assert summary['v2_helper_sha256'] == sha(project/'audit_closed_helpers_v2.py')
    audits = [('performance', performance), ('oracle', oracle)]
    for label, names in audits:
        path = within(output, summary[label+'_audit_summary_relative'])
        assert sha(path) == summary[label+'_audit_summary_sha256']
        audit = read(path)
        assert audit['status'] == 'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
        assert audit['cells'] == audit['expected_cells'] == len(names) and not audit['failures']
        assert {x['cell'] for x in audit['checks']} == set(names)
        assert audit['script_sha256'] == summary['v2_audit_sha256']
        assert audit['actual_model_calls'] > 0, 'Real recorded calls cannot become a copied zero'
    index_path = within(output, summary['raw_input_index_relative'])
    assert sha(index_path) == summary['raw_input_index_sha256']
    index = read(index_path)
    entries = {item['path']: item for item in index['files']}
    assert len(entries) == len(index['files']), 'Duplicate raw file identity'
    required = set()
    for stage, names in (('smoke', performance), ('smoke_oracle', oracle)):
        for cell in names:
            for name in REQUIRED_RAW:
                required.add(f'{stage}/{cell}/{name}')
            provenance = read(output/stage/cell/'provenance.json')
            journal = Path(provenance['durable_journal_path']).resolve()
            required.add(journal.relative_to(output).as_posix())
            assert provenance['code_commit'] == plan['runtime_commit']
            cfg = read(output/stage/cell/'config.json')
            assert cfg['ces_study']['calibration_sha256'] == plan['calibration_sha256']
            assert cfg['ces_study']['closed_config_sha256'] == plan['closed_config_sha256']
            assert cfg['manifest_sha256'] == plan['manifest_sha256']
    assert required <= set(entries), 'Reaudit raw index omitted an original audit input'
    for relative, entry in entries.items():
        path = within(output, relative)
        assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Original smoke data changed: '+relative
    old_stop = output/'smoke_STOP.json'
    assert old_stop.is_file() or (output/'smoke_SUMMARY.json').is_file(), 'Original smoke terminal record was removed'
    expected_stop_hash = sha(old_stop) if old_stop.is_file() else None
    assert summary['original_v1_stop_sha256'] == expected_stop_hash, 'Original v1 STOP was removed or replaced'
    return {'status': STATUS, 'summary_sha256': sha(summary_path),
        'raw_files_verified': len(entries), 'performance_cells': len(performance),
        'oracle_cells': len(oracle), 'original_v1_stop_retained': old_stop.is_file()}
