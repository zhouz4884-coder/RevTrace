"""Separate provenance for exposure primary/independent CPU29 tasks."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--audit',action='store_true');a=p.parse_args()
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops';tag='METRICS_AUDIT_v2' if a.audit else 'METRICS_v2';stem='exposure_independent_v2' if a.audit else 'exposure_v2'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/'+stem;O=B+'/results/revtrace/dsn_strengthening_v16_20261111/'+stem
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def run(x):return subprocess.check_output(x,text=True,stderr=subprocess.STDOUT).strip()
oldpre=json.loads((H/'PRELAUNCH_v1.json').read_bytes());oldcfg=json.loads((H/'AUDIT_CONFIG_v1.json').read_bytes())
bound=oldcfg['bound_files'];original_config=oldpre['remote_source'].rsplit('/',1)[0]+'/CONFIG_v1.json'
exposure_results=B+'/results/revtrace/dsn_strengthening_v16_20261111/exposure_v2'
if a.audit:
 code='O='+repr(exposure_results)+'\n'+r'''
from pathlib import Path
import hashlib,json
O=Path(O);assert json.loads((O/'GATE.json').read_bytes())['status']=='PASS_ALL29_EXPOSURE_AREA_AND_HORIZON_CURVES'
files=list(O.glob('*.json'))+list((O/'cells').glob('*/*.json'))+[O/'STABLE_PREFIX_CURVES.csv']
print(json.dumps([dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]))
'''
 with m.Remote() as c:extra=json.loads(c.python(code,timeout=60))
 bound=bound+extra
rootgate=H/(tag+'_ROOT_PREFLIGHT.json');run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(rootgate)])
dev=H/'exposure_audit_dev_v2' if a.audit else E/'history_metrics_v2_dev';S=H/(stem+'_source');S.mkdir(exist_ok=False)
for f in sorted(dev.glob('*.py')):ast.parse(f.read_text(encoding='utf8'));shutil.copyfile(f,S/f.name)
(S/'PROTOCOL.md').write_bytes((H/'EXPOSURE_STABLE_PREFIX_V2_PLAN.zh.md').read_bytes())
(S/'.gitattributes').write_text('* -text\n',encoding='utf8');(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
run(['git','-C',str(S),'init']);run(['git','-C',str(S),'config','core.autocrlf','false']);run(['git','-C',str(S),'checkout','-b','codex/'+stem]);run(['git','-C',str(S),'add','.']);run(['git','-C',str(S),'commit','-m','Freeze offline exposure stable prefix and exact final text audit'])
commit=run(['git','-C',str(S),'rev-parse','HEAD']);files=run(['git','-C',str(S),'ls-files']).splitlines();mp=H/(tag+'_SOURCE.json');put(mp,dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in files]))
bundle=H/(tag+'_SOURCE.bundle');run(['git','-C',str(S),'bundle','create',str(bundle),'HEAD']);run(['git','-C',str(R),'bundle','verify',str(bundle)]);run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/heads/codex/'+stem])
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(mp),'--output',str(H/(tag+'_EXPLICIT_PREFLIGHT.json'))])
cfg=dict(experiment_id='REVTRACE-V16-EXPOSURE-'+('INDEPENDENT-' if a.audit else '')+'20261111-V2',analysis_module='exposure_audit_core' if a.audit else 'exposure_core',expected_controls=6,
 designated_experiment_disk_prefix=B,original_config=original_config,original_results=oldpre['raw_result_location'],exposure_results=exposure_results,bound_files=bound,
 actual_original_analysis_source=oldpre['code_commit'],new_model_calls=0,semantics='Exposure proxy and per-source last-actual-observation horizon; retrospective stable prefix; codepoint seconds not validated human reading or causal benefit')
cp=H/(tag+'_CONFIG.json');put(cp,cfg);ep=H/(tag+'_ENVIRONMENT.json');shutil.copyfile(H/'ENVIRONMENT_v1.json',ep)
pre=dict(experiment_id=cfg['experiment_id'],code_commit=commit,source_manifest_sha256=sha(mp),source_bundle_sha256=sha(bundle),frozen_config_sha256=sha(cp),environment_sha256=sha(ep),
 root_preflight_path=P+'/'+rootgate.name,root_preflight_sha256=sha(rootgate),raw_result_location=O,aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',remote_source=P+'/source_v1')
pp=H/(tag+'_PRELAUNCH.json');put(pp,pre)
with m.Remote() as c:
 c.python('from pathlib import Path\nPath('+repr(P)+').mkdir(parents=True,exist_ok=False)\n')
 for path in (mp,bundle,cp,ep,pp,rootgate):c.put(path,P+'/'+path.name)
 program='P='+repr(P)+'\nTAG='+repr(tag)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
P=Path(P);pre=json.loads((P/(TAG+'_PRELAUNCH.json')).read_bytes());S=Path(pre['remote_source']);O=Path(pre['raw_result_location'])
assert hashlib.sha256((P/(TAG+'_SOURCE.bundle')).read_bytes()).hexdigest()==pre['source_bundle_sha256']
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/(TAG+'_SOURCE.bundle')),str(S)],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(P/(TAG+'_SOURCE.bundle'))],check=True,capture_output=True)
assert not O.exists();O.parent.mkdir(parents=True,exist_ok=True);log=O.parent/(O.name+'_PROCESS.log')
args=[sys.executable,'-B',str(S/'run_task.py'),'--config',str(P/(TAG+'_CONFIG.json')),'--manifest',str(P/(TAG+'_SOURCE.json')),'--environment',str(P/(TAG+'_ENVIRONMENT.json')),'--prelaunch',str(P/(TAG+'_PRELAUNCH.json')),'--out',str(O)]
with log.open('x') as f:child=subprocess.Popen(args,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21];record=dict(pre,pid=child.pid,start_ticks=ticks,argv=args,log=str(log),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
(P/'PROCESS_LAUNCH.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 raw=c.python(program,timeout=60)
(H/(tag+'_PROCESS_LAUNCH.json')).write_bytes(raw+b'\n');print(raw.decode())
