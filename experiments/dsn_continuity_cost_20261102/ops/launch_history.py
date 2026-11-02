"""Launch the frozen original-clock history analysis with immutable bindings."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from remote import Remote,E,B,P,O,PY
R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--selection',choices=['positive3','all','current_s_on'],required=True)
p.add_argument('--version',type=int,choices=[2,3],default=2);a=p.parse_args()
name='HISTORY_V'+str(a.version);tag='H_'+a.selection.upper()+'_V'+str(a.version)
M=E/'packages'/(name+'_SOURCE.json');commit=json.loads(M.read_bytes())['code_commit']
source=E/('history/source_v'+str(a.version));source_remote=P+'/history_v'+str(a.version)
plan=E/'history/plans'/tag;plan.mkdir(parents=True,exist_ok=False)
current=a.selection=='current_s_on'
config=json.loads((E/'history'/('CURRENT_CONFIG.json' if current else 'CONFIG.json')).read_bytes());config.update(experiment_id='REVTRACE_'+tag+'_20261102',selection=a.selection)
cfg=plan/'CONFIG.json';cfg.write_bytes((json.dumps(config,indent=2)+'\n').encode())
bank=E/'history'/('CURRENT_BANK_MANIFEST.json' if current else 'BANK_MANIFEST.json');sha=lambda b:hashlib.sha256(b).hexdigest()
out=O+'/'+tag.lower();remote_config=P+'/'+tag+'_CONFIG.json';remote_env=P+'/'+tag+'_ENVIRONMENT.json';bank_remote=P+('/HISTORY_CURRENT_BANK_MANIFEST.json' if current else '/HISTORY_BANK_MANIFEST.json')
with Remote() as c:
    c.put(cfg,remote_config);c.put(bank,bank_remote)
    script='C='+repr(dict(source=source_remote,manifest=P+'/'+M.name,commit=commit,tmp=O+'/history_tmp'))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,platform,subprocess,sys
s=Path(C['source']);m=json.loads(Path(C['manifest']).read_bytes())
def git(*a):return subprocess.check_output(['git','-C',str(s),*a],text=True).strip()
assert git('rev-parse','HEAD')==C['commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (s/r['path']).stat().st_size==r['bytes'] and hashlib.sha256((s/r['path']).read_bytes()).hexdigest()==r['sha256']
Path(C['tmp']).mkdir(exist_ok=True)
print(json.dumps(dict(executable=sys.executable,python=sys.version,platform=platform.platform(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_commit=C['commit'],complete_files=len(m['files']),CUDA_VISIBLE_DEVICES='',TMPDIR=C['tmp'],scope='CPU original-clock offline analysis, no model calls')))
'''
    env=c.python(script);(plan/'ENVIRONMENT.json').write_bytes(env);c.put(plan/'ENVIRONMENT.json',remote_env)
    record=dict(experiment_id=config['experiment_id'],code_commit=commit,
        frozen_config=str(cfg.resolve()),frozen_config_sha256=sha(cfg.read_bytes()),
        environment_record=str((plan/'ENVIRONMENT.json').resolve()),environment_record_sha256=sha(env),
        raw_result_location=out,aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',
        remote_config=remote_config,remote_environment=remote_env,raw_input_manifest=bank_remote,
        raw_input_manifest_sha256=sha(bank.read_bytes()),source_manifest=str(M.resolve()),source_manifest_sha256=sha(M.read_bytes()),
        mirror_scope='Windows byte-exact prelaunch input mirror; original analysis writes its actual remote paths.',launcher_sha256=sha(Path(__file__).read_bytes()))
    rec=plan/'RUN_RECORD_PRELAUNCH.json';rec.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    r=subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(M),'--tag',tag,'--run-record',str(rec)],cwd=R,capture_output=True,check=True)
    print(r.stdout.decode(),flush=True)
    rootgate=E/('ROOT_NOARG_'+tag+'.json');c.put(rootgate,P+'/'+rootgate.name);c.put(rec,P+'/'+tag+'_PRELAUNCH.json')
    params=dict(source=source_remote,source_manifest=P+'/'+M.name,commit=commit,config=remote_config,environment=remote_env,
        record=P+'/'+tag+'_PRELAUNCH.json',config_sha=record['frozen_config_sha256'],env_sha=record['environment_record_sha256'],
        bank=bank_remote,bank_sha=record['raw_input_manifest_sha256'],rootgate=P+'/'+rootgate.name,rootgate_sha=sha(rootgate.read_bytes()),
        selection=a.selection,out=out,python=PY,tmp=O+'/history_tmp',log=O+'/'+tag.lower()+'.log',handle=O+'/'+tag.lower()+'_HANDLE.json')
    script='C='+repr(params)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['config'])==C['config_sha'] and sha(C['environment'])==C['env_sha'] and sha(C['bank'])==C['bank_sha'] and sha(C['rootgate'])==C['rootgate_sha']
g=json.loads(Path(C['rootgate']).read_bytes());assert g['run_record_prelaunch_checked'] and g['code_commit']==C['commit']
assert not Path(C['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'Do not add CPU analysis load during another GPU study'
cmd=[C['python'],'-B',str(Path(C['source'])/'history_analysis.py'),'--manifest',C['bank'],'--config',C['config'],'--source-commit',C['commit'],'--source-manifest',C['source_manifest'],'--selection',C['selection'],'--output',C['out']]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=C['tmp'])
with Path(C['log']).open('xb') as f:proc=subprocess.Popen(cmd,cwd=C['source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
stat=Path('/proc')/str(proc.pid)/'stat';ticks=int(stat.read_text().split()[21]);line=(Path('/proc')/str(proc.pid)/'cmdline').read_bytes()
h=dict(pid=proc.pid,start_ticks=ticks,cmdline_sha256=hashlib.sha256(line).hexdigest(),command=cmd,code_commit=C['commit'],out=C['out'],log=C['log'],selection=C['selection'],root_prelaunch_gate=C['rootgate'],root_prelaunch_gate_sha256=C['rootgate_sha'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
Path(C['handle']).write_text(json.dumps(h,indent=2));print(json.dumps(h))
'''
    handle=c.python(script);(E/'history'/(tag+'_HANDLE.json')).write_bytes(handle);print(handle.decode())
