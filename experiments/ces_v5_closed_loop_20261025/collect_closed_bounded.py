"""Post-formal, model-free bounded evidence collector; never launches GPU/SSH.

Usage: python collect_closed_bounded.py --base /designated/8TB
       [--output-dir bounded_evidence_v1] [--check-only]

Raw worker inputs, audio and weights remain on 8TB. Archive parts and every
payload published by this collector are strictly below 40,000,000 bytes.
Run only after the formal controller and all owned Workers have exited. A
foreign new GPU owner is reported, never stopped or mistaken for our Worker.
Do not redirect stdout to a changing raw log other than the documented
<output-dir>_COLLECTOR.log, which is an explicit self-log exclusion.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time


STUDY = 'REVTRACE-CES-V5-CLOSED-LOOP-20261025'
RAW_RELATIVE = 'results/revtrace/ces_v5_closed_loop_20261025'
PROJECT_RELATIVE = 'projects/revtrace_ces_v5_closed_loop_20261025'
PASS = 'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
COMPLETE = 'COMPLETE_FROZEN_CLOSED_LOOP_STAGE_AND_AUDIT'
MAX_PUBLISH_BYTES = 40_000_000
PART_BYTES = 32_000_000
NO_COPY = {'.wav', '.flac', '.mp3', '.pcm', '.safetensors', '.bin', '.pt',
           '.pth', '.ckpt', '.npy', '.npz'}
REQUIRED_CELL = ('config.json', 'provenance.json', 'initial_states.json',
    'sessions.json', 'workers.json', 'result.json', 'OWNED_WORKER_HANDLES.json',
    'events.jsonl', 'consumer.jsonl', 'worker_batch_accounting.jsonl',
    'worker_records.jsonl', 'power_samples.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(4*1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def within(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Confined relative path required: '+str(relative))
    target = (root/relative).resolve()
    target.relative_to(root)
    return target


def cell_name(item):
    return '-'.join((item.get('pool', 'validation'), item['arrival'],
        item['traffic'], item['label'], 'r'+str(item['repeat'])))


def names_of(path):
    value = read(path)
    return value if isinstance(value, list) else value['cells']


def audit_gate(path, expected, auditor_sha):
    audit = read(path)
    assert audit['status'] == PASS and not audit['failures'], str(path)
    assert audit['cells'] == audit['expected_cells'] == len(expected)
    assert len(audit['checks']) == len(expected)
    assert {x['cell'] for x in audit['checks']} == set(expected)
    assert audit['script_sha256'] == auditor_sha
    assert audit['actual_model_calls'] > 0
    return audit


def completed_gate(base, project, output):
    """No collection from PROGRESS/RUNNING/partial PASS or filtered cells."""
    assert not (output/'formal_STOP.json').exists(), 'Formal STOP must not be hidden'
    summary = read(output/'formal_SUMMARY.json')
    freeze = read(output/'formal_FREEZE.json')
    plan_path = project/'PLAN.formal.json'
    plan = read(plan_path)
    expected = [cell_name(x) for x in plan['stages']['formal']['cells']]
    assert len(expected) == len(set(expected)) == 72
    assert plan['study_id'] == STUDY and plan['formal_approved_after_smoke'] is True
    assert plan['output_relative'] == RAW_RELATIVE
    assert summary['status'] == COMPLETE and summary['stage'] == 'formal'
    assert summary['performance_cells'] == 72 and summary['GPU_queue_closed'] is True
    assert summary['completed_performance'] == expected
    assert summary['source_commit'] == plan['runtime_commit'] == freeze['runtime_commit']
    assert freeze['plan_sha256'] == sha(plan_path) and freeze['plan'] == plan
    assert names_of(output/'formal_EXPECTED.json') == expected
    actual = {p.name for p in (output/'formal').iterdir()
              if p.is_dir() and (p/'result.json').is_file()}
    assert actual == set(expected), 'Missing/unplanned completed formal cell'
    manifest_path = project/'SOURCE_MANIFEST.json'
    assert sha(manifest_path) == plan['runtime_manifest_sha256']
    manifest = read(manifest_path)
    assert manifest['code_commit'] == plan['runtime_commit']
    for item in manifest['files']:
        path = within(project/'runtime', item['path'])
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    auditor_sha = sha(project/'audit_closed_v2.py')
    for name, expected_digest in freeze['controllers'].items():
        assert sha(within(project, name)) == expected_digest, 'Frozen controller/auditor changed'
    assert freeze['controllers']['audit_closed_v2.py'] == auditor_sha
    assert freeze['controllers']['audit_closed_helpers_v2.py'] == sha(project/'audit_closed_helpers_v2.py')
    formal_audit = audit_gate(output/'formal_audit/SUMMARY.json', expected, auditor_sha)
    assert (output/'formal_summary/PAIRED_SUMMARY.json').is_file()
    # Revalidate the original smoke raw-index/hash chain. This preserves the
    # v1 failure rather than silently treating the same-raw v2 audit as rerun.
    from smoke_reaudit_gate_v2 import verify_smoke_reaudit, expected_smoke
    smoke_gate = verify_smoke_reaudit(output, plan, project)
    smoke_names, oracle_names = expected_smoke(read(output/'smoke_FREEZE.json'))
    assert len(smoke_names) == 4 and len(oracle_names) == 2
    smoke_summary = read(output/'smoke_REAUDITED_SUMMARY.json')
    smoke_audit = audit_gate(within(output, smoke_summary['performance_audit_summary_relative']),
        smoke_names, auditor_sha)
    oracle_audit = audit_gate(within(output, smoke_summary['oracle_audit_summary_relative']),
        oracle_names, auditor_sha)
    assert (output/'smoke_STOP.json').is_file(), 'The original v1 failure must remain'
    groups = {'formal': expected, 'smoke': smoke_names, 'smoke_oracle': oracle_names}
    # Any separately declared formal Oracle must be complete, audited and kept.
    formal_oracles = [cell_name(x) for x in plan['stages']['formal'].get('oracles', [])]
    assert summary['completed_oracles'] == formal_oracles
    if formal_oracles:
        groups['formal_oracle'] = formal_oracles
        audit_gate(output/'formal_oracle_audit/SUMMARY.json', formal_oracles, auditor_sha)
    for stage, names in groups.items():
        for name in names:
            directory = output/stage/name
            for required in REQUIRED_CELL:
                assert (directory/required).is_file(), str(directory/required)
            result = read(directory/'result.json')
            assert result['fine_window_accounting_complete'] is True
            assert result['decision'] in ('PASS_PROTOCOL_COMPLETENESS', 'TOKEN_LIMIT_BOUNDARY')
            provenance = read(directory/'provenance.json')
            assert provenance['code_commit'] == plan['runtime_commit']
            journal = Path(provenance['durable_journal_path']).resolve()
            journal.relative_to(output)
            assert journal.is_file(), 'Every real history needs its full indexed WAL'
    return plan, groups, {'status': 'PASS_72_FORMAL_AND_SAME_RAW_SMOKE_V2_COLLECTION_GATE',
        'runtime_commit': plan['runtime_commit'], 'formal_plan_sha256': sha(plan_path),
        'formal_audit_sha256': sha(output/'formal_audit/SUMMARY.json'),
        'formal_cells': 72, 'formal_actual_model_calls': formal_audit['actual_model_calls'],
        'smoke_cells': 4, 'smoke_actual_model_calls': smoke_audit['actual_model_calls'],
        'oracle_cells': 2, 'oracle_actual_model_calls': oracle_audit['actual_model_calls'],
        'old_smoke_v1_failure_retained': True, 'smoke_v2_same_raw_gate': smoke_gate,
        'no_new_model_or_GPU_work': True, 'negative_complete_runs_retained': True}


def proc_info(pid):
    root = Path('/proc')/str(pid)
    try:
        tail = (root/'stat').read_text().rsplit(')', 1)[1].split()
        return {'start_ticks': tail[19], 'state': tail[0],
                'argv': (root/'cmdline').read_bytes().split(b'\0')[:-1]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def resource_gate(output, project, groups, excluded=()):
    assert Path('/proc').is_dir(), 'Resource validation requires the actual Linux host'
    controllers = []
    for stage in ('smoke', 'formal'):
        launch = read(output/(stage+'_LAUNCH_PID.json'))
        started = read(output/(stage+'_GPU_STARTED.json'))
        assert launch['pid'] == started['pid']
        current = proc_info(launch['pid'])
        alive = False
        if current is not None:
            expected_ticks = launch.get('linux_start_ticks')
            if expected_ticks is not None:
                alive = current['start_ticks'] == str(expected_ticks) and current['state'] != 'Z'
            else:
                # Launch metadata predates controller start-tick capture.
                # Compare its complete original argv; a same-command live PID
                # is conservatively blocked, never assumed to have exited.
                alive = current['state'] != 'Z' and current['argv'] == [s.encode() for s in launch['argv']]
        controllers.append({'stage': stage, 'pid': launch['pid'],
            'original_controller_command_alive': alive,
            'observed_process_state': current['state'] if current else None,
            'verification': 'PID/startticks where recorded, otherwise full original argv; zombie is exited'})
        assert not alive, 'Original controller still running: '+stage
    workers = []
    handle_files = sorted(p for p in output.rglob('OWNED_WORKER_HANDLES.json')
        if not any(p == d or d in p.parents for d in excluded))
    required_handles = {output/stage/name/'OWNED_WORKER_HANDLES.json'
        for stage, names in groups.items() for name in names}
    assert required_handles <= set(handle_files)
    # Check every recorded task Worker, including an extra/failed raw scope,
    # rather than only the 72 successful formal cells.
    for handle_path in handle_files:
        handles = read(handle_path)
        assert len(handles) == 2, 'Frozen two-GPU run requires both owned Worker handles'
        for handle in handles:
            ticks = handle['linux_start_ticks']
            assert ticks is not None and str(ticks).isdigit()
            current = proc_info(handle['pid'])
            same = current is not None and current['start_ticks'] == str(ticks)
            workers.append({'raw_cell_path': handle_path.parent.relative_to(output).as_posix(),
                'worker': handle['name'], 'pid': handle['pid'], 'expected_start_ticks': str(ticks),
                'observed_start_ticks': current['start_ticks'] if current else None,
                'same_original_process_present': same})
            assert not same, 'Owned Worker PID/startticks not released'
    try:
        gpu = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
            '--format=csv,noheader'], text=True, stderr=subprocess.STDOUT)
        gpu_status = 'snapshot_only_not_a_global_idle_requirement'
    except (OSError, subprocess.CalledProcessError) as error:
        gpu, gpu_status = repr(error), 'current_GPU_snapshot_unavailable_ownership_still_checked_via_proc'
    return {'controllers': controllers, 'worker_handles_checked': len(workers),
        'workers': workers, 'all_this_task_workers_released': True,
        'current_GPU_processes': gpu, 'current_GPU_snapshot_scope': gpu_status,
        'foreign_processes_not_touched': True, 'time_unix': time.time()}


def excluded_project(path, project):
    parts = path.relative_to(project).parts
    return any(p in ('.git', '__pycache__', '.pytest_cache') or p.startswith(('cpu_tmp', 'tmp_'))
               for p in parts)


def inventory(base, project, output, derived):
    """Full study-raw and project-artifact inventory, not unrelated 8TB projects."""
    entries = {}
    for root in (output, project):
        for path in sorted(root.rglob('*')):
            if any(path == x or x in path.parents for x in derived):
                continue
            if root == project and excluded_project(path, project):
                continue
            if path.is_symlink():
                raise ValueError('Symlinks are not silently followed/indexed: '+str(path))
            if not path.is_file():
                continue
            stat = path.stat()
            entries[path] = (stat.st_size, stat.st_mtime_ns)
    return entries


def safe_snapshot_hash(path, expected):
    assert (path.stat().st_size, path.stat().st_mtime_ns) == expected
    digest = sha(path)
    assert (path.stat().st_size, path.stat().st_mtime_ns) == expected, 'Raw changed while hashing'
    return digest


def gzip_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as inp, target.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=6) as out:
            shutil.copyfileobj(inp, out, 1024*1024)


class Collector:
    def __init__(self, base, project, output, directory, large, hashes):
        self.base, self.project, self.output = base, project, output
        self.directory, self.large, self.hashes = directory, large, hashes
        self.logical = []
        self.omitted_binary = []

    def add(self, source, relative, *, zipped=False):
        source = Path(source)
        if source.suffix.lower() in NO_COPY:
            self.omitted_binary.append({'path': source.relative_to(self.base).as_posix(),
                'reason': 'Audio/model/array binary is indexed on 8TB, not copied'})
            return
        target = within(self.directory, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists()
        if zipped:
            gzip_file(source, target)
        else:
            with source.open('rb') as inp, target.open('xb') as out:
                shutil.copyfileobj(inp, out, 1024*1024)
        payload_sha = sha(target)
        if not zipped:
            assert payload_sha == self.hashes[source], 'Byte-exact source changed during copy'
        self.logical.append({'logical_path': relative,
            'source_path': source.relative_to(self.base).as_posix(),
            'source_bytes': source.stat().st_size, 'source_sha256': self.hashes[source],
            'representation': 'gzip' if zipped else 'byte_exact',
            'payload_bytes': target.stat().st_size, 'payload_sha256': payload_sha,
            'parts': [relative]})

    def generated_record(self, relative):
        path = within(self.directory, relative)
        self.logical.append({'logical_path': relative, 'representation': 'generated_bounded_evidence',
            'payload_bytes': path.stat().st_size, 'payload_sha256': sha(path), 'parts': [relative]})

    def split_large_payloads(self):
        for item in self.logical:
            source = within(self.directory, item['logical_path'])
            if source.stat().st_size < MAX_PUBLISH_BYTES:
                continue
            parts = split_stream(source, self.directory, item['logical_path'], PART_BYTES)
            item['parts'] = [p.relative_to(self.directory).as_posix() for p in parts]
            self.large.mkdir(parents=True, exist_ok=True)
            retained = within(self.large, item['logical_path'])
            retained.parent.mkdir(parents=True, exist_ok=True)
            assert not retained.exists()
            # Only move this collector's generated oversized representation.
            # The original raw source is never moved, removed or rewritten.
            source.rename(retained)
            item['large_derived_retained_8TB'] = retained.relative_to(self.base).as_posix()


def split_stream(source, output, logical_name, chunk_size=PART_BYTES):
    count = (source.stat().st_size+chunk_size-1)//chunk_size
    parts = []
    with source.open('rb') as handle:
        for i in range(count):
            target = within(output, logical_name+f'.part{i+1:03d}-of-{count:03d}')
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as out:
                remaining = chunk_size
                while remaining:
                    chunk = handle.read(min(1024*1024, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
            assert target.stat().st_size < MAX_PUBLISH_BYTES
            parts.append(target)
        assert handle.read(1) == b''
    combined = hashlib.sha256()
    for path in parts:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024*1024), b''):
                combined.update(chunk)
    assert combined.hexdigest() == sha(source), 'Part concatenation differs from logical source'
    return parts


def canonical_witnesses(collector, stage, name):
    cell = collector.output/stage/name
    commits = {}
    with (cell/'events.jsonl').open(encoding='utf8') as handle:
        for line in handle:
            event = json.loads(line)
            if event['kind'] == 'commit':
                assert event['job_id'] not in commits
                commits[event['job_id']] = event
    relative = f'canonical_witnesses/{stage}/{name}.jsonl.gz'
    target = within(collector.directory, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    full = cell/'worker_records.jsonl'
    seen = set()
    with full.open(encoding='utf8') as inp, target.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as out:
            for line in inp:
                rec = json.loads(line)
                job, result = rec['job'], rec['result']
                if job['role'] != 'authority':
                    continue
                jid = job['job_id']
                assert jid not in seen
                seen.add(jid)
                assert all(key in result for key in ('token_ids', 'state_tokens', 'text',
                    'terminated_by_eos', 'hit_token_limit', '_row_receipt'))
                selected = {key: value for key, value in result.items() if key != 'model_input_audit'}
                witness = {'job': job, 'selected_result': selected,
                    'model_input_audit_sha256': canonical_sha(result['model_input_audit']),
                    'actual_commit_event': commits.get(jid), 'was_canonically_committed': jid in commits,
                    'raw_worker_records_path': full.relative_to(collector.base).as_posix(),
                    'raw_worker_records_sha256': collector.hashes[full],
                    'scope': 'Actual complete Authority Z/P/text/stop/verification/receipt; full model-input arrays stay in indexed8TB raw. Receipt body recheck requires that full raw file.'}
                out.write((json.dumps(witness, ensure_ascii=True, separators=(',', ':'))+'\n').encode())
    assert set(commits) <= seen, 'Committed Authority witness missing'
    collector.generated_record(relative)
    return {'stage': stage, 'cell': name, 'authority_rows': len(seen),
            'committed_rows': len(commits), 'uncommitted_paid_authority_rows_retained': len(seen-set(commits))}


def external_assets(base, plan):
    """Audio/weights are referenced and never copied into the bounded payload."""
    manifest = within(base, plan['manifest_relative'])
    donors = within(base, plan['donors_relative'])
    assert sha(manifest) == plan['manifest_sha256'] and sha(donors) == plan['donors_sha256']
    result = [{'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
               'sha256': sha(path), 'verification': 'fresh_file_hash_at_collection'}
              for path in (manifest, donors)]
    audio_seen = set()
    for row in read(manifest)['sessions']:
        path = Path(row['path'])
        if not path.is_file():
            path = manifest.parent/path.name
        path = path.resolve()
        path.relative_to(base)
        if path in audio_seen:
            continue
        audio_seen.add(path)
        result.append({'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
            'sha256': sha(path), 'declared_decoded_PCM_sha256': row['audio_sha256'],
            'verification': 'fresh container hash; decoded PCM hash is the manifest value verified during actual runtime load'})
    model = within(base, plan['model_relative'])
    for name, digest in plan['model_files'].items():
        path = within(model, name)
        result.append({'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest, 'verification': 'frozen_controller_preflight_hash_not_rehashed_during_collection'})
    return result


def collect(base, output_name, check_only=False):
    base = Path(base).resolve()
    assert base.is_dir() and base != Path(base.anchor), 'Explicit designated experiment disk required'
    if (Path(output_name).name != output_name or output_name in ('.', '..', '')
            or any(c in output_name for c in ('/', '\\'))):
        raise ValueError('--output-dir is a new single directory name beneath this study')
    project, output = within(base, PROJECT_RELATIVE), within(base, RAW_RELATIVE)
    directory = within(output, output_name)
    large = within(output, output_name+'_large_derived')
    archive = within(output, output_name+'.tar.gz')
    index_path = output/('BOUNDED_INDEX.json' if output_name == 'bounded_evidence_v1'
                         else output_name+'_BOUNDED_INDEX.json')
    self_log = output/(output_name+'_COLLECTOR.log')
    assert not any(p.exists() for p in (directory, large, archive, index_path)), 'No overwrite/retry into existing collection'
    plan, groups, gate = completed_gate(base, project, output)
    resource = resource_gate(output, project, groups)
    if check_only:
        return {'status': 'PASS_COLLECTION_PRECONDITIONS_ONLY_NO_PACKAGE_WRITTEN',
                'gate': gate, 'resources': resource}
    directory.mkdir()
    # Own generated collection artifacts and live stdout self-log are excluded;
    # old failures, CPU logs and all other study raw files remain indexed.
    derived = [directory, large, archive, index_path, self_log]
    try:
        snapshot = inventory(base, project, output, derived)
        hashes = {path: safe_snapshot_hash(path, stamp) for path, stamp in snapshot.items()}
        collector = Collector(base, project, output, directory, large, hashes)
        write_new(directory/'COLLECTION_GATE.json', gate)
        write_new(directory/'RESOURCE_RELEASE.json', resource)
        stages = set(groups)
        known_cells = {output/stage/name for stage, names in groups.items() for name in names}
        witnesses = []
        journals = set()
        for stage, names in groups.items():
            for name in names:
                cell = output/stage/name
                for path in sorted(cell.rglob('*')):
                    if not path.is_file() or path.name == 'worker_records.jsonl':
                        continue
                    folder = 'traces' if path.name in ('events.jsonl', 'consumer.jsonl',
                        'worker_batch_accounting.jsonl') else 'cell_metadata'
                    rel = f'{folder}/{stage}/{name}/{path.relative_to(cell).as_posix()}.gz'
                    collector.add(path, rel, zipped=True)
                witnesses.append(canonical_witnesses(collector, stage, name))
                journal = Path(read(cell/'provenance.json')['durable_journal_path']).resolve()
                journals.add(journal)
            for path in sorted((output/stage).iterdir()):
                if path.is_file():
                    collector.add(path, f'cell_logs/{stage}/{path.name}.gz', zipped=True)
        # Include every WAL, including an unexpected/failed prior history, not
        # only the journals currently named by successful cells.
        journals.update(output.rglob('*.wal'))
        for path in sorted(journals):
            if directory in path.parents or large in path.parents:
                continue
            collector.add(path, 'journals/'+path.relative_to(output).as_posix()+'.gz', zipped=True)
        # All auxiliary directories include failed v1 and corrected v2 audits,
        # formal/smoke/oracle metrics, and any diagnosis_v1/CPU output already
        # present. No selection by sign of result is made.
        for path in sorted(output.rglob('*')):
            if not path.is_file() or any(path == d or d in path.parents for d in derived):
                continue
            relative = path.relative_to(output)
            if path.suffix == '.wal':
                continue
            if relative.parts[0] in stages:
                if path.parent == output/relative.parts[0] or any(c in path.parents for c in known_cells):
                    continue
                # Unplanned/failed partial directories are retained as extra
                # bounded raw evidence, not re-labelled part of the72PASS set.
                if path.name == 'worker_records.jsonl':
                    collector.omitted_binary.append({'path': path.relative_to(base).as_posix(),
                        'reason': 'Extra raw worker-record/model-input arrays remain fully SHA-indexed8TB; negative scope is not removed'})
                else:
                    collector.add(path, 'extra_cell_evidence/'+relative.as_posix()+'.gz', zipped=True)
                continue
            if path.name == 'worker_records.jsonl':
                collector.omitted_binary.append({'path': path.relative_to(base).as_posix(),
                    'reason': 'Auxiliary full worker arrays remain fully SHA-indexed8TB, not duplicated in bounded package'})
                continue
            # Keep audit CSV/JSON paths byte-exact and directly usable by the
            # local independent review. Only rich per-cell traces are gzipped.
            collector.add(path, relative.as_posix(), zipped=False)
        for path in sorted(project.rglob('*')):
            if not path.is_file() or excluded_project(path, project):
                continue
            # Source bundles stay indexed on8TB; frozen individual source,
            # CPU logs/gates and profile data remain directly inspectable.
            if path.name.endswith(('.tar.gz', '.zip', '.bundle')):
                continue
            if path.name == 'remote_ops.py' or 'operations' in path.relative_to(project).parts:
                collector.omitted_binary.append({'path': path.relative_to(base).as_posix(),
                    'reason': 'Credential-routing/transport artifacts stay indexed8TB, not publication payload'})
                continue
            collector.add(path, 'project_artifacts/'+path.relative_to(project).as_posix(), zipped=False)
        assets = external_assets(base, plan)
        reference_path = within(base, plan['manifest_relative'])
        collector.hashes[reference_path] = plan['manifest_sha256']
        collector.add(reference_path, 'source_reference_manifest.json', zipped=False)
        reference_rows = read(reference_path)['sessions']
        assert all('source_id' in r and 'reference' in r for r in reference_rows)
        write_new(directory/'SOURCE_REFERENCE_IDENTITY.json', {
            'source_manifest_path': reference_path.relative_to(base).as_posix(),
            'source_manifest_sha256': plan['manifest_sha256'],
            'bounded_copy': 'source_reference_manifest.json', 'byte_exact': True,
            'rows': len(reference_rows), 'unique_source_ids': len({r['source_id'] for r in reference_rows}),
            'contains_reference_text_not_audio_or_weights': True})
        raw_index = {'experiment_id': STUDY,
            'scope': 'Every study-results file and project artifact at collection checkpoint, excluding only own collection products/self-log and project cache/Git/temporary fixture directories; unrelated8TB projects are not traversed.',
            'files': [{'path': path.relative_to(base).as_posix(), 'bytes': stamp[0], 'sha256': hashes[path]}
                      for path, stamp in sorted(snapshot.items())],
            'external_audio_model_and_source_assets': assets,
            'full_worker_records_and_model_input_arrays_stay_on8TB': True}
        write_new(directory/'RAW_INDEX.json', raw_index)
        write_new(directory/'CANONICAL_WITNESS_COUNTS.json', witnesses)
        collector.split_large_payloads()
        write_new(directory/'LOGICAL_PAYLOADS.json', {'files': collector.logical,
            'excluded_binary_payloads_still_indexed': collector.omitted_binary,
            'parts_reassemble': 'Concatenate each parts list in its listed order, verify payload_sha256, then gunzip if representation=gzip.'})
        note = ('All archive/payload parts are ordered in their SHA indices. Concatenate archive publish_files before tar extraction and verify full_archive_sha256. '
            'For any logical payload split into parts, concatenate LOGICAL_PAYLOADS.parts in order and verify payload_sha256 before gzip decoding. '
            'Full worker result/model-input arrays, audio and weights remain on indexed8TB paths; bounded receipts are references, not a self-contained re-execution of the full raw audit. '
            'Negative/capped results, original smoke v1 FAIL and corrected same-raw v2 PASS are retained. No models, SSH, process kills or new GPU work are performed.\n')
        (directory/'RECONSTRUCTION.txt').write_text(note, encoding='utf8')
        final_resource = resource_gate(output, project, groups, excluded=(directory, large))
        assert final_resource['all_this_task_workers_released']
        assert inventory(base, project, output, derived) == snapshot, 'Original data/project changed during collection'
        manifest = [{'path': path.relative_to(directory).as_posix(),
                     'bytes': path.stat().st_size, 'sha256': sha(path)}
                    for path in sorted(directory.rglob('*')) if path.is_file()]
        assert all(row['bytes'] < MAX_PUBLISH_BYTES for row in manifest), 'Oversized metadata needs a separately bounded representation'
        write_new(directory/'MANIFEST.json', {'experiment_id': STUDY, 'files': manifest,
            'raw_index_sha256': sha(directory/'RAW_INDEX.json'),
            'collector_script_sha256': sha(Path(__file__)),
            'scope': 'Every packaged file except this self-referencing manifest; archive SHA is in external BOUNDED_INDEX'})
        assert (directory/'MANIFEST.json').stat().st_size < MAX_PUBLISH_BYTES
        # A gzip stream over deterministic tar members is retained complete on
        # 8TB, but publication uses32MBparts whenever the archive reaches40MB.
        with archive.open('xb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=6) as zipped:
                with tarfile.open(fileobj=zipped, mode='w|') as tar:
                    for path in sorted(directory.rglob('*')):
                        if not path.is_file():
                            continue
                        info = tar.gettarinfo(str(path), arcname=path.relative_to(directory).as_posix())
                        info.uid = info.gid = 0
                        info.uname = info.gname = ''
                        info.mtime = 0
                        info.mode = 0o644
                        with path.open('rb') as handle:
                            tar.addfile(info, handle)
        publish = [archive] if archive.stat().st_size < MAX_PUBLISH_BYTES else split_stream(
            archive, output, archive.name, PART_BYTES)
        derived.extend(path for path in publish if path != archive)
        record = {'status': 'COMPLETE_BOUNDED_72_FORMAL_COLLECTION_NO_NEW_GPU',
            'experiment_id': STUDY, 'directory': str(directory),
            'full_archive_path': str(archive), 'full_archive_bytes': archive.stat().st_size,
            'full_archive_sha256': sha(archive), 'compressed_size_over_90MB': archive.stat().st_size > 90_000_000,
            'publish_files': [{'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in publish],
            'publication_limit_bytes_exclusive': MAX_PUBLISH_BYTES,
            'manifest_sha256': sha(directory/'MANIFEST.json'),
            'raw_index_sha256': sha(directory/'RAW_INDEX.json'),
            'raw_files': len(snapshot), 'raw_bytes': sum(stamp[0] for stamp in snapshot.values()),
            'packaged_files': len(manifest)+1, 'logical_payloads': len(collector.logical),
            'formal_cells': 72, 'smoke_cells': 4, 'oracle_cells': 2,
            'old_negative_results_retained': True, 'all_this_task_workers_released': True,
            'global_GPU_idle_not_required_foreign_owners_untouched': True,
            'GPU_or_model_calls_by_collector': 0, 'collector_script_sha256': sha(Path(__file__)),
            'time_unix': time.time()}
        assert all(row['bytes'] < MAX_PUBLISH_BYTES for row in record['publish_files'])
        assert inventory(base, project, output, derived) == snapshot, 'Raw changed before final index publication'
        write_new(index_path, record)
        record['bounded_index_path'] = str(index_path)
        return record
    except BaseException as error:
        if directory.is_dir() and not (directory/'COLLECTION_STOP.json').exists():
            write_new(directory/'COLLECTION_STOP.json', {'status': 'COLLECTION_FAILED_RAW_PRESERVED',
                'error': repr(error), 'retry_requires_new_output_dir': True, 'no_new_GPU': True})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output-dir', default='bounded_evidence_v1')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(collect(args.base, args.output_dir, args.check_only), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
