"""Fail-closed local source identity check; does not launch a model or certify a run."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(cwd, *args):
    return subprocess.check_output(['git', '-C', str(cwd), *args], stderr=subprocess.PIPE).decode().strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(source, manifest_path, run_record=None):
    source = source.resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    commit = manifest['code_commit']
    require(re.fullmatch('[0-9a-f]{40}', commit), 'Require a full commit ID')
    require(git(ROOT, 'cat-file', '-t', commit) == 'commit', 'Missing source commit')
    require(git(source, 'rev-parse', '--show-toplevel').replace('\\', '/').lower() == source.as_posix().lower(), 'Not a separate worktree root')
    require(git(source, 'rev-parse', 'HEAD') == commit, 'HEAD is not the manifest code_commit')
    require(git(source, 'config', '--get', 'core.autocrlf') == 'false', 'Byte-exact checkout required')
    require(not git(source, 'status', '--porcelain', '--untracked-files=all'), 'Dirty source worktree')
    tracked = set(git(source, 'ls-files').splitlines())
    rows = manifest['files']
    expected = {row['path'] for row in rows}
    require(len(expected) == len(rows) and expected == tracked, 'Manifest and tracked file sets differ')
    for row in rows:
        path = source / row['path']
        require(not path.is_symlink() and path.resolve().is_relative_to(source), row['path'])
        require(path.is_file() and path.stat().st_size == row['bytes'], row['path'])
        require(sha256(path) == row['sha256'], row['path'])
    record_checked = False
    if run_record is not None:
        record = json.loads(run_record.read_text(encoding='utf-8'))
        required = ['experiment_id', 'code_commit', 'frozen_config', 'environment_record',
                    'raw_result_location', 'aggregate_summary_location', 'gate_decision_location']
        for key in required:
            require(isinstance(record.get(key), str) and record[key].strip(), 'Missing run field: ' + key)
        require(record['code_commit'] == commit, 'Run record code_commit mismatch')
        for key in ['frozen_config', 'environment_record']:
            path = Path(record[key])
            require(path.is_file(), 'Missing frozen input: ' + key)
            require(record.get(key + '_sha256') == sha256(path), 'Input hash mismatch: ' + key)
        require(record['raw_result_location'].startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/'), 'Raw results must target the designated experiment disk')
        record_checked = True
    return dict(gate='SOURCE_IDENTITY_PASS', source=str(source), code_commit=commit,
                source_manifest=str(manifest_path), manifest_sha256=sha256(manifest_path),
                files_verified=len(rows), run_record_prelaunch_checked=record_checked,
                scope='CPU/local provenance only; not GPU evidence or a completed experiment gate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--run-record', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        setup = json.loads((HERE / 'SETUP.json').read_text())
        result = check(args.source or Path(setup['source_worktree']),
                       args.manifest or Path(setup['source_manifest']), args.run_record)
    except (AssertionError, KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps(dict(gate='NO_GO_SOURCE_IDENTITY', error=str(exc)), ensure_ascii=False))
        return 1
    if args.output:
        # Do not contaminate the checked source or overwrite an evidence input.
        output = args.output.resolve()
        require(not output.is_relative_to(Path(result['source'])), 'Write reports outside frozen source')
        require(not output.exists(), 'Never replace an existing gate result')
        output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
