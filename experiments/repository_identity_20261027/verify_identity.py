"""Independently recompute bounded repository-maintenance postconditions."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def git(*args, cwd=ROOT, raw=False):
    result = subprocess.check_output(['git', '-C', str(cwd), *args], stderr=subprocess.PIPE)
    return result if raw else result.decode().strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = json.loads((OUT / 'BEFORE.json').read_text())
    after = json.loads((OUT / 'AFTER.json').read_text())
    setup = json.loads((OUT / 'SETUP.json').read_text())
    assert before['head'] == after['head'] == git('rev-parse', 'HEAD')
    assert before['branch'] == after['branch']
    assert before['staged_paths'] == after['staged_paths'] == []
    for row in before['tracked_dirty']:
        assert sha(ROOT / row['path']) == row['sha256'], row['path']
    old_dirty = {r['path'] for r in before['tracked_dirty']}
    new_dirty = {r['path'] for r in after['tracked_dirty']}
    assert new_dirty - old_dirty == {'AGENTS.md'}, new_dirty - old_dirty
    for label in ['archive', 'source']:
        checkout = Path(setup[label + '_worktree'])
        assert git('rev-parse', 'HEAD', cwd=checkout) == setup[label + '_commit']
        assert not git('status', '--porcelain', '--untracked-files=all', cwd=checkout)
    assert git('rev-parse', 'main') == git('rev-parse', 'origin/main') == setup['archive_commit']
    assert git('cat-file', '-t', '62b1003c2db6766118244c78fa95e2c3fac42c16') == 'commit'
    assert git('rev-parse', '--is-shallow-repository') == 'false'
    manifest = Path(setup['source_manifest'])
    archive_path = 'experiments/legal_progress_20261026/final_source_v2_SOURCE.json'
    assert hashlib.sha256(git('show', setup['archive_commit'] + ':' + archive_path, raw=True)).hexdigest() == sha(manifest)
    for row in setup['imports']:
        assert git('rev-parse', row['ref']) == row['code_commit']
        assert git('cat-file', '-t', row['code_commit']) == 'commit'
    fsck = subprocess.run(['git', '-C', str(ROOT), 'fsck', '--connectivity-only', '--no-reflogs'],
                          capture_output=True, text=True, check=True)
    fsck_text = fsck.stdout + fsck.stderr
    assert all(not line or line.startswith('dangling ') for line in fsck_text.splitlines()), fsck_text
    (OUT / 'FSCK.txt').write_text(fsck_text)
    counts = {}
    for filename in ['RUNTIME_CPU.xml', 'GATE_TESTS_v2.xml']:
        root = ET.parse(OUT / filename).getroot()
        suites = list(root.iter('testsuite'))
        counts[filename] = {k: sum(int(s.attrib.get(k, 0)) for s in suites)
                            for k in ['tests', 'failures', 'errors', 'skipped']}
        assert counts[filename]['failures'] == counts[filename]['errors'] == 0
    record = dict(maintenance_id='REPO-IDENTITY-20261027', gate='PASS_LOCAL_SOURCE_IDENTITY',
                  observed_unix=time.time(), environment=dict(python=sys.version, executable=sys.executable,
                     platform=platform.platform(), git=git('--version')),
                  original_tracked_edits_preserved=len(old_dirty), root_head_preserved=before['head'],
                  original_index_byte_unchanged=before['index_sha256'] == after['index_sha256'],
                  original_index_staged_content_unchanged=True, deliberate_tracked_edit='AGENTS.md',
                  archive_commit=setup['archive_commit'], execution_source_commit=setup['source_commit'],
                  source_refs_verified=len(setup['imports']), source_manifest_sha256=sha(manifest),
                  cpu_tests=counts, fsck_exit=fsck.returncode,
                  dangling_objects_retained=len(fsck_text.splitlines()),
                  gpu_runs_started=0, papers_modified=False, remote_pushes=0,
                  scope='Local Git identity and CPU preflight only. Not a retrospective audit of every historical run or a new research result.')
    (OUT / 'VERIFICATION.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
