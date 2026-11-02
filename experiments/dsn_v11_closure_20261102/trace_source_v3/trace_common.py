"""Pure-stdlib identity and bounded immutable-input gates for recorded CPU traces."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys

BASE = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
NN4F = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
NN_MANIFEST_SHA = '60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457'


class TraceError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise TraceError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def put(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def csvout(path, rows):
    with Path(path).open('x', encoding='utf8', newline='') as stream:
        if not rows:
            stream.write('no_rows\n')
            return
        keys = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                             if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})


def close(actual, expected, label):
    if type(expected) in (int, float) and type(actual) in (int, float):
        need(math.isfinite(actual) and math.isfinite(expected)
             and abs(actual - expected) <= 1e-7, label)
    else:
        need(actual == expected, label)


def disk(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve().is_relative_to(BASE.resolve()),
         'outside designated experiment disk: ' + str(path))
    need(not path.is_symlink(), 'symlink input/output forbidden')
    return path


def verify_tree(root, manifest, expected_commit, expected_manifest_sha, expected_files=None):
    root = disk(root).resolve()
    manifest = disk(manifest)
    need(sha(manifest) == expected_manifest_sha, 'source manifest SHA differs')
    obj = read(manifest)
    need(obj['source_commit'] == obj.get('code_commit', expected_commit) == expected_commit,
         'source manifest commit differs')

    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args],
                                       text=True, stderr=subprocess.PIPE).strip()

    need(Path(git('rev-parse', '--show-toplevel')).resolve() == root,
         'source must be an independent checkout')
    need(git('rev-parse', 'HEAD') == expected_commit
         and git('cat-file', '-t', expected_commit) == 'commit', 'full source commit differs')
    need(not git('status', '--porcelain', '--untracked-files=all'), 'source is dirty')
    items = obj['files']
    names = [item['path'] for item in items]
    need(len(names) == len(set(names)), 'duplicate source manifest path')
    need(set(git('ls-files', '-z').split('\0')) - {''} == set(names),
         'complete tracked source manifest differs')
    if expected_files is not None:
        need(len(items) == expected_files, 'complete dependency file count differs')
    for item in items:
        path = root / item['path']
        need(not path.is_symlink() and path.resolve().is_relative_to(root), 'source path escape')
        need(path.is_file() and path.stat().st_size == item['bytes']
             and sha(path) == item['sha256'], 'source bytes differ: ' + item['path'])
    return dict(source_root=str(root), source_commit=expected_commit,
                source_manifest=str(manifest), source_manifest_sha256=expected_manifest_sha,
                complete_files=len(items), clean=True)


def current_environment():
    return dict(python_executable=str(Path(sys.executable).resolve()), python_version=sys.version,
                platform=platform.platform(), CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
                PYTHONDONTWRITEBYTECODE=os.environ.get('PYTHONDONTWRITEBYTECODE'),
                dont_write_bytecode=sys.dont_write_bytecode, model_calls=0,
                analysis='pure stdlib; original feedback_contract and read-only resilience_storage scanner only')


def no_model_imports():
    forbidden = ('torch', 'transformers', 'numpy', 'soundfile', 'peft', 'native_service',
                 'native_bridge', 'candidate_bridge', 'stage_worker')
    need(not any(name == prefix or name.startswith(prefix + '.')
                 for name in sys.modules for prefix in forbidden), 'model/runtime module imported')


class Inputs:
    def __init__(self, items, max_bytes):
        self.items = {str(disk(item['path']).resolve()): item for item in items}
        need(len(self.items) == len(items), 'duplicate frozen input path')
        need(all(type(item['bytes']) is int and item['bytes'] >= 0 for item in items), 'bad input size')
        need(sum(item['bytes'] for item in items) <= max_bytes, 'input byte budget exceeded')
        self.accessed = set()

    def path(self, path):
        path = disk(path).resolve()
        need(str(path) in self.items, 'unlisted raw input access: ' + str(path))
        self.accessed.add(str(path))
        return path

    def json(self, path):
        return read(self.path(path))

    def lines(self, path):
        return [json.loads(line) for line in self.path(path).read_bytes().splitlines() if line.strip()]

    def verify(self):
        result = {}
        for name, item in sorted(self.items.items()):
            path = disk(name)
            need(path.is_file() and path.stat().st_size == item['bytes'], 'input size/missing: ' + name)
            actual = sha(path)
            need(actual == item['sha256'], 'immutable input SHA differs: ' + name)
            result[name] = dict(bytes=item['bytes'], sha256=actual)
        return result
