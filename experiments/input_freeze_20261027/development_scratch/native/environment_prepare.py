"""Create only the separately authorized 8 TB native venv; no GPU research."""
from pathlib import Path
import hashlib
import importlib.util
import json
import time

helper_path = Path(r"C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py")
spec = importlib.util.spec_from_file_location("authorized_ssh", helper_path)
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
B = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
remote = r'''
from pathlib import Path
import subprocess,sys,os,json,hashlib,time,platform
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
base=B/'envs/revbatch-cu128/bin/python'; target=B/'envs/revtrace_native_20261027'
out=B/'results/revtrace/freeze_boundary_20261027/native_environment_v1'
assert base.is_file() and B.resolve()==B
assert not target.exists(), 'target exists; inspect identity before changing it'
assert not out.exists(), 'environment receipt directory already exists'
out.mkdir(parents=True)
tmp=B/'tmp/revtrace_native_20261027'; tmp.mkdir(parents=True,exist_ok=True)
cache=B/'cache/pip/native_20261027'; cache.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TMPDIR=str(tmp),PIP_CACHE_DIR=str(cache),PIP_CONFIG_FILE=os.devnull,
         PIP_INDEX_URL='https://pypi.org/simple',PIP_EXTRA_INDEX_URL='',PIP_TRUSTED_HOST='',
         PIP_USER='0',PYTHONNOUSERSITE='1')
def put(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
commands=[]
def run(label,args,timeout):
 start=time.time_ns()
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,env=env,timeout=timeout)
 (out/(label+'.stdout.txt')).write_text(p.stdout); (out/(label+'.stderr.txt')).write_text(p.stderr)
 record=dict(label=label,argv=[str(x) for x in args],returncode=p.returncode,started_ns=start,completed_ns=time.time_ns(),
             stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest())
 commands.append(record);put('COMMANDS.json',commands)
 print(json.dumps(record),flush=True)
 return p
before=run('base-freeze-before',[base,'-m','pip','freeze'],60)
assert before.returncode==0
create=run('create-venv',[base,'-m','venv','--system-site-packages',target],120)
if create.returncode:
 put('RESULT.json',dict(status='FAILED_VENV_CREATION',commands=commands));sys.exit(2)
py=target/'bin/python'
pins=['langgraph==1.0.3','langgraph-checkpoint-sqlite==3.0.0','langgraph-checkpoint==3.0.1','langchain-core==1.7.0']
install=run('install-pinned',[py,'-m','pip','install','--disable-pip-version-check','--no-input',*pins],600)
after=run('base-freeze-after',[base,'-m','pip','freeze'],60)
base_unchanged=before.stdout==after.stdout
if install.returncode:
 put('RESULT.json',dict(status='FAILED_PINNED_INSTALL',base_unchanged=base_unchanged,commands=commands));sys.exit(3)
smoke="""import importlib.metadata as m,json,sys
from langgraph.func import entrypoint,task
from langgraph.types import interrupt,Command
from langgraph.checkpoint.sqlite import SqliteSaver
names=['langgraph','langgraph-checkpoint-sqlite','langgraph-checkpoint','langchain-core']
print(json.dumps(dict(prefix=sys.prefix,packages={n:m.version(n) for n in names},native_imports='PASS',scope='imports only; no model/test/experiment invocation')))
"""
check=run('native-import-smoke',[py,'-c',smoke],90)
freeze=run('new-env-freeze',[py,'-m','pip','freeze'],60)
data=json.loads(check.stdout) if check.returncode==0 else {}
expected=dict(p.split('==') for p in pins)
ok=check.returncode==0 and data.get('packages')==expected and data.get('prefix')==str(target) and base_unchanged
put('RESULT.json',dict(status='PASS_ENVIRONMENT_ONLY' if ok else 'FAILED_IDENTITY_OR_IMPORT',target=str(target),
    base_unchanged=base_unchanged,actual=data,python=sys.version,platform=platform.platform(),commands=commands,
    scope='new isolated native venv on8TB; GPU/models and study tests not invoked'))
print((out/'RESULT.json').read_text(),flush=True)
sys.exit(0 if ok else 4)
'''
client = helper.ssh_client()
try:
    stdin, stdout, stderr = client.exec_command(B + "/envs/revbatch-cu128/bin/python -", timeout=750)
    stdin.write(remote); stdin.channel.shutdown_write()
    output, error = stdout.read().decode(), stderr.read().decode()
    rc = stdout.channel.recv_exit_status()
    record = {"observed_ns": time.time_ns(), "script_sha256": hashlib.sha256(remote.encode()).hexdigest(),
              "returncode": rc, "stdout": output, "stderr": error,
              "remote_receipt": B + "/results/revtrace/freeze_boundary_20261027/native_environment_v1/RESULT.json"}
    path = Path(__file__).parent / "ENVIRONMENT_PREPARE.json"
    assert not path.exists();path.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record, indent=2))
finally:
    client.close()
