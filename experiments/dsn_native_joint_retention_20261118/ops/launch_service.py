"""Root-owned serial service phase launch under the completed strict reference."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
p=argparse.ArgumentParser();p.add_argument('phase',choices=['PILOT20_V1','CONFIRM60_V1']);a=p.parse_args();phase=a.phase;D=E/'launch_ops'/phase
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
planpath=E/'plans'/(phase+'_PLAN.json');plan=json.loads(planpath.read_bytes());assert json.loads((E/'gpu_results/REFERENCE8_V3/GATE.json').read_bytes())['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
if phase=='CONFIRM60_V1':assert json.loads((E/'gpu_results/PILOT20_V1/GATE.json').read_bytes())['status']=='COMPLETE_NATIVE_FACTORIAL_AND_CONSERVATIVE_TASK_AND_ENDPOINTS'
assert not(D/'HANDLE.json').exists()
rec=dict(experiment_id=plan['experiment_id'],code_commit=plan['driver']['source_commit'],actual_NN_source_commit=plan['actual_NN']['source_commit'],frozen_config=str(planpath.resolve()),frozen_config_sha256=sha(planpath),environment_record=str((E/'plans/ENVIRONMENT.json').resolve()),environment_record_sha256=sha(E/'plans/ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',planned_trials=len(plan['cells']))
put(D/'RUN_RECORD_PRELAUNCH.json',rec);g=D/'DRIVER_EXPLICIT.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str((E/'campaign_source').resolve()),'--manifest',str((E/'packages/CAMPAIGN_SOURCE_V1.json').resolve()),'--run-record',str((D/'RUN_RECORD_PRELAUNCH.json').resolve()),'--output',str(g.resolve())],cwd=R,check=True,capture_output=True)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 c.put(g,P+'/root_gates/'+phase+'_DRIVER_EXPLICIT.json')
 pre=dict(plan_sha256=sha(planpath),root_noarg_preflight=P+'/root_gates/ROOT_NOARG_RUNTIME.json',root_noarg_preflight_sha256=sha(E/'baseline/ROOT_NOARG_RUNTIME.json'),driver_explicit_preflight=P+'/root_gates/'+phase+'_DRIVER_EXPLICIT.json',driver_explicit_preflight_sha256=sha(g),exclusive_GPU_window_authorized_by_root=True,asset_byte_gate=dict(path=P+'/MODEL_ASSET_GATE_V1.json',sha256=sha(E/'plans/MODEL_ASSET_GATE_V1.json')))
 put(D/'PRELAUNCH.json',pre);c.put(D/'PRELAUNCH.json',P+'/'+phase+'_PRELAUNCH.json')
 command=[plan['environment_python'],'-B',plan['driver']['source_root']+'/run_native_factorial.py','--plan',P+'/'+phase+'_PLAN.json','--manifest',plan['driver']['source_manifest'],'--prelaunch',P+'/'+phase+'_PRELAUNCH.json','--out',plan['raw_result_location']]
 C=dict(command=command,source=plan['driver']['source_root'],out=plan['raw_result_location'],log=O+'/'+phase+'.process.log',handle=O+'/'+phase+'.HANDLE.json',cache=B+'/cache/revtrace_native_rs_20261118',planned=len(plan['cells']))
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists()and not Path(C['log']).exists()and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
for key,leaf in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba'),('TMPDIR','service_tmp')]:
 p=Path(C['cache'])/leaf;p.mkdir(parents=True,exist_ok=True);env[key]=str(p)
env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb')as f:child=subprocess.Popen(C['command'],cwd=C['source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
p=Path('/proc')/str(child.pid);h=dict(pid=child.pid,start_ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest(),command=C['command'],out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_trials=C['planned'])
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
''',timeout=30);(D/'HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
