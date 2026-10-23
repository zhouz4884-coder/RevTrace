"""Capture complete local CPU test evidence; failures are never overwritten."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
W=Path(__file__).resolve().parent;S=W/'runtime';D=W/'cpu_tests_v5';assert not D.exists();D.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(str(S/p) for p in ['src','scripts','tests']))
scope=['test_ces.py','test_online_admission.py','test_dgft.py','test_live_qwen.py','test_properties_abc.py','test_continuity_proof.py','test_consumer_bound_identity.py','test_localagreement_display.py','test_certified_display.py','test_durable_journal.py','test_standard_async.py','test_lazy_reconciliation.py','test_model_lifecycle_telemetry.py','test_result_delivery_hold.py','test_execution_context_fault_seam.py','test_diagnostic_switch.py','test_row_progress_integration.py','test_row_executor_protocol.py','test_row_lifecycle_transport.py','test_row_worker_provenance.py','test_complete_row_stream.py']
cmd=[sys.executable,'-m','pytest',*[str(S/'tests'/n) for n in scope],'-q','--tb=short','--basetemp',str(W/'tmp/cpu_complete_v5')]
a=time.time();r=subprocess.run(cmd,cwd=S,env=env,capture_output=True,text=True)
(D/'pytest.log').write_text(r.stdout+'\n'+r.stderr)
x={'status':'PASS' if r.returncode==0 else 'FAIL','evidence':'CPU tests, not GPU evidence','seconds':time.time()-a,'argv':cmd,
   'returncode':r.returncode,'source_sha256':{str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*.py') if '.git' not in p.parts}}
(D/'SUMMARY.json').write_text(json.dumps(x,indent=2)+'\n');print(r.stdout[-6000:]);print(r.stderr[-1500:]);raise SystemExit(r.returncode)
