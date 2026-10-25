"""CPU audit correction controls; no GPU run or frozen source is changed."""
from copy import deepcopy
from pathlib import Path
import json
import sys
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE/'runtime/src'), str(HERE/'runtime/tests')]

import audit_closed_helpers as original
import audit_closed_helpers_v2 as corrected
from test_controller_audit import cpu_trace
from revtrace.ces_runtime import CESScheduler
from revtrace.dgft import digest_tokens
from revtrace.live_qwen import fingerprint
from finalize_smoke_reaudit_v2 import finalize
from smoke_reaudit_gate_v2 import verify_smoke_reaudit, sha, REQUIRED_RAW


def owner_with_released_backlog(mode='causal'):
    """Exercise the actual owner with all three audio windows released.

    The existing fake monotonic clock is advanced before dispatch. Neural
    outputs and service costs remain explicit CPU fixtures, not GPU evidence.
    No implementation, Parent or execution input is patched.
    """
    normal_run = CESScheduler.run

    def start_after_audio_release(self):
        self.clock.sleep(6.1)
        return normal_run(self)

    with patch.object(CESScheduler, 'run', start_after_audio_release):
        return cpu_trace(mode)


def run_audit(module, trace):
    cfg, events, records, sessions, initial, render, _ = trace
    return module.audit_closed_events(cfg, events, records, sessions, initial,
        trusted_render=render, digest_tokens=digest_tokens, fingerprint=fingerprint)


def released_contexts(trace):
    return [record for e in trace[1] if e['kind'] == 'closed-loop-observation'
            for record in e['contexts'].values() if record['target_context']['successors']]


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_frozen_owner_first_successor_true_was_original_audit_false_positive(mode):
    trace = owner_with_released_backlog(mode)
    contexts = released_contexts(trace)
    assert contexts and any(len(c['target_context']['successors']) == 2 for c in contexts)
    for record in contexts:
        c = record['target_context']
        first, *later = c['successors']
        assert first['inherit_current_transition_model'] is True
        assert first['direct_private_probability'] == c['direct_private_probability']
        assert first['fallback_private_probability'] == c['fallback_private_probability']
        assert first['unknown_private_probability'] is None
        assert all(u['inherit_current_transition_model'] is False and
            u['direct_private_probability'] is None and u['fallback_private_probability'] is None for u in later)
    with pytest.raises(AssertionError):
        run_audit(original, trace)
    result = run_audit(corrected, trace)
    assert result['actual_commit_retirements'] == 6
    assert result['closed_observations'] == result['physical_service_dispatches']
    assert result['future_execution_permissions_created'] == 0
    assert trace[-1]['fine_window_accounting_complete']


@pytest.mark.parametrize('mutation', ['first_flag', 'first_direct', 'first_fallback',
                                     'later_flag', 'later_direct', 'legacy_single_rate'])
def test_correction_does_not_accept_wrong_transition_models(mutation):
    trace = deepcopy(owner_with_released_backlog())
    record = next(c for c in released_contexts(trace) if len(c['target_context']['successors']) == 2)
    first, later = record['target_context']['successors']
    if mutation == 'first_flag': first['inherit_current_transition_model'] = False
    if mutation == 'first_direct': first['direct_private_probability'] = .8
    if mutation == 'first_fallback': first['fallback_private_probability'] = .1
    if mutation == 'later_flag': later['inherit_current_transition_model'] = True
    if mutation == 'later_direct': later['direct_private_probability'] = .8
    if mutation == 'legacy_single_rate': first['unknown_private_probability'] = .8
    # The logged duplicate is changed too, so this is a semantic check rather
    # than merely detecting two differing serializations of the same object.
    record['released_successors'] = deepcopy(record['target_context']['successors'])
    with pytest.raises(AssertionError):
        run_audit(corrected, trace)


def test_original_frozen_audit_files_are_unchanged():
    import hashlib
    assert hashlib.sha256((HERE/'audit_closed_helpers.py').read_bytes()).hexdigest() == \
        'faeab42a3e81deaf1a67b4acce30aa1fe87fa466e58b78cfd509c8d6a3a94021'
    assert hashlib.sha256((HERE/'audit_closed.py').read_bytes()).hexdigest() == \
        '1e764d5bbc3e802018f7f584ac0972697221793231bec00b3dcf9326e8ea0a23'


def gate_fixture(tmp_path):
    """Metadata/file-tree fixture only, not a fabricated GPU experiment."""
    output = tmp_path/'CPU_GATE_FIXTURE'
    project = tmp_path/'CPU_PROJECT_FIXTURE'
    output.mkdir(); project.mkdir()
    for name in ('audit_closed_v2.py', 'audit_closed_helpers_v2.py'):
        (project/name).write_text('CPU metadata gate fixture only', encoding='utf8')
    plan = json.loads((HERE/'PLAN.example.json').read_text(encoding='utf8'))
    plan.update(runtime_commit='f'*40, runtime_manifest_sha256='a'*64,
        calibration_sha256='b'*64, closed_config_sha256='c'*64,
        manifest_sha256='d'*64, donors_sha256='e'*64,
        model_files={'CPU_ONLY_FIXTURE': 'a'*64})
    freeze = {'plan': deepcopy(plan), **{k: plan[k] for k in ('runtime_commit',
        'runtime_manifest_sha256', 'calibration_sha256', 'closed_config_sha256')}}
    (output/'smoke_FREEZE.json').write_text(json.dumps(freeze), encoding='utf8')
    (output/'smoke_STOP.json').write_text(json.dumps({'scope': 'CPU original-audit-failure fixture'}), encoding='utf8')
    for key, stage, audit_directory in (('cells', 'smoke', 'smoke_audit_v2'),
                                      ('oracles', 'smoke_oracle', 'smoke_oracle_audit_v2')):
        names = []
        for item in plan['stages']['smoke'][key]:
            name = '-'.join((item['pool'], item['arrival'], item['traffic'], item['label'], 'r'+str(item['repeat'])))
            names.append(name)
            directory = output/stage/name
            directory.mkdir(parents=True)
            for filename in REQUIRED_RAW:
                (directory/filename).write_text('{}', encoding='utf8')
            wal = output/stage/'journals'/(name+'.wal')
            wal.parent.mkdir(exist_ok=True)
            wal.write_bytes(b'CPU WAL metadata fixture, not a real journal')
            (directory/'provenance.json').write_text(json.dumps({'durable_journal_path': str(wal.resolve()),
                'code_commit': plan['runtime_commit']}), encoding='utf8')
            (directory/'config.json').write_text(json.dumps({'ces_study': {
                'calibration_sha256': plan['calibration_sha256'],
                'closed_config_sha256': plan['closed_config_sha256']},
                'manifest_sha256': plan['manifest_sha256']}), encoding='utf8')
        audited = output/audit_directory
        audited.mkdir()
        (audited/'SUMMARY.json').write_text(json.dumps({
            'status': 'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT',
            'cells': len(names), 'expected_cells': len(names), 'failures': [],
            'checks': [{'cell': name} for name in names],
            'script_sha256': sha(project/'audit_closed_v2.py'),
            'actual_model_calls': 1, 'scope': 'CPU gate fixture, not a model-call measurement'}), encoding='utf8')
    return output, project, plan


def test_same_raw_smoke_finalizer_binds_six_cells_and_retains_old_stop(tmp_path):
    output, project, plan = gate_fixture(tmp_path)
    original_stop = (output/'smoke_STOP.json').read_bytes()
    result = finalize(output, project)
    assert result['performance_cells'] == 4 and result['oracle_cells'] == 2
    assert result['raw_files_verified'] == 72
    assert (output/'smoke_STOP.json').read_bytes() == original_stop
    assert verify_smoke_reaudit(output, plan, project)['original_v1_stop_retained']
    with pytest.raises(FileExistsError):
        finalize(output, project)


@pytest.mark.parametrize('mutation', ['source', 'calibration', 'raw', 'stop', 'order', 'dropcell', 'auditor'])
def test_formal_gate_rejects_changed_history_or_posthoc_matrix(tmp_path, mutation):
    output, project, plan = gate_fixture(tmp_path)
    finalize(output, project)
    if mutation == 'source': plan['runtime_commit'] = '0'*40
    if mutation == 'calibration': plan['calibration_sha256'] = '0'*64
    if mutation == 'raw':
        next((output/'smoke').glob('*/worker_records.jsonl')).write_text('changed CPU fixture', encoding='utf8')
    if mutation == 'stop': (output/'smoke_STOP.json').unlink()
    if mutation == 'order': plan['stages']['formal']['cells'].reverse()
    if mutation == 'dropcell': plan['stages']['formal']['cells'].pop()
    if mutation == 'auditor': (project/'audit_closed_v2.py').write_text('different', encoding='utf8')
    with pytest.raises(AssertionError):
        verify_smoke_reaudit(output, plan, project)
