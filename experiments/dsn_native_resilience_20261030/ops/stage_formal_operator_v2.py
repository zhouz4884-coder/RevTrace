"""Root-gated formal operator/Linux26 preparation only; never launches NN."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--plan',type=pathlib.Path,default=F/'FORMAL_SHORT28_v1_FROZEN.json');a=p.parse_args()
if not a.execute:print(json.dumps(dict(status='DRY_RUN_NO_MUTATION',plan=str(a.plan),operator_source_commit=read(F/'packages/FORMAL_OPERATOR_SOURCE_v2.json')['source_commit'],CPU_expected=26,NN_launches=0)));raise SystemExit(0)
plan=read(a.plan);assert plan['campaign_kind']=='formal_short28','This one-time operator/short85 readiness stage is short28 only; sustained8 uses its own immutable input stage.'
operator=read(F/'packages/FORMAL_OPERATOR_SOURCE_v2.json');assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==operator['source_commit']
pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=F/'FORMAL_OPERATOR_REMOTE_STAGE_ROOT_NOARG_v2.json';assert not target.exists();target.write_bytes(pre.stdout)
pairs=[(F/'packages/FORMAL_OPERATOR_SOURCE_v2.json',P+'/FORMAL_OPERATOR_SOURCE_v2.json'),(F/'packages/FORMAL_OPERATOR_SOURCE_v2.bundle',P+'/FORMAL_OPERATOR_SOURCE_v2.bundle'),(a.plan,P+'/'+a.plan.name),(F/'SHORT_REFERENCE_EXPORT_RESULTS_v1/DETAILS.json',plan['reference_details']),(F/'SHORT_REFERENCE_EXPORT_RESULTS_v1/GATE.json',plan['reference_gate'])]
for cell in plan['cells']:
 remote=pathlib.PurePosixPath(cell['config']);local=F/remote.parent.name/remote.name;assert sha(local)==cell['config_sha256'];pairs.append((local,str(remote)))
script=r'''import pathlib,json,hashlib,subprocess,sys,os,platform,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);planpath=P/PLANNAME;plan=json.loads(planpath.read_bytes());M=P/'FORMAL_OPERATOR_SOURCE_v2.json';m=json.loads(M.read_bytes());S=P/'formal_operator_source_v2'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(planpath)==PLANSHA and sha(M)==OPSHA
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host; no heavy staging CPU'
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'FORMAL_OPERATOR_SOURCE_v2.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
sys.path.insert(0,str(S));import run_campaign as op
identity=op.verify_checkout(S,M,m['source_commit'],5);nnpre=O/'RUNTIME_PREREQUISITE_v2.json';assert sha(nnpre)==NNPRESHA
op.validate_inputs(planpath,nnpre,NNPRESHA)
out=O/'formal_operator_cpu_v2';out.mkdir();tmp=out/'tmp';tmp.mkdir()
put=lambda path,value:path.write_bytes((json.dumps(value,indent=2)+'\n').encode())
cfg=dict(experiment_id='SC_FINAL_FORMAL_OPERATOR26_LINUX_CPU_V2',code_commit=m['source_commit'],operator_manifest_sha256=sha(M),NN_source_commit=plan['source_commit'],frozen_plan_sha256=sha(planpath),expected_tests=26,trained_models_loaded=False,actual_serving_cells=0);put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',trained_models_loaded=False));put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
harness="import io,json,unittest; suite=unittest.defaultTestLoader.discover('.',pattern='test_*.py'); stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); print(stream.getvalue()); print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()))); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==26 and not result.skipped else 1)"
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp),XDG_CACHE_HOME=str(out/'cache'))
run=subprocess.run([sys.executable,'-B','-c',harness],cwd=S,capture_output=True,env=environment);(out/'unittest.log').write_bytes(run.stdout+run.stderr);result=json.loads(run.stdout.splitlines()[-1]);gate=dict(status='PASS_FORMAL_OPERATOR26_LINUX_CPU_ZERO_SKIP' if run.returncode==0 else 'FAIL_FORMAL_OPERATOR_CPU_PRESERVED',code_commit=m['source_commit'],source_manifest_sha256=sha(M),model_calls=0,actual_serving_cells=0,**result);put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate);assert run.returncode==0 and result['tests']==26 and result['skipped']==0
op.verify_checkout(S,M,m['source_commit'],5);op.validate_inputs(planpath,nnpre,NNPRESHA);gpu=op.gpu_empty()
receipt=dict(status='PASS_FINAL_FORMAL_OPERATOR_SOURCE_CPU_AND_ALL_FROZEN_INPUTS_NO_NN',operator_source_commit=m['source_commit'],operator_manifest_sha256=sha(M),neural_source_commit=plan['source_commit'],neural_prerequisite_sha256=NNPRESHA,plan_sha256=sha(planpath),environment_sha256=plan['environment_sha256'],runtime_environment=plan['runtime_environment'],reference_details_sha256=plan['reference_details_sha256'],reference_gate_sha256=plan['reference_gate_sha256'],operator_CPU_gate=str(out/'GATE.json'),operator_CPU_gate_sha256=sha(out/'GATE.json'),tests=26,skipped=0,actual_serving_cells=0,GPU=gpu)
rp=O/'FORMAL_OPERATOR_PREREQUISITE_v2.json';assert not rp.exists();put(rp,receipt);print(json.dumps(receipt))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANNAME',repr(a.plan.name)).replace('PLANSHA',repr(sha(a.plan))).replace('OPSHA',repr(sha(F/'packages/FORMAL_OPERATOR_SOURCE_v2.json'))).replace('NNPRESHA',repr(sha(F/'RUNTIME_PREREQUISITE_v2.json')))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 # The remote idle probe precedes all immutable transfer work.
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0,'NN owns host; defer stage'
 s=c.open_sftp();dirs=set()
 for local,remote in pairs:
  folder=str(pathlib.PurePosixPath(remote).parent)
  if folder not in dirs:
   try:s.stat(folder)
   except FileNotFoundError:s.mkdir(folder)
   dirs.add(folder)
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as stream:assert stream.read()==data,'existing immutable bytes differ'
  except FileNotFoundError:
   with s.open(remote,'wx') as stream:stream.write(data);stream.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=300);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'FORMAL_OPERATOR_STAGE_STDOUT_v2.txt').write_bytes(stdout);(F/'FORMAL_OPERATOR_STAGE_STDERR_v2.txt').write_bytes(stderr);assert rc==0,stderr.decode();(F/'FORMAL_OPERATOR_PREREQUISITE_v2.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()
