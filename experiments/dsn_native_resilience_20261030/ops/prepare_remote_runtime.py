"""Root-only B-disk source/assets/Linux CPU setup. Default dry-run; never launches NN."""
import argparse,datetime,hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--version',default='v1');ap.add_argument('--attempt',default='');ap.add_argument('--plan',type=pathlib.Path);ap.add_argument('--minimum-tests',type=int,default=238);a=ap.parse_args()
 import re
 assert not a.attempt or re.fullmatch(r'r[1-9]\d*',a.attempt),'attempt must be a new rN label'
 runlabel=a.version+('_'+a.attempt if a.attempt else '')
 planpath=a.plan or F/('SHORT_PILOT_'+a.version+'_FROZEN.json');manifest=F/'packages'/('SOURCE_'+a.version+'.json');bundle=F/'packages'/('SOURCE_'+a.version+'.bundle')
 if not a.execute:print(json.dumps(dict(status='DRY_RUN_NO_REMOTE_OR_MUTATION',plan=str(planpath),manifest=str(manifest),remote_project=P,remote_python=PY,attempt=a.attempt or 'initial',runlabel=runlabel,cpu_output=O+'/runtime_cpu_'+runlabel,scope='complete source,26 model assets,author pin,environment and all formal zero-skip CPU; no neural execution')));return
 plan=read(planpath);m=read(manifest);assert m['source_commit']==plan['source_commit'] and sha(manifest)==plan['source_manifest_sha256'];assert plan['environment_python']==PY
 current=read(R/'experiments/repository_identity_20261027/CURRENT.json');assert current['source_commit']==m['source_commit'] and current['source_manifest_sha256']==sha(manifest)
 pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);assert json.loads(pre.stdout)['gate']=='SOURCE_IDENTITY_PASS';prepath=F/('REMOTE_SETUP_ROOT_NOARG_'+runlabel+'.json');assert not prepath.exists();prepath.write_bytes(pre.stdout)
 cfgfolder=F/('short_pilot_'+a.version+'_configs');assert cfgfolder.is_dir()
 runner=F/'ops/runtime_cpu_runner.py';runner_target=P+'/runtime_cpu_runner_'+runlabel+'.py'
 pairs=[(manifest,P+'/SOURCE_'+a.version+'.json'),(bundle,P+'/SOURCE_'+a.version+'.bundle'),(planpath,P+'/'+planpath.name),(runner,runner_target)]+[(f,P+'/short_pilot_'+a.version+'_configs/'+f.name) for f in sorted(cfgfolder.glob('*.json'))]
 sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
 client=ssh_client()
 try:
  s=client.open_sftp()
  def mkdir(path):
   assert path.startswith(B+'/');now=''
   for part in pathlib.PurePosixPath(path).parts:
    now=now+'/'+part if now else part
    if len(now)<=len(B):continue
    try:s.stat(now)
    except FileNotFoundError:s.mkdir(now)
  for path in (P,O,P+'/short_pilot_'+a.version+'_configs'):mkdir(path)
  for local,target in pairs:
   assert target.startswith(B+'/');data=local.read_bytes()
   try:
    with s.open(target,'rb') as f:assert f.read()==data,'existing remote immutable bytes differ'
   except FileNotFoundError:
    with s.open(target,'wx') as f:f.write(data);f.flush()
  s.close()
  code=r'''import pathlib,json,hashlib,subprocess,sys,os,datetime,platform,importlib.metadata,io,unittest
P=pathlib.Path(PVALUE);O=pathlib.Path(OVALUE);version=VERSION;runlabel=RUNLABEL;mp=P/('SOURCE_'+version+'.json');pp=P/PLANNAME;m=json.loads(mp.read_bytes());plan=json.loads(pp.read_bytes());S=P/('source_'+version);runner=pathlib.Path(RUNNERPATH)
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
assert sha(mp)==MANIFESTSHA and sha(pp)==PLANSHA
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host; do not stage heavyIO/CPU'
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,driver_version','--format=csv,noheader'],text=True)
assert len(gpu.strip().splitlines())==2 and gpu.count('RTX 3090')==2
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/('SOURCE_'+version+'.bundle')),str(S)],check=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
sys.path.insert(0,str(S));from native_service import verify_source
identity=verify_source(mp);assert identity['source_commit']==plan['source_commit']
for cell in plan['cells']:assert sha(cell['config'])==cell['config_sha256']
first=json.loads(pathlib.Path(plan['cells'][0]['config']).read_bytes());settings=first['settings'];backend=settings['backend'];contract=backend['contract'];author=pathlib.Path(backend['author_root'])
assert contract['native_author_commit']=='bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3'
assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==contract['native_author_commit']
assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert sha(author/'simul_whisper/simul_whisper.py')==contract['author_whisper_sha256']
author_files=[]
for name in ('simul_whisper/simul_whisper.py','simul_whisper/config.py','token_buffer.py'):
 data=(author/name).read_bytes();blob=subprocess.check_output(['git','-C',str(author),'show',contract['native_author_commit']+':'+name]);assert data==blob;author_files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
assert sha(plan['environment_record'])==plan['environment_sha256'];frozen=json.loads(pathlib.Path(plan['environment_record']).read_bytes());packages={k:importlib.metadata.version(k) for k in frozen['packages']};assert packages==frozen['packages']
assert sha(plan['reference_details'])==plan['reference_details_sha256']
assets=[]
assert len(contract['model_assets'])==26
for path,row in contract['model_assets'].items():
 assert str(path).startswith(BVALUE+'/') and row.get('path',path)==path and pathlib.Path(path).stat().st_size==row['bytes'] and sha(path)==row['sha256'];assets.append(dict(path=path,bytes=row['bytes'],sha256=row['sha256']))
audio=[]
for source in settings['model_sources']:assert sha(source['path'])==source['audio_sha256'];audio.append(dict(source_id=source['source_id'],audio_sha256=source['audio_sha256']))
assert sha(runner)==RUNNERSHA
cache=O/('cpu_cache_'+runlabel);cache.mkdir();tmp=cache/'tmp';tmp.mkdir()
for key,leaf in [('HF_HOME','hf'),('HF_MODULES_CACHE','modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor')]:
 d=cache/leaf;d.mkdir();os.environ[key]=str(d)
os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),REVTRACE_NATIVE_AUTHOR_FILE=str(author/'simul_whisper/simul_whisper.py'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
import tempfile;tempfile.tempdir=str(tmp)
out=O/('runtime_cpu_'+runlabel);out.mkdir();config=dict(experiment_id='SC_NATIVE_RESILIENCE_COMPLETE_SOURCE_CPU_'+runlabel.upper(),source_commit=m['source_commit'],manifest_sha256=sha(mp),plan_sha256=sha(pp),minimum_tests=MINTESTS,operator_cpu_runner_path=str(runner),operator_cpu_runner_bytes=runner.stat().st_size,operator_cpu_runner_sha256=sha(runner),operator_attempt=runlabel,scope='all frozen source CPU controls and independent source/assets/environment readiness; no trained neural model loaded, no serving')
put=lambda name,x:(out/name).write_bytes((json.dumps(x,indent=2)+'\n').encode())
put('CONFIG.json',config);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages=packages,CUDA_VISIBLE_DEVICES='',trained_neural_models_loaded=False))
put('RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),operator_cpu_runner_path=str(runner),operator_cpu_runner_bytes=runner.stat().st_size,operator_cpu_runner_sha256=sha(runner),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
command=[sys.executable,'-B',str(runner),'--source',str(S),'--manifest',str(mp),'--out',str(out),'--minimum-tests',str(MINTESTS)]
result=subprocess.run(command,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'));(out/'runner_stdout.txt').write_bytes(result.stdout);(out/'runner_stderr.txt').write_bytes(result.stderr)
summary=json.loads((out/'GATE.json').read_bytes());assert result.returncode==0 and summary['status']=='PASS_ALL_FROZEN_SOURCE_CPU_ZERO_SKIP' and summary['skipped']==0,'formal complete CPU gate failed; preserved distinct attempt, no NN launch'
verify_source(mp);assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
receipt=dict(status='PASS_COMPLETE_RUNTIME_SOURCE_26_ASSETS_AUTHOR_ENV_AND_ALL_CPU_NO_NEURAL',source_commit=m['source_commit'],source_manifest_sha256=sha(mp),plan_sha256=sha(pp),environment_record_sha256=sha(plan['environment_record']),reference_details_sha256=sha(plan['reference_details']),CPU_gate=str(out/'GATE.json'),CPU_gate_sha256=sha(out/'GATE.json'),tests=summary['tests'],skipped=0,model_assets_fully_SHA_reverified=len(assets),model_asset_bytes=sum(a['bytes'] for a in assets),assets=assets,author_commit=contract['native_author_commit'],author_files=author_files,audio_sources=audio,actual_GPU=gpu,python=sys.executable,operator_attempt=runlabel,operator_cpu_runner_path=str(runner),operator_cpu_runner_bytes=runner.stat().st_size,operator_cpu_runner_sha256=sha(runner),trained_neural_models_loaded=False,GPU_launched=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
target=O/('RUNTIME_PREREQUISITE_'+runlabel+'.json');assert not target.exists();target.write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k!='assets'},indent=2))
'''
  code=code.replace('PVALUE',repr(P)).replace('OVALUE',repr(O)).replace('BVALUE',repr(B)).replace('VERSION',repr(a.version)).replace('RUNLABEL',repr(runlabel)).replace('RUNNERPATH',repr(runner_target)).replace('RUNNERSHA',repr(sha(runner))).replace('PLANNAME',repr(planpath.name)).replace('MANIFESTSHA',repr(sha(manifest))).replace('PLANSHA',repr(sha(planpath))).replace('MINTESTS',str(a.minimum_tests))
  stdin,stdout,stderr=client.exec_command(shlex.quote(PY)+' -B -',timeout=600);stdin.write(code);stdin.flush();stdin.channel.shutdown_write();result=stdout.read();errors=stderr.read();rc=stdout.channel.recv_exit_status();(F/('REMOTE_SETUP_STDOUT_'+runlabel+'.json')).write_bytes(result);(F/('REMOTE_SETUP_STDERR_'+runlabel+'.txt')).write_bytes(errors)
  if rc:raise RuntimeError('remote source/assets/CPU gate failed; no NN launched. '+errors.decode('utf8',errors='replace')[-2000:])
  s=client.open_sftp();dest=F/('runtime_cpu_'+runlabel);dest.mkdir()
  for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','unittest.log','SUMMARY.json','GATE.json','runner_stdout.txt','runner_stderr.txt'):s.get(O+'/runtime_cpu_'+runlabel+'/'+name,str(dest/name))
  s.get(O+'/RUNTIME_PREREQUISITE_'+runlabel+'.json',str(F/('RUNTIME_PREREQUISITE_'+runlabel+'.json')));s.close();print(result.decode('utf8'))
 finally:client.close()
if __name__=='__main__':main()

