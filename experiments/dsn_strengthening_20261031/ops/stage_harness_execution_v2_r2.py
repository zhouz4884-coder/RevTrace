"""Root-authorized immutable staging and formal readiness launch; zero NN."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
gatepath=E/'EXECUTION_STAGE_ROOT_NOARG_v2_r2.json';need_gate=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);assert not gatepath.exists();gatepath.write_bytes(need_gate.stdout);assert read(gatepath)['code_commit']=='a13fa0a335529dc188f7e738877a3acd027ce4a7'
pairs=[]
for file in (E/'paired_resident_inputs_v2').rglob('*'):
 if file.is_file():pairs.append((file,P+'/'+file.relative_to(E/'paired_resident_inputs_v2').as_posix()))
for folder,stem in [('paired_resident_packages_v2','PAIRED_RESIDENT_SOURCE_v2'),('execution_support_packages_v1','EXECUTION_SUPPORT_SOURCE_v1')]:
 for extension in ('json','bundle'):pairs.append((E/folder/(stem+'.'+extension),P+'/'+stem+'.'+extension))
pairs.append((gatepath,P+'/EXECUTION_STAGE_ROOT_NOARG_v2_r2.json'))
script=r'''import json,pathlib,subprocess,sys,os,hashlib
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);PY=PYTHON_BIN_TOKEN
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip()
for name,manifestname in [('paired_resident_source_v2','PAIRED_RESIDENT_SOURCE_v2'),('execution_support_source_v1','EXECUTION_SUPPORT_SOURCE_v1')]:
 S=P/name;M=P/(manifestname+'.json');manifest=read(M)
 if not S.exists():
  subprocess.run(['git','clone','-q','--no-checkout',str(P/(manifestname+'.bundle')),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',manifest['source_commit']],check=True)
sys.path.insert(0,str(P/'paired_resident_source_v2'));from common import verify_checkout
identities=[verify_checkout(P/name,P/(m+'.json')) for name,m in [('paired_resident_source_v2','PAIRED_RESIDENT_SOURCE_v2'),('execution_support_source_v1','EXECUTION_SUPPORT_SOURCE_v1')]]
out=O/'readiness_v2';assert not out.exists();log=O/'readiness_v2.log';assert not log.exists();O.mkdir(parents=True,exist_ok=True)
command=[PY,'-B',str(P/'execution_support_source_v1/readiness.py'),'--controller',str(P/'paired_resident_source_v2'),'--controller-manifest',str(P/'PAIRED_RESIDENT_SOURCE_v2.json'),'--support-manifest',str(P/'EXECUTION_SUPPORT_SOURCE_v1.json'),'--project',str(P),'--out',str(out),'--root-receipt',str(P/'EXECUTION_STAGE_ROOT_NOARG_v2_r2.json')]
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');environment.pop('PYTORCH_ALLOC_CONF',None)
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=environment)
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,identities=identities,out=str(out),log=str(log),GPU_neural_launches=0)
target=O/'READINESS_HANDLE_v2.json';assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PYTHON_BIN_TOKEN',repr(PY))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0
 s=c.open_sftp();made=set()
 for local,remote in pairs:
  folder=pathlib.PurePosixPath(remote).parent
  for parent in [*reversed(folder.parents),folder]:
   if str(parent) in made or not str(parent).startswith(B):continue
   try:s.stat(str(parent))
   except FileNotFoundError:s.mkdir(str(parent))
   made.add(str(parent))
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as stream:assert stream.read()==data,'immutable remote bytes differ: '+remote
  except FileNotFoundError:
   with s.open(remote,'wx') as stream:stream.write(data);stream.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=120);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(E/'READINESS_STAGE_STDOUT_v2_r2.txt').write_bytes(stdout);(E/'READINESS_STAGE_STDERR_v2_r2.txt').write_bytes(stderr);assert rc==0,stderr.decode();(E/'READINESS_HANDLE_v2.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()
