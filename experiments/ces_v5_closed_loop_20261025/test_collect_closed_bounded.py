"""Collector CPU fixtures only: no8TB, SSH, CUDA or real process is touched."""
from copy import deepcopy
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import tarfile

import pytest

import collect_closed_bounded_v2 as c
import collect_closed_bounded as preserved_v1


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf8')
    return path


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'nested/../../escape'])
def test_relative_and_absolute_path_escapes_are_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        c.within(tmp_path, name)
    assert c.within(tmp_path, 'safe/f.json') == tmp_path/'safe/f.json'


def test_symlink_escape_is_not_resolved_outside_root(tmp_path):
    root, outside = tmp_path/'root', tmp_path/'outside'
    root.mkdir(); outside.mkdir()
    try:
        (root/'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Windows process has no symlink privilege; string containment controls still execute')
    with pytest.raises(ValueError):
        c.within(root, 'link/f.json')


def test_multipart_order_sha_and_existing_parts_refuse_overwrite(tmp_path):
    source = put(tmp_path/'source.dat', bytes(range(251))*3)
    destination = tmp_path/'parts'; destination.mkdir()
    parts = c.split_stream(source, destination, 'archive.gz', chunk_size=97)
    reconstructed = b''.join(p.read_bytes() for p in parts)
    assert reconstructed == source.read_bytes()
    assert hashlib.sha256(reconstructed).hexdigest() == c.sha(source)
    assert all(p.stat().st_size <= 97 for p in parts)
    prior = [p.read_bytes() for p in parts]
    with pytest.raises(FileExistsError):
        c.split_stream(source, destination, 'archive.gz', chunk_size=97)
    assert [p.read_bytes() for p in parts] == prior


def test_changing_collector_self_log_is_not_in_raw_inventory(tmp_path):
    project, output = tmp_path/'project', tmp_path/'results'
    project.mkdir(); output.mkdir()
    raw = put(output/'formal_CONTROLLER.log', b'completed real-run log fixture')
    self_log = put(output/'bounded_evidence_v1_COLLECTOR.log', b'growing')
    directory = output/'bounded_evidence_v1'; directory.mkdir()
    put(directory/'not-raw.json', {'derived': True})
    first = c.inventory(tmp_path, project, output, (self_log, directory))
    self_log.write_bytes(b'growing collector log now longer')
    second = c.inventory(tmp_path, project, output, (self_log, directory))
    assert first == second and raw in first and self_log not in first
    assert not any(directory in p.parents for p in first)


def test_declared_output_cpu_basetemp_excludes_fixture_links_not_unknown_links(tmp_path, monkeypatch):
    project, output = tmp_path/'project', tmp_path/'results'
    project.mkdir(); output.mkdir()
    fixture = output/'linux_cpu_tmp_v1'
    current = put(fixture/'test_ack_is_immutable_and_actucurrent', b'CPU pytest bookkeeping')
    put(fixture/'test_case/temporary.wal', b'CPU fake state, not GPU history')
    log = put(output/'LINUX_CPU_REGRESSION.log', b'original CPU command and output')
    junit = put(output/'LINUX_CPU_REGRESSION.xml', b'<testsuite tests="367"/>')
    negative = put(output/'smoke_STOP.json', {'original_failure': True})
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self == current or real_is_symlink(self))
    with pytest.raises(ValueError, match='Symlinks'):
        preserved_v1.inventory(tmp_path, project, output, ())
    roots, records = c.declared_output_cpu_basetemps(output)
    assert roots == [fixture.resolve()]
    assert records[0]['path_relative_to_study'] == 'linux_cpu_tmp_v1'
    indexed = c.inventory(tmp_path, project, output, tuple(roots))
    assert log in indexed and junit in indexed and negative in indexed
    assert not any(fixture == p or fixture in p.parents for p in indexed)
    unknown = put(output/'unknown_link', b'not a declared CPU fixture')
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self in (current, unknown) or real_is_symlink(self))
    with pytest.raises(ValueError, match='Symlinks'):
        c.inventory(tmp_path, project, output, tuple(roots))
    assert current.exists() and current.read_bytes() == b'CPU pytest bookkeeping'


def test_declared_cpu_basetemp_root_cannot_itself_be_a_symlink(tmp_path, monkeypatch):
    output = tmp_path/'results'; output.mkdir()
    fixture = output/'linux_cpu_tmp_v1'; fixture.mkdir()
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self == fixture or real_is_symlink(self))
    with pytest.raises(ValueError, match='must itself be a real directory'):
        c.declared_output_cpu_basetemps(output)


def fake_study(tmp_path, monkeypatch):
    """72 explicitly synthetic cell directories exercise packaging, not audits."""
    # Real collection runs on Linux. Windows CPU fixtures use its native
    # extended-length spelling so deeply nested evidence names are not turned
    # into misleading MAX_PATH setup failures.
    if c.os.name == 'nt' and not str(tmp_path).startswith('\\\\?\\'):
        tmp_path = Path('\\\\?\\'+str(tmp_path.resolve()))
    base = tmp_path/'f'; base.mkdir()
    project, output = base/c.PROJECT_RELATIVE, base/c.RAW_RELATIVE
    project.mkdir(parents=True); output.mkdir(parents=True)
    runtime = put(project/'runtime/toy.py', b'# CPU collector fixture, not inference\n')
    manifest = {'code_commit': 'e'*40, 'files': [{'path': 'toy.py',
        'bytes': runtime.stat().st_size, 'sha256': c.sha(runtime)}]}
    put(project/'SOURCE_MANIFEST.json', manifest)
    put(project/'audit_closed_v2.py', b'# fake CPU audit identity fixture\n')
    put(project/'audit_closed_helpers_v2.py', b'# fake CPU helper identity fixture\n')
    put(project/'CPU_PREFLIGHT.log', b'CPU fixture log retained\n')
    put(project/'remote_ops.py', b'# Credential route placeholder; not publication content\n')
    put(project/'operations/transport.json', {'fixture_transport': True})
    rows = []
    for i in range(16):
        wav = put(base/f'data/waves/{i}.wav', b'not-real-audio-CPU-fixture')
        rows.append({'path': str(wav), 'audio_sha256': 'b'*64,
            'source_id': str(i), 'reference': 'CPU reference '+str(i)})
    refs = put(base/'data/MANIFEST.json', {'sessions': rows})
    donors = put(base/'data/DONORS.json', {'CPU_fixture': True})
    model = put(base/'models/toy/weights.safetensors', b'not-real-model-CPU-fixture')
    def item(label):
        return {'pool': 'validation', 'label': label, 'arrival': 'sync',
            'traffic': 'mixed', 'repeat': 0, 'method': 'fine'}
    formal = [item(f'cpu-fixture-{i:02d}') for i in range(72)]
    smoke = [item(f'smoke-{i}') for i in range(4)]
    oracle = [item(f'oracle-{i}') for i in range(2)]
    plan = {'study_id': c.STUDY, 'formal_approved_after_smoke': True,
        'output_relative': c.RAW_RELATIVE, 'runtime_commit': 'e'*40,
        'runtime_manifest_sha256': c.sha(project/'SOURCE_MANIFEST.json'),
        'manifest_relative': 'data/MANIFEST.json', 'manifest_sha256': c.sha(refs),
        'donors_relative': 'data/DONORS.json', 'donors_sha256': c.sha(donors),
        'model_relative': 'models/toy', 'model_files': {'weights.safetensors': c.sha(model)},
        'stages': {'formal': {'cells': formal, 'oracles': []},
                   'smoke': {'cells': smoke, 'oracles': oracle}}}
    put(project/'PLAN.formal.json', plan)
    freeze = {'runtime_commit': plan['runtime_commit'], 'plan': deepcopy(plan),
        'plan_sha256': c.sha(project/'PLAN.formal.json'),
        'controllers': {n: c.sha(project/n) for n in ('audit_closed_v2.py', 'audit_closed_helpers_v2.py')}}
    put(output/'formal_FREEZE.json', freeze)
    put(output/'smoke_FREEZE.json', {'plan': plan})
    expected = [c.cell_name(x) for x in formal]
    put(output/'formal_EXPECTED.json', {'cells': expected})
    put(output/'formal_SUMMARY.json', {'status': c.COMPLETE, 'stage': 'formal',
        'performance_cells': 72, 'GPU_queue_closed': True,
        'completed_performance': expected, 'source_commit': plan['runtime_commit'],
        'completed_oracles': []})
    put(output/'formal_summary/PAIRED_SUMMARY.json', {'CPU_fixture_not_superiority': True})
    put(output/'smoke_STOP.json', {'error': 'Original false-positive CPU fixture retained'})
    put(output/'smoke_audit/SUMMARY.json', {'status': 'FAILED_AUDIT_CPU_FIXTURE'})
    put(output/'diagnosis_v1/NEGATIVE.csv', b'name,value\nnegative,-1\n')
    put(output/'smoke_REAUDITED_SUMMARY.json', {
        'performance_audit_summary_relative': 'smoke_audit_v2/SUMMARY.json',
        'oracle_audit_summary_relative': 'smoke_oracle_audit_v2/SUMMARY.json'})
    groups = {'formal': formal, 'smoke': smoke, 'smoke_oracle': oracle}
    for stage, items in groups.items():
        names = [c.cell_name(x) for x in items]
        audited = {'formal': 'formal_audit', 'smoke': 'smoke_audit_v2',
                   'smoke_oracle': 'smoke_oracle_audit_v2'}[stage]
        put(output/audited/'SUMMARY.json', {'status': c.PASS, 'cells': len(names),
            'expected_cells': len(names), 'checks': [{'cell': n} for n in names],
            'failures': [], 'actual_model_calls': len(names),
            'script_sha256': c.sha(project/'audit_closed_v2.py')})
        put(output/audited/'COMMON_FRONTIERS.csv', b'CPU_fixture,value\nfrontier,0\n')
        for index, name in enumerate(names):
            cell = output/stage/name
            for required in c.REQUIRED_CELL:
                put(cell/required, {})
            put(cell/'result.json', {'fine_window_accounting_complete': True,
                'decision': 'TOKEN_LIMIT_BOUNDARY' if index == 0 else 'PASS_PROTOCOL_COMPLETENESS'})
            wal = put(output/stage/'journals'/(name+'.wal'), b'CPU fake WAL, not certified inference')
            put(cell/'provenance.json', {'code_commit': plan['runtime_commit'],
                'durable_journal_path': str(wal)})
            put(cell/'OWNED_WORKER_HANDLES.json', [
                {'pid': 300, 'name': 'p', 'linux_start_ticks': '20'},
                {'pid': 301, 'name': 'a', 'linux_start_ticks': '21'}])
            result = {'token_ids': [7, 9], 'state_tokens': [7], 'text': 'CPU fixture',
                'terminated_by_eos': True, 'hit_token_limit': False,
                '_row_receipt': {'payload_sha256': 'a'*64}, 'model_input_audit': {'array': [0, 1]}}
            (cell/'worker_records.jsonl').write_text(json.dumps({'job': {
                'role': 'authority', 'job_id': 'a'}, 'result': result})+'\n', encoding='utf8')
            (cell/'events.jsonl').write_text(json.dumps({'kind': 'commit', 'job_id': 'a'})+'\n')
            (cell/'consumer.jsonl').write_text('{}\n')
            (cell/'worker_batch_accounting.jsonl').write_text('{}\n')
    # This test mocks only the previously tested same-raw smoke gate; it does
    # not claim that toy rows passed real certificate/Worker/Consumer audits.
    import smoke_reaudit_gate_v2
    monkeypatch.setattr(smoke_reaudit_gate_v2, 'verify_smoke_reaudit',
        lambda *_args: {'status': 'CPU_SYNTHETIC_SMOKE_GATE_FIXTURE'})
    return base, project, output, plan


def test_complete_gate_requires_exact72_before_packaging(tmp_path, monkeypatch):
    base, project, output, plan = fake_study(tmp_path, monkeypatch)
    assert c.completed_gate(base, project, output)[2]['formal_cells'] == 72
    summary = c.read(output/'formal_SUMMARY.json')
    summary['performance_cells'] = 71
    put(output/'formal_SUMMARY.json', summary)
    with pytest.raises(AssertionError):
        c.completed_gate(base, project, output)


@pytest.mark.parametrize('mutation', ['plan_hash', 'audit_hash', 'missing_cell', 'source_hash', 'formal_stop'])
def test_wrong_hash_or_incomplete_scope_is_not_collected(tmp_path, monkeypatch, mutation):
    base, project, output, plan = fake_study(tmp_path, monkeypatch)
    if mutation == 'plan_hash':
        value = c.read(output/'formal_FREEZE.json'); value['plan_sha256'] = '0'*64
        put(output/'formal_FREEZE.json', value)
    if mutation == 'audit_hash':
        value = c.read(output/'formal_audit/SUMMARY.json'); value['script_sha256'] = '0'*64
        put(output/'formal_audit/SUMMARY.json', value)
    if mutation == 'missing_cell':
        (output/'formal'/c.cell_name(plan['stages']['formal']['cells'][0])/'result.json').unlink()
    if mutation == 'source_hash':
        (project/'runtime/toy.py').write_bytes(b'changed source')
    if mutation == 'formal_stop':
        put(output/'formal_STOP.json', {'negative': 'must not be hidden'})
    with pytest.raises(AssertionError):
        c.completed_gate(base, project, output)


def test_reference_manifest_sha_and_byte_exact_copy(tmp_path, monkeypatch):
    base, project, output, plan = fake_study(tmp_path, monkeypatch)
    refs = base/plan['manifest_relative']
    c.external_assets(base, plan)
    directory = output/'manual-bounded'; directory.mkdir()
    collector = c.Collector(base, project, output, directory, output/'large-unused',
                            {refs: plan['manifest_sha256']})
    collector.add(refs, 'source_reference_manifest.json')
    assert (directory/'source_reference_manifest.json').read_bytes() == refs.read_bytes()
    assert collector.logical[0]['payload_sha256'] == plan['manifest_sha256']
    refs.write_text('{"corrupt": true}')
    with pytest.raises(AssertionError):
        c.external_assets(base, plan)


def test_pid_reuse_foreign_gpu_does_not_require_global_idle_or_kill(tmp_path, monkeypatch):
    output, project = tmp_path/'raw', tmp_path/'project'
    output.mkdir(); project.mkdir()
    proc = tmp_path/'proc'; proc.mkdir()
    actual_path = c.Path
    monkeypatch.setattr(c, 'Path', lambda value, *a: proc if str(value) == '/proc' else actual_path(value, *a))
    for stage, pid in [('smoke', 100), ('formal', 101)]:
        put(output/(stage+'_LAUNCH_PID.json'), {'pid': pid, 'argv': ['python', 'old-'+stage]})
        put(output/(stage+'_GPU_STARTED.json'), {'pid': pid})
    put(output/'formal/cell/OWNED_WORKER_HANDLES.json', [
        {'pid': 300, 'name': 'p', 'linux_start_ticks': '20'},
        {'pid': 301, 'name': 'a', 'linux_start_ticks': '21'}])
    put(output/'linux_cpu_tmp_v1/test_fixture/OWNED_WORKER_HANDLES.json',
        {'deliberately': 'CPU mock, not a GPU Worker handle list'})
    cpu_roots, _ = c.declared_output_cpu_basetemps(output)
    def observe(pid):
        return {'state': 'R', 'start_ticks': '999', 'argv': [b'foreign-task']}
    monkeypatch.setattr(c, 'proc_info', observe)
    queries = []
    monkeypatch.setattr(c.subprocess, 'check_output', lambda command, **_kw:
        queries.append(command) or '999, foreign_training, 12000 MiB\n')
    monkeypatch.setattr(c.os, 'kill', lambda *_: pytest.fail('Collector must never kill a process'))
    result = c.resource_gate(output, project, {'formal': ['cell']}, excluded=tuple(cpu_roots))
    assert result['all_this_task_workers_released']
    assert result['foreign_processes_not_touched']
    assert all(not x['same_original_process_present'] for x in result['workers'])
    assert 'foreign_training' in result['current_GPU_processes']
    assert len(queries) == 1 and queries[0][0] == 'nvidia-smi'
    monkeypatch.setattr(c, 'proc_info', lambda pid: {'state': 'R',
        'start_ticks': '20' if pid == 300 else '999', 'argv': [b'foreign-task']})
    with pytest.raises(AssertionError, match='Owned Worker'):
        c.resource_gate(output, project, {'formal': ['cell']}, excluded=tuple(cpu_roots))
    monkeypatch.setattr(c, 'proc_info', lambda pid: {'state': 'R',
        'start_ticks': '999', 'argv': [b'python', b'old-formal']} if pid == 101 else None)
    with pytest.raises(AssertionError, match='controller still running'):
        c.resource_gate(output, project, {'formal': ['cell']}, excluded=tuple(cpu_roots))


def test_mocked_full_collection_preserves_negatives_refs_and_multipart_index(tmp_path, monkeypatch):
    base, project, output, plan = fake_study(tmp_path, monkeypatch)
    put(output/'diagnosis_v1/LARGE_NEGATIVE.dat', random.Random(13).randbytes(3_000_000))
    cpu_fixture = output/'linux_cpu_tmp_v1'
    current = put(cpu_fixture/'test_ack_is_immutable_and_actucurrent', b'CPU fixture link marker')
    put(cpu_fixture/'test_partial/fixture.wal', b'CPU fake WAL must not be GPU evidence')
    put(output/'LINUX_CPU_COMMAND.json', {'argv': ['CPU pytest fixture command'], 'tests': 367})
    put(output/'LINUX_CPU_JUNIT.xml', b'<testsuite tests="367"/>')
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self == current or real_is_symlink(self))
    monkeypatch.setattr(c, 'resource_gate', lambda *_a, **_kw: {
        'all_this_task_workers_released': True, 'CPU_fixture_not_process_check': True})
    monkeypatch.setattr(c, 'MAX_PUBLISH_BYTES', 2_000_000)
    monkeypatch.setattr(c, 'PART_BYTES', 128_000)
    record = c.collect(base, 'bounded_cpu_fixture')
    directory = output/'bounded_cpu_fixture'
    assert record['formal_cells'] == 72 and record['smoke_cells'] == 4 and record['oracle_cells'] == 2
    assert len(record['publish_files']) > 1
    archive = b''.join(Path(p['path']).read_bytes() for p in record['publish_files'])
    assert hashlib.sha256(archive).hexdigest() == record['full_archive_sha256']
    assert all(p['bytes'] < 2_000_000 for p in record['publish_files'])
    assert (directory/'smoke_STOP.json').read_bytes() == (output/'smoke_STOP.json').read_bytes()
    assert (directory/'smoke_audit/SUMMARY.json').read_bytes() == (output/'smoke_audit/SUMMARY.json').read_bytes()
    assert (directory/'diagnosis_v1/NEGATIVE.csv').read_bytes() == (output/'diagnosis_v1/NEGATIVE.csv').read_bytes()
    assert (directory/'LINUX_CPU_COMMAND.json').read_bytes() == (output/'LINUX_CPU_COMMAND.json').read_bytes()
    assert (directory/'LINUX_CPU_JUNIT.xml').read_bytes() == (output/'LINUX_CPU_JUNIT.xml').read_bytes()
    assert not (directory/'linux_cpu_tmp_v1').exists()
    exclusions = c.read(directory/'CPU_FIXTURE_EXCLUSIONS.json')['directories']
    assert len(exclusions) == 1 and exclusions[0]['path_relative_to_study'] == 'linux_cpu_tmp_v1'
    assert cpu_fixture.exists() and current.exists(), 'Temporary data is not deleted'
    assert (directory/'source_reference_manifest.json').read_bytes() == (base/plan['manifest_relative']).read_bytes()
    assert c.read(directory/'SOURCE_REFERENCE_IDENTITY.json')['unique_source_ids'] == 16
    assert not (directory/'project_artifacts/remote_ops.py').exists()
    raw = c.read(directory/'RAW_INDEX.json')
    assert len([r for r in raw['files'] if r['path'].endswith('/worker_records.jsonl')]) == 78
    assert not any('bounded_cpu_fixture' in r['path'] for r in raw['files'])
    assert not any('/linux_cpu_tmp_v1/' in r['path'] for r in raw['files'])
    assert raw['declared_CPU_fixture_exclusions'] == exclusions
    assert not any('fixture.wal' in r['logical_path'] for r in c.read(directory/'LOGICAL_PAYLOADS.json')['files'])
    for row in raw['files']:
        path = base/row['path']
        assert path.stat().st_size == row['bytes'] and c.sha(path) == row['sha256']
    manifest = c.read(directory/'MANIFEST.json')
    assert c.sha(directory/'MANIFEST.json') == record['manifest_sha256']
    assert len(manifest['files'])+1 == record['packaged_files']
    for row in manifest['files']:
        path = directory/row['path']
        assert path.stat().st_size == row['bytes'] and c.sha(path) == row['sha256']
    logical = c.read(directory/'LOGICAL_PAYLOADS.json')['files']
    large = next(r for r in logical if r['logical_path'] == 'diagnosis_v1/LARGE_NEGATIVE.dat')
    assert len(large['parts']) > 1
    joined = b''.join((directory/p).read_bytes() for p in large['parts'])
    assert hashlib.sha256(joined).hexdigest() == large['payload_sha256']
    assert (base/large['large_derived_retained_8TB']).exists()
    assert (output/'diagnosis_v1/LARGE_NEGATIVE.dat').exists(), 'Never move the raw negative'
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as packed:
        assert all(m.size < 2_000_000 for m in packed.getmembers())
        assert not any(Path(m.name).suffix in ('.wav', '.safetensors') for m in packed.getmembers())
        witness = packed.extractfile('canonical_witnesses/formal/'+c.cell_name(plan['stages']['formal']['cells'][0])+'.jsonl.gz')
        row = json.loads(gzip.decompress(witness.read()).decode())
        assert row['selected_result']['token_ids'] == [7, 9]
        assert row['selected_result']['state_tokens'] == [7]
        assert 'model_input_audit' not in row['selected_result']
        assert row['raw_worker_records_sha256']
    with pytest.raises(AssertionError, match='No overwrite'):
        c.collect(base, 'bounded_cpu_fixture')
