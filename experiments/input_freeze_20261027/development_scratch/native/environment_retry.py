"""One bounded retry of exact pins after a retained public-wheel read timeout."""
from pathlib import Path
import importlib.util
import hashlib
import json
spec=importlib.util.spec_from_file_location('authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
source=r'''
from pathlib import Path
import subprocess,os,json,hashlib,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
py=B/'envs/revtrace_native_20261027/bin/python';base=B/'envs/revbatch-cu128/bin/python'
old=B/'results/revtrace/freeze_boundary_20261027/native_environment_v1'
out=B/'results/revtrace/freeze_boundary_20261027/native_environment_v2'
assert json.loads((old/'RESULT.json').read_text())['status']=='FAILED_PINNED_INSTALL'
assert py.is_file() and not out.exists();out.mkdir()
env=dict(os.environ,TMPDIR=str(B/'tmp/revtrace_native_20261027'),PIP_CACHE_DIR=str(B/'cache/pip/native_20261027'),
         PIP_CONFIG_FILE=os.devnull,PIP_INDEX_URL='https://pypi.org/simple',PIP_EXTRA_INDEX_URL='',PIP_TRUSTED_HOST='',
         PIP_USER='0',PYTHONNOUSERSITE='1')
commands=[]
def run(label,args,timeout):
 start=time.time_ns()
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,env=env,timeout=timeout)
 (out/(label+'.stdout.txt')).write_text(p.stdout);(out/(label+'.stderr.txt')).write_text(p.stderr)
 r=dict(label=label,argv=[str(x) for x in args],returncode=p.returncode,started_ns=start,completed_ns=time.time_ns(),
        stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest())
 commands.append(r);(out/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');print(json.dumps(r),flush=True)
 return p
prefix=run('target-identity',[py,'-c','import sys;print(sys.prefix)'],30)
assert prefix.returncode==0 and prefix.stdout.strip()==str(py.parent.parent)
pins=['langgraph==1.0.3','langgraph-checkpoint-sqlite==3.0.0','langgraph-checkpoint==3.0.1','langchain-core==1.7.0']
p=run('install-pinned',[py,'-m','pip','install','--disable-pip-version-check','--no-input','--timeout','60','--retries','3',*pins],600)
base_freeze=run('base-freeze-after',[base,'-m','pip','freeze'],60)
unchanged=base_freeze.stdout==(old/'base-freeze-before.stdout.txt').read_text()
actual={}
if p.returncode==0:
 code="""import importlib.metadata as m,json,sys
from langgraph.func import entrypoint,task
from langgraph.types import Command,interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
print(json.dumps(dict(prefix=sys.prefix,packages={n:m.version(n) for n in ['langgraph','langgraph-checkpoint-sqlite','langgraph-checkpoint','langchain-core']},native_imports='PASS')))
"""
 smoke=run('native-import-smoke',[py,'-c',code],90)
 if smoke.returncode==0:actual=json.loads(smoke.stdout)
 run('new-env-freeze',[py,'-m','pip','freeze'],60)
ok=p.returncode==0 and unchanged and actual.get('packages')==dict(x.split('==') for x in pins)
result=dict(status='PASS_ENVIRONMENT_ONLY' if ok else 'FAILED_RETRY_RETAINED',base_unchanged=unchanged,actual=actual,
            commands=commands,scope='environment/import smoke only; no model/GPU/native-study tests')
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
'''
client=helper.ssh_client()
try:
 i,o,e=client.exec_command(B+'/envs/revbatch-cu128/bin/python -',timeout=750)
 i.write(source);i.channel.shutdown_write()
 out,err=o.read().decode(),e.read().decode();rc=o.channel.recv_exit_status()
 r=dict(returncode=rc,stdout=out,stderr=err,script_sha256=hashlib.sha256(source.encode()).hexdigest())
 dest=Path(__file__).parent/'ENVIRONMENT_RETRY.json';assert not dest.exists();dest.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
finally:client.close()
