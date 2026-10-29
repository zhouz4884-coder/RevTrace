import pathlib,json,hashlib,subprocess,sys,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(O/'median_gpu_gate_v8/GATE.json')['status']=='PASS_NATIVE_MEDIAN_API_AND_SIGNED_FINITE_GPU_ORACLE_CONTROLS'
assert read(O/'median_gpu_gate_v8/SUMMARY.json')['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c'
assert read(O/'cpu_environment_pipeline_v8/STATUS.json')['status']=='PASS_READY_FOR_ROOT_SERIALIZED_NATIVE_GPU_WINDOW'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
plan=P/'NATIVE_CAMPAIGN_v8_FROZEN.json';identity=read(O/'FROZEN_CAMPAIGN_IDENTITY_v8.json');assert sha(plan)==identity['sha256']
frozen=read(plan);assert frozen['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c' and len(frozen['cells'])==14
for cell in frozen['cells']:
 r=read(pathlib.Path(cell['prelaunch_record']));assert r['code_commit']==frozen['source_commit']
 assert sha(pathlib.Path(r['frozen_config']))==r['frozen_config_sha256']
 assert sha(pathlib.Path(r['environment_record']))==r['environment_record_sha256']
sys.path.insert(0,str(P/'runtime_source_v8'));from native_service import verify_source
source=verify_source(P/'SOURCE_v8.json');assert source['source_commit']==frozen['source_commit']
r=dict(status='PASS_NATIVE_V8_FROZEN_SOURCE_CONFIG_ENV_AND_ACTUAL_MEDIAN_GATES',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=source,plan_sha256=sha(plan),environment_sha256=sha(pathlib.Path(frozen['environment_record'])),cells=14,median_gate_sha256=sha(O/'median_gpu_gate_v8/GATE.json'),gpu_apps_empty=True,completed_native_service_cells=0)
p=O/'NATIVE_PRELAUNCH_GATE_v8.json';assert not p.exists();p.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
