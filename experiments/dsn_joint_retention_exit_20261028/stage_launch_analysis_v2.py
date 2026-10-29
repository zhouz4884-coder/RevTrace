"""Preserve failed v1 and launch the clean fixture-identity CPU repair."""
from pathlib import Path
import hashlib,json,shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_physical_retirement_20261028'
manifest_sha=hashlib.sha256((HERE/'ANALYSIS_SOURCE_v2.json').read_bytes()).hexdigest()
program=r'''
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_physical_retirement_20261028';O=B/'results/revtrace/physical_retirement_20261028'
old=json.loads((O/'dsn_joint_analysis_v1/SUMMARY.json').read_text());assert old['accepted']==0 and len(old['failures'])==24 and all('input fixture changed' in r['error'] for r in old['failures'])
assert json.loads((O/'dsn_joint_controller_v1/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
manifest=P/'DSN_JOINT_ANALYSIS_SOURCE_v2.json';assert hashlib.sha256(manifest.read_bytes()).hexdigest()==MANIFEST_SHA
m=json.loads(manifest.read_text());source=P/'dsn_joint_analysis_source_v2'
if not source.exists():subprocess.run(['git','clone','--quiet',str(P/'DSN_JOINT_ANALYSIS_SOURCE_v2.bundle'),str(source)],check=True)
def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for row in m['files']:
 f=source/row['path'];assert f.stat().st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']
out=O/'dsn_joint_analysis_v2';log=O/'dsn_joint_analysis_v2.log';handle=P/'DSN_JOINT_ANALYSIS_HANDLE_v2.json'
assert not out.exists() and not log.exists() and not handle.exists()
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(source/'joint_recount.py'),'--source-manifest',str(manifest),'--plan',str(P/'DSN_JOINT_PLAN_v1_FROZEN.json'),'--out',str(out)]
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='')
pre=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-OFFLINE-RECOUNT-v2',code_commit=m['code_commit'],source_manifest_sha256=MANIFEST_SHA,frozen_plan_sha256=hashlib.sha256((P/'DSN_JOINT_PLAN_v1_FROZEN.json').read_bytes()).hexdigest(),environment=environment,environment_sha256=hashlib.sha256(json.dumps(environment,sort_keys=True,separators=(',',':')).encode()).hexdigest(),argv=argv,raw_result_location=str(O/'dsn_joint_v1'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),preserved_failure=str(O/'dsn_joint_analysis_v1'))
with (P/'DSN_JOINT_ANALYSIS_PREFLIGHT_v2.json').open('x') as stream:json.dump(pre,stream,indent=2);stream.write('\n')
with log.open('x') as stream:child=subprocess.Popen(argv,cwd=source,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id=pre['experiment_id'],pid=child.pid,start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=argv,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),output=str(out),log=str(log))
with handle.open('x') as stream:json.dump(h,stream,indent=2);stream.write('\n')
print(json.dumps(h))
'''.replace('MANIFEST_SHA',repr(manifest_sha))
client=ssh_client()
try:
 s=client.open_sftp()
 try:
  for name in ['ANALYSIS_SOURCE_v2.json','ANALYSIS_SOURCE_v2.bundle']:
   target=P+'/DSN_JOINT_'+name
   try:
    with s.open(target,'rb') as stream:existing=stream.read()
    assert existing==(HERE/name).read_bytes()
   except FileNotFoundError:s.put(str(HERE/name),target)
 finally:s.close()
 i,o,e=client.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45);i.write(program);i.flush();i.channel.shutdown_write()
 raw=o.read();error=e.read();assert o.channel.recv_exit_status()==0,error.decode();print(raw.decode())
finally:client.close()
