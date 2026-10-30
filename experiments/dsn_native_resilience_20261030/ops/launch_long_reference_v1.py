"""Root-owned launch of the already frozen continuous-author native oracle."""
import datetime,hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];D=F.parent/'dsn_native_sustained_20261030'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
planpath=D/'LONG_REFERENCE_PLAN_v1_FROZEN.json';plan=read(planpath);pre=F/'RUNTIME_PREREQUISITE_v1_r2.json'
assert sha(planpath)=='79b1c3ace4bd419ea998ed3dec37f73a4487122a7228d8bc00fcb15940b92efb'
assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==plan['source_commit']
rootcheck=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],cwd=R,capture_output=True,check=True)
rootrecord=F/'LONG_REFERENCE_ROOT_PREFLIGHT_v1.json';assert not rootrecord.exists();rootrecord.write_bytes(rootcheck.stdout)
record=dict(experiment_id=plan['experiment_id'],code_commit=plan['source_commit'],source_manifest_sha256=plan['source_manifest_sha256'],frozen_config=P+'/'+planpath.name,config_sha256=sha(planpath),environment_record=plan['environment_record'],environment_sha256=plan['environment_record_sha256'],prerequisite_sha256=sha(pre),source_receipt_sha256=plan['source_receipt_sha256'],raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['aggregate_summary_location'],gate_decision_location=plan['gate_decision_location'],reference_only=True,actual_serving_cells=0,launcher_sha256=sha(__file__))
prelaunch=F/'LONG_REFERENCE_PRELAUNCH_v1.json';assert not prelaunch.exists();prelaunch.write_bytes((json.dumps(record,indent=2)+'\n').encode())
script=r'''import pathlib,json,hashlib,subprocess,sys,os,datetime,importlib.metadata
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);p=P/PLANNAME;plan=json.loads(p.read_bytes());prepath=O/'RUNTIME_PREREQUISITE_v1_r2.json'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(p)==PLANSHA and sha(prepath)==PRESHA
pre=json.loads(prepath.read_bytes());assert pre['tests']==249 and pre['skipped']==0 and pre['source_commit']==plan['source_commit']
assert sha(pre['CPU_gate'])==pre['CPU_gate_sha256'];cpu=json.loads(pathlib.Path(pre['CPU_gate']).read_bytes());assert cpu['status']=='PASS_ALL_FROZEN_SOURCE_CPU_ZERO_SKIP' and cpu['skipped']==0
assert sha(plan['source_manifest'])==plan['source_manifest_sha256'];sys.path.insert(0,plan['source_root']);from native_service import verify_source;verify_source(pathlib.Path(plan['source_manifest']))
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host'
for key in ('environment_record','source_receipt'):assert sha(plan[key])==plan[key+'_sha256']
env=json.loads(pathlib.Path(plan['environment_record']).read_bytes());assert {k:importlib.metadata.version(k) for k in env['packages']}==env['packages']
receipt=json.loads(pathlib.Path(plan['source_receipt']).read_bytes());assert receipt['sources']==plan['settings']['sources']
audio=[]
for source in plan['settings']['model_sources']:
 assert sha(source['path'])==source['audio_sha256'];audio.append(dict(source_id=source['source_id'],sha256=source['audio_sha256'],frames=source['frames']))
for asset in pre['assets']:assert pathlib.Path(asset['path']).stat().st_size==asset['bytes']
contract=plan['settings']['backend']['contract'];author=pathlib.Path(plan['settings']['backend']['author_root'])
assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==contract['native_author_commit']
assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip()
for row in pre['author_files']:assert sha(author/row['path'])==row['sha256']
raw=pathlib.Path(plan['raw_result_location']);log=O/'long_reference_v1.log';assert not raw.exists() and not log.exists()
ready=dict(status='PASS_ACTUAL_FROZEN_LONG_ORACLE_PREREQUISITES',source_commit=plan['source_commit'],source_manifest_sha256=sha(plan['source_manifest']),plan_sha256=sha(p),prior_complete_asset_CPU_prerequisite_sha256=sha(prepath),environment_sha256=sha(plan['environment_record']),source_receipt_sha256=sha(plan['source_receipt']),audio=audio,reference_only=True,actual_serving_cells=0)
target=O/'LONG_REFERENCE_PREREQUISITE_v1.json';assert not target.exists();target.write_bytes((json.dumps(ready,indent=2)+'\n').encode())
command=[sys.executable,'-B',str(pathlib.Path(plan['source_root'])/'long_reference.py'),'--plan',str(p),'--manifest',plan['source_manifest'],'--out',str(raw)]
childenv=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');childenv.pop('CUDA_VISIBLE_DEVICES',None)
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=childenv)
proc=pathlib.Path('/proc')/str(child.pid);handle=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit=plan['source_commit'],plan_sha256=sha(p),prerequisite_sha256=sha(target),out=str(raw),log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0)
hp=O/'LONG_REFERENCE_HANDLE_v1.json';assert not hp.exists();hp.write_bytes((json.dumps(handle,indent=2)+'\n').encode());print(json.dumps(handle))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANNAME',repr(planpath.name)).replace('PLANSHA',repr(sha(planpath))).replace('PRESHA',repr(sha(pre)))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp();remote=P+'/'+planpath.name;data=planpath.read_bytes()
 try:
  with s.open(remote,'rb') as stream:assert stream.read()==data
 except FileNotFoundError:
  with s.open(remote,'wx') as stream:stream.write(data);stream.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=40);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'LONG_REFERENCE_LAUNCH_STDOUT_v1.txt').write_bytes(stdout);(F/'LONG_REFERENCE_LAUNCH_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();(F/'LONG_REFERENCE_HANDLE_v1.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()
