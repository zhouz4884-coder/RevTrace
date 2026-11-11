"""Owned async CPU modes; acquisition is a separate explicit root-coordinated call."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];P=E/'header_packages_v1'
F=json.loads((P/'FREEZE_RECORD.json').read_bytes());C=F['source_commit'];PY='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists(),p;p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('launch','status','collect'));p.add_argument('--mode',choices=('controls','acquire_census'),required=True);a=p.parse_args()
    cfg=json.loads((P/'CONFIG.json').read_bytes());out=F['remote_result_base']+'/'+a.mode
    if a.action=='launch':
        default=json.loads(subprocess.check_output([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],cwd=R,text=True));put(P/('DEFAULT_PREFLIGHT_'+a.mode+'.json'),default)
        record=dict(experiment_id=cfg['experiment_ids'][a.mode],code_commit=C,frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),
            environment_record=str(P/'FROZEN_ENVIRONMENT.json'),environment_record_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),raw_result_location=out,
            aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',mode=a.mode,default_execution_pointer=default)
        put(P/('PRELAUNCH_'+a.mode+'.json'),record)
        subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(E/'magicdata_header_source'),'--manifest',str(P/'SOURCE.json'),
            '--run-record',str(P/('PRELAUNCH_'+a.mode+'.json')),'--output',str(P/('EXPLICIT_PREFLIGHT_'+a.mode+'.json'))],check=True,cwd=R)
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
    client=ssh_client()
    def remote(code):
        i,o,e=client.exec_command(shlex.quote(PY)+' -B -',timeout=90);i.write(code);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();rc=o.channel.recv_exit_status()
        if rc:raise RuntimeError(err.decode('utf8',errors='replace')+'\n'+raw.decode('utf8',errors='replace'))
        return json.loads(raw)
    params=dict(project=F['remote_project'],result_base=F['remote_result_base'],out=out,mode=a.mode,commit=C,hashes={n:sha(P/n) for n in ('SOURCE.json','SOURCE.bundle','CONFIG.json','FROZEN_ENVIRONMENT.json')})
    try:
        if a.action=='launch':
            remote('PARAMS='+repr(params)+'\n'+r'''import json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9').resolve()
for k in ('project','result_base'):
 p=pathlib.Path(PARAMS[k]);assert p.resolve().is_relative_to(B);p.mkdir(parents=True,exist_ok=True)
print(json.dumps(dict(directories_ready=True)))
''')
            s=client.open_sftp()
            try:
                for name in params['hashes']:
                    data=(P/name).read_bytes();dest=F['remote_project']+'/'+name
                    try:
                        with s.open(dest,'rb') as f:assert f.read()==data
                    except FileNotFoundError:
                        with s.open(dest,'wb') as f:f.write(data)
            finally:s.close()
            result=remote('PARAMS='+repr(params)+'\n'+r'''import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
P=pathlib.Path(PARAMS['project']);O=pathlib.Path(PARAMS['out']);S=P/'source';C=PARAMS['commit'];mode=PARAMS['mode']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
for n,h in PARAMS['hashes'].items():assert sha(P/n)==h
if not S.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE.bundle'),str(S)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout',C],check=True,capture_output=True)
m=json.loads((P/'SOURCE.json').read_bytes());cfg=json.loads((P/'CONFIG.json').read_bytes());env=json.loads((P/'FROZEN_ENVIRONMENT.json').read_bytes())
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==C==cfg['source_commit']==m['code_commit']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (S/r['path']).stat().st_size==r['bytes'] and sha(S/r['path'])==r['sha256']
assert cfg['source_manifest_sha256']==sha(P/'SOURCE.json')
for k,v in dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node()).items():assert env[k]==v
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True,timeout=10).strip()
if mode=='controls':assert not compute,'short CPU controls wait for root GPU quiescence'
base=pathlib.Path(PARAMS['result_base']);pre=base/(mode+'_PRELAUNCH.json');handle=base/(mode+'_HANDLE.json');log=base/(mode+'_controller.log');tmp=base/(mode+'_tmp');tmp.mkdir(exist_ok=False)
assert not O.exists()
command=[sys.executable,'-B',str(S/'run_task.py'),'--config',str(P/'CONFIG.json'),'--manifest',str(P/'SOURCE.json'),'--mode',mode,'--out',str(O)]
record=dict(experiment_id=cfg['experiment_ids'][mode],code_commit=C,mode=mode,frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),environment_record=str(P/'FROZEN_ENVIRONMENT.json'),environment_record_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),source_manifest_sha256=sha(P/'SOURCE.json'),raw_result_location=str(O),aggregate_summary_location=str(O/'SUMMARY.json'),gate_decision_location=str(O/'GATE.json'),command=command,observed_host_compute_processes=compute,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),CPU_only=True)
put(pre,record)
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=str(tmp)))
proc=pathlib.Path('/proc')/str(child.pid);tail=(proc/'stat').read_text().rsplit(')',1)[1].split()
result=dict(pid=child.pid,start_ticks=int(tail[19]),cmdline_sha256=sha(proc/'cmdline'),source_commit=C,mode=mode,out=str(O),log=str(log),prelaunch_record_sha256=sha(pre),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive_download_authorized_in_this_mode=mode=='acquire_census',model_calls=0,GPU_calls=0)
put(handle,result);print(json.dumps(result))
''')
            put(P/('LAUNCH_'+a.mode+'.json'),result)
        else:
            result=remote('PARAMS='+repr(params)+'\nCOLLECT='+repr(a.action=='collect')+'\n'+r'''import datetime,hashlib,json,pathlib,subprocess
B=pathlib.Path(PARAMS['result_base']);O=pathlib.Path(PARAMS['out']);mode=PARAMS['mode'];h=json.loads((B/(mode+'_HANDLE.json')).read_bytes());proc=pathlib.Path('/proc')/str(h['pid'])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
alive=False;state=None
if proc.exists():
 tail=(proc/'stat').read_text().rsplit(')',1)[1].split();state=tail[0];assert int(tail[19])==h['start_ticks'],'PID identity changed'
 alive=state not in ('Z','X')
 if alive:assert sha(proc/'cmdline')==h['cmdline_sha256'],'command identity changed'
r=dict(handle=h,alive=alive,state=state,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
for name in ('DOWNLOAD_PROGRESS.json','SCAN_PROGRESS.json','GATE.json','SUMMARY.json'):
 p=O/name
 if p.exists():r[name]=json.loads(p.read_bytes())
if COLLECT:
 assert not alive and (O/'GATE.json').exists(),'not complete; do not collect/restart'
 files=[]
 for p in sorted(O.iterdir()):
  if p.is_file() and p.stat().st_size<2000000:files.append(dict(path=p.name,remote=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 for suffix in ('_PRELAUNCH.json','_HANDLE.json','_controller.log'):
  p=B/(mode+suffix);assert p.stat().st_size<2000000;files.append(dict(path='launch/'+p.name,remote=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 S=pathlib.Path(PARAMS['project'])/'source';assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
 r.update(files=files,source_clean=True)
print(json.dumps(r))
''')
            if a.action=='collect':
                dest=E/('MAGICDATA_HEADER_'+a.mode.upper()+'_v1');dest.mkdir(exist_ok=False);s=client.open_sftp()
                try:
                    for row in result['files']:
                        with s.open(row['remote'],'rb') as f:data=f.read()
                        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];p=dest/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
                finally:s.close()
                put(dest/'COLLECTION_MANIFEST.json',result)
                default=json.loads(subprocess.check_output([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],cwd=R,text=True));put(dest/'DEFAULT_PREFLIGHT_AFTER.json',default)
        print(json.dumps(result,indent=2))
    finally:client.close()
if __name__=='__main__':main()
