"""Bind the measured byte-readiness receipt to the reference gate schema."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
ready=json.loads((E/'baseline/CPU_READINESS_V1/SUMMARY.json').read_bytes());gate=json.loads((E/'baseline/CPU_READINESS_V1/GATE.json').read_bytes())
assert ready['status']==gate['status']=='PASS_FROZEN_CPU_BYTE_AND_ENVIRONMENT_READINESS'and gate['summary_sha256']==sha(E/'baseline/CPU_READINESS_V1/SUMMARY.json')
assert ready['asset_files']==31 and len(ready['rows'])==ready['asset_files']+ready['audio_files'] and ready['checked_bytes']==sum(r['bytes']for r in ready['rows'])
asset=dict(status='PASS_DERIVED_FRESH_MODEL_BYTE_BINDING',all_asset_bytes_verified=True,asset_manifest_sha256=ready['asset_manifest_sha256'],verified_asset_files=ready['asset_files'],measured_readiness_summary=dict(path=O+'/CPU_READINESS_V1/SUMMARY.json',sha256=sha(E/'baseline/CPU_READINESS_V1/SUMMARY.json')),measured_readiness_gate=dict(path=O+'/CPU_READINESS_V1/GATE.json',sha256=sha(E/'baseline/CPU_READINESS_V1/GATE.json')),new_model_calls=0,operator_sha256=sha(__file__))
put(E/'plans/MODEL_ASSET_GATE_V1.json',asset)
plan=json.loads((E/'plans/REFERENCE_PLAN.json').read_bytes());plan.update(experiment_id='REVTRACE_NATIVE_RS_REFERENCE8_V2_20261118',raw_result_location=O+'/REFERENCE8_V2',asset_byte_gate=P+'/MODEL_ASSET_GATE_V1.json',asset_byte_gate_sha256=sha(E/'plans/MODEL_ASSET_GATE_V1.json'))
plan['inputs'][P+'/MODEL_ASSET_GATE_V1.json']=dict(bytes=(E/'plans/MODEL_ASSET_GATE_V1.json').stat().st_size,sha256=sha(E/'plans/MODEL_ASSET_GATE_V1.json'));put(E/'plans/REFERENCE_PLAN_V2.json',plan)
rec=dict(experiment_id=plan['experiment_id'],code_commit=plan['generator']['source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],frozen_config=str((E/'plans/REFERENCE_PLAN_V2.json').resolve()),frozen_config_sha256=sha(E/'plans/REFERENCE_PLAN_V2.json'),environment_record=str((E/'plans/ENVIRONMENT.json').resolve()),environment_record_sha256=sha(E/'plans/ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',reference_only=True)
put(E/'launch_ops/REFERENCE8_V2/RUN_RECORD_PRELAUNCH.json',rec)
g=E/'launch_ops/REFERENCE8_V2/DRIVER_EXPLICIT.json';subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str((E/'campaign_source').resolve()),'--manifest',str((E/'packages/CAMPAIGN_SOURCE_V1.json').resolve()),'--run-record',str((E/'launch_ops/REFERENCE8_V2/RUN_RECORD_PRELAUNCH.json').resolve()),'--output',str(g.resolve())],cwd=R,check=True,capture_output=True)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 failed=dict(status='FAIL_PREMODEL_ASSET_RECEIPT_SCHEMA_PRESERVED',failure_category='operator receipt schema before model import/load',source_commit=plan['generator']['source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],original_handle=json.loads((E/'launch_ops/REFERENCE8_V1/HANDLE.json').read_bytes()),original_output_created=False,source_bytes_changed=False,model_calls=0,repair='Bind existing full-byte measured readiness to explicit all_asset_bytes_verified gate; no model/data or benchmark setting changed')
 put(E/'launch_ops/REFERENCE8_V1/ROOT_CLOSEOUT.json',failed);c.put(E/'launch_ops/REFERENCE8_V1/ROOT_CLOSEOUT.json',O+'/REFERENCE8_V1.ROOT_CLOSEOUT.json')
 for f,target in [(E/'plans/MODEL_ASSET_GATE_V1.json',P+'/MODEL_ASSET_GATE_V1.json'),(E/'plans/REFERENCE_PLAN_V2.json',P+'/REFERENCE_PLAN_V2.json'),(g,P+'/root_gates/REFERENCE_V2_DRIVER_EXPLICIT.json')]:c.put(f,target)
 pre=dict(plan_sha256=sha(E/'plans/REFERENCE_PLAN_V2.json'),root_noarg_preflight=P+'/root_gates/ROOT_NOARG_RUNTIME.json',root_noarg_preflight_sha256=sha(E/'baseline/ROOT_NOARG_RUNTIME.json'),driver_explicit_preflight=P+'/root_gates/REFERENCE_V2_DRIVER_EXPLICIT.json',driver_explicit_preflight_sha256=sha(g),exclusive_GPU_window_authorized_by_root=True);put(E/'plans/REFERENCE_PRELAUNCH_V2.json',pre);c.put(E/'plans/REFERENCE_PRELAUNCH_V2.json',P+'/REFERENCE_PRELAUNCH_V2.json')
 command=[plan['environment_python'],'-B',plan['generator']['source_root']+'/run_reference.py','--plan',P+'/REFERENCE_PLAN_V2.json','--manifest',plan['generator']['source_manifest'],'--prelaunch',P+'/REFERENCE_PRELAUNCH_V2.json'];C=dict(command=command,cwd=plan['generator']['source_root'],out=plan['raw_result_location'],log=O+'/REFERENCE8_V2.process.log',handle=O+'/REFERENCE8_V2.HANDLE.json')
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists()and not Path(C['log']).exists()and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/cache/revtrace_native_rs_20261118/launch_tmp');env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb')as f:p=subprocess.Popen(C['command'],cwd=C['cwd'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
q=Path('/proc')/str(p.pid);h=dict(pid=p.pid,start_ticks=int((q/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((q/'cmdline').read_bytes()).hexdigest(),command=C['command'],out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True)
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
''',timeout=30);(E/'launch_ops/REFERENCE8_V2/HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
