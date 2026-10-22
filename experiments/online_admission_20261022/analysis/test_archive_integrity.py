"""CPU-only file-safety tests, not study measurements."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import pytest
from archive_integrity import safe_extract, verify_manifest


def make_archive(path, entries):
    with tarfile.open(path, 'w:gz') as f:
        for name, raw, kind in entries:
            t = tarfile.TarInfo(name); t.size = len(raw)
            if kind == 'symlink': t.type = tarfile.SYMTYPE; t.linkname = '../outside'
            f.addfile(t, io.BytesIO(raw))


def test_exact_bytes_and_manifest(tmp_path):
    raw = b'a\r\nb\n'; item = {'path': 'collected/value.csv', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    mf = json.dumps({'files': [item]}).encode()
    archive = tmp_path / 'a.tar.gz'; make_archive(archive, [(item['path'], raw, 'file'), ('MANIFEST.json', mf, 'file')])
    out = tmp_path / 'out'; safe_extract(archive, out)
    assert verify_manifest(out)['files'] == 1
    assert (out / item['path']).read_bytes() == raw


@pytest.mark.parametrize('bad', ['../escape.txt', '/escape.txt', 'C:/escape.txt', 'a\\..\\escape.txt', 'a:stream', 'NUL.txt'])
def test_unsafe_member_rejects_before_any_write(tmp_path, bad):
    archive = tmp_path / 'bad.tar.gz'; make_archive(archive, [('good.txt', b'x', 'file'), (bad, b'x', 'file')])
    out = tmp_path / 'out'
    with pytest.raises(AssertionError): safe_extract(archive, out)
    assert not out.exists()


def test_link_and_case_collision_are_rejected(tmp_path):
    for i, entries in enumerate([[('link', b'', 'symlink')], [('A.txt', b'x', 'file'), ('a.txt', b'y', 'file')]]):
        archive = tmp_path / f'bad{i}.tar.gz'; make_archive(archive, entries)
        with pytest.raises(AssertionError): safe_extract(archive, tmp_path / f'out{i}')


def test_decompression_limit_and_no_overwrite(tmp_path):
    archive = tmp_path / 'big.tar.gz'; make_archive(archive, [('v', b'1234', 'file')])
    with pytest.raises(AssertionError): safe_extract(archive, tmp_path / 'too_big', max_bytes=3)
    destination = tmp_path / 'existing'; destination.mkdir()
    with pytest.raises(AssertionError): safe_extract(archive, destination)
