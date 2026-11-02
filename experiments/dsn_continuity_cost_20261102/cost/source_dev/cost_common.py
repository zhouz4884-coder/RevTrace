"""Source identity and immutable data helpers; never initialize a model."""
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import sys

NN4F = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf8'))

def jsonl(path):
    with pathlib.Path(path).open(encoding='utf8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def put(path, value):
    pathlib.Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def bind_base(root, manifest, require_clean=True):
    root, manifest = pathlib.Path(root).resolve(), pathlib.Path(manifest).resolve()
    m = read(manifest)
    if m['source_commit'] != NN4F:
        raise ValueError('cost study requires the actual original NN4f source')
    for row in m['files']:
        p = root/row['path']
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise ValueError('NN4f dependency bytes changed: '+row['path'])
    if require_clean:
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
        if git('rev-parse', 'HEAD') != NN4F or git('status', '--porcelain', '--untracked-files=all'):
            raise ValueError('NN4f original execution checkout must stay clean')
        if set(git('ls-files', '-z').split('\x00'))-{''} != {x['path'] for x in m['files']}:
            raise ValueError('NN4f complete tracked file set mismatch')
    sys.path.insert(0, str(root))
    return dict(actual_nn_source=NN4F, base_source=str(root), manifest_sha256=sha(manifest),
                complete_files=len(m['files']), clean_checkout_checked=require_clean)

def verify_observer(manifest, expected=None):
    root=pathlib.Path(__file__).resolve().parent
    manifest=pathlib.Path(manifest).resolve();m=read(manifest)
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    if pathlib.Path(git('rev-parse','--show-toplevel')).resolve()!=root:
        raise ValueError('observer must run from its own frozen execution checkout')
    commit=git('rev-parse','HEAD')
    if commit!=m['source_commit'] or (expected is not None and commit!=expected):
        raise ValueError('observer actual source commit differs')
    if git('status','--porcelain','--untracked-files=all'):
        raise ValueError('observer execution source is dirty')
    if set(git('ls-files','-z').split('\x00'))-{''}!={r['path'] for r in m['files']}:
        raise ValueError('observer complete tracked manifest differs')
    for row in m['files']:
        path=root/row['path']
        if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
            raise ValueError('observer source bytes differ: '+row['path'])
    return dict(observer_source_commit=commit,observer_manifest_sha256=sha(manifest),
                observer_complete_files=len(m['files']),observer_clean=True)

