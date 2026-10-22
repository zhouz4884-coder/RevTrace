"""Bounded, byte-exact extraction for the task's own measured-evidence archive."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import tarfile


def sha256(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def safe_extract(archive, destination, *, max_bytes=125_000_000, max_files=5000):
    destination = Path(destination).resolve()
    assert not destination.exists(), 'Do not overwrite prior evidence'
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ['COM', 'LPT'] for i in range(1, 10)}
    with tarfile.open(archive, 'r:gz') as tf:
        members = tf.getmembers(); assert len(members) <= max_files
        total = 0; seen = set(); checked = []
        for m in members:
            assert m.isfile(), 'Only regular files are admitted into the evidence copy'
            name = m.name; rel = PurePosixPath(name)
            assert name and not rel.is_absolute() and '\\' not in name and ':' not in name
            assert all(p not in ['.', '..', ''] for p in rel.parts)
            assert all(p.split('.')[0].upper() not in reserved for p in rel.parts)
            assert all(p == p.rstrip(' .') for p in rel.parts)
            target = destination.joinpath(*rel.parts).resolve(); assert target.is_relative_to(destination)
            assert str(target).casefold() not in seen, 'Windows-equivalent duplicate archive path'
            seen.add(str(target).casefold()); total += m.size
            assert total <= max_bytes, 'Refuse unbounded decompression'
            checked.append((m, target))
        # Validate every member before writing any of them.
        destination.mkdir(parents=True)
        for m, target in checked:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(m) as source, target.open('xb') as out: shutil.copyfileobj(source, out)
    return {'regular_files': len(checked), 'bytes': total, 'overwritten_files': 0}


def verify_manifest(root):
    root = Path(root); data = json.loads((root / 'MANIFEST.json').read_text())
    expected = {}
    for r in data['files']:
        rel = PurePosixPath(r['path']); path = root.joinpath(*rel.parts)
        assert not rel.is_absolute() and '..' not in rel.parts and path.resolve().is_relative_to(root.resolve())
        assert r['path'] not in expected
        assert path.is_file() and path.stat().st_size == r['bytes'] and sha256(path) == r['sha256']
        expected[r['path']] = r['sha256']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual == set(expected) | {'MANIFEST.json'}, 'Unmanifested or missing evidence file'
    return {'status': 'PASS_EXACT_LOCAL_ARCHIVE_MANIFEST', 'files': len(expected),
            'manifest_sha256': sha256(root / 'MANIFEST.json'), 'all_payload_bytes_verified': True}
