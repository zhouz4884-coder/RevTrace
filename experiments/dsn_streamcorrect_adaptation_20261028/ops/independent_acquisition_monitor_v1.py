"""Read-only process, progress, and bounded asset metadata for SC acquisition.

Does not launch, stop, modify, hash large files, or expose ephemeral URLs.
"""
import datetime
import hashlib
import json
import pathlib
import shlex
import sys

T = pathlib.Path(__file__).resolve().parents[1]
REMOTE = r'''
import datetime, hashlib, json, pathlib, shutil
B = pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O = B / 'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
W = B / 'projects/revtrace_dsn_streamcorrect_20261028/asset_acquisition_worker_v2.py'
result = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              free_bytes=shutil.disk_usage(B).free)
names = ['ACTIVE_DOWNLOAD_HANDLE.json', 'GATE.json', 'ASSET_MANIFEST.json', 'PROGRESS.json']
names += [p.name for p in O.glob('DETACHED_LAUNCH_HANDLE_attempt*.json')]
for name in names:
    p = O / name
    if p.exists():
        value = json.loads(p.read_text())
        result[name] = dict(mtime_ns=p.stat().st_mtime_ns, value=value)
result['detached_process_inventory'] = []
for name in names:
    if not name.startswith('DETACHED_LAUNCH_HANDLE_'):
        continue
    candidate = result.get(name, {}).get('value', {})
    p = pathlib.Path('/proc') / str(candidate.get('pid'))
    inventory = dict(handle=name, pid=candidate.get('pid'), proc_exists=p.exists())
    if p.exists():
        fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        inventory.update(identity_matches=int(fields[19]) == candidate['start_ticks'], state=fields[0])
    result['detached_process_inventory'].append(inventory)
h = result.get('ACTIVE_DOWNLOAD_HANDLE.json', {}).get('value')
active_launch = None
if h:
    for name in names:
        if name.startswith('DETACHED_LAUNCH_HANDLE_'):
            candidate = result.get(name, {}).get('value', {})
            if candidate.get('pid') == h['pid'] and candidate.get('start_ticks') == h['start_ticks']:
                active_launch = candidate
                result['active_detached_launch_handle_name'] = name
    p = pathlib.Path('/proc') / str(h['pid'])
    result['proc_exists'] = p.exists()
    if p.exists():
        fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        result['process'] = dict(pid=h['pid'], identity_matches=int(fields[19]) == h['start_ticks'],
            state=fields[0], parent_pid=int(fields[1]), process_group=int(fields[2]),
            session_id=int(fields[3]), cmdline_sha256=hashlib.sha256((p / 'cmdline').read_bytes()).hexdigest(),
            fd0=str((p / 'fd/0').resolve()), fd1=str((p / 'fd/1').resolve()),
            fd2=str((p / 'fd/2').resolve()), io=(p / 'io').read_text())
result['exact_worker_pids'] = []
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        args = (p / 'cmdline').read_bytes().split(b'\0')
        if any(pathlib.PurePosixPath(a.decode(errors='replace')).name.startswith('asset_acquisition_worker_')
               and a.endswith(b'.py') for a in args):
            result['exact_worker_pids'].append(int(p.name))
    except (OSError, ProcessLookupError):
        pass
result['assets'] = []
for folder in (B / 'models/revtrace_streamcorrect_20261028',
               B / 'cache/revtrace_streamcorrect_20261028',
               B / 'datasets/revtrace/streamcorrect_adaptation_20261028'):
    if folder.exists():
        for p in folder.rglob('*'):
            if p.is_file():
                s = p.stat()
                result['assets'].append(dict(relative_path=str(p.relative_to(B)), bytes=s.st_size,
                    mode=oct(s.st_mode & 0o777), mtime_ns=s.st_mtime_ns))
plan_path = O / 'PUBLIC_PLAN.json'
if plan_path.exists():
    plan = json.loads(plan_path.read_text())
    expected = {row['path'] for row in plan['files'] + plan['range_files']}
    expected.add(plan['model_root'] + '/asr/large-v2-zh.pt')
    result['planned_assets'] = [row for row in result['assets']
        if str(B / row['relative_path']).removesuffix('.partial') in expected]
p = pathlib.Path(active_launch['safe_log']) if active_launch else O / 'acquisition_attempt03_detached.log'
if p.exists():
    with p.open('rb') as f:
        f.seek(max(0, p.stat().st_size - 4096))
        result['safe_log_tail'] = f.read().decode()
worker = pathlib.Path(active_launch['worker']) if active_launch else W
if worker.exists():
    result['worker_sha256'] = hashlib.sha256(worker.read_bytes()).hexdigest()
cpu_root = O.parent
cpu_handle = cpu_root / 'CPU_ENV_PIPELINE_v6_HANDLE.json'
cpu_status = cpu_root / 'cpu_environment_pipeline_v6/STATUS.json'
if cpu_status.exists():
    result['cpu_pipeline_v6_status'] = json.loads(cpu_status.read_text())
if cpu_handle.exists():
    ch = json.loads(cpu_handle.read_text())
    cp = pathlib.Path('/proc') / str(ch['pid'])
    cr = dict(pid=ch['pid'], start_ticks=ch['start_ticks'], proc_exists=cp.exists())
    if cp.exists():
        fields = (cp / 'stat').read_text().rsplit(')', 1)[1].split()
        digest = hashlib.sha256((cp / 'cmdline').read_bytes()).hexdigest()
        selected = [item.split(b'=', 1)[1].decode() for item in (cp / 'environ').read_bytes().split(b'\0')
                    if item.startswith(b'CUDA_VISIBLE_DEVICES=')]
        cr.update(identity_matches=int(fields[19]) == ch['start_ticks'], state=fields[0],
            cmdline_sha256=digest, cmdline_matches_handle=digest == ch['cmdline_sha256'],
            cuda_visible_devices=selected)
    manifest_path = pathlib.Path(ch['operations_manifest'])
    if manifest_path.exists():
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        cr.update(operations_manifest_sha256=digest,
            operations_manifest_matches_handle=digest == ch['operations_manifest_sha256'])
    result['cpu_pipeline_v6_process'] = cr
print(json.dumps(result))
'''

sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client

c = ssh_client()
try:
    _, out, err = c.exec_command(
        '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '
        + shlex.quote(REMOTE), timeout=40)
    data = out.read()
    diagnostics = err.read()
    rc = out.channel.recv_exit_status()
    if rc:
        raise RuntimeError('Read-only monitor failed; remote diagnostics suppressed')
    result = json.loads(data)
    folder = T / 'acquisition_monitor_v1'
    folder.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = folder / (stamp + '.json')
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if '--summary' in sys.argv:
        gate = result.get('GATE.json', {})
        active = result.get('ACTIVE_DOWNLOAD_HANDLE.json', {})
        print(json.dumps(dict(evidence=str(path), observed_utc=result['observed_utc'],
            free_bytes=result['free_bytes'], process=result.get('process'),
            exact_worker_pids=result['exact_worker_pids'],
            active_detached_launch_handle_name=result.get('active_detached_launch_handle_name'),
            detached_process_inventory=result.get('detached_process_inventory'),
            gate=gate.get('value'), gate_newer_than_active=gate.get('mtime_ns', 0) >= active.get('mtime_ns', 1),
            manifest_present='ASSET_MANIFEST.json' in result,
            cpu_pipeline_v6_status=result.get('cpu_pipeline_v6_status'),
            cpu_pipeline_v6_process=result.get('cpu_pipeline_v6_process'),
            completed_final_files=sum(not p['relative_path'].endswith('.partial') for p in result.get('planned_assets', result['assets'])),
            partial_assets=[p for p in result.get('planned_assets', result['assets']) if p['relative_path'].endswith('.partial')],
            last_safe_log_line=result.get('safe_log_tail', '').splitlines()[-1:] or None), indent=2))
    else:
        print(json.dumps(dict(evidence=str(path), **result), indent=2))
finally:
    c.close()
