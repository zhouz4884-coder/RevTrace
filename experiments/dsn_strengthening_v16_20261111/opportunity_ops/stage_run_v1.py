"""Root-authorized postpilot idle staging and CPU-only opportunity audit."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'opportunity_ops';PACK=E/'opportunity_packages_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/pilot_opportunity_audit_v1';O=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_OPPORTUNITY_AUDIT_V1'
PLAN=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_PREPARATION_V2/SERVICE_PLAN.json'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rootgate=H/'ROOT_DEFAULT_PREFLIGHT_V1.json';explicit=H/'AUDIT_EXPLICIT_PREFLIGHT_V1.json'
for args in (['--output',str(rootgate)],['--source',str(E/'opportunity_audit_source_v1'),'--manifest',str(PACK/'SOURCE.json'),'--output',str(explicit)]):
 subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args],check=True,capture_output=True)
manifest=json.loads((PACK/'SOURCE.json').read_bytes())
with m.Remote() as c:
 code='P='+repr(P)+'\n'+r'''
from pathlib import Path
import datetime,json,subprocess
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'Root idle window has CUDA owner'
P=Path(P);P.mkdir(parents=True,exist_ok=False)
now=datetime.datetime.now(datetime.timezone.utc)
receipt=dict(root_authorized_postpilot_idle_window=True,timed_service_active=False,pilot_driver_confirmed_exited=True,
 pilot_driver_pid=2798710,exit_evidence='Root confirmed original PID generation gone and CUDA empty at2026-11-11T12:17:50UTC',
 pilot_plan_sha256='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6',
 not_after_utc=(now+datetime.timedelta(minutes=25)).isoformat(),created_utc=now.isoformat(),
 authority='Root explicit postpilot CPU window message; no further permission requested')
(P/'ROOT_IDLE_V1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
'''
 raw=c.python(code,timeout=60);(H/'ROOT_IDLE_V1.json').write_bytes(raw+b'\n')
 for path,name in ((PACK/'SOURCE.bundle','SOURCE.bundle'),(PACK/'SOURCE.json','SOURCE.json'),(rootgate,rootgate.name),(explicit,explicit.name)):c.put(path,P+'/'+name)
 code='P='+repr(P)+'\nPLAN='+repr(PLAN)+'\nO='+repr(O)+'\nBUNDLE_SHA='+repr(sha(PACK/'SOURCE.bundle'))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
P=Path(P);S=P/'source';D=P/'prepared_v1';O=Path(O);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'SOURCE.bundle')==BUNDLE_SHA
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'SOURCE.bundle'),str(S)],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(P/'SOURCE.bundle')],check=True,capture_output=True)
cmd=[sys.executable,'-B',str(S/'prepare_postpilot.py'),'--manifest',str(P/'SOURCE.json'),'--plan',PLAN,'--idle-receipt',str(P/'ROOT_IDLE_V1.json'),'--out-dir',str(D),'--raw-out',str(O)]
prep=subprocess.run(cmd,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
(P/'PREPARE_STDOUT.log').write_text(prep.stdout);(P/'PREPARE_STDERR.log').write_text(prep.stderr)
assert prep.returncode==0,prep.stderr[-6000:]
cfg=json.loads((D/'CONFIG.json').read_bytes());manifest=json.loads((P/'SOURCE.json').read_bytes())
pre=dict(experiment_id=cfg['experiment_id'],code_commit=manifest['code_commit'],source_manifest_sha256=sha(P/'SOURCE.json'),
 frozen_config_sha256=sha(D/'CONFIG.json'),environment_sha256=sha(D/'ENVIRONMENT.json'),raw_result_location=str(O),
 aggregate_summary_location=str(O/'SUMMARY.json'),gate_decision_location=str(O/'GATE.json'),
 root_noarg_preflight=str(P/'ROOT_DEFAULT_PREFLIGHT_V1.json'),root_noarg_preflight_sha256=sha(P/'ROOT_DEFAULT_PREFLIGHT_V1.json'),
 audit_explicit_preflight=str(P/'AUDIT_EXPLICIT_PREFLIGHT_V1.json'),audit_explicit_preflight_sha256=sha(P/'AUDIT_EXPLICIT_PREFLIGHT_V1.json'),
 new_model_calls=0,source_root=str(S),frozen_config=str(D/'CONFIG.json'),environment_record=str(D/'ENVIRONMENT.json'))
(P/'PRELAUNCH_V1.json').write_text(json.dumps(pre,indent=2)+'\n')
assert not O.exists();O.parent.mkdir(parents=True,exist_ok=True);log=O.parent/'PILOT_OPPORTUNITY_AUDIT_V1_PROCESS.log'
command=[sys.executable,'-B',str(S/'run_audit.py'),'--config',str(D/'CONFIG.json'),'--manifest',str(P/'SOURCE.json'),'--environment',str(D/'ENVIRONMENT.json'),'--prelaunch',str(P/'PRELAUNCH_V1.json'),'--out',str(O)]
with log.open('x') as f:child=subprocess.Popen(command,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(S)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
record=dict(pre,pid=child.pid,start_ticks=ticks,command=command,log=str(log),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 prepared_input_files=len(cfg['bound_files']),prepared_input_bytes=sum(r['bytes'] for r in cfg['bound_files']),missing_inputs=cfg['missing_inputs_preserved'])
(P/'PROCESS_LAUNCH_V1.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 raw=c.python(code,timeout=60)
 (H/'PROCESS_LAUNCH_V1.json').write_bytes(raw+b'\n')
 for remote,name in ((P+'/prepared_v1/CONFIG.json','CONFIG_V1.json'),(P+'/prepared_v1/ENVIRONMENT.json','ENVIRONMENT_V1.json'),(P+'/PRELAUNCH_V1.json','PRELAUNCH_V1.json'),(P+'/prepared_v1/PREPARATION_RECORD.json','PREPARATION_RECORD_V1.json')):c.get(remote,H/name,maximum=4000000)
 print(raw.decode())
