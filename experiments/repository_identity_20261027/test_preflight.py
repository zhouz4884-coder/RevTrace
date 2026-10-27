"""CPU negative controls for the new identity gate, not serving evidence."""
import json

import pytest
import preflight

COMMIT = 'a' * 40


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    code = source / 'code.py'
    code.write_bytes(b'print(1)\n')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(dict(code_commit=COMMIT, files=[dict(
        path='code.py', bytes=code.stat().st_size, sha256=preflight.sha256(code))])))
    answers = {('cat-file', '-t', COMMIT): 'commit',
               ('rev-parse', '--show-toplevel'): source.as_posix(),
               ('rev-parse', 'HEAD'): COMMIT,
               ('config', '--get', 'core.autocrlf'): 'false',
               ('status', '--porcelain', '--untracked-files=all'): '',
               ('ls-files',): 'code.py'}
    monkeypatch.setattr(preflight, 'git', lambda cwd, *args: answers[args])
    return source, manifest, answers


def test_complete_identity_passes(frozen):
    source, manifest, _ = frozen
    assert preflight.check(source, manifest)['files_verified'] == 1
    assert not preflight.check(source, manifest)['run_record_prelaunch_checked']


def test_wrong_head_fails(frozen):
    source, manifest, answers = frozen
    answers[('rev-parse', 'HEAD')] = 'b' * 40
    with pytest.raises(ValueError, match='HEAD'):
        preflight.check(source, manifest)


def test_same_size_byte_edit_fails_even_if_git_claimed_clean(frozen):
    source, manifest, _ = frozen
    (source / 'code.py').write_bytes(b'print(2)\n')
    with pytest.raises(ValueError, match='code.py'):
        preflight.check(source, manifest)


def test_dirty_worktree_fails(frozen):
    source, manifest, answers = frozen
    answers[('status', '--porcelain', '--untracked-files=all')] = ' M code.py'
    with pytest.raises(ValueError, match='Dirty'):
        preflight.check(source, manifest)


def test_missing_run_fields_fail(frozen, tmp_path):
    source, manifest, _ = frozen
    record = tmp_path / 'record.json'
    record.write_text('{}')
    with pytest.raises(ValueError, match='experiment_id'):
        preflight.check(source, manifest, record)


def test_metadata_hash_and_disk_checked(frozen, tmp_path):
    source, manifest, _ = frozen
    config = tmp_path / 'config.json'
    config.write_text('{}')
    env = tmp_path / 'env.json'
    env.write_text('{"kind":"CPU fixture"}')
    record = tmp_path / 'record.json'
    data = dict(experiment_id='CPU-FIXTURE-NOT-A-GPU-RUN', code_commit=COMMIT,
                frozen_config=str(config), frozen_config_sha256=preflight.sha256(config),
                environment_record=str(env), environment_record_sha256=preflight.sha256(env),
                raw_result_location='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/fixture',
                aggregate_summary_location='planned/summary.json', gate_decision_location='planned/gate.json')
    record.write_text(json.dumps(data))
    assert preflight.check(source, manifest, record)['run_record_prelaunch_checked']
    data['frozen_config_sha256'] = '0' * 64
    record.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='hash mismatch'):
        preflight.check(source, manifest, record)
    data['frozen_config_sha256'] = preflight.sha256(config)
    data['raw_result_location'] = '/tmp/not-the-experiment-disk'
    record.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='designated experiment disk'):
        preflight.check(source, manifest, record)
