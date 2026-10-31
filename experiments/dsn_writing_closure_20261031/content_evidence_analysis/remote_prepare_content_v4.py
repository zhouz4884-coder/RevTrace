from pathlib import Path
import json,os,shutil,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_writing_closure_20261031'
O=B/'results/revtrace/dsn_writing_closure_20261031'
assert B.is_mount() and shutil.disk_usage(B).free>1024**3
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip(),'GPU queue must be quiet'
P.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
assert os.stat(P).st_dev==os.stat(B).st_dev==os.stat(O).st_dev
assert not (P/'content_source_v4').exists()
print(json.dumps(dict(status='PASS_8TB_DEVICE_FREE_AND_GPU_QUIET',device=os.stat(B).st_dev,free_bytes=shutil.disk_usage(B).free,python=sys.version,executable=sys.executable)))
# AFTER_UPLOAD
from pathlib import Path
import hashlib,json,os,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_writing_closure_20261031'
source=P/'content_source_v4'
msha='2dac41b61a84c5de8846564bdcb7c7c6bd8159e51b35012f385c6e781282637c'
commit='6eb6639478a87e6be971e23282bd2f31789f242f'
assert hashlib.sha256((P/'CONTENT_SOURCE_v4.json').read_bytes()).hexdigest()==msha
subprocess.run(['git','clone',str(P/'CONTENT_SOURCE_v4_UPLOAD1.bundle'),str(source)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
sys.path.insert(0,str(source))
from evidence_io import source_gate,put,sha
identity=source_gate(source,P/'CONTENT_SOURCE_v4.json',msha,commit)
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from run_content_recount import current_environment
env=current_environment();path=P/'ENVIRONMENT_CONTENT_v4_FROZEN.json';put(path,env)
print(json.dumps(dict(status='PASS_CLEAN_CONTENT_SOURCE_AND_FROZEN_CPU_ENVIRONMENT',source_gate=identity,environment_record=str(path),environment_sha256=sha(path),environment=env)))
