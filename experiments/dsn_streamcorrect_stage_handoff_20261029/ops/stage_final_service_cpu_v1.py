"""Stage final v2 plan/configs and independent CPU prerequisites; never launch NN."""
import datetime,hashlib,json,pathlib,subprocess,sys,shlex
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029';ROOT=H.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def put(p,x):pathlib.Path(p).write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
planpath=I/'FINAL_SERVICE_v2_FROZEN.json';plan=read(planpath);assert sha(planpath)=='cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a'
source=I/'service_preflight_source_v1';commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
packages=I/'packages';packages.mkdir(exist_ok=True);manifestpath=packages/'SERVICE_PREFLIGHT_SOURCE_v1.json';bundle=packages/'SERVICE_PREFLIGHT_SOURCE_v1.bundle'
if not manifestpath.exists():
 files=subprocess.check_output(['git','-C',str(source),'ls-files','-z']).decode().rstrip('\0').split('\0');put(manifestpath,dict(source_commit=commit,code_commit=commit,files=[dict(path=f,bytes=(source/f).stat().st_size,sha256=sha(source/f)) for f in files],scope='Only CPU prerequisite; never model or deployed service'));subprocess.run(['git','-C',str(source),'bundle','create',str(bundle),'HEAD'],check=True)
assert read(manifestpath)['source_commit']==commit
# Local config-only review is independent of the template generator; no results used.
sys.path.insert(0,str(source));from review_final import validate
pilotplan=read(H/'SERVICE_PILOT_v1_FROZEN.json');pilotcell=next(c for c in pilotplan['cells'] if c['arm']=='two_full_spec_early');pilotlocal=H/'service_pilot_v1_configs'/pathlib.PurePosixPath(pilotcell['config']).name
configs=[read(I/'service_v1_configs'/pathlib.PurePosixPath(c['config']).name) for c in plan['cells']]
local_review=validate(plan,read(I/'SOURCE_RECEIPT_v1.json'),read(I/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json'),configs,read(pilotlocal)['settings'],read(I/'REFERENCE_RESULTS_v1/DETAILS.json'));put(I/'FINAL_SERVICE_LOCAL_CONFIG_REVIEW_v1.json',dict(status='PASS_INDEPENDENT_FINAL16_LOCAL_CONFIG_REVIEW',code_commit=commit,plan_sha256=sha(planpath),**local_review))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 def mkdir(p):
  assert p.startswith(B+'/')
  try:s.stat(p)
  except FileNotFoundError:mkdir(str(pathlib.PurePosixPath(p).parent));s.mkdir(p)
 uploads=[(manifestpath,P+'/SERVICE_PREFLIGHT_SOURCE_v1.json'),(bundle,P+'/SERVICE_PREFLIGHT_SOURCE_v1.bundle'),(planpath,P+'/FINAL_SERVICE_v2_FROZEN.json'),(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json',plan['final_method_freeze_record']),(I/'METADATA_SELECTION_v1_FROZEN.json',plan['metadata_selection']),(I/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json',plan['frozen_appraisal'])]
 uploads += [(I/'service_v1_configs'/pathlib.PurePosixPath(cell['config']).name,cell['config']) for cell in plan['cells']]
 for local,target in uploads:
  mkdir(str(pathlib.PurePosixPath(target).parent));data=local.read_bytes()
  try:
   with s.open(target,'rb') as f:assert f.read()==data,'Existing frozen bytes differ; never overwrite'
  except FileNotFoundError:
   with s.open(target,'wb') as f:f.write(data)
 s.close()
 script="""import pathlib,json,hashlib,subprocess,sys,os,io,unittest
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);source=P/'service_preflight_source_v1';manifest=json.loads((P/'SERVICE_PREFLIGHT_SOURCE_v1.json').read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'SERVICE_PREFLIGHT_SOURCE_v1.json')==MANIFEST_SHA
if not source.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'SERVICE_PREFLIGHT_SOURCE_v1.bundle'),str(source)],check=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(source),'checkout',manifest['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==manifest['source_commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
for f in manifest['files']:assert sha(source/f['path'])==f['sha256'] and (source/f['path']).stat().st_size==f['bytes']
sys.path.insert(0,str(source));log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(source),pattern='test_*.py'));assert result.wasSuccessful() and result.testsRun==12 and not result.skipped and 'torch' not in sys.modules
planpath=P/'FINAL_SERVICE_v2_FROZEN.json';out=O/'service_cpu_v1'
command=[sys.executable,'-B',str(source/'review_final.py'),'--plan',str(planpath),'--plan-sha',PLAN_SHA,'--pilot-config',PILOT,'--out',str(out)]
subprocess.run(command,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'));(out/'CPU_CONTROLS.log').write_text(log.getvalue());print(json.dumps(dict(CPU_gate=str(out/'GATE.json'),CPU_gate_sha256=sha(out/'GATE.json'),source_commit=manifest['source_commit'],source_manifest_sha256=MANIFEST_SHA,controls=12,model_calls=0,gpu_calls=0)))
""".replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('MANIFEST_SHA',repr(sha(manifestpath))).replace('PLAN_SHA',repr(sha(planpath))).replace('PILOT',repr(pilotcell['config']))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=90);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(I/'FINAL_SERVICE_CPU_STAGE_STDOUT_v1.txt').write_bytes(stdout);(I/'FINAL_SERVICE_CPU_STAGE_STDERR_v1.txt').write_bytes(stderr);print(stdout.decode());print(stderr.decode(),file=sys.stderr)
 s=c.open_sftp();dest=I/'SERVICE_CPU_RESULTS_v1';dest.mkdir(exist_ok=False)
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','CPU_CONTROLS.log','failure.txt']:
  try:
   with s.open(O+'/service_cpu_v1/'+name,'rb') as f:data=f.read()
   (dest/name).write_bytes(data)
  except FileNotFoundError:pass
 s.close();assert rc==0,'Preserved CPU prerequisite failure; no NN launched'
 pointer=read(ROOT/'experiments/repository_identity_20261027/CURRENT.json');pointer.update(source_worktree=str(H/'source_v3'),source_commit=plan['source_commit'],source_manifest=str(H/'packages/SOURCE_v3_LOCAL_PREFLIGHT.json'),source_manifest_sha256=sha(H/'packages/SOURCE_v3_LOCAL_PREFLIGHT.json'),research_state=str(I/'FINAL_SERVICE_v2_FROZEN.json'),GPU_queue='FINAL4_NEW_SPEAKERS_16_FRESH_SERVICE_CELLS_ONLY',scope='Unchanged bdfa frozen before new metadata; new4 exact full-state/C/IDs including stage_execution required.',previous_pointer=str(I/'CURRENT_BEFORE_FINAL_SERVICE_v1.json'))
 put(I/'CURRENT_FINAL_SERVICE_CANDIDATE_v1.json',pointer)
 put(I/'FINAL_SERVICE_CPU_READY_v1.json',dict(status='READY_FOR_ROOT_CURRENT_PREFLIGHT_AND_ALLOCATED_LAUNCH',plan=str(planpath),plan_sha256=sha(planpath),remote_plan=P+'/FINAL_SERVICE_v2_FROZEN.json',CPU_gate=O+'/service_cpu_v1/GATE.json',CPU_gate_sha256=sha(dest/'GATE.json'),method_source_commit=plan['source_commit'],reviewer_source_commit=commit,model_calls=0,gpu_calls=0,IO_released=True))
finally:c.close()
