"""Run frozen359b literal/strict-clock audit after both actual formal groups."""
import hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030/native_work_recount_v1';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
M=F/'packages/NATIVE_WORK_SOURCE_v1.json';m=read(M);assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==m['source_commit'];pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=F/'NATIVE_WORK_REMOTE_ROOT_NOARG_v1.json';assert not target.exists();target.write_bytes(pre.stdout);plans=[F/'FORMAL_SHORT28_v1_FROZEN.json',F/'FORMAL_SUSTAINED8_v1_FROZEN.json']
script=r'''import pathlib,json,hashlib,subprocess,sys,os,platform,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);M=P/'NATIVE_WORK_SOURCE_v1.json';S=P/'native_work_source_v1';m=json.loads(M.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha(M)==MSHA and not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'NATIVE_WORK_SOURCE_v1.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
sys.path.insert(0,str(S));from run_recount import identity
assert identity(S,M)==m['source_commit'];assert identity(P/'source_v2',P/'SOURCE_v2.json')=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
cells=[];bindings=[]
for name,digest in PLANS:
 pp=P/name;assert sha(pp)==digest;plan=json.loads(pp.read_bytes());gate=json.loads(pathlib.Path(plan['gate_decision_location']).read_bytes());assert gate['status']=='PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE' and gate['completed_cells']==plan['expected_cells'];cells.extend(plan['cells']);bindings.append(dict(path=str(pp),sha256=digest))
assert len(cells)==len({c['cell_id'] for c in cells})==36;O.mkdir();cpu=O/'cpu';cpu.mkdir();tmp=cpu/'tmp';tmp.mkdir();put=lambda p,x:p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
cfg=dict(experiment_id='SC_SELECTED_NATIVE_MARKER_STRICT_CLOCK_CPU8_LINUX_V1',code_commit=m['source_commit'],expected_tests=8,new_model_calls=0);put(cpu/'CONFIG.json',cfg);put(cpu/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0));put(cpu/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(cpu/'CONFIG.json'),config_sha256=sha(cpu/'CONFIG.json'),environment_record=str(cpu/'ENVIRONMENT.json'),environment_sha256=sha(cpu/'ENVIRONMENT.json'),raw_result_location=str(cpu/'unittest.log'),aggregate_summary_location=str(cpu/'GATE.json'),gate_decision_location=str(cpu/'GATE.json'),new_model_calls=0))
harness="import io,json,unittest; suite=unittest.defaultTestLoader.discover('.',pattern='test_*.py'); stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); print(stream.getvalue()); print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()))); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==8 and not result.skipped else 1)";env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp));r=subprocess.run([sys.executable,'-B','-c',harness],cwd=S,capture_output=True,env=env);(cpu/'unittest.log').write_bytes(r.stdout+r.stderr);test=json.loads(r.stdout.splitlines()[-1]);put(cpu/'GATE.json',dict(status='PASS_FROZEN_NATIVE_COUNTER_CPU8_LINUX_ZERO_SKIP' if r.returncode==0 else 'FAIL_CPU_PRESERVED',code_commit=m['source_commit'],new_model_calls=0,**test));assert r.returncode==0 and test['tests']==8 and test['skipped']==0
config=dict(experiment_id='SC_FORMAL36_LITERAL_SELECTED_NATIVE_AND_STRICT_FAULT_CLOCK_V1',code_commit=m['source_commit'],runtime_source=str(P/'source_v2'),runtime_manifest=str(P/'SOURCE_v2.json'),runtime_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',runtime_manifest_sha256=sha(P/'SOURCE_v2.json'),expected_cells=36,cells=cells,original_plans=bindings,new_model_calls=0);cp=O/'RECOUNT_CONFIG_FROZEN.json';put(cp,config)
with (O/'stdout.log').open('x') as out,(O/'stderr.log').open('x') as err:r=subprocess.run([sys.executable,'-B',str(S/'run_recount.py'),'--config',str(cp),'--manifest',str(M),'--out',str(O/'results')],stdout=out,stderr=err,env=env)
assert r.returncode==0,'native/strict-clock raw audit failed; no missing clock or count filled';summary=json.loads((O/'results/GATE.json').read_bytes());assert summary['cells']==36 and summary['kill_fault_cells']==16;print(json.dumps({k:v for k,v in summary.items() if k!='results'}))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('MSHA',repr(sha(M))).replace('PLANS',repr([(p.name,sha(p)) for p in plans]))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0,'NN owns host; no recount IO'
 s=c.open_sftp()
 for local,remote in [(M,P+'/NATIVE_WORK_SOURCE_v1.json'),(F/'packages/NATIVE_WORK_SOURCE_v1.bundle',P+'/NATIVE_WORK_SOURCE_v1.bundle')]:
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as f:assert f.read()==data
  except FileNotFoundError:
   with s.open(remote,'wx') as f:f.write(data);f.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=600);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'NATIVE_WORK36_STDOUT_v1.json').write_bytes(stdout);(F/'NATIVE_WORK36_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();print(stdout.decode())
finally:c.close()
