"""Launch one frozen cost phase; every experiment role remains distinct."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from remote import Remote,E,B,P,O,PY
R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['cpu','nn'],required=True);a=p.parse_args()
tag='COST_'+a.phase.upper()+'_V1';source=E/'cost/driver_dev';M=E/'packages/COST_DRIVER_V1_SOURCE.json'
commit=json.loads(M.read_bytes())['code_commit'];plan_path=E/'cost/plan_v1/PLAN.json';plan=json.loads(plan_path.read_bytes())
folder=E/'cost'/('launch_'+a.phase+'_v1');folder.mkdir(exist_ok=False);sha=lambda b:hashlib.sha256(b).hexdigest()
out=O+'/'+tag.lower()+'_campaign';remote_plan=P+'/cost_configs_v1/PLAN.json'
support=B+'/projects/revtrace_dsn_strengthening_20261031'
config=dict(experiment_id='REVTRACE_'+tag+'_20261102',phase=a.phase,code_commit=commit,
    driver_manifest_sha256=sha(M.read_bytes()),plan=remote_plan,plan_sha256=sha(plan_path.read_bytes()),
    observer_source_commit=plan['observer_source_commit'],actual_nn_source_commit=plan['actual_nn_source_commit'],
    support_source_commit='a13fa0a335529dc188f7e738877a3acd027ce4a7',cpu_timeout_seconds=180,nn_timeout_seconds=600,
    complete_CPU_cases=12,complete_NN_cases=16,performance_pruning=False)
cfg=folder/'CONFIG.json';cfg.write_bytes((json.dumps(config,indent=2)+'\n').encode())
with Remote() as c:
    c.put(cfg,P+'/'+tag+'_CONFIG.json')
    script='C='+repr(dict(python=PY,source=P+'/cost_driver_v1',commit=commit,nn=a.phase=='nn'))+'\n'+r'''
from pathlib import Path
import datetime,importlib.metadata,json,platform,subprocess,sys
assert subprocess.check_output(['git','-C',C['source'],'rev-parse','HEAD'],text=True).strip()==C['commit']
assert not subprocess.check_output(['git','-C',C['source'],'status','--porcelain','--untracked-files=all'],text=True).strip()
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()
assert not gpu,'Do not overlap this cost phase with another GPU workload'
print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_commit=C['commit'],packages={n:importlib.metadata.version(n) for n in ['torch','transformers','soundfile','numpy']},GPU_processes=gpu,CPU_only=not C['nn'],original_environment_dependency_retained=True)))
'''
    env=c.python(script);envpath=folder/'ENVIRONMENT.json';envpath.write_bytes(env);c.put(envpath,P+'/'+tag+'_ENVIRONMENT.json')
    record=dict(experiment_id=config['experiment_id'],code_commit=commit,
        frozen_config=str(cfg.resolve()),frozen_config_sha256=sha(cfg.read_bytes()),
        environment_record=str(envpath.resolve()),environment_record_sha256=sha(env),
        raw_result_location=out,aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',
        execution_roles=dict(driver=commit,observer=plan['observer_source_commit'],actual_NN=plan['actual_nn_source_commit'],production_support=config['support_source_commit']),
        remote_config=P+'/'+tag+'_CONFIG.json',remote_environment=P+'/'+tag+'_ENVIRONMENT.json',
        plan_sha256=config['plan_sha256'],launcher_sha256=sha(Path(__file__).read_bytes()),
        mirror_scope='Byte-exact root prelaunch mirror; remote driver writes actual record and all phase/cell bindings.')
    rec=folder/'RUN_RECORD_PRELAUNCH.json';rec.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    r=subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(M),'--tag',tag,'--run-record',str(rec)],cwd=R,capture_output=True,check=True)
    print(r.stdout.decode(),flush=True)
    rootgate=E/('ROOT_NOARG_'+tag+'.json');c.put(rootgate,P+'/'+rootgate.name)
    pre=dict(plan_sha256=config['plan_sha256'],root_noarg_preflight=P+'/'+rootgate.name,
        root_noarg_preflight_sha256=sha(rootgate.read_bytes()),cpu_timeout_seconds=180,nn_timeout_seconds=600,
        exclusive_GPU_window_authorized_by_root=a.phase=='nn')
    if a.phase=='nn':
        asset=json.loads((E/'cost/ASSET_BYTE_GATE_v1.json').read_bytes())
        assert asset['gate']=='PASS_DECLARED_MODEL_ASSET_BYTES' and len(asset['rows'])==asset['files']
        declared=dict(status=asset['gate'],all_asset_bytes_verified=True,files=asset['files'],bytes=asset['bytes'],
            original_receipt_sha256=sha((E/'cost/ASSET_BYTE_GATE_v1.json').read_bytes()),source_manifest_sha256=asset['manifest_sha256'],verified_utc=asset['utc'])
        ap=folder/'ASSET_GATE_BINDING.json';ap.write_bytes((json.dumps(declared,indent=2)+'\n').encode());c.put(ap,P+'/'+tag+'_ASSET_GATE.json')
        c.put(E/'cost/ASSET_BYTE_GATE_v1.json',P+'/ASSET_BYTE_GATE_v1.json')
        pre['asset_byte_gate']=dict(path=P+'/'+tag+'_ASSET_GATE.json',sha256=sha(ap.read_bytes()))
    prepath=folder/'PRELAUNCH.json';prepath.write_bytes((json.dumps(pre,indent=2)+'\n').encode());c.put(prepath,P+'/'+tag+'_PRELAUNCH.json')
    params=dict(python=PY,source=P+'/cost_driver_v1',manifest=P+'/'+M.name,plan=remote_plan,prelaunch=P+'/'+tag+'_PRELAUNCH.json',
        prelaunch_sha=sha(prepath.read_bytes()),observer_source=P+'/cost_v1',observer_manifest=P+'/COST_V1_SOURCE.json',
        support_source=support+'/paired_resident_source_v2',support_manifest=support+'/PAIRED_RESIDENT_SOURCE_v2.json',
        out=out,phase=a.phase,log=O+'/'+tag.lower()+'.log',handle=O+'/'+tag.lower()+'_HANDLE.json',commit=commit)
    script='C='+repr(params)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert hashlib.sha256(Path(C['prelaunch']).read_bytes()).hexdigest()==C['prelaunch_sha']
assert not Path(C['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[C['python'],'-B',str(Path(C['source'])/'run_campaign.py'),'--phase',C['phase'],'--plan',C['plan'],'--manifest',C['manifest'],'--prelaunch',C['prelaunch'],'--observer-source',C['observer_source'],'--observer-manifest',C['observer_manifest'],'--support-source',C['support_source'],'--support-manifest',C['support_manifest'],'--out',C['out']]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('CUDA_VISIBLE_DEVICES',None)
if C['phase']=='cpu':env['CUDA_VISIBLE_DEVICES']=''
with Path(C['log']).open('xb') as f:child=subprocess.Popen(cmd,cwd=C['source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
p=Path('/proc')/str(child.pid);ticks=int((p/'stat').read_text().split()[21]);line=(p/'cmdline').read_bytes()
handle=dict(pid=child.pid,start_ticks=ticks,cmdline_sha256=hashlib.sha256(line).hexdigest(),command=cmd,driver_code_commit=C['commit'],out=C['out'],log=C['log'],phase=C['phase'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),prelaunch_sha256=C['prelaunch_sha'])
Path(C['handle']).write_text(json.dumps(handle,indent=2));print(json.dumps(handle))
'''
    raw=c.python(script);(E/'cost'/(tag+'_HANDLE.json')).write_bytes(raw);print(raw.decode())
