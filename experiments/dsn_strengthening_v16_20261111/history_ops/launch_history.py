"""Stage frozen offline-only source and launch its preregistered CPU analysis."""
from pathlib import Path
import importlib.util,json,hashlib
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pre=json.loads((H/'PRELAUNCH_v1.json').read_bytes());P=pre['remote_source'].rsplit('/',1)[0]
with m.Remote() as c:
 c.python("from pathlib import Path\np=Path("+repr(P)+");p.mkdir(parents=True,exist_ok=True)\n(p/'metadata').mkdir(exist_ok=True)\nprint('checked frozen CPU staging')\n")
 for name in ('SOURCE_v1.bundle','SOURCE_v1.json','CONFIG_v1.json','ENVIRONMENT_v1.json','PRELAUNCH_v1.json','ROOT_DEFAULT_PREFLIGHT_v1.json'):
  c.put(H/name,P+'/'+name)
 for p in sorted((H/'metadata_v1').glob('*.json')):c.put(p,P+'/metadata/'+p.name)
 program="P="+repr(P)+"\n"+r'''
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
P=Path(P);pre=json.loads((P/'PRELAUNCH_v1.json').read_bytes());S=Path(pre['remote_source']);O=Path(pre['raw_result_location'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'SOURCE_v1.bundle')==pre['source_bundle_sha256']
assert sha(P/'SOURCE_v1.json')==pre['source_manifest_sha256']
assert sha(P/'CONFIG_v1.json')==pre['frozen_config_sha256']
assert sha(P/'ENVIRONMENT_v1.json')==pre['environment_sha256']
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'SOURCE_v1.bundle'),str(S)],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(P/'SOURCE_v1.bundle')],check=True,capture_output=True)
sys.path.insert(0,str(S));from run_content_edit import source_gate
source_gate(json.loads((P/'SOURCE_v1.json').read_bytes()))
env=json.loads((P/'ENVIRONMENT_v1.json').read_bytes())
assert env['python']==sys.version and env['executable']==sys.executable and env['platform']==platform.platform()
assert not O.exists();O.parent.mkdir(parents=True,exist_ok=True)
log=O.parent/'history_cpu_v1_PROCESS.log';assert not log.exists()
args=[sys.executable,'-B',str(S/'run_content_edit.py'),'--config',str(P/'CONFIG_v1.json'),'--source-manifest',str(P/'SOURCE_v1.json'),
 '--environment',str(P/'ENVIRONMENT_v1.json'),'--prelaunch',str(P/'PRELAUNCH_v1.json'),'--out',str(O)]
with log.open('x') as stream:
 child=subprocess.Popen(args,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),
  stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]
record=dict(experiment_id=pre['experiment_id'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=child.pid,start_ticks=ticks,
 argv=args,code_commit=pre['code_commit'],source_manifest_sha256=pre['source_manifest_sha256'],frozen_config_sha256=pre['frozen_config_sha256'],
 environment_sha256=pre['environment_sha256'],raw_result_location=str(O),summary=str(O/'SUMMARY.json'),gate=str(O/'GATE.json'),log=str(log),new_model_calls=0)
(P/'PROCESS_LAUNCH_v1.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
'''
 raw=c.python(program,timeout=60)
 p=H/'PROCESS_LAUNCH_v1.json';assert not p.exists();p.write_bytes(raw+b'\n')
 print(raw.decode())
