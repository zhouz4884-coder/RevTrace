"""Stage and detach the supplemental CPU audit after the complete frozen recount."""
from pathlib import Path
import hashlib,json,shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028'
program=r'''
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_physical_retirement_20261028'
O=B/'results/revtrace/physical_retirement_20261028'
assert json.loads((O/'dsn_joint_analysis_v2/GATE.json').read_text())['gate']=='PASS_OFFLINE_RECOUNT'
assert json.loads((O/'dsn_joint_controller_v1/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
manifest=P/'DSN_JOINT_DETAIL_SOURCE_v2.json'
m=json.loads(manifest.read_text())
source=P/'dsn_joint_detail_source_v2'
if not source.exists():subprocess.run(['git','clone','--quiet',str(P/'DSN_JOINT_DETAIL_SOURCE_v2.bundle'),str(source)],check=True)
def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:
 f=source/r['path'];assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
out=O/'dsn_joint_detail_v2';log=O/'dsn_joint_detail_v2.log';handle=P/'DSN_JOINT_DETAIL_HANDLE_v2.json'
assert not out.exists() and not log.exists() and not handle.exists()
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(source/'audit_presence_consumer_v1.py'),'--plan',str(P/'DSN_JOINT_PLAN_v1_FROZEN.json'),'--analysis',str(O/'dsn_joint_analysis_v2'),'--out',str(out),'--source-manifest',str(manifest)]
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),timed_GPU_processes=0,CUDA_VISIBLE_DEVICES='')
preflight=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-ACTUAL-INPUT-CONSUMER-AUDIT',code_commit=m['code_commit'],source_manifest=str(manifest),source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),frozen_plan=str(P/'DSN_JOINT_PLAN_v1_FROZEN.json'),frozen_plan_sha256=hashlib.sha256((P/'DSN_JOINT_PLAN_v1_FROZEN.json').read_bytes()).hexdigest(),environment=environment,environment_sha256=hashlib.sha256(json.dumps(environment,sort_keys=True,separators=(',',':')).encode()).hexdigest(),argv=argv,raw_result_location=str(O/'dsn_joint_v1'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'))
with (P/'DSN_JOINT_DETAIL_PREFLIGHT_v2.json').open('x') as stream:json.dump(preflight,stream,indent=2);stream.write('\n')
with log.open('x') as stream:
 child=subprocess.Popen(argv,cwd=source,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid))
h=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-ACTUAL-INPUT-CONSUMER-AUDIT',pid=child.pid,start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=argv,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),output=str(out),log=str(log))
with handle.open('x') as stream:json.dump(h,stream,indent=2);stream.write('\n')
print(json.dumps(h))
'''
client=ssh_client()
try:
 sftp=client.open_sftp()
 try:
  for name in ['DETAIL_SOURCE_v2.json','DETAIL_SOURCE_v2.bundle']:
   target=P+'/DSN_JOINT_'+name
   try:
    with sftp.open(target,'rb') as stream:existing=stream.read()
    assert existing==(HERE/name).read_bytes(),'never replace frozen source'
   except FileNotFoundError:sftp.put(str(HERE/name),target)
 finally:sftp.close()
 i,o,e=client.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45)
 i.write(program);i.flush();i.channel.shutdown_write()
 result=o.read();error=e.read();assert o.channel.recv_exit_status()==0,error.decode('utf8',errors='replace')
 print(result.decode('utf8'))
finally:client.close()
