"""Root-owned one-time launch after complete local/remote scientific gates."""
import datetime,hashlib,json,pathlib,shlex,subprocess,sys
T=pathlib.Path(__file__).resolve().parents[1];R=T.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((T/'SERVICE_PILOT_v1_FROZEN.json').read_text(encoding='utf8'));pre=json.loads((T/'SERVICE_PREREQUISITE_v1.json').read_text(encoding='utf8'));review=json.loads((T/'INDEPENDENT_PILOT_CONFIG_REVIEW_v1.json').read_text(encoding='utf8'))
assert pre['plan_sha256']==sha(T/'SERVICE_PILOT_v1_FROZEN.json') and pre['tests']==118 and pre['skipped']==0
assert 'PASS' in str(review.get('status',review.get('gate',''))),review
result=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True)
source=json.loads(result.stdout);assert source['gate']=='SOURCE_IDENTITY_PASS' and source['code_commit']==plan['source_commit']
(T/'SERVICE_SOURCE_PREFLIGHT_v1.json').write_bytes(result.stdout)
P=str(pathlib.PurePosixPath(plan['source_root']).parent);O=str(pathlib.PurePosixPath(plan['raw_result_location']).parent)
code=r'''import datetime,hashlib,json,os,pathlib,subprocess,sys
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);plan=json.loads((P/'SERVICE_PILOT_v1_FROZEN.json').read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'SERVICE_PILOT_v1_FROZEN.json')==PLAN_SHA and sha(O/'SERVICE_PREREQUISITE_v1.json')==PRE_SHA
pre=json.loads((O/'SERVICE_PREREQUISITE_v1.json').read_text());assert pre['status']=='PASS_PILOT_SOURCE_ASSETS_ENVIRONMENT_AND_CPU118_NO_NEURAL_LAUNCH'
assert pre['tests']==118 and pre['skipped']==0
sys.path.insert(0,plan['source_root']);from native_service import verify_source
identity=verify_source(P/'SOURCE_v3.json');assert identity['source_commit']==plan['source_commit'] and sha(P/'SOURCE_v3.json')==plan['source_manifest_sha256']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied; no launch'
base=pathlib.Path(plan['raw_result_location']);assert str(base).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/');assert not base.exists();base.mkdir();(base/'cells').mkdir();(base/'logs').mkdir()
handle=O/'SERVICE_HANDLE_v1.json';assert not handle.exists();log=O/'service_pilot_v1.log';assert not log.exists()
cmd=[sys.executable,'-B',str(pathlib.Path(plan['source_root'])/'run_service_campaign.py'),'--plan',str(P/'SERVICE_PILOT_v1_FROZEN.json'),'--manifest',str(P/'SOURCE_v3.json'),'--out',plan['campaign_output']]
with log.open('x') as stream:child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=cmd,source_commit=identity['source_commit'],source_manifest_sha256=sha(P/'SOURCE_v3.json'),plan_sha256=sha(P/'SERVICE_PILOT_v1_FROZEN.json'),prerequisite_sha256=sha(O/'SERVICE_PREREQUISITE_v1.json'),log=str(log),raw_result_location=str(base),campaign_output=plan['campaign_output'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
handle.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('PLAN_SHA',repr(sha(T/'SERVICE_PILOT_v1_FROZEN.json'))).replace('PRE_SHA',repr(sha(T/'SERVICE_PREREQUISITE_v1.json')))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=60);i.write(code);i.flush();i.channel.shutdown_write();stdout=o.read().decode();stderr=e.read().decode();rc=o.channel.recv_exit_status()
 (T/'SERVICE_LAUNCH_STDOUT_v1.txt').write_text(stdout,encoding='utf8');(T/'SERVICE_LAUNCH_STDERR_v1.txt').write_text(stderr,encoding='utf8');assert rc==0,stderr
 handle=json.loads(stdout);(T/'SERVICE_HANDLE_v1.json').write_text(json.dumps(handle,indent=2)+'\n',encoding='utf8')
 p=T/'CURRENT_STATUS.json';status=json.loads(p.read_text(encoding='utf8'));status.update(status='RUNNING_FROZEN_SOURCE0_THREE_ARM_SERVICE_PILOT',handle=handle,GPU_launched=True,remote_resources_released=False,actual_serving_cells=0,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),next_action='Finish all3 fresh cells and complete task audit, then inspect frozen opportunity gates. No parallel remote heavyCPU/IO/modelsetup.')
 p.write_text(json.dumps(status,indent=2)+'\n',encoding='utf8');print(json.dumps(handle,indent=2))
finally:c.close()
