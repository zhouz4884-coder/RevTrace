"""Start the fixed four timing witnesses only after formal fixture CPU gate."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
receipt=E/'BUFFER4_LAUNCH_ROOT_NOARG_v1.json';assert not receipt.exists();run=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);receipt.write_bytes(run.stdout);assert json.loads(run.stdout)['code_commit']=='a13fa0a335529dc188f7e738877a3acd027ce4a7'
script=r'''import pathlib,json,subprocess,os,sys,hashlib
P=pathlib.Path(__PROJECT__);O=pathlib.Path(__OUTPUT__);S=P/'paired_resident_source_v2';sys.path.insert(0,str(S));from common import read,put,sha,need,verify_checkout
plan=read(P/'BUFFER4_v1_FROZEN.json');need(sha(P/'BUFFER4_v1_FROZEN.json')==__PLANSHA__,'fixture frozen plan changed')
for dep in plan['dependencies'].values():verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit'])
cpu=O/'fixture_linux_cpu_v1_r2/GATE.json';gate=read(cpu);need(gate['status']=='PASS_FORMAL_FIXTURE25_LINUX_CPU_ZERO_SKIP' and gate['source_commit']==plan['source_commit'] and gate['shared_environment_sha256']==plan['environment_sha256'],'formal CPU binding differs')
need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=5).strip(),'GPU occupied')
need(sha(P/'run_fixture_campaign_v1.py')==__QUEUESHA__,'actual queue wrapper differs');log=O/'buffer4_campaign_v1.log';need(not log.exists(),'existing fixture attempt')
command=[sys.executable,'-B',str(P/'run_fixture_campaign_v1.py'),'--project',str(P),'--root-receipt',str(P/'BUFFER4_LAUNCH_ROOT_NOARG_v1.json'),'--cpu-gate',str(cpu)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('PYTORCH_ALLOC_CONF',None);env.pop('CUDA_VISIBLE_DEVICES',None);env.update(plan['runtime_environment'])
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);handle=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,out=plan['raw_result_location'],log=str(log),expected_cells=4,plan_sha256=sha(P/'BUFFER4_v1_FROZEN.json'),formal_CPU_gate_sha256=sha(cpu),actual_queue_wrapper_sha256=__QUEUESHA__);put(O/'BUFFER4_HANDLE_v1.json',handle);print(json.dumps(handle))
'''.replace('__PROJECT__',repr(P)).replace('__OUTPUT__',repr(O)).replace('__PLANSHA__',repr(sha(E/'buffer_fixture_inputs_v1/BUFFER4_v1_FROZEN.json'))).replace('__QUEUESHA__',repr(sha(E/'ops/run_fixture_campaign_v1.py')))
compile(script,'remote_fixture_launcher','exec')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 for local,remote in [(receipt,P+'/BUFFER4_LAUNCH_ROOT_NOARG_v1.json'),(E/'ops/run_fixture_campaign_v1.py',P+'/run_fixture_campaign_v1.py')]:
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as f:assert f.read()==data
  except FileNotFoundError:
   with s.open(remote,'wx') as f:f.write(data);f.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=40);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(E/'BUFFER4_LAUNCH_STDOUT_v1.txt').write_bytes(stdout);(E/'BUFFER4_LAUNCH_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();(E/'BUFFER4_HANDLE_v1.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()
