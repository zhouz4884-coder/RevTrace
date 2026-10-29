"""Byte-exact B-only source stage and CPU gate. Does not initialize models/GPU."""
import pathlib,json,hashlib,shlex,sys
T=pathlib.Path(__file__).resolve().parents[1];plan=json.loads((T/'PLAN_v1_FROZEN.json').read_text(encoding='utf-8'));P=str(pathlib.PurePosixPath(plan['source_root']).parent);O=str(pathlib.PurePosixPath(plan['raw_result_location']).parent)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 for p in [P,O]:
  try:s.mkdir(p)
  except OSError:s.stat(p)
 for local,name in [(T/'packages/SOURCE_v1.bundle','SOURCE_v1.bundle'),(T/'packages/SOURCE_v1.json','SOURCE_v1.json'),(T/'PLAN_v1_FROZEN.json','PLAN_v1_FROZEN.json')]:
  target=P+'/'+name;data=local.read_bytes()
  try:
   with s.open(target,'rb') as f:assert f.read()==data,'existing staged bytes differ'
  except FileNotFoundError:
   with s.open(target,'wb') as f:f.write(data)
 s.close()
 code=r'''import pathlib,json,hashlib,subprocess,os,sys
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);plan=json.loads((P/'PLAN_v1_FROZEN.json').read_text());source=P/'source_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if not source.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE_v1.bundle'),str(source)],check=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(source),'checkout',plan['source_commit']],check=True)
sys.path.insert(0,str(source));from run_stage_profile import verified_source
verified_source(P/'SOURCE_v1.json')
native=json.loads(pathlib.Path(plan['native_plan']).read_text());assert sha(plan['native_plan'])==plan['native_plan_sha256']
assert sha(native['environment_record'])==plan['native_frozen_environment_sha256']
author=pathlib.Path(native['model_contract']['model_assets'] and '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f')
assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==plan['author_commit']
assert sha(author/'simul_whisper/simul_whisper.py')==plan['author_infer_sha256']
assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip()
gate=O/'cpu_v1/GATE.json'
if not gate.exists():subprocess.run([sys.executable,'-B',str(source/'run_cpu_gate.py'),'--out',str(O/'cpu_v1'),'--manifest',str(P/'SOURCE_v1.json')],check=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
assert json.loads(gate.read_text())['status']=='PASS_CPU_STATE_CONTRACT_TESTS_ONLY'
receipt=dict(status='PASS_FROZEN_STAGE_SOURCE_DEPENDENCIES_AND_SAME_ENV_CPU_ONLY',source_commit=plan['source_commit'],plan_sha256=sha(P/'PLAN_v1_FROZEN.json'),source_manifest_sha256=sha(P/'SOURCE_v1.json'),cpu_gate=str(gate),cpu_gate_sha256=sha(gate),environment_python=sys.executable,author_infer_sha256=sha(author/'simul_whisper/simul_whisper.py'),native_environment_sha256=sha(native['environment_record']),gpu_launched=False,models_loaded=False)
dest=O/'PREREQUISITE_GATE_v1.json'
if dest.exists():assert json.loads(dest.read_text())==receipt
else:dest.write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=60);i.write(code);i.flush();i.channel.shutdown_write();stdout=o.read().decode();stderr=e.read().decode();rc=o.channel.recv_exit_status()
 (T/'REMOTE_CPU_SETUP_STDOUT.txt').write_text(stdout,encoding='utf-8');(T/'REMOTE_CPU_SETUP_STDERR.txt').write_text(stderr,encoding='utf-8')
 print(stdout);print(stderr,file=sys.stderr);assert rc==0,'preserved CPU setup error'
 s=c.open_sftp();dest=T/'remote_cpu_v1';dest.mkdir(exist_ok=True)
 for rel in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','unittest.log']:
  p=dest/rel
  if not p.exists():s.get(O+'/cpu_v1/'+rel,str(p))
 s.get(O+'/PREREQUISITE_GATE_v1.json',str(T/'PREREQUISITE_GATE_v1.json'));s.close()
finally:c.close()
