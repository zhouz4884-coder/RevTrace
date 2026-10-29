"""B-only immutable staging, complete source/assets/environment and CPU gates; no GPU run."""
import hashlib,json,pathlib,shlex,sys
T=pathlib.Path(__file__).resolve().parents[1];plan=json.loads((T/'SERVICE_PILOT_v1_FROZEN.json').read_text(encoding='utf8'));P=str(pathlib.PurePosixPath(plan['source_root']).parent);O=str(pathlib.PurePosixPath(plan['raw_result_location']).parent)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp();configdir=P+'/service_pilot_v1_configs'
 try:s.mkdir(configdir)
 except OSError:s.stat(configdir)
 pairs=[(T/'packages/SOURCE_v3.bundle',P+'/SOURCE_v3.bundle'),(T/'packages/SOURCE_v3.json',P+'/SOURCE_v3.json'),(T/'SERVICE_PILOT_v1_FROZEN.json',P+'/SERVICE_PILOT_v1_FROZEN.json')]
 pairs += [(f,configdir+'/'+f.name) for f in sorted((T/'service_pilot_v1_configs').glob('*.json'))]
 for local,target in pairs:
  assert target.startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/');data=local.read_bytes()
  try:
   with s.open(target,'rb') as f:assert f.read()==data,'existing remote bytes differ'
  except FileNotFoundError:
   with s.open(target,'wb') as f:f.write(data)
 s.close()
 code=r'''import pathlib,json,hashlib,subprocess,os,sys,datetime
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);plan=json.loads((P/'SERVICE_PILOT_v1_FROZEN.json').read_text());S=P/'source_v3'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'other GPU worker exists; do not stage heavy IO'
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,driver_version','--format=csv,noheader'],text=True)
assert len(gpu.strip().splitlines())==2 and gpu.count('RTX 3090')==2
assert sha(P/'SOURCE_v3.json')==plan['source_manifest_sha256']
if not S.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE_v3.bundle'),str(S)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout',plan['source_commit']],check=True,capture_output=True)
sys.path.insert(0,str(S));from native_service import verify_source
identity=verify_source(P/'SOURCE_v3.json');assert identity['source_commit']==plan['source_commit']
assert sha(plan['environment_record'])==plan['environment_sha256'];assert sha(plan['reference_details'])==plan['reference_details_sha256'];assert sha(plan['old_task_fidelity_gate'])==plan['old_task_fidelity_gate_sha256']
cfg=json.loads(pathlib.Path(plan['cells'][0]['config']).read_text());settings=cfg['settings'];author=pathlib.Path(settings['backend']['author_root']);contract=settings['backend']['contract']
assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==contract['native_author_commit']
assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip();assert sha(author/'simul_whisper/simul_whisper.py')==contract['author_whisper_sha256']
assets=[]
for path,row in contract['model_assets'].items():
 p=pathlib.Path(path);assert str(p).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/') and p.stat().st_size==row['bytes'];assert sha(p)==row['sha256'];assets.append(dict(path=path,bytes=row['bytes'],sha256=row['sha256']))
for source in settings['model_sources']:assert sha(source['path'])==source['audio_sha256']
for cell in plan['cells']:assert sha(cell['config'])==cell['config_sha256']
cpu=O/'service_cpu_v3';assert not cpu.exists(),'CPU run already exists; do not overwrite'
result=subprocess.run([sys.executable,'-B',str(S/'run_cpu_gate.py'),'--out',str(cpu),'--manifest',str(P/'SOURCE_v3.json')],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
assert result.returncode==0,(result.stdout,result.stderr)
gate=json.loads((cpu/'GATE.json').read_text());assert gate['tests']==118 and gate['skipped']==0 and gate['status']=='PASS_CPU_STATE_CONTRACT_TESTS_ONLY'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
receipt=dict(status='PASS_PILOT_SOURCE_ASSETS_ENVIRONMENT_AND_CPU118_NO_NEURAL_LAUNCH',source_commit=identity['source_commit'],source_manifest_sha256=sha(P/'SOURCE_v3.json'),plan_sha256=sha(P/'SERVICE_PILOT_v1_FROZEN.json'),cpu_gate=str(cpu/'GATE.json'),cpu_gate_sha256=sha(cpu/'GATE.json'),tests=118,skipped=0,model_assets_fully_SHA_reverified=len(assets),model_asset_bytes=sum(x['bytes'] for x in assets),audio_sources_SHA_reverified=len(settings['model_sources']),actual_GPU=gpu,environment_python=sys.executable,environment_sha256=sha(plan['environment_record']),reference_details_sha256=sha(plan['reference_details']),old_task_fidelity_gate_sha256=sha(plan['old_task_fidelity_gate']),GPU_launched=False,models_loaded=False,assets=assets,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
dest=O/'SERVICE_PREREQUISITE_v1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='assets'},indent=2))
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=600);i.write(code);i.flush();i.channel.shutdown_write();stdout=o.read().decode();stderr=e.read().decode();rc=o.channel.recv_exit_status()
 (T/'SERVICE_SETUP_STDOUT_v1.txt').write_text(stdout,encoding='utf8');(T/'SERVICE_SETUP_STDERR_v1.txt').write_text(stderr,encoding='utf8');print(stdout);assert rc==0,'Preserved remote CPU/setup failure: '+stderr[-2000:]
 s=c.open_sftp();dest=T/'service_cpu_v3';dest.mkdir(exist_ok=False)
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','unittest.log']:s.get(O+'/service_cpu_v3/'+name,str(dest/name))
 s.get(O+'/SERVICE_PREREQUISITE_v1.json',str(T/'SERVICE_PREREQUISITE_v1.json'));s.close()
finally:c.close()
