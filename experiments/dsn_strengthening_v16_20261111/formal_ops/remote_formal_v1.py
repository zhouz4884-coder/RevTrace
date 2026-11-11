"""Stage/run/collect one frozen CPU specification; no GPU or process signals."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

E=Path(__file__).resolve().parents[1];R=E.parents[1];P=E/'formal_packages_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
freeze=json.loads((P/'FREEZE_RECORD.json').read_bytes())
PROJECT=freeze['remote_project'];OUT=freeze['remote_output'];COMMIT=freeze['source_commit']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('launch','status','collect'));a=p.parse_args()
    if a.action=='launch':
        record=dict(experiment_id=freeze['experiment_id'],code_commit=COMMIT,
            frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),
            environment_record=str(P/'FROZEN_ENVIRONMENT.json'),environment_record_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),
            raw_result_location=freeze['raw_result_location'],aggregate_summary_location=freeze['summary'],gate_decision_location=freeze['gate'],
            source_manifest_sha256=freeze['source_manifest_sha256'],scope='CPU bounded design verification; no neural/GPU calls')
        put(P/'LOCAL_PRELAUNCH_RUN_RECORD.json',record)
        subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),
            '--source',str(E/'formal_source_dev'),'--manifest',str(P/'SOURCE.json'),
            '--run-record',str(P/'LOCAL_PRELAUNCH_RUN_RECORD.json'),'--output',str(P/'EXPLICIT_SOURCE_RUN_PREFLIGHT.json')],check=True,cwd=R)
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    client=ssh_client()
    def remote(code):
        i,o,e=client.exec_command(shlex.quote(PY)+' -B -',timeout=90)
        i.write(code);i.flush();i.channel.shutdown_write()
        raw,err=o.read(),e.read();rc=o.channel.recv_exit_status()
        if rc:raise RuntimeError(err.decode('utf8',errors='replace')+'\n'+raw.decode('utf8',errors='replace'))
        return raw
    try:
        params=dict(base=B,project=PROJECT,out=OUT,commit=COMMIT,
            hashes={name:sha(P/name) for name in ('SOURCE.json','SOURCE.bundle','CONFIG.json','FROZEN_ENVIRONMENT.json')})
        if a.action=='launch':
            remote('PARAMS='+repr(params)+'\n'+r'''import pathlib,json
base=pathlib.Path(PARAMS['base']).resolve()
for name in ('project','out'):
 p=pathlib.Path(PARAMS[name]);assert p.resolve().is_relative_to(base);p.mkdir(parents=True,exist_ok=True)
print(json.dumps(dict(directories_ready=True)))
''')
            sftp=client.open_sftp()
            try:
                for name in params['hashes']:
                    dest=PROJECT+'/'+name;data=(P/name).read_bytes()
                    try:
                        with sftp.open(dest,'rb') as f:assert f.read()==data
                    except FileNotFoundError:
                        with sftp.open(dest,'wb') as f:f.write(data)
            finally:sftp.close()
            code='PARAMS='+repr(params)+'\n'+r'''import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
P=pathlib.Path(PARAMS['project']);O=pathlib.Path(PARAMS['out']);S=P/'source';C=PARAMS['commit']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
for name,value in PARAMS['hashes'].items():assert sha(P/name)==value
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True,timeout=10).strip()
assert not compute,'GPU is not quiescent; do not launch this CPU audit'
assert not S.exists(),'source path already exists; never replace a launch source'
subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE.bundle'),str(S)],check=True,capture_output=True)
subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
subprocess.run(['git','-C',str(S),'checkout',C],check=True,capture_output=True)
manifest=json.loads((P/'SOURCE.json').read_bytes());plan=json.loads((P/'CONFIG.json').read_bytes());frozen_env=json.loads((P/'FROZEN_ENVIRONMENT.json').read_bytes())
assert manifest['source_commit']==plan['source_commit']==C
assert sha(P/'SOURCE.json')==plan['source_manifest_sha256'] and sha(P/'FROZEN_ENVIRONMENT.json')==plan['frozen_environment_sha256']
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==C
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in manifest['files']}
for row in manifest['files']:assert (S/row['path']).stat().st_size==row['bytes'] and sha(S/row['path'])==row['sha256']
for key,value in dict(python=sys.version,executable=sys.executable,platform=platform.platform()).items():assert frozen_env[key]==value
environment=dict(frozen_environment=frozen_env,source_commit=C,source_files=len(manifest['files']),CUDA_VISIBLE_DEVICES='',prelaunch_resource_check=dict(compute_processes=compute,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),scope='CPU finite specification; zero model/GPU calls')
put(O/'PRELAUNCH_ENVIRONMENT.json',environment)
command=[sys.executable,'-B',str(S/'run_checks.py'),'--plan',str(P/'CONFIG.json'),'--manifest',str(P/'SOURCE.json'),'--out',str(O/'results')]
record=dict(experiment_id=plan['experiment_id'],code_commit=C,frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),environment_record=str(O/'PRELAUNCH_ENVIRONMENT.json'),environment_record_sha256=sha(O/'PRELAUNCH_ENVIRONMENT.json'),frozen_environment_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),source_manifest_sha256=sha(P/'SOURCE.json'),raw_result_location=str(O/'results'),aggregate_summary_location=str(O/'results/SUMMARY.json'),gate_decision_location=str(O/'results/GATE.json'),command=command,scope=plan['scope'])
put(O/'PRELAUNCH_RUN_RECORD.json',record)
assert not (O/'results').exists()
with (O/'controller.log').open('x') as f:
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
proc=pathlib.Path('/proc')/str(child.pid);tail=(proc/'stat').read_text().rsplit(')',1)[1].split()
handle=dict(pid=child.pid,start_ticks=int(tail[19]),cmdline_sha256=sha(proc/'cmdline'),source_commit=C,source_manifest_sha256=sha(P/'SOURCE.json'),config_sha256=sha(P/'CONFIG.json'),prelaunch_record_sha256=sha(O/'PRELAUNCH_RUN_RECORD.json'),out=str(O/'results'),log=str(O/'controller.log'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),GPU_launched=False)
put(O/'HANDLE.json',handle);print(json.dumps(handle))
'''
            raw=remote(code);put(P/'LAUNCH_HANDLE.json',json.loads(raw));print(raw.decode())
        else:
            code='PARAMS='+repr(params)+'\nCOLLECT='+repr(a.action=='collect')+'\n'+r'''import datetime,hashlib,json,pathlib,subprocess
O=pathlib.Path(PARAMS['out']);P=pathlib.Path(PARAMS['project']);handle=json.loads((O/'HANDLE.json').read_bytes());proc=pathlib.Path('/proc')/str(handle['pid'])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
alive=False;state=None
if proc.exists():
 tail=(proc/'stat').read_text().rsplit(')',1)[1].split();state=tail[0]
 assert int(tail[19])==handle['start_ticks'],'PID identity changed'
 alive=state not in ('Z','X')
 if alive:assert sha(proc/'cmdline')==handle['cmdline_sha256'],'command identity changed'
gate=O/'results/GATE.json';result=dict(controller_alive=alive,state=state,handle=handle,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
if gate.exists():result['gate']=json.loads(gate.read_bytes());result['gate_sha256']=sha(gate)
if COLLECT:
 assert not alive and gate.exists(),'not complete; do not collect/restart'
 source=P/'source';assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
 files=[]
 for path in sorted(O.rglob('*')):
  if path.is_file():
   assert path.stat().st_size<2000000,'bounded collection limit'
   files.append(dict(path=str(path.relative_to(O)),remote=str(path),bytes=path.stat().st_size,sha256=sha(path)))
 result.update(files=files,source_commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),source_clean=True)
print(json.dumps(result,indent=2))
'''
            raw=remote(code);result=json.loads(raw)
            if a.action=='collect':
                dest=E/'FORMAL_ACTION_RESULTS_v1';dest.mkdir(exist_ok=False)
                sftp=client.open_sftp()
                try:
                    for row in result['files']:
                        target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
                        with sftp.open(row['remote'],'rb') as f:data=f.read()
                        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
                        target.write_bytes(data)
                finally:sftp.close()
                put(dest/'COLLECTION_MANIFEST.json',result)
                after=json.loads(subprocess.check_output([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],text=True,cwd=R))
                assert after['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
                assert after['setup_pointer_sha256']==freeze['default_current_sha256_before']
                put(dest/'DEFAULT_PREFLIGHT_AFTER.json',after)
            print(raw.decode())
    finally:client.close()

if __name__=='__main__':main()
