"""Root-only exact handoff: activate new NN source, bind gates, launch reference.

Reference inference is paid GPU work, never an actual serving trial. No service
configs/receipts are generated here. The frozen entrypoint must pass its task
checks; its results and process release are checked before any service launch.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
D=E/'launch_ops/REFERENCE_FULL4_V2'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_strengthening_v16_20261111'
O=B+'/results/revtrace/dsn_strengthening_v16_20261111'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2);f.write('\n')
def need(x,w):
    if not x:raise RuntimeError(w)
def gate(args,name):
    out=D/name;subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args,'--output',str(out.resolve())],cwd=R,check=True,capture_output=True);return out
def main():
    a=argparse.ArgumentParser();a.add_argument('--launch',action='store_true',required=True);a.parse_args()
    handpath=E/'baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json';hand=json.loads(handpath.read_bytes())
    planpath=E/'baseline_ops/PILOT_PREPARATION_V2/REFERENCE_PLAN.json';plan=json.loads(planpath.read_bytes())
    need(sha(planpath)==hand['reference_plan_sha256'],'plan/handoff bytes')
    need(plan['actual_NN_source_commit']=='de0936b2e30179d63aeef6e235cd1af685578c58','actual NN pin')
    need(hand['driver']['source_commit']=='f367c4e1068a9391a0e99d8537c94995a3388e13','driver pin')
    D.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    remote_probe='C='+repr(dict(hand=hand,env=plan['environment_record'],plan=hand['ordered_commands'][0]['command'][6],expected_plan_sha=sha(planpath)))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,importlib.metadata,json,subprocess,sys
h=C['hand'];sys.path.insert(0,h['driver']['source_root'])
assert hashlib.sha256(Path(C['plan']).read_bytes()).hexdigest()==C['expected_plan_sha']
from confirmation_common import verify_source
identities={}
for role in ('driver','runtime','support'):
 x=h[role];identities[role]=verify_source(x['source_root'],x['source_manifest'],x['source_commit'])
 assert identities[role]['source_manifest_sha256']==x['source_manifest_sha256']
env=json.loads(Path(C['env']).read_bytes());packages={k:importlib.metadata.version(k) for k in env['packages']};assert packages==env['packages']
assert Path(sys.executable).resolve()==Path(env['executable']).resolve()
def query(s):return subprocess.check_output(['nvidia-smi','--query-'+s,'--format=csv,noheader'],text=True).strip()
owners=query('compute-apps=pid,process_name,used_memory');assert not owners
gpus=query('gpu=index,uuid,name,memory.total,memory.used,utilization.gpu')
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),executable=sys.executable,packages=packages,source_identities=identities,gpus=gpus,compute_owners=owners,new_model_calls=0,scope='Fresh source/environment/owner prelaunch check, not inference or reservation')))
'''
    with m.Remote() as c:
        raw=c.python(remote_probe,timeout=45);(D/'FRESH_REMOTE_ENVIRONMENT.json').write_bytes(raw+b'\n')
        envpath=E/'baseline_ops/PILOT_PREPARATION_V2/ENVIRONMENT.json'
        record=dict(experiment_id=plan['experiment_id'],code_commit=hand['driver']['source_commit'],actual_NN_source_commit=hand['runtime']['source_commit'],frozen_config=str(planpath.resolve()),frozen_config_sha256=sha(planpath),environment_record=str(envpath.resolve()),environment_record_sha256=sha(envpath),fresh_resource_environment_record=str((D/'FRESH_REMOTE_ENVIRONMENT.json').resolve()),fresh_resource_environment_sha256=sha(D/'FRESH_REMOTE_ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',source_manifest_sha256=hand['driver']['source_manifest_sha256'],launcher_sha256=sha(__file__),reference_only=True,actual_serving_runs=0)
        put(D/'RUN_RECORD_PRELAUNCH.json',record)
        gate([],'ROOT_DEFAULT_BEFORE.json')
        drv_gate=gate(['--source',str((E/'pilot_driver_source_v2').resolve()),'--manifest',str((E/'packages/PILOT_DRIVER_SOURCE_v2.json').resolve()),'--run-record',str((D/'RUN_RECORD_PRELAUNCH.json').resolve())],'DRIVER_EXPLICIT.json')
        pointer=R/'experiments/repository_identity_20261027/CURRENT.json';old=pointer.read_bytes();(D/'CURRENT_BEFORE.json').write_bytes(old);j=json.loads(old)
        j.update(updated_date='2026-11-11',source_worktree=str((E/'baseline_source_v3').resolve()),source_commit=hand['runtime']['source_commit'],source_manifest=str((E/'packages/BASELINE_SOURCE_v3.json').resolve()),source_manifest_sha256=hand['runtime']['source_manifest_sha256'],research_state=str((E/'WORKING_STATE.json').resolve()),GPU_queue='V16_NEW_RUNTIME_REFERENCE_FULL4_THEN_TECHNICAL_PILOT24',scope='New complete shared-dispatch runtime for future owned launches; historical sources/runs and legacy dirty HEAD preserved.',previous_pointer=str((D/'CURRENT_BEFORE.json').resolve()))
        new=D/'CURRENT_NEW.json';put(new,j);os.replace(new,pointer)
        try:nn_gate=gate([],'ROOT_NOARG_RUNTIME.json')
        except BaseException:pointer.write_bytes(old);raise
        destinations=[(nn_gate,hand['Root_gates_to_upload']['root_noarg_runtime']['path']),(drv_gate,hand['Root_gates_to_upload']['driver_explicit']['path'])]
        c.python('from pathlib import Path\nfor p in '+repr([x[1] for x in destinations])+': Path(p).parent.mkdir(parents=True,exist_ok=True)\n')
        for local,remote in destinations:c.put(local,remote)
        c.python('import subprocess\nsubprocess.run('+repr(hand['ordered_commands'][0]['command'])+',check=True)\n',timeout=45)
        prep=hand['ordered_commands'][0]['command'][-1]
        c.get(prep,D/'ENTRY_PRELAUNCH.json')
        rp=P+'/pilot_driver_v2/root_gates/REFERENCE_FULL4_V2_RUN_RECORD_PRELAUNCH.json';c.put(D/'RUN_RECORD_PRELAUNCH.json',rp)
        command=hand['ordered_commands'][1]['command'];launch=dict(command=command,driver=hand['driver'],root=P+'/pilot_driver_v2',out=plan['raw_result_location'],log=O+'/REFERENCE_FULL4_V2.process.log',handle=O+'/REFERENCE_FULL4_V2.HANDLE.json',tmp=B+'/cache/revtrace_dsn_strengthening_v16_20261111/root_launch_tmp',plan_sha=sha(planpath),plan=command[command.index('--plan')+1])
        script='C='+repr(launch)+'\n'+r'''
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys
assert hashlib.sha256(Path(C['plan']).read_bytes()).hexdigest()==C['plan_sha']
assert not Path(C['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
sys.path.insert(0,C['driver']['source_root']);import run_reference
a=argparse.Namespace(plan=C['plan'],manifest=C['driver']['source_manifest'],prelaunch=C['command'][C['command'].index('--prelaunch')+1])
run_reference.boot(a,json.loads(Path(C['plan']).read_bytes()))
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
Path(C['tmp']).mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=C['tmp'])
env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb') as f:
 child=subprocess.Popen(C['command'],cwd=C['driver']['source_root'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
p=Path('/proc')/str(child.pid);ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
h=dict(pid=child.pid,start_ticks=ticks,cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest(),command=C['command'],command_sha256=hashlib.sha256(json.dumps(C['command'],separators=(',',':')).encode()).hexdigest(),out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),driver_commit=C['driver']['source_commit'],reference_only=True,actual_serving_runs=0,actual_model_calls='pending real reference ledger, never assumed zero after launch')
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
'''
        raw=c.python(script,timeout=45);(D/'HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
if __name__=='__main__':main()
