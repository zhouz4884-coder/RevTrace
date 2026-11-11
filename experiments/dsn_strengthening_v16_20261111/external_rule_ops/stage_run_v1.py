"""Do not execute until Root supplies this experiment's new GPU-idle receipt."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'external_rule_ops';PACK=E/'external_rule_packages_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/external_la2_shadow_v1'
O=B+'/results/revtrace/dsn_strengthening_v16_20261111/EXTERNAL_LA2_SHADOW_V1'
OP=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_OPPORTUNITY_AUDIT_V1'
ID='REVTRACE-V16-EXTERNAL-LA2-SHADOW-20261111-V1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt=H/'ROOT_IDLE_V1.json'
if not receipt.exists():raise SystemExit('HELD: no Root-specific CPU idle receipt; do not create one without Root authorization')
r=json.loads(receipt.read_bytes())
assert r['experiment_id']==ID and r['root_authorized_CPU_idle_window'] is True and r['timed_service_active'] is False
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(r['not_after_utc'].replace('Z','+00:00'))
rootgate=H/'ROOT_DEFAULT_PREFLIGHT_V1.json';explicit=H/'ANALYSIS_EXPLICIT_PREFLIGHT_V1.json'
for args in (['--output',str(rootgate)],['--source',str(E/'external_rule_source_v1'),'--manifest',str(PACK/'SOURCE.json'),'--output',str(explicit)]):
 subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args],check=True,capture_output=True)
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with m.Remote() as c:
 code='P='+repr(P)+'\n'+r'''
from pathlib import Path
import subprocess
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'CUDA owner: do not stage formal CPU analysis'
Path(P).mkdir(parents=True,exist_ok=False)
'''
 c.python(code,timeout=60)
 for path,name in ((PACK/'source.bundle','source.bundle'),(PACK/'SOURCE.json','SOURCE.json'),(rootgate,rootgate.name),(explicit,explicit.name),(receipt,receipt.name)):c.put(path,P+'/'+name)
 code='P='+repr(P)+'\nO='+repr(O)+'\nOP='+repr(OP)+'\nBUNDLE_SHA='+repr(sha(PACK/'source.bundle'))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
P=Path(P);S=P/'source';D=P/'prepared_v1';O=Path(O);OP=Path(OP);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'source.bundle')==BUNDLE_SHA
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'source.bundle'),str(S)],check=True)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(S))
cmd=[sys.executable,'-B',str(S/'prepare_idle.py'),'--manifest',str(P/'SOURCE.json'),'--op-config',str(OP/'CONFIG.json'),'--op-gate',str(OP/'GATE.json'),'--idle-receipt',str(P/'ROOT_IDLE_V1.json'),'--out-dir',str(D),'--raw-out',str(O)]
prep=subprocess.run(cmd,cwd=S,env=env,capture_output=True,text=True)
(P/'PREPARE_STDOUT.log').write_text(prep.stdout);(P/'PREPARE_STDERR.log').write_text(prep.stderr)
assert prep.returncode==0,prep.stderr[-6000:]
cmd=[sys.executable,'-B',str(S/'make_prelaunch.py'),'--config',str(D/'CONFIG.json'),'--environment',str(D/'ENVIRONMENT.json'),'--manifest',str(P/'SOURCE.json'),'--root-noarg',str(P/'ROOT_DEFAULT_PREFLIGHT_V1.json'),'--analysis-explicit',str(P/'ANALYSIS_EXPLICIT_PREFLIGHT_V1.json'),'--out',str(P/'PRELAUNCH_V1.json')]
subprocess.run(cmd,cwd=S,env=env,check=True,capture_output=True,text=True)
pre=json.loads((P/'PRELAUNCH_V1.json').read_bytes());cfg=json.loads((D/'CONFIG.json').read_bytes())
assert not O.exists();O.parent.mkdir(parents=True,exist_ok=True)
log=O.parent/'EXTERNAL_LA2_SHADOW_V1_PROCESS.log'
cmd=[sys.executable,'-B',str(S/'run_shadow.py'),'--config',str(D/'CONFIG.json'),'--manifest',str(P/'SOURCE.json'),'--environment',str(D/'ENVIRONMENT.json'),'--prelaunch',str(P/'PRELAUNCH_V1.json'),'--out',str(O)]
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
record=dict(pre,pid=child.pid,start_ticks=ticks,command=cmd,log=str(log),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),input_files=len(cfg['bound_files']),input_bytes=sum(x['bytes'] for x in cfg['bound_files']))
(P/'PROCESS_LAUNCH_V1.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 raw=c.python(code,timeout=60);(H/'PROCESS_LAUNCH_V1.json').write_bytes(raw+b'\n')
 for path,name in ((P+'/prepared_v1/CONFIG.json','CONFIG_V1.json'),(P+'/prepared_v1/ENVIRONMENT.json','ENVIRONMENT_V1.json'),(P+'/PRELAUNCH_V1.json','PRELAUNCH_V1.json'),(P+'/prepared_v1/PREPARATION_RECORD.json','PREPARATION_RECORD_V1.json')):c.get(path,H/name,maximum=4000000)
 print(raw.decode())
