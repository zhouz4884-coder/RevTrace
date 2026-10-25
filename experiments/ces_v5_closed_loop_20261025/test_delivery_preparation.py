"""Synthetic CPU safety controls; never packs real evidence or contacts GitHub."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile

import pytest

from make_delivery import (banned_path, confined, scan_plain, scan_tar,
    scan_package, ConcatenatedReader, verify_manifest)
from publish_closed import check_additive, PREFIX, blob_oid


def test_no_audio_weights_repository_metadata_or_temporary_payload():
    for path in ('runtime/.git/config', 'operations/command.json', 'tmp_fixture/a.json',
                 'model.safetensors', 'speech.wav', 'cache.npy', 'remote_ops.py'):
        assert banned_path(path)
    for path in ('runtime/.gitignore', 'runtime/src/revtrace/dgft.py', 'evidence/RAW_INDEX.json'):
        assert not banned_path(path)


def test_confined_path_cannot_escape_delivery(tmp_path):
    for relative in ('../outside', '/absolute', 'C:/outside', 'a/../../outside'):
        with pytest.raises(ValueError):
            confined(tmp_path, relative)


def test_secret_value_is_not_echoed_in_failure():
    fake = b'ghp_'+b'a'*32
    with pytest.raises(ValueError) as error:
        scan_plain(io.BytesIO(fake), 'synthetic-memory')
    assert fake.decode() not in str(error.value)
    route = b'contractkv_ssh_'+b'credential.py'
    with pytest.raises(ValueError):
        scan_plain(io.BytesIO(route), 'synthetic-route')


def test_gzip_logical_parts_are_reassembled_before_secret_scan(tmp_path):
    # Deliberately fake pattern; never an actual GitHub credential.
    plain = b'CPU fixture '+b'ghp_'+b'a'*32
    packed = gzip.compress(plain, mtime=0)
    split = len(packed)//2
    for name, data in (('part1', packed[:split]), ('part2', packed[split:])):
        (tmp_path/name).write_bytes(data)
    (tmp_path/'LOGICAL_PAYLOADS.json').write_text(json.dumps({'files': [{
        'logical_path': 'synthetic.json.gz', 'representation': 'gzip',
        'payload_bytes': len(packed), 'payload_sha256': hashlib.sha256(packed).hexdigest(),
        'parts': ['part1', 'part2']}]}), encoding='utf8')
    with pytest.raises(ValueError, match='Recognized secret'):
        scan_package(tmp_path)


def test_concatenated_reader_preserves_order_without_materializing_large_file(tmp_path):
    (tmp_path/'one').write_bytes(b'first')
    (tmp_path/'two').write_bytes(b'second')
    with io.BufferedReader(ConcatenatedReader([tmp_path/'one', tmp_path/'two'])) as reader:
        assert reader.read(7) == b'firstse'
        assert reader.read() == b'cond'


def test_tar_members_are_checked_not_just_compressed_wrapper():
    stream = io.BytesIO()
    data = b'CPU fixture '+b'hf_'+b'b'*28
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        info = tarfile.TarInfo('fixture.txt'); info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    stream.seek(0)
    with pytest.raises(ValueError, match='Recognized secret'):
        scan_tar(stream, 'synthetic.tar.gz')


def test_tar_does_not_publish_symlinks_or_model_weights():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        info = tarfile.TarInfo('link'); info.type = tarfile.SYMTYPE; info.linkname = 'outside'
        archive.addfile(info)
    stream.seek(0)
    with pytest.raises(ValueError, match='Forbidden archive member'):
        scan_tar(stream, 'synthetic.tar.gz')


def test_manifest_checks_extra_unindexed_files_and_bytes(tmp_path):
    path = tmp_path/'safe.txt'; path.write_bytes(b'safe')
    manifest = {'files': [{'path': 'safe.txt', 'bytes': 4,
        'sha256': hashlib.sha256(b'safe').hexdigest()}]}
    (tmp_path/'MANIFEST.json').write_text(json.dumps(manifest), encoding='utf8')
    verify_manifest(tmp_path)
    (tmp_path/'unexpected.txt').write_bytes(b'not indexed')
    with pytest.raises(AssertionError):
        verify_manifest(tmp_path)


def test_additive_tree_requires_every_old_blob_and_exact_new_byte_oid(tmp_path):
    path = tmp_path/'new.txt'; path.write_bytes(b'new artifact\n')
    old = {'old/file.txt': ('100644', 'a'*40)}
    current = {**old, PREFIX+'new.txt': ('100644', blob_oid(path))}
    check_additive(old, current, {'new.txt': path})
    bad = dict(current); bad['old/file.txt'] = ('100644', 'b'*40)
    with pytest.raises(AssertionError):
        check_additive(old, bad, {'new.txt': path})
    bad = dict(current); bad['unrelated.txt'] = ('100644', 'c'*40)
    with pytest.raises(AssertionError):
        check_additive(old, bad, {'new.txt': path})


def test_blob_oid_uses_raw_bytes_not_newline_normalization(tmp_path):
    path = tmp_path/'windows.txt'; path.write_bytes(b'one\r\ntwo\r\n')
    normalized = b'one\ntwo\n'
    wrong = hashlib.sha1(b'blob '+str(len(normalized)).encode()+b'\0'+normalized).hexdigest()
    assert blob_oid(path) != wrong
