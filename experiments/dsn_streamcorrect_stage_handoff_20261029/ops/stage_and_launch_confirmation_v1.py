"""Two explicit root phases for the frozen16-cell confirmation; no source changes."""
import argparse,datetime,hashlib,json,pathlib,shlex,subprocess,sys
T=pathlib.Path(__file__).resolve().parents[1];R=T.parents[1];localplan=T/'SERVICE_CONFIRMATION_v1_FROZEN.json';plan=json.loads(localplan.read_text(encoding='utf8'));P=str(pathlib.PurePosixPath(plan['source_root']).parent);O=str(pathlib.PurePosixPath(plan['raw_result_location']).parent)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['stage','launch'],required=True);args=p.parse_args()
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 if args.mode=='stage':
  s=c.open_sftp();directory=P+'/service_confirmation_v1_configs'
  try:s.mkdir(directory)
  except OSError:s.stat(directory)
  pairs=[(localplan,P+'/SERVICE_CONFIRMATION_v1_FROZEN.json')]+[(f,directory+'/'+f.name) for f in sorted((T/'service_confirmation_v1_configs').glob('*.json'))]
  for f,target in pairs:
   assert target.startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/');data=f.read_bytes()
   try:
    with s.open(target,'rb') as r:assert r.read()==data
   except FileNotFoundError:
    with s.open(target,'wb') as r:r.write(data)
  s.close()
  code=r'''import pathlib,json,hashlib,subprocess,sys,datetime
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);p=P/'SERVICE_CONFIRMATION_v1_FROZEN.json';plan=json.loads(p.read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(p)==PLAN_SHA and plan['expected_cells']==16
sys.path.insert(0,plan['source_root']);from native_service import verify_source
i=verify_source(pathlib.Path(plan['source_manifest']));assert i['source_commit']==plan['source_commit'] and sha(plan['source_manifest'])==plan['source_manifest_sha256']
assert sha(plan['prior_source_and_model_gate'])==plan['prior_source_and_model_gate_sha256'];old=json.loads(pathlib.Path(plan['prior_source_and_model_gate']).read_text());assert old['source_commit']==plan['source_commit'] and old['tests']==118 and old['skipped']==0
assert sha(plan['prior_pilot_summary'])==plan['prior_pilot_summary_sha256'];assert json.loads(pathlib.Path(plan['prior_pilot_summary']).read_text())['completed_cells']==3
assert sha(plan['environment_record'])==plan['environment_sha256'];assert sha(plan['reference_details'])==plan['reference_details_sha256'];assert sha(plan['old_task_fidelity_gate'])==plan['old_task_fidelity_gate_sha256']
for cell in plan['cells']:assert sha(cell['config'])==cell['config_sha256']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
r=dict(status='PASS_CONFIRMATION16_UNCHANGED_SOURCE_AND_ENVIRONMENT',source_commit=i['source_commit'],plan_sha256=sha(p),source_manifest_sha256=sha(plan['source_manifest']),prior_model_and_CPU118_gate_sha256=sha(plan['prior_source_and_model_gate']),CPU_tests_reused_unchanged_source=118,new_CPU_tests_run=0,configs_SHA_verified=16,original_reference_sha256=sha(plan['reference_details']),GPU_launched=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
out=O/'CONFIRMATION_PREREQUISITE_v1.json';assert not out.exists();out.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
'''
 else:
  review=json.loads((T/'INDEPENDENT_CONFIRMATION_CONFIG_REVIEW_v1.json').read_text(encoding='utf8'));assert 'PASS' in str(review.get('status',review.get('gate',''))),review
  pointer=R/'experiments/repository_identity_20261027/CURRENT.json';backup=T/'CURRENT_BEFORE_SERVICE_CONFIRMATION_v1.json'
  if not backup.exists():backup.write_bytes(pointer.read_bytes())
  x=json.loads(pointer.read_text(encoding='utf8'));assert x['source_commit']==plan['source_commit'];x.update(GPU_queue='FROZEN_FOUR_SOURCE_16CELL_NATIVE_SERVICE_CONFIRMATION',previous_pointer=str(backup));pointer.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
  check=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);identity=json.loads(check.stdout);assert identity['gate']=='SOURCE_IDENTITY_PASS' and identity['code_commit']==plan['source_commit'];(T/'CONFIRMATION_SOURCE_PREFLIGHT_v1.json').write_bytes(check.stdout)
  env=T/'service_cpu_v3/ENVIRONMENT.json';record=dict(experiment_id=plan['experiment_id'],code_commit=plan['source_commit'],frozen_config=str(localplan),frozen_config_sha256=sha(localplan),environment_record=str(env),environment_record_sha256=sha(env),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['aggregate_summary_location'],gate_decision_location=plan['gate_decision_location']);(T/'CONFIRMATION_PRELAUNCH_RECORD_v1.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
  code=r'''import pathlib,json,hashlib,subprocess,sys,os,datetime
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);p=P/'SERVICE_CONFIRMATION_v1_FROZEN.json';plan=json.loads(p.read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(p)==PLAN_SHA and sha(O/'CONFIRMATION_PREREQUISITE_v1.json')==PRE_SHA
assert json.loads((O/'CONFIRMATION_PREREQUISITE_v1.json').read_text())['status']=='PASS_CONFIRMATION16_UNCHANGED_SOURCE_AND_ENVIRONMENT'
sys.path.insert(0,plan['source_root']);from native_service import verify_source
i=verify_source(pathlib.Path(plan['source_manifest']));assert i['source_commit']==plan['source_commit']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
base=pathlib.Path(plan['raw_result_location']);assert str(base).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/');assert not base.exists();base.mkdir();(base/'cells').mkdir();(base/'logs').mkdir();handle=O/'CONFIRMATION_HANDLE_v1.json';assert not handle.exists();log=O/'service_confirmation_v1.log';assert not log.exists()
cmd=[sys.executable,'-B',str(pathlib.Path(plan['source_root'])/'run_service_campaign.py'),'--plan',str(p),'--manifest',plan['source_manifest'],'--out',plan['campaign_output']]
with log.open('x') as stream:child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
proc=pathlib.Path('/proc')/str(child.pid);r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=cmd,source_commit=i['source_commit'],source_manifest_sha256=sha(plan['source_manifest']),plan_sha256=sha(p),prerequisite_sha256=sha(O/'CONFIRMATION_PREREQUISITE_v1.json'),log=str(log),raw_result_location=str(base),campaign_output=plan['campaign_output'],planned_cells=16,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());handle.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
'''.replace('PRE_SHA',repr(sha(T/'CONFIRMATION_PREREQUISITE_v1.json')))
 code=code.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('PLAN_SHA',repr(sha(localplan)))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=60);i.write(code);i.flush();i.channel.shutdown_write();stdout=o.read().decode();stderr=e.read().decode();rc=o.channel.recv_exit_status();(T/('CONFIRMATION_'+args.mode.upper()+'_STDOUT_v1.txt')).write_text(stdout,encoding='utf8');(T/('CONFIRMATION_'+args.mode.upper()+'_STDERR_v1.txt')).write_text(stderr,encoding='utf8');assert rc==0,stderr
 result=json.loads(stdout)
 if args.mode=='stage':
  s=c.open_sftp();s.get(O+'/CONFIRMATION_PREREQUISITE_v1.json',str(T/'CONFIRMATION_PREREQUISITE_v1.json'));s.close()
 else:
  (T/'CONFIRMATION_HANDLE_v1.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');path=T/'CURRENT_STATUS.json';status=json.loads(path.read_text(encoding='utf8'));status.update(status='RUNNING_FROZEN_FOUR_OLD_SOURCE_16CELL_SERVICE_CONFIRMATION',confirmation_handle=result,completed_pilot_cells=3,current_campaign_completed=0,planned_current_campaign_cells=16,remote_resources_released=False,GPU_launched=True,next_action='Finish all16 old-source confirmation cells and audit before any new-source measurement; no heavy remote CPU/IO/model setup concurrently.');path.write_text(json.dumps(status,indent=2)+'\n',encoding='utf8')
 print(json.dumps(result,indent=2))
finally:c.close()
