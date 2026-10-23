set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
O=$B/results/revtrace/ces_20261023
"$B/envs/revbatch-cu128/bin/python" - "$P" "$O" <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,os,subprocess,sys,tarfile,time
P,O=map(Path,sys.argv[1:]);S=P/'runtime_v1';assert not S.exists();S.mkdir()
with tarfile.open(P/'runtime_v1.tar.gz') as f:
 for m in f.getmembers():
  r=PurePosixPath(m.name);assert m.isfile() and not r.is_absolute() and '..' not in r.parts and m.size<2_000_000
  q=S/m.name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(f.extractfile(m).read())
meta=json.loads((S/'SOURCE_MANIFEST.json').read_text())
for r in meta['files']:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['sha256']
scope=['test_ces.py','test_online_admission.py','test_dgft.py','test_live_qwen.py','test_properties_abc.py','test_continuity_proof.py','test_consumer_bound_identity.py','test_certified_display.py','test_durable_journal.py','test_standard_async.py','test_lazy_reconciliation.py','test_row_progress_integration.py','test_row_executor_protocol.py','test_row_lifecycle_transport.py','test_row_worker_provenance.py','test_complete_row_stream.py']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(str(S/p) for p in ['src','scripts','tests']))
r=subprocess.run([sys.executable,'-B','-m','pytest','-q','--tb=short',*[str(S/'tests'/n) for n in scope]],cwd=S,env=env,capture_output=True,text=True)
(O/'CPU_LINUX_v1.log').write_text(r.stdout+'\n'+r.stderr);print(r.stdout[-1600:]);assert r.returncode==0
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
with (O/'PILOT_CONTROLLER_v1.log').open('w') as f:q=subprocess.Popen([sys.executable,'-u',str(P/'run_pilot.py'),str(P.parents[1])],cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
handle={'pid':q.pid,'script_sha256':hashlib.sha256((P/'run_pilot.py').read_bytes()).hexdigest(),'source_commit':meta['code_commit'],'started_unix':time.time()}
(O/'PILOT_PID_v1.json').write_text(json.dumps(handle,indent=2)+'\n');print(json.dumps(handle))
PY
