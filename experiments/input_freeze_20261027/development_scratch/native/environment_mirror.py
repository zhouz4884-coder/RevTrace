"""Download public wheels, verify every SHA256 with official PyPI, then install."""
from pathlib import Path
import importlib.util,hashlib,json
spec=importlib.util.spec_from_file_location('authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
source=r'''
from pathlib import Path
import subprocess,os,json,hashlib,time,urllib.request,concurrent.futures
from packaging.utils import parse_wheel_filename
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
py=B/'envs/revtrace_native_20261027/bin/python';base=B/'envs/revbatch-cu128/bin/python'
out=B/'results/revtrace/freeze_boundary_20261027/native_environment_v3'
wheelhouse=B/'cache/pip/native_wheelhouse_20261027'
assert py.is_file() and not out.exists() and not wheelhouse.exists()
# Never overlap another installer of this exact environment.
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  a=p.joinpath('cmdline').read_bytes().decode().rstrip('\0').split('\0')
  assert not (len(a)>=4 and a[0]==str(py) and a[1:4]==['-m','pip','install']), 'owned previous installer still live'
 except (FileNotFoundError,PermissionError,UnicodeError):pass
out.mkdir();wheelhouse.mkdir(parents=True)
env=dict(os.environ,TMPDIR=str(B/'tmp/revtrace_native_20261027'),PIP_CACHE_DIR=str(B/'cache/pip/native_20261027'),
 PIP_CONFIG_FILE=os.devnull,PIP_INDEX_URL='https://pypi.tuna.tsinghua.edu.cn/simple',PIP_EXTRA_INDEX_URL='',PIP_TRUSTED_HOST='',
 PIP_USER='0',PYTHONNOUSERSITE='1')
commands=[]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v):(out/n).write_text(json.dumps(v,indent=2)+'\n')
def run(label,args,timeout):
 st=time.time_ns();of=out/(label+'.stdout.txt');ef=out/(label+'.stderr.txt')
 with of.open('x') as o,ef.open('x') as e:
  proc=subprocess.Popen([str(x) for x in args],stdout=o,stderr=e,env=env)
  put('OWNED_PROCESS.json',dict(pid=proc.pid,argv=[str(x) for x in args],label=label))
  timed_out=False
  try:rc=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:proc.kill();rc=proc.wait();timed_out=True
 r=dict(label=label,argv=[str(x) for x in args],returncode=rc,timed_out=timed_out,started_ns=st,completed_ns=time.time_ns(),stdout_sha256=h(of),stderr_sha256=h(ef))
 commands.append(r);put('COMMANDS.json',commands);print(json.dumps(r),flush=True)
 return rc
pins=['langgraph==1.0.3','langgraph-checkpoint-sqlite==3.0.0','langgraph-checkpoint==3.0.1','langchain-core==1.7.0']
status='FAILED_BEFORE_INSTALL';verified=[]
try:
 rc=run('download-wheels',[py,'-m','pip','download','--disable-pip-version-check','--only-binary=:all:','--no-input','--timeout','25','--retries','1','--dest',wheelhouse,*pins],420)
 if rc:raise RuntimeError('mirror-download-failed')
 def verify(p):
  name,version,build,tags=parse_wheel_filename(p.name)
  url='https://pypi.org/pypi/'+str(name)+'/'+str(version)+'/json'
  with urllib.request.urlopen(url,timeout=30) as response:meta=json.load(response)
  choices=[x for x in meta['urls'] if x['filename']==p.name]
  assert len(choices)==1 and choices[0]['digests']['sha256']==h(p), 'official wheel hash mismatch'
  return dict(file=p.name,bytes=p.stat().st_size,sha256=h(p),official_metadata_url=url,official_file_url=choices[0]['url'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:verified=list(pool.map(verify,sorted(wheelhouse.glob('*.whl'))))
 assert verified;put('OFFICIAL_WHEEL_HASHES.json',verified)
 rc=run('offline-install',[py,'-m','pip','install','--disable-pip-version-check','--no-input','--no-index','--find-links',wheelhouse,*pins],180)
 if rc:raise RuntimeError('verified-offline-install-failed')
 code="""import importlib.metadata as m,json,sys
from langgraph.func import entrypoint,task
from langgraph.types import Command,interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
print(json.dumps(dict(prefix=sys.prefix,packages={n:m.version(n) for n in ['langgraph','langgraph-checkpoint-sqlite','langgraph-checkpoint','langchain-core']},native_imports='PASS')))
"""
 rc=run('native-import-smoke',[py,'-c',code],90)
 if rc:raise RuntimeError('native-import-smoke-failed')
 actual=json.loads((out/'native-import-smoke.stdout.txt').read_text())
 assert actual['prefix']==str(py.parent.parent) and actual['packages']==dict(x.split('==') for x in pins)
 status='PASS_ENVIRONMENT_ONLY'
except BaseException as exc:
 import traceback
 put('FAILURE.json',dict(error=type(exc).__name__,detail=str(exc),traceback=traceback.format_exc()))
run('base-freeze-after',[base,'-m','pip','freeze'],60)
run('new-env-freeze',[py,'-m','pip','freeze'],60)
original=B/'results/revtrace/freeze_boundary_20261027/native_environment_v1/base-freeze-before.stdout.txt'
unchanged=(out/'base-freeze-after.stdout.txt').read_bytes()==original.read_bytes()
if not unchanged:status='FAIL_BASE_ENV_CHANGED'
put('RESULT.json',dict(status=status,base_unchanged=unchanged,verified_wheels=len(verified),commands=commands,
 scope='environment/import smoke; no GPU or native study execution'))
print((out/'RESULT.json').read_text(),flush=True)
'''
c=helper.ssh_client()
try:
 i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -',timeout=900)
 i.write(source);i.channel.shutdown_write();out,err=o.read().decode(),e.read().decode();rc=o.channel.recv_exit_status()
 r=dict(returncode=rc,stdout=out,stderr=err,script_sha256=hashlib.sha256(source.encode()).hexdigest())
 p=Path(__file__).parent/'ENVIRONMENT_MIRROR.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
finally:c.close()
