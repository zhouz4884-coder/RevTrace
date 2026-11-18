"""Preserve the original selection order and preflight the exact frozen entry."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
plan=json.loads((E/'plans/REFERENCE_PLAN_V2.json').read_bytes());bank=json.loads((E/'baseline/ORIGINAL_SELECTION_BANK.json').read_bytes());assert {s['source_id']for s in plan['sources']}=={s['source_id']for s in bank['sources']}
assert sorted(plan['sources'],key=lambda s:s['source_id'])==sorted(bank['sources'],key=lambda s:s['source_id'])
plan.update(experiment_id='REVTRACE_NATIVE_RS_REFERENCE8_V3_20261118',sources=bank['sources'],raw_result_location=O+'/REFERENCE8_V3');put(E/'plans/REFERENCE_PLAN_V3.json',plan)
rec=dict(experiment_id=plan['experiment_id'],code_commit=plan['generator']['source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],frozen_config=str((E/'plans/REFERENCE_PLAN_V3.json').resolve()),frozen_config_sha256=sha(E/'plans/REFERENCE_PLAN_V3.json'),environment_record=str((E/'plans/ENVIRONMENT.json').resolve()),environment_record_sha256=sha(E/'plans/ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',reference_only=True)
put(E/'launch_ops/REFERENCE8_V3/RUN_RECORD_PRELAUNCH.json',rec);g=E/'launch_ops/REFERENCE8_V3/DRIVER_EXPLICIT.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str((E/'campaign_source').resolve()),'--manifest',str((E/'packages/CAMPAIGN_SOURCE_V1.json').resolve()),'--run-record',str((E/'launch_ops/REFERENCE8_V3/RUN_RECORD_PRELAUNCH.json').resolve()),'--output',str(g.resolve())],cwd=R,check=True,capture_output=True)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 failed=dict(status='FAIL_PREMODEL_SELECTION_ORDER_BINDING_PRESERVED',failure_category='operator sorted a reference source list while exact original selection receipt retains another order',model_calls=0,source_bytes_changed=False,scientific_source_objects_changed=False,repair='Use exact receipt order for reference generation; service ABBA order and source set unchanged',handle=json.loads((E/'launch_ops/REFERENCE8_V2/HANDLE.json').read_bytes()));put(E/'launch_ops/REFERENCE8_V2/ROOT_CLOSEOUT.json',failed);c.put(E/'launch_ops/REFERENCE8_V2/ROOT_CLOSEOUT.json',O+'/REFERENCE8_V2.ROOT_CLOSEOUT.json')
 c.put(E/'plans/REFERENCE_PLAN_V3.json',P+'/REFERENCE_PLAN_V3.json');c.put(g,P+'/root_gates/REFERENCE_V3_DRIVER_EXPLICIT.json')
 pre=dict(plan_sha256=sha(E/'plans/REFERENCE_PLAN_V3.json'),root_noarg_preflight=P+'/root_gates/ROOT_NOARG_RUNTIME.json',root_noarg_preflight_sha256=sha(E/'baseline/ROOT_NOARG_RUNTIME.json'),driver_explicit_preflight=P+'/root_gates/REFERENCE_V3_DRIVER_EXPLICIT.json',driver_explicit_preflight_sha256=sha(g),exclusive_GPU_window_authorized_by_root=True);put(E/'plans/REFERENCE_PRELAUNCH_V3.json',pre);c.put(E/'plans/REFERENCE_PRELAUNCH_V3.json',P+'/REFERENCE_PRELAUNCH_V3.json')
 C=dict(root=plan['generator']['source_root'],plan=P+'/REFERENCE_PLAN_V3.json',manifest=plan['generator']['source_manifest'],pre=P+'/REFERENCE_PRELAUNCH_V3.json')
 raw=c.python('C='+repr(C)+'\n'+r'''
import json,sys
from types import SimpleNamespace
sys.path.insert(0,C['root']);import run_reference
args=SimpleNamespace(plan=C['plan'],manifest=C['manifest'],prelaunch=C['pre']);p=run_reference.read(args.plan);own,base,sources,packages,gpu=run_reference.boot(args,p)
assert not any(n in sys.modules for n in('torch','transformers','whisper','peft','soundfile'))
print(json.dumps(dict(status='PASS_EXACT_REFERENCE_ENTRY_CPU_PREFLIGHT',driver=own['source_commit'],runtime=base['source_commit'],sources=len(sources),expected_original_steps=p['expected_original_steps'],no_neural_imports=True)))
''',timeout=45);(E/'launch_ops/REFERENCE8_V3/ENTRY_CPU_PREFLIGHT.json').write_bytes(raw+b'\n');print(raw.decode(),flush=True)
 command=[plan['environment_python'],'-B',C['root']+'/run_reference.py','--plan',C['plan'],'--manifest',C['manifest'],'--prelaunch',C['pre']];C=dict(command=command,cwd=C['root'],out=plan['raw_result_location'],log=O+'/REFERENCE8_V3.process.log',handle=O+'/REFERENCE8_V3.HANDLE.json')
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists()and not Path(C['log']).exists()and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/cache/revtrace_native_rs_20261118/launch_tmp');env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb')as f:p=subprocess.Popen(C['command'],cwd=C['cwd'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
q=Path('/proc')/str(p.pid);h=dict(pid=p.pid,start_ticks=int((q/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((q/'cmdline').read_bytes()).hexdigest(),command=C['command'],out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True)
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
''',timeout=30);(E/'launch_ops/REFERENCE8_V3/HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
