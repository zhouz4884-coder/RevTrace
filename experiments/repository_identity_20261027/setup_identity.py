"""Local Git housekeeping only. Never changes the original worktree or its HEAD."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ARCHIVE = ROOT / '.execution' / 'archive_main'
SOURCE = ROOT / '.execution' / 'lp1_runtime'
ARCHIVE_COMMIT = '84c41fca5b2576d121e67b9273b2b72ea2b53b7c'
SOURCE_COMMIT = '7c176556592c2a4fad436056b8b96be52cac9ea4'


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', '-C', str(cwd), *args], stderr=subprocess.PIPE).decode().strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = json.loads((OUT / 'BEFORE.json').read_text())
    assert git('rev-parse', 'HEAD') == before['head']
    assert git('rev-parse', 'origin/main') == ARCHIVE_COMMIT
    assert git('rev-parse', '--is-shallow-repository') == 'false'
    assert not ARCHIVE.exists() and not SOURCE.exists(), 'Never overwrite an existing checkout'
    for row in before['tracked_dirty']:
        assert digest(ROOT / row['path']) == row['sha256'], row['path']
    old_main = git('rev-parse', 'refs/heads/main')
    git('merge-base', '--is-ancestor', old_main, ARCHIVE_COMMIT)
    git('update-ref', 'refs/archive/revtrace/housekeeping-20261027/original-local-main', old_main)
    git('update-ref', 'refs/heads/main', ARCHIVE_COMMIT, old_main)
    # No core.worktree/core.bare migration is needed in this non-bare repository.
    assert not git('config', '--get-regexp', '^core\\.(bare|worktree)$').endswith('true')
    git('config', 'extensions.worktreeConfig', 'true')
    git('-c', 'core.autocrlf=false', '-c', 'core.longpaths=true',
        'worktree', 'add', str(ARCHIVE), 'main')
    git('config', '--worktree', 'core.autocrlf', 'false', cwd=ARCHIVE)
    git('config', '--worktree', 'core.longpaths', 'true', cwd=ARCHIVE)
    payload = ARCHIVE / 'experiments/legal_progress_20261026'
    releases = json.loads((payload / 'SOURCE_RELEASES.json').read_text())['releases']
    imported = []
    for row in releases:
        bundle = payload / 'frozen_sources' / (row['name'] + '.bundle')
        assert digest(bundle) == row['bundle_sha256'], row['name']
        heads = git('bundle', 'list-heads', str(bundle)).splitlines()
        assert heads and all(x.split()[0] == row['code_commit'] for x in heads), row['name']
        git('bundle', 'verify', str(bundle))
        git('bundle', 'unbundle', str(bundle))
        ref = 'refs/archive/revtrace/lp1/' + row['name']
        git('update-ref', ref, row['code_commit'])
        assert git('cat-file', '-t', row['code_commit']) == 'commit'
        imported.append(dict(name=row['name'], code_commit=row['code_commit'],
                             ref=ref, bundle_sha256=row['bundle_sha256']))
    baseline = ARCHIVE / 'experiments/composed_kernel_20261026/RUNTIME_CK5_v6.bundle'
    baseline_commit = 'b8aa802c687256d3801612dc8bee585ee849ddea'
    assert git('bundle', 'list-heads', str(baseline)).split()[0] == baseline_commit
    git('bundle', 'verify', str(baseline))
    git('bundle', 'unbundle', str(baseline))
    git('update-ref', 'refs/archive/revtrace/ck5/runtime-v6', baseline_commit)
    imported.append(dict(name='ck5-runtime-v6', code_commit=baseline_commit,
                         ref='refs/archive/revtrace/ck5/runtime-v6', bundle_sha256=digest(baseline)))
    git('-c', 'core.autocrlf=false', 'worktree', 'add', '-b', 'codex/lp1-next',
        str(SOURCE), SOURCE_COMMIT)
    git('config', '--worktree', 'core.autocrlf', 'false', cwd=SOURCE)
    git('config', '--worktree', 'core.longpaths', 'true', cwd=SOURCE)
    for row in before['tracked_dirty']:
        assert digest(ROOT / row['path']) == row['sha256'], row['path']
    assert git('rev-parse', 'HEAD') == before['head']
    record = dict(maintenance_id='REPO-IDENTITY-20261027', observed_unix=time.time(),
                  root=str(ROOT), preserved_root_head=before['head'], old_local_main=old_main,
                  archive_worktree=str(ARCHIVE), archive_commit=ARCHIVE_COMMIT,
                  source_worktree=str(SOURCE), source_commit=SOURCE_COMMIT,
                  source_manifest=str(payload / 'final_source_v2_SOURCE.json'),
                  imports=imported, gpu_runs_started=0, paper_edits=False)
    # Manifest packaging has an explicit name; never guess a fallback silently.
    assert Path(record['source_manifest']).is_file(), record['source_manifest']
    (OUT / 'SETUP.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
