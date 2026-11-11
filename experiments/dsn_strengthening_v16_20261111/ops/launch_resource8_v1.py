"""Root-only eight-cell same-resource two/four-session GPU comparison."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/RESOURCE8_V1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111';O=B+'/results/revtrace/dsn_strengthening_v16_20261111'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
 with Path(p).open('x',encoding='utf8')as f:json.dump(x,f,indent=2);f.write('\n')
def gate(args,name):
 out=D/name;subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args,'--output',str(out.resolve())],cwd=R,check=True,capture_output=True);return out
def main():
 q=argparse.ArgumentParser();q.add_argument('--launch',action='store_true',required=True);q.parse_args()
 hand=json.loads((E/'baseline_ops/RESOURCE_PREPARATION_V2/LAUNCH_HANDOFF.json').read_bytes());lp=E/'baseline_ops/RESOURCE_PREPARATION_V2/RESOURCE_PLAN_v1.json';plan=json.loads(lp.read_bytes());assert sha(lp)==hand['resource_plan_sha256'] and len(plan['cells'])==8
 assert json.loads((E/'launch_ops/PILOT24_V2/RESOURCE_CLOSURE.json').read_bytes())['status']=='PASS_PILOT24_COMPLETED_AND_OWNED_PHYSICAL_RELEASE'
 assert json.loads((E/'baseline_ops/CPU_RESOURCE_DRIVER_V2/GATE.json').read_bytes())['status']=='PASS_GROUPED_RESOURCE_CPU_ONLY'
 D.mkdir(parents=True,exist_ok=False)
 sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 with m.Remote()as c:
  C=dict(plan=hand['resource_plan'],sha=sha(lp),identities=[plan[k]for k in ('driver','actual_NN','production_support','reference_generator')])
  script='C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,importlib.metadata,json,subprocess,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['plan'])==C['sha'];p=json.loads(Path(C['plan']).read_bytes())
for x in C['identities']:
 root=Path(x['source_root']);mf=Path(x['source_manifest']);assert sha(mf)==x['source_manifest_sha256'];m=json.loads(mf.read_bytes())
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==x['source_commit']
 assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip()
 assert set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines())=={r['path']for r in m['files']}
 for r in m['files']:assert (root/r['path']).stat().st_size==r['bytes'] and sha(root/r['path'])==r['sha256']
env=json.loads(Path(p['environment_record']).read_bytes());assert {k:importlib.metadata.version(k)for k in env['packages']}==env['packages']
assert Path(sys.executable).resolve()==Path(env['executable']).resolve()
for cell in p['cells']:assert sha(cell['config'])==cell['config_sha256'] and not Path(cell['out']).exists()
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),executable=sys.executable,package_versions=env['packages'],full_source_identities_checked=4,cells_checked=8,compute_owners=owners,models_launched=False)))
'''
  raw=c.python(script,timeout=45);(D/'FRESH_REMOTE_ENVIRONMENT.json').write_bytes(raw+b'\n')
  local_env=E/'baseline_ops/PILOT_PREPARATION_V2/ENVIRONMENT.json';assert sha(local_env)==plan['environment_sha256']
  rec=dict(experiment_id=plan['experiment_id'],code_commit=hand['driver_source_commit'],actual_NN_source_commit=hand['actual_NN'],reference_generator_commit=hand['reference_generator_commit'],frozen_config=str(lp.resolve()),frozen_config_sha256=sha(lp),environment_record=str(local_env.resolve()),environment_record_sha256=sha(local_env),fresh_resource_record=str((D/'FRESH_REMOTE_ENVIRONMENT.json').resolve()),fresh_resource_sha256=sha(D/'FRESH_REMOTE_ENVIRONMENT.json'),raw_result_location=hand['raw_result_location'],aggregate_summary_location=hand['raw_result_location']+'/SUMMARY.json',gate_decision_location=hand['raw_result_location']+'/GATE.json',launcher_sha256=sha(__file__),new_acoustic_speakers=0)
  put(D/'RUN_RECORD_PRELAUNCH.json',rec);nn=gate([],'ROOT_NOARG_RUNTIME_RESOURCE.json');drv=gate(['--source',str((E/'resource_driver_source_v2').resolve()),'--manifest',str((E/'packages/RESOURCE_DRIVER_SOURCE_v2.json').resolve()),'--run-record',str((D/'RUN_RECORD_PRELAUNCH.json').resolve())],'RESOURCE_DRIVER_EXPLICIT.json')
  rg=P+'/resource_driver_v2/root_gates/';c.python('from pathlib import Path\nPath('+repr(rg)+').mkdir(parents=True,exist_ok=True)\n')
  for p in [nn,drv,D/'RUN_RECORD_PRELAUNCH.json']:c.put(p,rg+p.name)
  pre=dict(plan_sha256=sha(lp),root_noarg_preflight=rg+nn.name,root_noarg_preflight_sha256=sha(nn),driver_explicit_preflight=rg+drv.name,driver_explicit_preflight_sha256=sha(drv),exclusive_GPU_window_authorized_by_root=True,exclusive_window_id='V16_ROOT_RESOURCE8_AFTER_PILOT24',asset_byte_gate=hand['prelaunch_requirements']['asset_byte_gate'])
  put(D/'ENTRY_PRELAUNCH.json',pre);prepath=hand['resource_command'][hand['resource_command'].index('--prelaunch')+1];c.put(D/'ENTRY_PRELAUNCH.json',prepath)
  command=hand['resource_command'];C=dict(command=command,source=hand['remote_source'],out=hand['raw_result_location'],log=O+'/RESOURCE8_V1.process.log',handle=O+'/RESOURCE8_V1.HANDLE.json',plan=hand['resource_plan'],plan_sha=sha(lp),tmp=B+'/cache/revtrace_dsn_strengthening_v16_20261111/resource_launch_tmp')
  script='C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
assert hashlib.sha256(Path(C['plan']).read_bytes()).hexdigest()==C['plan_sha']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip()
Path(C['tmp']).mkdir(parents=True,exist_ok=True);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=C['tmp']);env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb')as f:child=subprocess.Popen(C['command'],cwd=C['source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
p=Path('/proc')/str(child.pid);h=dict(pid=child.pid,start_ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest(),command=C['command'],command_sha256=hashlib.sha256(json.dumps(C['command'],separators=(',',':')).encode()).hexdigest(),out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_trials=8,driver_commit='7b83b2151040512776b5bdaa7f7680e7a8f59047',NN_commit='de0936b2e30179d63aeef6e235cd1af685578c58')
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
'''
  raw=c.python(script,timeout=45);(D/'HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
if __name__=='__main__':main()
