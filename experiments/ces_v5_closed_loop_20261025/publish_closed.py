"""Publish only the completed bounded closed-loop prefix, never root edits.

No action at import. Default invocation verifies the local delivery only;
--publish is required for native Git network/write operations. Existing prior
blobs are byte-addressed and preserved; changed remote base stops publication.
No force push or root-worktree staging is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from make_delivery import (STATUS, STUDY, RUNTIME, MAX_FILE, sha, read,
                           verify_manifest, scan_package)


BASE = 'd0529564935b4a045960645d3a00a2740c4bbaf4'
PREFIX = 'experiments/ces_v5_closed_loop_20261025/'
REPOSITORY = 'zhouz4884-coder/RevTrace'


def save_new(path, value):
    if path.exists():
        raise FileExistsError('Publication record already exists; do not overwrite history: '+str(path))
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')


def blob_oid(path):
    size = path.stat().st_size
    digest = hashlib.sha1(b'blob '+str(size).encode()+b'\0')
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


class NativeGit:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
        for name in ('GIT_TRACE', 'GIT_CURL_VERBOSE', 'GIT_TRACE_CURL', 'GIT_TRACE_PACKET'):
            self.env.pop(name, None)

    def __call__(self, *args, input=None):
        command = ['git', '-c', 'credential.helper=manager', '-c', 'http.version=HTTP/1.1',
                   '-C', str(self.directory), *args]
        result = subprocess.run(command, input=input, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=self.env, timeout=300)
        if result.returncode:
            # Never print HTTP/GCM credential-bearing diagnostics. Preserve a
            # bounded non-secret operation identity, not argv containing data.
            raise RuntimeError('Native Git operation failed; no force/retry performed: '+str(args[0]))
        return result.stdout


def tree(git, ref):
    result = {}
    for item in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        if kind != 'blob':
            raise AssertionError('Prior gitlinks/special tree entries require an explicit separate workflow')
        result[name.decode('utf8')] = (mode, oid)
    return result


def index_tree(git):
    result = {}
    for item in git('ls-files', '--stage', '-z').split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        assert stage == '0', 'Unmerged staged entry'
        result[name.decode('utf8')] = (mode, oid)
    return result


def check_additive(old, new, files):
    assert all(new.get(path) == value for path, value in old.items()), 'A prior blob was changed or removed'
    assert set(new)-set(old) == {PREFIX+name for name in files}, 'Publication escaped the new artifact prefix'
    for relative, path in files.items():
        assert new[PREFIX+relative] == ('100644', blob_oid(path)), 'Git normalization or blob mismatch: '+relative


def verify_delivery(directory):
    manifest = verify_manifest(directory)
    assert manifest['status'] == STATUS and manifest['experiment_id'] == STUDY
    assert manifest['runtime_commit'] == RUNTIME and manifest['runtime_tracked_files_byte_verified'] == 140
    source = read(directory/'runtime/SOURCE_MANIFEST.json')
    assert source['code_commit'] == RUNTIME and len(source['files']) == 140
    assert sha(directory/'runtime/SOURCE_MANIFEST.json') == manifest['runtime_manifest_sha256']
    assert read(directory/'PLAN.formal.json')['runtime_manifest_sha256'] == manifest['runtime_manifest_sha256']
    for row in source['files']:
        path = directory/'runtime'/row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    assert (manifest['formal_cells'], manifest['smoke_cells'], manifest['oracle_cells']) == (72, 4, 2)
    assert manifest['GPU_queue_closed'] and manifest['all_this_task_workers_released']
    assert manifest['manuscript_edits'] is False and manifest['independent_confirmation'] is False
    assert (directory/'.gitattributes').read_bytes() == b'* -text\n'
    assert all(row['bytes'] < MAX_FILE for row in manifest['files'])
    scan = scan_package(directory)
    return manifest, scan


def remote_head(git):
    rows = git('ls-remote', 'origin', 'refs/heads/main').decode().splitlines()
    assert len(rows) == 1
    return rows[0].split()[0]


def origin_identity(git):
    origin = git('remote', 'get-url', 'origin').decode().strip()
    assert '@' not in origin or origin.startswith('git@github.com:'), 'Credential-bearing remote URL is forbidden'
    accepted = {'https://github.com/'+REPOSITORY, 'https://github.com/'+REPOSITORY+'.git',
                'git@github.com:'+REPOSITORY, 'git@github.com:'+REPOSITORY+'.git'}
    assert origin in accepted, 'Wrong publication repository'


def publish(stage, directory, git_directory, *, resume=False):
    stage, directory = Path(stage).resolve(), Path(directory).resolve()
    manifest, scan = verify_delivery(directory)
    files = {p.relative_to(directory).as_posix(): p for p in directory.rglob('*') if p.is_file()}
    git = NativeGit(git_directory)
    origin_identity(git)
    base = BASE
    old = tree(git, base)
    assert not any(path.startswith(PREFIX) for path in old), 'Prior archive prefix already exists'
    record_path = stage/'GITHUB_PREPUSH_CLOSED.json'
    if resume:
        record = read(record_path)
        assert record['base'] == base and record['manifest_sha256'] == sha(directory/'MANIFEST.json')
        commit = record['commit']
        assert git('rev-parse', commit+'^').decode().strip() == base
        check_additive(old, tree(git, commit), files)
        current = remote_head(git)
        assert current in (base, commit), 'Remote changed; preserve other work and stop'
    else:
        assert not record_path.exists(), 'Use explicit --resume-push for the exact prepared commit'
        assert remote_head(git) == base, 'Remote changed from expected base; stop without force'
        assert git('rev-parse', 'HEAD').decode().strip() == base, 'Delivery clone HEAD changed'
        assert git('symbolic-ref', '--quiet', 'HEAD').decode().strip() == 'refs/heads/main'
        assert not git('diff', '--cached', '--name-only').strip(), 'Delivery clone has existing staged changes'
        target = Path(git_directory).resolve()/PREFIX
        assert not target.exists(), 'Do not overwrite a previous/partial staged delivery'
        shutil.copytree(directory, target)
        # read-tree without -u changes only this dedicated delivery index; the
        # user's dirty root and intentionally missing partial-checkout files
        # are not reset, checked out, moved or deleted.
        git('read-tree', base)
        git('add', '--force', '--', PREFIX)
        check_additive(old, index_tree(git), files)
        new_tree = git('write-tree', '--missing-ok').decode().strip()
        commit = git('-c', 'user.name=Research Artifact', '-c', 'user.email=artifact@invalid.example',
            'commit-tree', new_tree, '-p', base,
            input=b'Archive frozen closed-loop CES source, all 72 formal cells, smoke/oracles and independent audits\n').decode().strip()
        assert remote_head(git) == base, 'Remote advanced during preparation; do not overwrite it'
        record = {'base': base, 'commit': commit, 'tree': new_tree, 'repository': REPOSITORY,
            'prefix': PREFIX, 'new_files': len(files), 'prior_blobs_preserved': len(old),
            'manifest_sha256': sha(directory/'MANIFEST.json'), 'time_unix': time.time(),
            'secret_scan': scan['status'], 'scope': 'Additive bounded research artifact only; no manuscript edits'}
        save_new(record_path, record)
        current = base
    if current == base:
        # A normal push rejects a concurrent divergent update. No force or
        # automatic rebase may turn somebody else's newer work into our base.
        git('-c', 'http.postBuffer=524288000', '-c', 'http.lowSpeedLimit=0',
            'push', 'origin', commit+':refs/heads/main')
    assert remote_head(git) == commit, 'Fresh remote ref differs; publication is not verified'
    actual_tree = tree(git, commit)
    check_additive(old, actual_tree, files)
    assert git('rev-parse', commit+'^').decode().strip() == base
    # Keep the dedicated clone coherent only after remote/content verification.
    if git('rev-parse', 'HEAD').decode().strip() == base:
        git('update-ref', 'refs/heads/main', commit, base)
    record.update(status='REMOTE_REF_AND_ADDITIVE_CONTENT_ADDRESSED_TREE_VERIFIED',
        verified_remote_ref=True, exact_new_blob_hashes=len(files), all_prior_blobs_preserved=len(old),
        verification_route='Fresh native Git remote ref, exact content-addressed commit/tree and all new blob OIDs',
        verification_limit='Not a claim that every remote blob was separately downloaded or that the anonymous mirror updated')
    save_new(stage/'FINAL_DELIVERY_VERIFIED_CLOSED.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--delivery', type=Path)
    parser.add_argument('--git-directory', type=Path)
    parser.add_argument('--publish', action='store_true', help='Explicitly authorize actual Git write/push for this invocation')
    parser.add_argument('--resume-push', action='store_true', help='Retry/verify only the exact saved prepared commit')
    args = parser.parse_args()
    directory = args.delivery or args.stage/'delivery'
    if not args.publish:
        manifest, scan = verify_delivery(directory)
        print(json.dumps({'status': 'PASS_LOCAL_DELIVERY_ONLY_NO_GIT_WRITE_OR_NETWORK',
            'manifest_sha256': sha(directory/'MANIFEST.json'), 'files': len(manifest['files'])+1,
            'secret_scan': scan['status']}))
        return
    clone = args.git_directory or args.stage.parent/'online_admission_20261022/git_delivery_stage_v1'
    print(json.dumps(publish(args.stage, directory, clone, resume=args.resume_push), indent=2))


if __name__ == '__main__':
    main()
