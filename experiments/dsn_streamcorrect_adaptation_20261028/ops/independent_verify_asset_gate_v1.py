"""Verify the completed SC asset gate without launching or changing remote files.

Large-file digests come from the acquisition worker's complete streamed hashes.
This independent check compares those digests with the frozen plan and checks
current sizes/read-only modes. It rehashes bounded metadata and ZIP members.
"""
import datetime
import hashlib
import json
import pathlib
import shlex
import sys

T = pathlib.Path(__file__).resolve().parents[1]
plan_path = T / 'download_plan_v1/PLAN.json'
payload = dict(plan=json.loads(plan_path.read_text()),
               plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest())
REMOTE = r'''
import datetime, hashlib, json, pathlib, sys, zlib
payload = json.load(sys.stdin)
plan = payload['plan']
B = pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O = B / 'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
manifest = json.loads((O / 'ASSET_MANIFEST.json').read_text())
gate = json.loads((O / 'GATE.json').read_text())
launches = [json.loads(p.read_text()) for p in O.glob('DETACHED_LAUNCH_HANDLE_attempt*.json')]
matches = [row for row in launches if row.get('pid') == manifest['pid'] and row.get('start_ticks') == manifest['start_ticks']]
assert len(matches) == 1, 'final manifest must match one preserved detached launch handle'
launch = matches[0]
assert manifest['status'] == gate['status'] == 'PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
assert manifest['plan_sha256'] == payload['plan_sha256']
assert manifest['pid'] == launch['pid'] and manifest['start_ticks'] == launch['start_ticks']
assert manifest['gpu_launched'] is False
rows = manifest['files']
by_path = {row['path']: row for row in rows}
assert len(rows) == len(by_path), 'duplicate manifest rows'
expected = {row['path'] for row in plan['files'] + plan['range_files']}
asr = plan['model_root'] + '/asr/large-v2-zh.pt'
expected.add(asr)
assert set(by_path) == expected and gate['files'] == len(expected), 'incomplete coverage'
checks = []
for row in plan['files']:
    p = pathlib.Path(row['path']); m = by_path[str(p)]; st = p.stat()
    assert st.st_size == row['bytes'] == m['bytes'] and st.st_mode & 0o222 == 0
    if row.get('sha256'):
        assert m['sha256'] == row['sha256'], 'streamed large SHA differs from plan'
    if row['bytes'] <= 100000:
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == m['sha256']
        if row.get('git_blob_sha1'):
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob_sha1']
    checks.append(dict(path=str(p), bytes=st.st_size, sha256=m['sha256'],
        verification='independent_small_rehash' if row['bytes'] <= 100000 else 'streamed_worker_sha_plan_match_and_current_readonly_size'))
for row in plan['range_files']:
    p = pathlib.Path(row['path']); m = by_path[str(p)]; data = p.read_bytes(); st = p.stat()
    assert st.st_mode & 0o222 == 0 and len(data) == row['entry']['bytes'] == m['bytes']
    assert zlib.crc32(data) == row['entry']['crc32']
    assert hashlib.sha256(data).hexdigest() == m['sha256']
    checks.append(dict(path=str(p), bytes=st.st_size, sha256=m['sha256'], verification='independent_full_sha256_and_frozen_zip_crc32'))
p = pathlib.Path(asr); m = by_path[asr]; st = p.stat()
archive = next(row for row in plan['files'] if row['path'].endswith('/large-v2-zh.pt.zip'))
assert st.st_size == m['bytes'] == 6173691427 and st.st_mode & 0o222 == 0
assert m['verified_parent_zip_sha256'] == archive['sha256']
assert not any(pathlib.Path(p).with_name(pathlib.Path(p).name + '.partial').exists() for p in expected)
checks.append(dict(path=asr, bytes=st.st_size, sha256=m['sha256'], verification='worker_zip_crc_checked_extraction_from_exact_sha256_archive_and_current_readonly_size'))
result = dict(status='PASS_INDEPENDENT_SC_ASSET_GATE_METADATA_AND_BOUNDED_REHASH',
    observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    plan_sha256=payload['plan_sha256'], worker_pid=manifest['pid'], worker_start_ticks=manifest['start_ticks'],
    exact_file_count=len(checks), actual_final_bytes=sum(row['bytes'] for row in checks),
    gpu_launched=False, independent_large_rehash=False,
    manifest_sha256=hashlib.sha256((O/'ASSET_MANIFEST.json').read_bytes()).hexdigest(), checks=checks)
print(json.dumps(result))
'''

sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client

c = ssh_client()
try:
    stdin, stdout, stderr = c.exec_command(
        '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '
        + shlex.quote(REMOTE), timeout=40)
    stdin.write(json.dumps(payload)); stdin.flush(); stdin.channel.shutdown_write()
    data = stdout.read(); diagnostic = stderr.read(); rc = stdout.channel.recv_exit_status()
    if rc:
        raise RuntimeError('Independent asset gate check failed; inspect source assertions; diagnostics suppressed')
    result = json.loads(data)
    folder = T / 'acquisition_monitor_v1'; folder.mkdir(exist_ok=True)
    path = folder / 'INDEPENDENT_FINAL_VERIFICATION.json'
    assert not path.exists(), 'do not replace prior independent verification'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(evidence=str(path), **result), indent=2))
finally:
    c.close()
