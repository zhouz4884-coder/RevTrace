"""Root-allocated local CPU window: formal controls then actual fixed-input export."""
import datetime,hashlib,json,pathlib,platform,re,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'reference_tools_source_v1';M=F/'packages/REFERENCE_EXPORT_SOURCE_v1.json'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
m=read(M);current=read(R/'experiments/repository_identity_20261027/CURRENT.json')
assert m['source_commit']=='293528d84a103054860051db90aeb36766b6b141' and current['source_commit']==m['source_commit'] and current['source_manifest_sha256']==sha(M)
pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);assert json.loads(pre.stdout)['gate']=='SOURCE_IDENTITY_PASS'
p=F/'SHORT_REFERENCE_EXPORT_ROOT_NOARG_v1.json';assert not p.exists();p.write_bytes(pre.stdout)
out=F/'REFERENCE_EXPORT_CPU_v1';out.mkdir()
cfg=dict(experiment_id='SC_PRIOR_BDFA_SHORT85_EXPORTER_CPU_CONTROLS_V1',code_commit=m['source_commit'],source_manifest_sha256=sha(M),expected_tests=13,model_calls=0)
put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0))
put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(S),'-p','test_*.py','-v'],capture_output=True);(out/'unittest.log').write_bytes(result.stdout+b'\n'+result.stderr);n=re.search(rb'Ran (\d+) tests?',result.stderr)
ok=result.returncode==0 and n and int(n[1])==13 and b'skipped=' not in result.stderr;gate=dict(status='PASS_ALL13_FROZEN_CPU_REFERENCE_EXPORT_CONTROLS' if ok else 'FAIL_REFERENCE_EXPORT_CPU_PRESERVED',code_commit=m['source_commit'],tests=int(n[1]) if n else None,skipped=0,model_calls=0)
put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate)
assert ok,result.stderr.decode('utf8',errors='replace')
config=F/'SHORT_REFERENCE_EXPORT_v1_FROZEN.json';export=F/'SHORT_REFERENCE_EXPORT_RESULTS_v1'
result=subprocess.run([sys.executable,'-B',str(S/'export_short_reference.py'),'--config',str(config),'--manifest',str(M),'--out',str(export)],capture_output=True)
(F/'SHORT_REFERENCE_EXPORT_STDOUT_v1.json').write_bytes(result.stdout);(F/'SHORT_REFERENCE_EXPORT_STDERR_v1.txt').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode('utf8',errors='replace')
summary=read(export/'GATE.json');assert summary['status']=='PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT'
print(json.dumps(dict(status=summary['status'],code_commit=m['source_commit'],CPU_controls=13,reference_calls=85,reference_details_sha256=summary['reference_details_sha256'],reference_gate_sha256=sha(export/'GATE.json'),out=str(export),model_calls=0),indent=2))

