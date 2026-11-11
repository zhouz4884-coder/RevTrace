"""Root-only launch of the unchanged frozen 24-cell serving controller."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/PILOT24_V2'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111';O=B+'/results/revtrace/dsn_strengthening_v16_20261111'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
 with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2);f.write('\n')
def gate(args,name):
 out=D/name;subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args,'--output',str(out.resolve())],cwd=R,check=True,capture_output=True);return out
def main():
 q=argparse.ArgumentParser();q.add_argument('--launch',action='store_true',required=True);q.parse_args()
 hand=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json').read_bytes());planpath=E/'baseline_ops/PILOT_PREPARATION_V2/SERVICE_PLAN.json';plan=json.loads(planpath.read_bytes())
 assert sha(planpath)=='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6' and len(plan['cells'])==24
 assert json.loads((E/'launch_ops/REFERENCE_FULL4_V2/RESOURCE_CLOSURE.json').read_bytes())['status']=='PASS_REFERENCE_AND_OWNED_PROCESS_PHYSICAL_RELEASE'
 assert json.loads((E/'baseline_ops/CPU_ENTRY_ROUTE_V1/GATE.json').read_bytes())['status']=='PASS_FROZEN_ACTUAL_ENTRY_ROUTE_NO_NEURAL_EXECUTION'
 decision=E/'plans/PILOT_OPPORTUNITY_AND_INTERPRETATION_v5.json';assert decision.exists()
 D.mkdir(parents=True,exist_ok=False)
 sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 with m.Remote() as c:
  script='C='+repr(dict(plan=hand['ordered_commands'][5]['command'][4],plan_sha=sha(planpath)))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,importlib.metadata,json,subprocess,sys
assert hashlib.sha256(Path(C['plan']).read_bytes()).hexdigest()==C['plan_sha']
p=json.loads(Path(C['plan']).read_bytes());sys.path.insert(0,p['driver']['source_root'])
from confirmation_common import verify_source,reference_binding,selected_sources,validate_matrix,sha
for name in ('driver','actual_NN','production_support'):
 x=p[name];assert verify_source(x['source_root'],x['source_manifest'],x['source_commit'])==x
s=selected_sources(json.loads(Path(p['selection_receipt']['path']).read_bytes()),2);validate_matrix(p['cells'],s)
reference_binding(p['reference_receipt']['path'],p['selection_receipt']['path'],s)
e=json.loads(Path(p['environment_record']).read_bytes());assert {k:importlib.metadata.version(k)for k in e['packages']}==e['packages']
assert Path(sys.executable).resolve()==Path(e['executable']).resolve()
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw','--format=csv,noheader'],text=True).strip()
for cell in p['cells']:
 assert sha(cell['config'])==cell['config_sha256'];cfg=json.loads(Path(cell['config']).read_bytes())
 assert cfg['arm']==cell['strategy'] and cfg['settings']['source_commit']==p['actual_NN']['source_commit']
 assert not Path(cell['out']).exists()
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,executable=sys.executable,gpus=gpus,compute_owners=owners,cells_checked=24,reference_bound=True,source_identities_revalidated=True,actual_serving_runs=0)))
'''
  raw=c.python(script,timeout=45);(D/'FRESH_REMOTE_ENVIRONMENT.json').write_bytes(raw+b'\n')
  envpath=E/'baseline_ops/PILOT_PREPARATION_V2/ENVIRONMENT.json'
  rec=dict(experiment_id=plan['experiment_id'],code_commit=plan['driver']['source_commit'],actual_NN_source_commit=plan['actual_NN']['source_commit'],frozen_config=str(planpath.resolve()),frozen_config_sha256=sha(planpath),environment_record=str(envpath.resolve()),environment_record_sha256=sha(envpath),fresh_resource_record=str((D/'FRESH_REMOTE_ENVIRONMENT.json').resolve()),fresh_resource_sha256=sha(D/'FRESH_REMOTE_ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',opportunity_interpretation_contract=str(decision.resolve()),opportunity_interpretation_sha256=sha(decision),entry_route_gate_sha256=sha(E/'baseline_ops/CPU_ENTRY_ROUTE_V1/GATE.json'),launcher_sha256=sha(__file__),reference_generation_is_separate=True)
  put(D/'RUN_RECORD_PRELAUNCH.json',rec)
  nn=gate([],'ROOT_NOARG_RUNTIME_SERVICE.json');drv=gate(['--source',str((E/'pilot_driver_source_v2').resolve()),'--manifest',str((E/'packages/PILOT_DRIVER_SOURCE_v2.json').resolve()),'--run-record',str((D/'RUN_RECORD_PRELAUNCH.json').resolve())],'DRIVER_EXPLICIT_SERVICE.json')
  rg=P+'/pilot_driver_v2/root_gates/'
  c.put(nn,rg+nn.name);c.put(drv,rg+drv.name);c.put(D/'RUN_RECORD_PRELAUNCH.json',rg+'PILOT24_RUN_RECORD_PRELAUNCH.json');c.put(decision,rg+'PILOT_OPPORTUNITY_AND_INTERPRETATION_v5.json')
  bind=list(hand['ordered_commands'][4]['command'])
  for key,value in [('--root-noarg-preflight',rg+nn.name),('--driver-explicit-preflight',rg+drv.name),('--out',rg+'SERVICE_PRELAUNCH_LAUNCH1.json')]:bind[bind.index(key)+1]=value
  c.python('import subprocess\nsubprocess.run('+repr(bind)+',check=True)\n',timeout=45);c.get(bind[-1],D/'ENTRY_PRELAUNCH.json')
  command=list(hand['ordered_commands'][5]['command']);command[command.index('--prelaunch')+1]=bind[-1]
  C=dict(command=command,driver=plan['driver'],plan=command[command.index('--plan')+1],plan_sha=sha(planpath),out=plan['raw_result_location'],log=O+'/PILOT24_V2.process.log',handle=O+'/PILOT24_V2.HANDLE.json',tmp=B+'/cache/revtrace_dsn_strengthening_v16_20261111/pilot_launch_tmp')
  script='C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
assert hashlib.sha256(Path(C['plan']).read_bytes()).hexdigest()==C['plan_sha']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip()
Path(C['tmp']).mkdir(parents=True,exist_ok=True);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=C['tmp']);env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb') as f:child=subprocess.Popen(C['command'],cwd=C['driver']['source_root'],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
p=Path('/proc')/str(child.pid);ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
h=dict(pid=child.pid,start_ticks=ticks,cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest(),command=C['command'],command_sha256=hashlib.sha256(json.dumps(C['command'],separators=(',',':')).encode()).hexdigest(),out=C['out'],log=C['log'],driver_commit=C['driver']['source_commit'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_trials=24,reference_generation_is_separate=True)
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
'''
  raw=c.python(script,timeout=45);(D/'HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
if __name__=='__main__':main()
