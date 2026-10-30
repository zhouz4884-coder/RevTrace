"""Root-gated B-disk source/CPU verification and exact default-r0 prefix launch."""
import datetime,hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
planpath=F/'LONG_MEMORY_DIAGNOSTIC_v2_FROZEN.json';plan=read(planpath);candidate=read(F/'CURRENT_LONG_MEMORY_DIAGNOSTIC_CANDIDATE_v2.json');assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==plan['source_commit']
pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);prepath=F/'LONG_MEMORY_DIAGNOSTIC_ROOT_NOARG_v2.json';assert not prepath.exists();prepath.write_bytes(pre.stdout)
pairs=[(F/'packages/LONG_MEMORY_DIAGNOSTIC_SOURCE_v2.json',P+'/LONG_MEMORY_DIAGNOSTIC_SOURCE_v2.json'),(F/'packages/LONG_MEMORY_DIAGNOSTIC_SOURCE_v2.bundle',P+'/LONG_MEMORY_DIAGNOSTIC_SOURCE_v2.bundle'),(planpath,P+'/'+planpath.name)]+[(p,P+'/long_memory_diagnostic_v2_configs/'+p.name) for p in sorted((F/'long_memory_diagnostic_v2_configs').glob('*.json'))]
script=r'''import pathlib,json,hashlib,subprocess,sys,os,datetime,platform
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);plan=json.loads((P/'LONG_MEMORY_DIAGNOSTIC_v2_FROZEN.json').read_bytes());S=pathlib.Path(plan['source_root']);M=pathlib.Path(plan['source_manifest'])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'LONG_MEMORY_DIAGNOSTIC_v2_FROZEN.json')==PLANSHA and sha(M)==plan['source_manifest_sha256']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert not S.exists();subprocess.run(['git','clone','-q','--no-checkout',str(P/'LONG_MEMORY_DIAGNOSTIC_SOURCE_v2.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',plan['source_commit']],check=True)
sys.path.insert(0,str(S));from diagnose_long_memory import own_identity;assert own_identity(M)==plan['source_commit']
out=pathlib.Path(plan['raw_result_location']);out.mkdir();cpu=out/'cpu';cpu.mkdir()
put=lambda p,x:p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
cfg=dict(experiment_id='SC_LONG_MEMORY_DIAGNOSTIC_SOURCE13_LINUX_CPU_V2',code_commit=plan['source_commit'],source_manifest_sha256=sha(M),expected_tests=13,model_calls=0);put(cpu/'CONFIG.json',cfg);put(cpu/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0));put(cpu/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=plan['source_commit'],frozen_config=str(cpu/'CONFIG.json'),config_sha256=sha(cpu/'CONFIG.json'),environment_record=str(cpu/'ENVIRONMENT.json'),environment_sha256=sha(cpu/'ENVIRONMENT.json'),raw_result_location=str(cpu/'unittest.log'),aggregate_summary_location=str(cpu/'SUMMARY.json'),gate_decision_location=str(cpu/'GATE.json')))
tmp=cpu/'tmp';tmp.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp),XDG_CACHE_HOME=str(cpu/'cache'));harness="import io,json,unittest; suite=unittest.defaultTestLoader.discover('.',pattern='test_*.py'); stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); print(stream.getvalue()); print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()))); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==13 and not result.skipped else 1)"
r=subprocess.run([sys.executable,'-B','-c',harness],cwd=S,capture_output=True,env=env);(cpu/'unittest.log').write_bytes(r.stdout+r.stderr);last=json.loads(r.stdout.splitlines()[-1]);gate=dict(status='PASS_DIAGNOSTIC13_LINUX_CPU_ZERO_SKIP' if r.returncode==0 else 'FAIL_DIAGNOSTIC_CPU_PRESERVED',code_commit=plan['source_commit'],**last);put(cpu/'SUMMARY.json',gate);put(cpu/'GATE.json',gate);assert r.returncode==0 and gate['tests']==13 and gate['skipped']==0
own_identity(M);cell=plan['cells'][0];assert cell['label']=='release_g_r0' and sha(cell['config'])==cell['config_sha256'];command=[sys.executable,'-B',str(S/'diagnose_long_memory.py'),'--config',cell['config'],'--manifest',str(M),'--out',cell['out']];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('CUDA_VISIBLE_DEVICES',None)
with open(cell['log'],'x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);h=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,diagnostic_source_commit=plan['source_commit'],imported_neural_source_commit=plan['imported_neural_source_commit'],out=cell['out'],log=cell['log'],config_sha256=cell['config_sha256'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0);put(out/'HANDLE_release_g_r0.json',h);print(json.dumps(h))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANSHA',repr(sha(planpath)))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 for directory in (P+'/long_memory_diagnostic_v2_configs',):
  try:s.stat(directory)
  except FileNotFoundError:s.mkdir(directory)
 for p,q in pairs:
  with s.open(q,'wx') as stream:stream.write(p.read_bytes());stream.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=40);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'LONG_MEMORY_DIAGNOSTIC_LAUNCH_STDOUT_v2.txt').write_bytes(stdout);(F/'LONG_MEMORY_DIAGNOSTIC_LAUNCH_STDERR_v2.txt').write_bytes(stderr);assert rc==0,stderr.decode();(F/'LONG_MEMORY_DIAGNOSTIC_HANDLE_release_g_r0.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()
