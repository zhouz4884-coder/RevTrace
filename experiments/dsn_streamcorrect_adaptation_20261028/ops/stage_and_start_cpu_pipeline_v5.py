"""Stage byte-identified operations scripts and launch CPU-only prerequisite chain."""
import pathlib,hashlib,json,shlex,sys,datetime
T=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_20261028';O=B+'/results/revtrace/dsn_streamcorrect_20261028'
names=['remote_bootstrap_cpu_env_v5.py','remote_prepare_native_environment_v5.py','remote_native_source_cpu_gate_v5.py','remote_native_interface_cpu_gate_v5.py','remote_build_campaign_v5.py','remote_cpu_environment_pipeline_v5.py']
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();records=[]
try:
 s=c.open_sftp();remote=P+'/cpu_setup_v5'
 try:s.mkdir(remote)
 except OSError:s.stat(remote)
 for name in names:
  data=(T/'ops'/name).read_bytes();path=remote+'/'+name
  try:
   with s.open(path,'rb') as f:assert f.read()==data,'existing operations source mismatch'
  except FileNotFoundError:
   with s.open(path,'wb') as f:f.write(data)
  records.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 manifest=dict(operation_id='SC_NATIVE_CPU_PREPARATION_PIPELINE_V5',native_runtime_commit='a652f6097c2269232b332ad046e399f9968b16e2',scripts=records,gpu_launched=False)
 mpath=remote+'/OPERATIONS_SOURCE_MANIFEST.json';body=json.dumps(manifest,indent=2).encode()
 try:
  with s.open(mpath,'rb') as f:assert f.read()==body
 except FileNotFoundError:
  with s.open(mpath,'wb') as f:f.write(body)
 s.close()
 code='''import pathlib,json,subprocess,hashlib,datetime,os
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
handle=O/'CPU_ENV_PIPELINE_v5_HANDLE.json';assert not handle.exists(),'existing setup handle; inspect instead of relaunch'
manifest=P/'cpu_setup_v5/OPERATIONS_SOURCE_MANIFEST.json'
for row in json.loads(manifest.read_text())['scripts']:
 b=pathlib.Path(row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
log=O/'cpu_environment_pipeline_v5.log';assert not log.exists()
command=[str(B/'envs/revbatch-cu128/bin/python'),'-B',str(P/'cpu_setup_v5/remote_cpu_environment_pipeline_v5.py')]
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid)
r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),safe_log=str(log),command=command,operations_manifest=str(manifest),operations_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),gate='wait exact assets PASS then CPU prerequisites only; no native GPU launch')
handle.write_text(json.dumps(r,indent=2));print(json.dumps(r))'''
 i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(code),timeout=45)
 output=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status()
 if rc:raise RuntimeError('CPU pipeline launch failed: '+err)
 handle=json.loads(output);folder=T/'cpu_pipeline_v5';folder.mkdir(exist_ok=False)
 (folder/'HANDLE.json').write_text(json.dumps(handle,indent=2));(folder/'OPERATIONS_SOURCE_MANIFEST.json').write_bytes(body)
 current=T/'CURRENT_STATUS.json';state=json.loads(current.read_text());state['cpu_preparation_pipeline']=handle;state['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();current.write_text(json.dumps(state,indent=2));print(json.dumps(handle,indent=2))
finally:c.close()
