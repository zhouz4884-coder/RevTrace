"""Frozen controller identities and bounded independent evidence primitives."""
from __future__ import annotations
import copy, hashlib, json, os, pathlib, re, subprocess, sys

B = '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
OLD = 'bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
FINAL = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
RUNTIME = {'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True'}

class GateError(RuntimeError): pass
def need(ok, message):
    if not ok: raise GateError(message)
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
def read(path): return json.loads(pathlib.Path(path).read_bytes())
def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()
def put(path, value, *, replace=False):
    path = pathlib.Path(path)
    with path.open('w' if replace else 'x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
def lines(path):
    path = pathlib.Path(path)
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()] if path.exists() else []
def git(root, *args): return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()
def verify_checkout(root, manifest, commit=None):
    root = pathlib.Path(root).resolve(strict=True); manifest = pathlib.Path(manifest).resolve(strict=True); data = read(manifest)
    actual = data.get('source_commit', data.get('code_commit')); need(re.fullmatch('[0-9a-f]{40}', actual or ''), 'full source commit required')
    if 'code_commit' in data: need(data['code_commit'] == actual, 'manifest aliases disagree')
    if commit is not None: need(actual == commit, 'wrong dependency commit')
    need(pathlib.Path(git(root, 'rev-parse', '--show-toplevel')).resolve() == root, 'not an independent execution source')
    need(git(root, 'cat-file', '-t', actual) == 'commit' and git(root, 'rev-parse', 'HEAD') == actual, 'actual full source commit not resolved at HEAD')
    need(git(root, 'config', '--get', 'core.autocrlf') == 'false', 'byte-exact checkout requires autocrlf=false')
    need(not git(root, 'status', '--porcelain', '--untracked-files=all'), 'dirty execution source')
    tracked = set(git(root, 'ls-files', '-z').split('\0')) - {''}; rows = data['files']; expected = {row['path'] for row in rows}
    need(len(expected) == len(rows) and tracked == expected, 'complete manifest file set differs')
    for row in rows:
        path = root / row['path']; need(not path.is_symlink() and path.resolve().is_relative_to(root), 'source path escapes checkout')
        need(path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'source bytes differ: ' + row['path'])
    return dict(source_commit=actual, source_root=str(root), source_manifest=str(manifest), source_manifest_sha256=sha(manifest), files_verified=len(rows), clean=True)
def disk_path(path):
    p = pathlib.Path(path); base = pathlib.Path(B)
    need(p.is_absolute() and p.resolve().is_relative_to(base.resolve()), 'path outside designated 8TB experiment disk: ' + str(path))
    return p
def child_environment(plan):
    need(plan['runtime_environment'] == RUNTIME, 'unfrozen allocator condition')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    env.pop('PYTORCH_ALLOC_CONF', None); env.pop('CUDA_VISIBLE_DEVICES', None); env.update(RUNTIME)
    return env
def mapped_state(state, actual):
    result = copy.deepcopy(state); marker = result['contract']['stage_execution']['source_commit']
    need(marker in (OLD, actual), 'unknown source marker cannot be projected')
    result['contract']['stage_execution']['source_commit'] = OLD
    return result
def verified_facts(path):
    """Independent strict binary chain reader, no neural/runtime import."""
    import struct
    previous = '0' * 64; sequence = 0
    with pathlib.Path(path).open('rb') as stream:
        while True:
            header = stream.read(8)
            if not header: return
            need(len(header) == 8 and header[:4] == b'RVN1', 'torn/corrupt fact header')
            size = struct.unpack('>I', header[4:])[0]; need(size <= 16 * 1024 * 1024, 'oversize fact')
            payload = stream.read(size); digest = stream.read(32)
            need(len(payload) == size and len(digest) == 32 and hashlib.sha256(payload).digest() == digest, 'torn/corrupt complete fact')
            obj = json.loads(payload); need(canonical(obj) == payload, 'noncanonical fact encoding')
            need(obj['sequence'] == sequence + 1 and obj['previous'] == previous, 'fact chain gap')
            sequence += 1; previous = digest.hex(); yield obj
def root_preflight_receipt(path, digest, controller_commit, controller_manifest_sha):
    need(sha(path) == digest, 'root no-argument preflight receipt changed')
    data = read(path); need(data['gate'] == 'SOURCE_IDENTITY_PASS', 'root source gate did not pass')
    need(data['code_commit'] == controller_commit and data['manifest_sha256'] == controller_manifest_sha, 'CURRENT did not identify this controller')
    need('setup_pointer_sha256' in data and data['setup_pointer'].replace('\\','/').split('/')[-1] == 'CURRENT.json', 'no CURRENT no-argument receipt')
    return data
