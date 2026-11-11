"""Reference-only experiment identity and immutable input helpers; stdlib."""
from __future__ import annotations
import hashlib, json, pathlib, re, subprocess

NN4F = '14ae77ee2f1f0c324be3f40b89fb6011972c35b9'
PARENT_RUNTIME = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
B = pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
SELECTION_STATUS = 'PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE'
SUCCESS = 'PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
SPLIT_NAMESPACE = 'AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96'
SPLIT_DIRECTORY = 'StreamCorrect/aishell1_testset'

class ReferenceError(RuntimeError): pass

def need(value, message):
    if not value: raise ReferenceError(message)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()

def read(path): return json.loads(pathlib.Path(path).read_bytes())

def put(path, value, *, replace=False):
    with pathlib.Path(path).open('w' if replace else 'x', encoding='utf8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')

def inventory(paths):
    return {str(pathlib.Path(p)): dict(bytes=pathlib.Path(p).stat().st_size, sha256=sha(p))
            for p in sorted(set(map(str, paths)))}

def verify_inventory(records):
    need(inventory(records) == records, 'frozen reference dependency bytes changed')

def disk(path):
    path = pathlib.Path(path)
    need(path.is_absolute() and path.resolve().is_relative_to(B.resolve()), 'reference path outside designated 8TB')
    return path

def verify_source(root, manifest, expected=None):
    root = pathlib.Path(root).resolve(strict=True); m = read(manifest)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()
    commit = m.get('source_commit', m.get('code_commit'))
    need(isinstance(commit, str) and re.fullmatch('[0-9a-f]{40}', commit) and
         (expected is None or commit == expected), 'wrong complete source identity')
    need(pathlib.Path(git('rev-parse', '--show-toplevel')).resolve() == root and
         git('rev-parse', 'HEAD') == commit and git('cat-file', '-t', commit) == 'commit', 'unresolved source checkout')
    need(git('config', '--get', 'core.autocrlf') == 'false' and
         not git('status', '--porcelain', '--untracked-files=all'), 'dirty source or line conversion enabled')
    tracked = set(git('ls-files', '-z').split('\0'))-{''}
    need(len(m['files']) == len({r['path'] for r in m['files']}) and
         tracked == {r['path'] for r in m['files']}, 'incomplete source manifest')
    for row in m['files']:
        p = root/row['path']
        need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root) and
             p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], 'source byte mismatch: '+row['path'])
    return dict(source_commit=commit, source_root=str(root),source_manifest=str(pathlib.Path(manifest).resolve()), manifest_sha256=sha(manifest),source_manifest_sha256=sha(manifest),complete_files=len(tracked),clean=True)

def sources_from_receipt(receipt):
    need(receipt['status'] == SELECTION_STATUS, 'metadata/audio selection receipt not terminal')
    need(receipt.get('metadata_first') is True and type(receipt.get('model_calls')) is int
         and receipt['model_calls'] == 0,
         'selection must precede every model call; missing is not zero')
    need(all(receipt.get(k) is True for k in ('no_concat', 'no_trim', 'no_resample')),
         'whole-utterance selection contract changed')
    sources = receipt['sources']; need(bool(sources), 'no frozen independent sources')
    need(len({s['source_id'] for s in sources}) == len(sources) ==
         len({s['speaker_id'] for s in sources}), 'duplicate source or speaker')
    for source in sources:
        need(re.fullmatch('[A-Za-z0-9_-]+', source['source_id']) is not None, 'unsafe source ID')
        need(source.get('original_split') == SPLIT_NAMESPACE, 'exact original split namespace/revision changed')
        need(source.get('split_directory') == SPLIT_DIRECTORY, 'original split directory changed')
        need(source.get('archive_member', {}).get('path') == SPLIT_DIRECTORY+'/'+source['source_id']+'.wav',
             'original archive member directory/source identity changed')
        need(type(source['frames']) is int and 96000 <= source['frames'] <= 320000,
             'source outside frozen complete 6--20s scope')
        need(abs(source['duration']-source['frames']/16000) < 1e-9 and
             isinstance(source['reference'], str), 'source duration/reference metadata changed')
        need(re.fullmatch('[0-9a-f]{64}', source['audio_sha256']) is not None,
             'actual full-WAV hash required')
        header = source['header']
        need(header['sample_rate'] == 16000 and header['channels'] == 1 and
             header['sample_width'] == 2 and header['frames'] == source['frames'] and
             re.fullmatch('[0-9a-f]{64}', header['PCM_sha256']) is not None,
             'actual original PCM/header receipt required')
    return sources

def expected_frontiers(frames):
    need(type(frames) is int and frames > 0, 'positive integer source frames required')
    return list(range(8000, frames, 8000))+[frames]
