"""Freeze the separate serial operator and run its local synthetic CPU controls."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'operator_source_v1'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):
 assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');assert git('rev-parse','--verify',commit+'^{commit}')==commit
names=sorted(set(subprocess.check_output(['git','-C',str(S),'ls-files','-z']).decode().split('\0'))-{''})
rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in names]
manifest=F/'packages/OPERATOR_SOURCE_v1.json'
put(manifest,dict(source_commit=commit,code_commit=commit,role='serial_frozen_six_development_campaign_operator_not_neural_runtime',neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',files=rows))
bundle=F/'packages/OPERATOR_SOURCE_v1.bundle';assert not bundle.exists()
subprocess.run(['git','-C',str(S),'bundle','create',str(bundle),'HEAD'],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(bundle)],check=True,capture_output=True)
snapshot=F/'operator_snapshot_v1';snapshot.mkdir(exist_ok=False)
for row in rows:
 target=snapshot/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((S/row['path']).read_bytes());assert sha(target)==row['sha256']
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/research/dsn-native-resilience-operator-v1'],check=True,capture_output=True)
assert subprocess.check_output(['git','-C',str(R),'rev-parse','--verify',commit+'^{commit}'],text=True).strip()==commit
pre=F/'OPERATOR_LOCAL_EXPLICIT_PREFLIGHT_v1.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(manifest),'--output',str(pre)],check=True,capture_output=True)
out=F/'operator_cpu_local_v1';out.mkdir(exist_ok=False)
config=dict(experiment_id='SC_NATIVE_RESILIENCE_OPERATOR_LOCAL_CPU_V1',source_commit=commit,source_manifest_sha256=sha(manifest),expected_CPU_controls=16,trained_neural_models_loaded=False,actual_serving_cells=0,scope='Synthetic protocol schema and tiny actual child-process controls only.')
put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,remote_operations=0,GPU_queries=0))
put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=commit,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
result=subprocess.run([sys.executable,'-B','-m','unittest','test_campaign','-v'],cwd=S,capture_output=True)
(out/'unittest.log').write_bytes(result.stdout+b'\n'+result.stderr)
success=result.returncode==0 and b'Ran 16 tests' in result.stderr and b'skipped=' not in result.stderr
summary=dict(status='PASS_OPERATOR16_LOCAL_SYNTHETIC_CPU_CONTROLS_ZERO_SKIP' if success else 'FAIL_OPERATOR_LOCAL_CPU_PRESERVED',source_commit=commit,source_manifest_sha256=sha(manifest),tests=16,skipped=0,actual_serving_cells=0,trained_neural_models_loaded=False,GPU_queries=0,scope='CPU operator correctness controls, not neural or serving results.')
put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary)
assert success,result.stderr.decode(errors='replace')
assert not git('status','--porcelain','--untracked-files=all')
put(F/'OPERATOR_READY_v1.json',dict(status='READY_FOR_ROOT_REMOTE_STAGE_CPU_AND_LAUNCH',operator_source_commit=commit,operator_manifest=str(manifest),operator_manifest_sha256=sha(manifest),bundle=str(bundle),bundle_sha256=sha(bundle),source_files=len(rows),local_CPU_tests=16,local_CPU_skipped=0,local_CPU_gate_sha256=sha(out/'GATE.json'),actual_neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',neural_launches=0,global_CURRENT_changed=False))
print(json.dumps(dict(operator_commit=commit,manifest_sha256=sha(manifest),bundle_sha256=sha(bundle),source_files=len(rows),CPU=summary,actual_neural_launches=0),indent=2))

