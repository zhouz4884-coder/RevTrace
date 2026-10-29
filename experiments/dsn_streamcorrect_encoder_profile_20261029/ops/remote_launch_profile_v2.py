"""Launch only the root-allocated frozen13 component controller, detached log."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_encoder_profile_20261029';O=B/'results/revtrace/dsn_streamcorrect_encoder_profile_20261029'
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
cfg=read(P/'PROFILE_PLAN_v2_FROZEN.json');assert sha(P/'PROFILE_PLAN_v2_FROZEN.json')=='789f0069a563f4cbc4e454c5259da9b482f588b8d6a708605d31ef134258a960'
assert sha(O/'ASSET_PREREQUISITE_v2.json')=='6473a07fea831bca671c49282f9b48b8dca17217c4aeb762b380ddb442d0ce72'
assert sha(O/'cpu_gate_v2/GATE.json')=='1ac312e981d60a5615c0660ccceed2070c7215f0926dec545089716caeb9d30c'
asset=read(O/'ASSET_PREREQUISITE_v2.json');assert asset['status']=='PASS_COMPLETE_MODEL_AUDIO_AND_CPU17_COMPONENT_PREREQUISITE'
assert read(O/'cpu_gate_v2/GATE.json')['tests']==17
localgate=read(P/'ROOT_NOARG_PREFLIGHT_v2.json');assert localgate['gate']=='SOURCE_IDENTITY_PASS' and localgate['files_verified']==8 and localgate['run_record_prelaunch_checked']
assert localgate['code_commit']==cfg['profile_source_commit']
for source,commit,m in [(P/'source_v2',cfg['profile_source_commit'],read(P/'SOURCE_v2.json')),(pathlib.Path(cfg['imported_runtime_root']),cfg['imported_runtime_commit'],read(cfg['imported_runtime_manifest']))]:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==commit
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip()
 for f in m['files']:assert sha(source/f['path'])==f['sha256']
for f in asset['full_rehashed_assets']:
 p=pathlib.Path(f['path']);assert p.stat().st_size==f['bytes'] and p.stat().st_mode&0o222==0
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],text=True).strip()
assert not pathlib.Path(cfg['out']).exists() and not (O/'HANDLE_v2.json').exists()
log=O/'profile_v2_controller.log'
with log.open('xb') as f:
 p=subprocess.Popen([sys.executable,'-B',str(P/'source_v2/run_profile.py'),'--config',str(P/'PROFILE_PLAN_v2_FROZEN.json')],cwd=P,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
time.sleep(.1);proc=pathlib.Path('/proc')/str(p.pid);stat=(proc/'stat').read_text().rsplit(') ',1)[1].split();cmd=(proc/'cmdline').read_bytes()
handle=dict(status='LAUNCHED_ACTUAL_FROZEN13_COMPONENT_CONTROLLER',pid=p.pid,start_ticks=stat[19],command_sha256=hashlib.sha256(cmd).hexdigest(),command=[x.decode() for x in cmd.split(b'\0') if x],profile_source_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit'],plan_sha256=sha(P/'PROFILE_PLAN_v2_FROZEN.json'),profile_manifest_sha256=sha(P/'SOURCE_v2.json'),CPU_gate_sha256=sha(O/'cpu_gate_v2/GATE.json'),asset_prerequisite_sha256=sha(O/'ASSET_PREREQUISITE_v2.json'),local_preflight_sha256=sha(P/'ROOT_NOARG_PREFLIGHT_v2.json'),raw=cfg['out'],log=str(log),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='13 component/oracle calls, not deployed service')
(O/'HANDLE_v2.json').write_text(json.dumps(handle,indent=2)+'\n');print(json.dumps(handle),flush=True)
