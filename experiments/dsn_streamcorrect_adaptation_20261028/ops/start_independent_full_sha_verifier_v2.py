"""Launch one detached read-only full SHA256 audit after the fresh asset PASS."""
import hashlib
import json
import pathlib
import shlex
import sys

T=pathlib.Path(__file__).resolve().parents[1];plan_path=T/'download_plan_v1/PLAN.json'
payload=dict(plan=json.loads(plan_path.read_text()),plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest())
dependency_path=T/'native_processor_dependency_v6/MANIFEST.json';dependency=json.loads(dependency_path.read_text())
payload['processor_dependency']=dict(manifest=dict(path=str(pathlib.PurePosixPath(dependency['path']).parent/'MANIFEST.json'),
    semantic_value=dependency),
    config={key:dependency[key] for key in ('path','bytes','sha256')})
source=T/'ops/remote_independent_verify_asset_gate_full_sha_v2.py';body=source.read_bytes()
worker='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/independent_asset_full_sha_worker_v2.py'
REMOTE=r'''
import datetime,hashlib,json,pathlib,subprocess,sys
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
payload=json.load(sys.stdin);worker=pathlib.Path(payload.pop('worker'));expected=payload.pop('worker_sha256')
assert hashlib.sha256(worker.read_bytes()).hexdigest()==expected
assert json.loads((O/'GATE.json').read_text())['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
A=O/'independent_full_sha_v2';A.mkdir(exist_ok=False)
with (A/'SAFE_LOG.jsonl').open('x') as log:
 child=subprocess.Popen([str(B/'envs/revbatch-cu128/bin/python'),'-B',str(worker)],stdin=subprocess.PIPE,
  stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 child.stdin.write(json.dumps(payload).encode());child.stdin.close()
p=pathlib.Path('/proc')/str(child.pid)
handle=dict(pid=child.pid,start_ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19]),
 cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest(),worker_sha256=expected,
 started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),audit_root=str(A),read_only_assets=True,gpu_launched=False)
(A/'HANDLE.json').write_text(json.dumps(handle,indent=2));print(json.dumps(handle))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    s=c.open_sftp()
    with s.open(payload['processor_dependency']['manifest']['path'],'rb') as f:remote_dependency=f.read(16385)
    assert len(remote_dependency)<=16384 and json.loads(remote_dependency)==dependency
    payload['processor_dependency']['manifest'].update(bytes=len(remote_dependency),sha256=hashlib.sha256(remote_dependency).hexdigest())
    try:
        with s.open(worker,'rb') as f:assert f.read()==body
    except FileNotFoundError:
        with s.open(worker,'wb') as f:f.write(body)
    s.close();payload.update(worker=worker,worker_sha256=hashlib.sha256(body).hexdigest())
    stdin,stdout,stderr=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(REMOTE),timeout=40)
    stdin.write(json.dumps(payload));stdin.flush();stdin.channel.shutdown_write()
    data=stdout.read();err=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Read-only audit launch failed; diagnostics suppressed')
    result=json.loads(data);path=T/'acquisition_monitor_v1/FULL_SHA_VERIFIER_HANDLE.json'
    assert not path.exists();path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
finally:c.close()
