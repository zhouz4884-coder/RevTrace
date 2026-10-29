"""Independent full-file SHA256 verification; reads assets, writes audit only."""
import datetime
import hashlib
import json
import os
import pathlib
import sys
import traceback
import zlib

B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
A=O/'independent_full_sha_v2'
payload=json.load(sys.stdin)
plan=payload['plan'];checks=[]
try:
    gate_path=O/'GATE.json';manifest_path=O/'ASSET_MANIFEST.json'
    original_gate=gate_path.read_bytes();original_manifest=manifest_path.read_bytes()
    gate=json.loads(original_gate);manifest=json.loads(original_manifest)
    active=json.loads((O/'ACTIVE_DOWNLOAD_HANDLE.json').read_text())
    assert gate['status']==manifest['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
    assert manifest['plan_sha256']==payload['plan_sha256'] and manifest['gpu_launched'] is False
    assert manifest['pid']==active['pid'] and manifest['start_ticks']==active['start_ticks']
    assert gate_path.stat().st_mtime_ns >= (O/'ACTIVE_DOWNLOAD_HANDLE.json').stat().st_mtime_ns
    launches=[json.loads(p.read_text()) for p in O.glob('DETACHED_LAUNCH_HANDLE_attempt*.json')]
    assert len([h for h in launches if h['pid']==manifest['pid'] and h['start_ticks']==manifest['start_ticks']])==1
    expected={row['path']:dict(row,kind='public_full_file') for row in plan['files']}
    expected.update({row['path']:dict(row,kind='frozen_zip_member') for row in plan['range_files']})
    asr=plan['model_root']+'/asr/large-v2-zh.pt'
    expected[asr]=dict(path=asr,bytes=6173691427,kind='native_asr_from_exact_zip')
    rows={row['path']:row for row in manifest['files']}
    assert len(rows)==len(manifest['files'])==gate['files'] and set(rows)==set(expected)
    for name,row in expected.items():
        p=pathlib.Path(name);resolved=p.resolve();before=p.stat();m=rows[name]
        assert p.is_absolute() and resolved.is_relative_to(B) and before.st_dev==B.stat().st_dev
        size=row['entry']['bytes'] if 'entry' in row else row['bytes']
        assert before.st_size==size==m['bytes'] and before.st_mode & 0o222==0
        assert not p.with_name(p.name+'.partial').exists()
        h=hashlib.sha256();git=hashlib.sha1(b'blob '+str(size).encode()+b'\0') if row.get('git_blob_sha1') else None;crc=0;count=0
        with p.open('rb') as source:
            for block in iter(lambda:source.read(8*1024*1024),b''):
                h.update(block)
                if git is not None:git.update(block)
                if 'entry' in row:crc=zlib.crc32(block,crc)
                count+=len(block)
        after=p.stat();observed=h.hexdigest()
        assert count==size and observed==m['sha256']
        assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
        assert after.st_mode & 0o222==0
        if row.get('sha256'):assert observed==row['sha256']
        if row.get('git_blob_sha1'):assert git.hexdigest()==row['git_blob_sha1']
        if 'entry' in row:assert crc==row['entry']['crc32']
        if name==asr:assert m['verified_parent_zip_sha256']==next(r['sha256'] for r in plan['files'] if r['path'].endswith('/large-v2-zh.pt.zip'))
        result=dict(path=name,bytes=count,sha256=observed,mode=oct(after.st_mode & 0o777),
            same_designated_device=True,resolved_path=str(resolved),kind=row['kind'],independent_full_sha256=True)
        checks.append(result);print(json.dumps(dict(verified_file=result,verified_count=len(checks))),flush=True)
    auxiliary=[]
    dep=payload['processor_dependency'];dep_path=pathlib.Path(dep['manifest']['path'])
    for row in (dep['manifest'],dep['config']):
        p=pathlib.Path(row['path']);stat=p.stat();data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
        assert p.resolve().is_relative_to(B) and stat.st_dev==B.stat().st_dev and stat.st_mode & 0o222==0
        assert len(data)==row['bytes'] and digest==row['sha256']
        auxiliary.append(dict(path=str(p),bytes=len(data),sha256=digest,independent_full_sha256=True,
            same_designated_device=True,mode=oct(stat.st_mode & 0o777)))
    dependency=json.loads(dep_path.read_text());cfg=json.loads(pathlib.Path(dep['config']['path']).read_text())
    assert dependency==dep['manifest']['semantic_value']
    assert dependency['status']=='PASS_PUBLIC_ORIGINAL_NATIVE_FEATURE_EXTRACTOR_METADATA'
    assert dependency['revision']=='41f01f3fe87f28c78e2fbf8b568835947dd65ed9'
    assert cfg['feature_size']==dependency['feature_size']==128 and cfg['sampling_rate']==16000
    workers=[]
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().split(b'\0')
            if any(pathlib.PurePosixPath(a.decode(errors='replace')).name.startswith('asset_acquisition_worker_') and a.endswith(b'.py') for a in args):workers.append(int(p.name))
        except OSError:pass
    assert not workers, 'completed acquisition must have no active writer'
    assert gate_path.read_bytes()==original_gate and manifest_path.read_bytes()==original_manifest
    result=dict(status='PASS_INDEPENDENT_ALL_FINAL_ASSET_SHA256',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        plan_sha256=payload['plan_sha256'],asset_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        fresh_gate_sha256=hashlib.sha256(gate_path.read_bytes()).hexdigest(),acquisition_pid=manifest['pid'],
        acquisition_start_ticks=manifest['start_ticks'],exact_final_file_count=len(checks),
        actual_final_bytes=sum(r['bytes'] for r in checks),remaining_asset_writer_pids=workers,
        independent_full_sha256=True,gpu_launched=False,checks=checks,
        auxiliary_dependency_checks=auxiliary,independent_verified_file_count=len(checks)+len(auxiliary))
    (A/'RECEIPT.json').write_text(json.dumps(result,indent=2))
    (A/'GATE.json').write_text(json.dumps(dict(status=result['status'],files=len(checks))))
    print(json.dumps(dict(status=result['status'],files=len(checks))),flush=True)
except BaseException as error:
    result=dict(status='FAIL_INDEPENDENT_FINAL_ASSET_VERIFICATION',error=type(error).__name__,verified_count=len(checks),
        frames=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)])
    (A/'GATE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    raise SystemExit(1)
