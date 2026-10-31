"""After normal queues stop: freeze-identity fixture staging and Linux25 CPU."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();pointer=R/'experiments/repository_identity_20261027/CURRENT.json';previous=None
try:
 code="import pathlib,json,subprocess; O=pathlib.Path("+repr(O)+"); assert json.loads((O/'paired32_v2/GATE.json').read_bytes())['status']=='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT'; assert json.loads((O/'resident4_v2/GATE.json').read_bytes())['status'] in ('PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE','NO_GO_RESIDENT_SMOKE_NO_CONTRACT_REPAIR'); assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip(); print('PASS_IDLE_FIXED_SCOPE_BOUNDARY')"
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -c '+shlex.quote(code),timeout=20);assert o.channel.recv_exit_status()==0,e.read().decode()
 previous=pointer.read_bytes();backup=E/'FIXTURE_CPU_PREVIOUS_CURRENT_v1_r2.json';assert not backup.exists();backup.write_bytes(previous);value=json.loads(previous);value.update(source_worktree=str(E/'buffer_fixture_source_v1'),source_commit='4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28',source_manifest=str(E/'buffer_fixture_packages_v1/BUFFER_FIXTURE_SOURCE_v1.json'),source_manifest_sha256=sha(E/'buffer_fixture_packages_v1/BUFFER_FIXTURE_SOURCE_v1.json'),GPU_queue='FIXTURE_FORMAL_LINUX25_CPU_ONLY_NO_NN');pointer.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
 gate=E/'FIXTURE_CPU_ROOT_NOARG_v1_r2.json';run=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);assert not gate.exists();gate.write_bytes(run.stdout)
 index=read(E/'buffer_fixture_inputs_v1/INPUT_INDEX_v1.json');pairs=[(pathlib.Path(row['local']),row['remote']) for row in index['files']]
 for ext in ('json','bundle'):pairs.append((E/'buffer_fixture_packages_v1'/('BUFFER_FIXTURE_SOURCE_v1.'+ext),P+'/BUFFER_FIXTURE_SOURCE_v1.'+ext))
 pairs.append((gate,P+'/FIXTURE_CPU_ROOT_NOARG_v1_r2.json'));s=c.open_sftp();made=set()
 for local,remote in pairs:
  folder=pathlib.PurePosixPath(remote).parent
  for parent in [*reversed(folder.parents),folder]:
   if str(parent) in made or not str(parent).startswith(B):continue
   try:s.stat(str(parent))
   except FileNotFoundError:s.mkdir(str(parent))
   made.add(str(parent))
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as stream:assert stream.read()==data,'existing immutable fixture bytes differ'
  except FileNotFoundError:
   with s.open(remote,'wx') as stream:stream.write(data);stream.flush()
 s.close()
 script=r'''import pathlib,json,sys,subprocess,os,hashlib,platform
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);M=P/'BUFFER_FIXTURE_SOURCE_v1.json';m=json.loads(M.read_bytes());S=P/'buffer_fixture_source_v1'
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'BUFFER_FIXTURE_SOURCE_v1.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
H=P/'paired_resident_source_v2';sys.path.insert(0,str(H));from common import read,sha,put,verify_checkout,need
identity=verify_checkout(S,M,'4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28');plan=read(P/'BUFFER4_v1_FROZEN.json');need(sha(P/'BUFFER4_v1_FROZEN.json')==PLANSHA,'fixture plan changed')
for name,dep in plan['dependencies'].items():verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit'])
for cell in plan['cells']:need(sha(cell['config'])==cell['config_sha256'],'fixture config changed')
need(sha(plan['reference_details'])==plan['reference_details_sha256'] and sha(plan['reference_gate'])==plan['reference_gate_sha256'],'old legal reference changed')
out=O/'fixture_linux_cpu_v1_r2';out.mkdir();tmp=out/'tmp';tmp.mkdir();put(out/'CONFIG.json',dict(experiment_id='SC_FIXTURE25_FORMAL_LINUX_CPU_20261031_V1_R2',source_commit=identity['source_commit'],source_manifest_sha256=sha(M),plan_sha256=sha(P/'BUFFER4_v1_FROZEN.json'),expected_tests=25,trained_model_calls=0));put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),source=identity,shared_environment_sha256=plan['environment_sha256'],CUDA_VISIBLE_DEVICES=''));put(out/'RUN_RECORD.json',dict(experiment_id='SC_FIXTURE25_FORMAL_LINUX_CPU_20261031_V1_R2',code_commit=identity['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp),REVTRACE_FIXTURE_TEST_ROOT=str(tmp),PYTHONPATH=os.pathsep.join([str(S),str(H),plan['dependencies']['base']['source_root']]))
code="import json,unittest,test_buffer_fixture as t; r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(t)); print(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped),successful=r.wasSuccessful(),CPU_control_child_terminations=t.DEVELOPMENT_CPU_CHILD_TERMINATIONS))); raise SystemExit(0 if r.wasSuccessful() and r.testsRun==25 and not r.skipped else 1)"
run=subprocess.run([sys.executable,'-B','-c',code],cwd=S,capture_output=True,env=env,timeout=180);(out/'stdout.log').write_bytes(run.stdout);(out/'stderr.log').write_bytes(run.stderr);result=json.loads(run.stdout.splitlines()[-1]);gate=dict(status='PASS_FORMAL_FIXTURE25_LINUX_CPU_ZERO_SKIP' if run.returncode==0 else 'FAIL_FORMAL_FIXTURE_CPU_PRESERVED',source_commit=identity['source_commit'],source_manifest_sha256=sha(M),harness_source_commit=plan['harness_source_commit'],actual_NN_source_commit=plan['actual_NN_source_commit'],shared_environment_sha256=plan['environment_sha256'],trained_model_calls=0,**result);put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate);verify_checkout(S,M);print(json.dumps(gate));need(run.returncode==0,'formal fixture CPU failed')
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANSHA',repr(sha(E/'buffer_fixture_inputs_v1/BUFFER4_v1_FROZEN.json')))
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=220);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(E/'FIXTURE_CPU_STDOUT_v1_r2.txt').write_bytes(stdout);(E/'FIXTURE_CPU_STDERR_v1_r2.txt').write_bytes(stderr);assert rc==0,stderr.decode();(E/'FIXTURE_FORMAL_CPU_GATE_v1_r2.json').write_bytes(stdout);print(stdout.decode())
finally:
 if previous is not None:
  pointer.write_bytes(previous);run=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=E/'FIXTURE_CPU_RETURN_A13_ROOT_NOARG_v1_r2.json';assert not target.exists();target.write_bytes(run.stdout)
 c.close()
