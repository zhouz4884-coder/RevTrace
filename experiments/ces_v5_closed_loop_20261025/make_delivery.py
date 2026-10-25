"""Build an additive, bounded, audited closed-loop research delivery.

Preparation code only until explicitly invoked. No model, SSH, Git write or
network operation is performed. Existing evidence/source/output is not edited.
"""
from __future__ import annotations
import argparse
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET


STUDY = 'REVTRACE-CES-V5-CLOSED-LOOP-20261025'
RUNTIME = 'e45c66475ba1173a98b49b8c9e62f3e8cb45b333'
STATUS = 'COMPLETE_AUDITED_BOUNDED_CLOSED_LOOP_RESEARCH_STAGE'
MAX_FILE = 40_000_000
FORBIDDEN_SUFFIXES = {'.wav', '.flac', '.mp3', '.mp4', '.pcm', '.bin', '.npy', '.npz',
                      '.safetensors', '.pt', '.pth', '.ckpt', '.onnx'}
FORBIDDEN_PARTS = {'.git', '.ssh', '.aws', '.codex', '.agents', '__pycache__', 'operations', 'node_modules'}
SENSITIVE_NAMES = {'remote_ops.py', '.env', 'credentials', 'credentials.json', 'id_rsa', 'id_ed25519',
    'known_hosts', 'config'}
SECRET = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}'
    rb'|gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{24,}|AKIA[A-Z0-9]{16}'
    rb'|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}')
CREDENTIAL_ROUTE = re.compile(rb'contractkv_ssh_credential[.]py|[.]codex[\\/]local-tools[\\/]', re.I)
FINAL_DOCS = ('RESEARCH_REPORT.zh.md', 'CONTRIBUTION_EVIDENCE_MATRIX.md', 'DECISION.json',
    'README.md', 'IMPLEMENTATION_COVERAGE.md', 'ALGORITHM_EXPLANATION.zh.md',
    'PROTOCOL.md', 'FORMAL_REVIEW_BOUNDARIES.md', 'AUDIT_V2_CORRECTION.md')
PROFILE_OUTPUTS = ('CALIBRATION.json', 'SUMMARY.json', 'INPUT_MANIFEST.json',
    'PROPOSAL_ROWS.csv', 'PROPOSAL_BATCHES.csv', 'ROOT_COMPATIBILITY.csv', 'CELL_STATUS.csv')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def confined(root, relative):
    normalized = str(relative).replace('\\', '/')
    logical = PurePosixPath(normalized)
    if logical.is_absolute() or '..' in logical.parts or ':' in normalized or '\x00' in normalized:
        raise ValueError('Unsafe artifact-relative path')
    path = (Path(root)/Path(*logical.parts)).resolve()
    path.relative_to(Path(root).resolve())
    return path


def banned_path(relative):
    p = PurePosixPath(str(relative).replace('\\', '/'))
    if any(part.lower() in FORBIDDEN_PARTS or part.lower().startswith(('tmp_', 'cpu_tmp_', '.pytest_cache'))
           for part in p.parts):
        return True
    if p.name.lower() in SENSITIVE_NAMES or p.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    return False


def atomic_new(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')


def verify_manifest(directory, manifest_name='MANIFEST.json'):
    manifest = read(directory/manifest_name)
    files = {row['path']: row for row in manifest['files']}
    assert len(files) == len(manifest['files']), 'Duplicate bounded manifest entry'
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    assert actual == set(files)|{manifest_name}, 'Bounded artifact has missing/unindexed files'
    for relative, row in files.items():
        path = confined(directory, relative)
        assert not path.is_symlink() and not banned_path(relative), 'Forbidden publication path: '+relative
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Bounded byte identity mismatch: '+relative
        assert row['bytes'] < MAX_FILE, 'Oversized publication payload must retain its indexed parts'
    return manifest


class ConcatenatedReader(io.RawIOBase):
    """Streaming logical payload reconstruction; no oversized local rewrite."""
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                try:
                    self.current = next(self.paths).open('rb')
                except StopIteration:
                    return 0
            count = self.current.readinto(buffer)
            if count:
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()


def scan_plain(stream, label):
    tail = b''
    total = 0
    while True:
        chunk = stream.read(1024*1024)
        if not chunk:
            return total
        probe = tail+chunk
        if SECRET.search(probe):
            raise ValueError('Recognized secret pattern; value suppressed: '+label)
        if CREDENTIAL_ROUTE.search(probe):
            raise ValueError('Local credential-routing code must not be published: '+label)
        total += len(chunk)
        tail = probe[-256:]


def scan_tar(stream, label, depth=0):
    if depth > 3:
        raise ValueError('Unbounded nested archive')
    total = members = 0
    with tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            members += 1
            if members > 20000:
                raise ValueError('Unbounded tar member count')
            if member.isdir():
                continue
            if not member.isfile() or banned_path(member.name):
                raise ValueError('Forbidden archive member: '+label+'!'+member.name)
            logical = PurePosixPath(member.name)
            if logical.is_absolute() or '..' in logical.parts:
                raise ValueError('Unsafe archive member')
            with archive.extractfile(member) as handle:
                child = label+'!'+member.name
                if member.name.endswith('.tar.gz'):
                    total += scan_tar(handle, child, depth+1)
                elif member.name.endswith('.gz'):
                    with gzip.GzipFile(fileobj=handle, mode='rb') as plain:
                        total += scan_plain(plain, child)
                else:
                    total += scan_plain(handle, child)
    return total


def scan_package(directory):
    """Inspect plain, gzip/tar and split logical streams without exposing hits."""
    consumed = set()
    logical_streams = plain_bytes = 0
    for index_path in directory.rglob('LOGICAL_PAYLOADS.json'):
        index = read(index_path)
        for item in index['files']:
            paths = [confined(index_path.parent, name) for name in item['parts']]
            assert all(p.is_file() for p in paths)
            with io.BufferedReader(ConcatenatedReader(paths)) as stream:
                digest = hashlib.sha256()
                count = 0
                for block in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(block); count += len(block)
            assert digest.hexdigest() == item['payload_sha256'] and count == item['payload_bytes']
            label = index_path.parent.relative_to(directory).as_posix()+'/'+item['logical_path']
            with io.BufferedReader(ConcatenatedReader(paths)) as stream:
                if item['representation'] == 'gzip':
                    with gzip.GzipFile(fileobj=stream, mode='rb') as plain:
                        plain_bytes += scan_plain(plain, label)
                else:
                    plain_bytes += scan_plain(stream, label)
            consumed.update(paths)
            logical_streams += 1
    ordinary = 0
    for path in sorted(directory.rglob('*')):
        if not path.is_file() or path.resolve() in consumed:
            continue
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink() or banned_path(relative):
            raise ValueError('Forbidden delivery path: '+relative)
        with path.open('rb') as stream:
            if path.name.endswith('.tar.gz'):
                plain_bytes += scan_tar(stream, relative)
            elif path.suffix == '.gz':
                with gzip.GzipFile(fileobj=stream, mode='rb') as plain:
                    plain_bytes += scan_plain(plain, relative)
            else:
                plain_bytes += scan_plain(stream, relative)
        ordinary += 1
    return {'status': 'PASS_RECOGNIZED_SECRET_PATTERN_AND_CREDENTIAL_ROUTE_SCAN',
        'ordinary_files': ordinary, 'reconstructed_logical_streams': logical_streams,
        'plain_bytes_scanned': plain_bytes,
        'limitations': 'Recognized patterns only, not a universal secret detector; gzip/tar and ordered split payloads are inspected after decoding.'}


def verify_runtime(stage):
    source = stage/'runtime'
    manifest = read(stage/'SOURCE_MANIFEST.json')
    assert manifest['code_commit'] == RUNTIME and len(manifest['files']) == 140
    git = lambda *args: subprocess.check_output(['git', '-C', str(source), *args])
    assert git('rev-parse', 'HEAD').decode().strip() == RUNTIME
    assert not git('status', '--porcelain').strip(), 'Frozen runtime was edited'
    tracked = set(git('ls-files', '-z').decode().rstrip('\0').split('\0'))
    assert tracked == {row['path'] for row in manifest['files']}
    for row in manifest['files']:
        path = confined(source, row['path'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        assert path.read_bytes() == git('show', RUNTIME+':'+row['path']), 'Tested bytes differ from committed blob'
    return manifest


def verify_cpu_and_profiles(stage):
    gate = read(stage/'INDEPENDENT_CPU_GATE.json')
    assert gate['status'] == 'PASS_CPU_IMPLEMENTATION_AND_SAFETY_GATE' and gate['failures'] == 0
    assert gate['tests'] == 367
    xml = stage/gate['junit_file']
    assert sha(xml) == gate['junit_sha256']
    suites = ET.parse(xml).getroot()
    assert all(int(s.get('failures', '0')) == 0 and int(s.get('errors', '0')) == 0
               for s in suites.iter('testsuite'))
    reviewer = read(stage/'FINAL_RUNTIME_REVIEW_FINAL.json')
    assert reviewer['source_commit'] == RUNTIME
    assert reviewer['status'] == 'GO_BOUNDED_GPU_VALIDATION_SOURCE_AND_CPU_REVIEW'
    assert reviewer['reviewer_related_tests_failed'] == 0 and reviewer['runtime_clean']
    for name, expected in reviewer['files_sha256'].items():
        assert sha(confined(stage, name)) == expected, 'Independent review identity changed: '+name
    assert read(stage/'INDEPENDENT_PROFILE_AUDIT_v1.json')['status'] == 'PASS_INDEPENDENT_EXTRACTED_PROFILE_ARITHMETIC_AND_FIT_AUDIT'
    for folder in ('profiles_training_v1', 'profiles_repeat_v1'):
        summary = read(stage/folder/'SUMMARY.json')
        assert summary['status'] == 'PASS_ACTUAL_SELECTED_EXECUTION_PROFILES' and summary['new_GPU_calls'] == 0
        for name, info in summary['outputs'].items():
            assert sha(stage/folder/name) == info['sha256']
    for name in PROFILE_OUTPUTS:
        if name == 'SUMMARY.json':
            continue  # creation timestamps may differ; data/model outputs must not.
        assert (stage/'profiles_training_v1'/name).read_bytes() == (stage/'profiles_repeat_v1'/name).read_bytes()


def verify_evidence(stage, collected, analysis):
    bounded = read(stage/'BOUNDED_INDEX.json')
    assert bounded['status'] == 'COMPLETE_BOUNDED_72_FORMAL_COLLECTION_NO_NEW_GPU'
    assert (bounded['formal_cells'], bounded['smoke_cells'], bounded['oracle_cells']) == (72, 4, 2)
    assert bounded['all_this_task_workers_released'] and bounded['GPU_or_model_calls_by_collector'] == 0
    verify_manifest(collected)
    assert sha(collected/'MANIFEST.json') == bounded['manifest_sha256']
    assert sha(collected/'RAW_INDEX.json') == bounded['raw_index_sha256']
    result = read(collected/'formal_SUMMARY.json')
    assert result['status'] == 'COMPLETE_FROZEN_CLOSED_LOOP_STAGE_AND_AUDIT'
    assert result['performance_cells'] == 72 and result['GPU_queue_closed'] and result['source_commit'] == RUNTIME
    formal = read(collected/'formal_audit/SUMMARY.json')
    smoke = read(collected/'smoke_audit_v2/SUMMARY.json')
    oracle = read(collected/'smoke_oracle_audit_v2/SUMMARY.json')
    for audit, expected in ((formal, 72), (smoke, 4), (oracle, 2)):
        assert audit['status'] == 'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
        assert audit['cells'] == audit['expected_cells'] == expected and not audit['failures']
        assert audit['actual_model_calls'] > 0
    assert read(collected/'RESOURCE_RELEASE.json')['all_this_task_workers_released']
    assert (collected/'smoke_STOP.json').is_file(), 'Original false-rejection history must remain'
    correction = read(collected/'smoke_REAUDITED_SUMMARY.json')
    assert correction['status'] == 'PASS_SMOKE_SAME_RAW_V2_REAUDIT' and correction['no_GPU_rerun']
    assert correction['original_v1_stop_sha256'] == sha(collected/'smoke_STOP.json')
    review = read(analysis/'SUMMARY.json')
    assert review['status'] == 'PASS_SEPARATE_LOCAL_EVENT_QUALITY_ENERGY_RECOMPUTATION'
    assert review['online_cells'] == 72 and review['new_GPU_calls'] == 0
    assert review['actual_model_calls'] == formal['actual_model_calls']
    assert review['same_source_repeat_not_IID_frontiers'] is True
    return bounded


def copy_new(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)
    shutil.copyfile(source, target)


def write_binary_attributes(path):
    """Exact LF bytes on Windows too; file contents themselves stay unnormalized."""
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(b'* -text\n')


def make_delivery(stage, collected, analysis, output):
    stage, collected, analysis, output = map(lambda p: Path(p).resolve(), (stage, collected, analysis, output))
    if output.exists():
        raise FileExistsError('Never overwrite an existing delivery/failed preparation')
    for name in FINAL_DOCS:
        assert (stage/name).is_file(), 'Missing final requested document: '+name
    decision = read(stage/'DECISION.json')
    assert decision['experiment_id'] == STUDY
    assert any(key in decision for key in ('algorithm_upgrade', 'C2_upgrade', 'algorithm_decision'))
    source = verify_runtime(stage)
    verify_cpu_and_profiles(stage)
    bounded = verify_evidence(stage, collected, analysis)
    output.mkdir(parents=True)
    excluded = []
    try:
        shutil.copytree(collected, output/'evidence')
        shutil.copytree(analysis, output/'analysis')
        copy_new(stage/'BOUNDED_INDEX.json', output/'COLLECTION_TRANSPORT_INDEX.json')
        # Preserve all historical bounded root CPU gates/reviews, including
        # early failures. Temporary directories/transport operations are not
        # traversed. Current completion state is labelled as a packaging-time
        # snapshot rather than silently updated after publication.
        for path in sorted(stage.iterdir()):
            if not path.is_file():
                continue
            name = path.name
            if name.startswith(('GITHUB_', 'FINAL_DELIVERY')) or name in (
                    'BOUNDED_INDEX.json', 'DELIVERY_BUILD_INDEX.json', 'DELIVERY_MANIFEST.json'):
                continue
            if path.suffix.lower() not in ('.md', '.json', '.xml', '.py', '.mjs') and name != 'SOURCE_AND_CONTROLLERS_smoke_v1.tar.gz':
                continue
            if banned_path(name) or CREDENTIAL_ROUTE.search(path.read_bytes()):
                excluded.append({'path': name, 'reason': 'Credential routing/transport material excluded'})
                continue
            if path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf8'))
            target = output/('STATE_AT_PACKAGING.json' if name == 'ACTIVE_STATE.json' else name)
            copy_new(path, target)
        assert all((output/name).is_file() for name in FINAL_DOCS), 'A required final report cannot be omitted by publication filtering'
        for folder in ('profiles_training_v1', 'profiles_repeat_v1', 'AUDIT_CORRECTION_V2_CPU', 'precollection'):
            shutil.copytree(stage/folder, output/folder)
        for row in source['files']:
            copy_new(stage/'runtime'/row['path'], output/'runtime'/row['path'])
        copy_new(stage/'SOURCE_MANIFEST.json', output/'runtime/SOURCE_MANIFEST.json')
        copy_new(stage/'profiles_training_v1/CALIBRATION.json', output/'CALIBRATION.json')
        write_binary_attributes(output/'.gitattributes')
        atomic_new(output/'PACKAGING_EXCLUSIONS.json', {'excluded_top_level_files': excluded,
            'never_traversed': ['operations/', 'tmp_*/', 'cpu_tmp_*/', '.git/', 'credential-routing helpers'],
            'audio_and_weights_not_copied': True})
        scan = scan_package(output)
        atomic_new(output/'SECRET_SCAN.json', scan)
        files = [{'path': p.relative_to(output).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(output.rglob('*')) if p.is_file()]
        assert all(row['bytes'] < MAX_FILE for row in files)
        manifest = {'status': STATUS, 'experiment_id': STUDY, 'runtime_commit': RUNTIME,
            'runtime_manifest_sha256': sha(stage/'SOURCE_MANIFEST.json'),
            'runtime_tracked_files_byte_verified': 140, 'formal_cells': 72, 'smoke_cells': 4,
            'oracle_cells': 2, 'all_requested_cells_retained': True, 'GPU_queue_closed': True,
            'all_this_task_workers_released': True, 'independent_confirmation': False,
            'pure_no_service_guard_GPU_ablation': False, 'manuscript_edits': False,
            'algorithm_decision': next(decision[k] for k in ('algorithm_upgrade', 'C2_upgrade', 'algorithm_decision') if k in decision),
            'collector_manifest_sha256': bounded['manifest_sha256'],
            'raw_index_sha256': bounded['raw_index_sha256'], 'files': files,
            'total_bytes': sum(row['bytes'] for row in files), 'time_unix': time.time(),
            'scope': 'Bounded evidence plus exact frozen source; full tensors/audio/models stay on indexed 8TB paths'}
        atomic_new(output/'MANIFEST.json', manifest)
        return {'files': len(files)+1, 'bytes': manifest['total_bytes'], 'output': str(output),
            'manifest_sha256': sha(output/'MANIFEST.json'), 'status': STATUS}
    except BaseException as error:
        if not (output/'DELIVERY_PREPARATION_FAILED.json').exists():
            atomic_new(output/'DELIVERY_PREPARATION_FAILED.json', {'error': type(error).__name__,
                'scope': 'Preparation failed; partial output retained, no publication performed',
                'requires_new_output_directory': True})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--collected', type=Path)
    parser.add_argument('--analysis', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(make_delivery(args.stage, args.collected or args.stage/'collected',
        args.analysis or args.stage/'local_review', args.output or args.stage/'delivery'), indent=2))


if __name__ == '__main__':
    main()
