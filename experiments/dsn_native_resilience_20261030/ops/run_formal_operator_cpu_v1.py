"""Actual root-gated local21 CPU controls for the formal serial operator."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'formal_operator_source_v1';M=F/'packages/FORMAL_OPERATOR_SOURCE_v1.json';out=F/'formal_operator_cpu_local_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
commit=read(M)['source_commit'];assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==commit
check=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);assert json.loads(check.stdout)['code_commit']==commit
out.mkdir();(out/'ROOT_PREFLIGHT.json').write_bytes(check.stdout)
cfg=dict(experiment_id='SC_FORMAL_SERIAL_OPERATOR21_LOCAL_CPU_V1',code_commit=commit,source_manifest_sha256=sha(M),expected_tests=21,model_calls=0,remote_calls=0)
put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,remote_calls=0))
put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
harness="import io,json,unittest; suite=unittest.defaultTestLoader.discover('.',pattern='test_*.py'); stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); print(stream.getvalue()); print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()))); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==21 and not result.skipped else 1)"
result=subprocess.run([sys.executable,'-B','-c',harness],cwd=S,capture_output=True);(out/'unittest.log').write_bytes(result.stdout+result.stderr);last=json.loads(result.stdout.splitlines()[-1]);ok=result.returncode==0 and last['tests']==21 and last['skipped']==0
gate=dict(status='PASS_FORMAL_OPERATOR21_LOCAL_CPU_ZERO_SKIP' if ok else 'FAIL_FORMAL_OPERATOR_CPU_PRESERVED',code_commit=commit,source_manifest_sha256=sha(M),model_calls=0,remote_calls=0,**last);put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate);print(json.dumps(gate));assert ok
