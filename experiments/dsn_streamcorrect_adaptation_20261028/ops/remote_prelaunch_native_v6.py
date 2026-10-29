import pathlib,json,hashlib,subprocess,sys,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';J=B/'results/revtrace/physical_retirement_20261028'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(J/'dsn_joint_controller_v1/GATE.json')['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
g=read(J/'dsn_joint_analysis_v2/GATE.json');assert g.get('gate',g.get('status'))=='PASS_OFFLINE_RECOUNT'
g=read(J/'dsn_joint_detail_v2/GATE.json');assert g.get('gate',g.get('status'))=='PASS_SUPPLEMENTAL_OFFLINE_AUDIT'
assert read(O/'cpu_environment_pipeline_v6/STATUS.json')['status']=='PASS_READY_FOR_ROOT_SERIALIZED_NATIVE_GPU_WINDOW'
assert read(O/'assets_v1/GATE.json')['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
plan=P/'NATIVE_CAMPAIGN_v6_FROZEN.json';assert sha(plan)=='ba1f52462534b8ee5286bcaed1f9b5f97042f9b4ac1e8ce9dbedd9d325c9b780'
frozen=read(plan);assert frozen['source_commit']=='a720d02a8cb81db6545d7d9ec6bdc31419dd091d' and len(frozen['cells'])==14
assert sha(pathlib.Path(frozen['environment_record']))=='1a54ad837c9bd71a0b39ba3e71f6dd1539181f7d95c1e44baf826bf861346222'
for cell in frozen['cells']:
 r=read(pathlib.Path(cell['prelaunch_record']));assert r['code_commit']==frozen['source_commit']
 assert sha(pathlib.Path(r['frozen_config']))==r['frozen_config_sha256']
 assert sha(pathlib.Path(r['environment_record']))==r['environment_record_sha256']
sys.path.insert(0,str(P/'runtime_source_v6'))
from native_service import verify_source
source=verify_source(P/'SOURCE_v6.json');assert source['source_commit']==frozen['source_commit'] if 'source_commit' in source else source['code_commit']==frozen['source_commit']
record=dict(status='PASS_NATIVE_V6_SOURCE_CONFIG_ENV_AND_PRECEDING24_GATES',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=source,plan_sha256=sha(plan),environment_sha256=sha(pathlib.Path(frozen['environment_record'])),cells=14,gpu_apps_empty=True,native_neural_calls=0)
p=O/'NATIVE_PRELAUNCH_GATE_v6.json';assert not p.exists();p.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
