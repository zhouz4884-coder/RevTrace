"""Root-allocated IO only: exact official Range -> RAM -> B, then frozen acquisition."""
import concurrent.futures,datetime,hashlib,json,os,pathlib,shlex,sys,urllib.request
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_sustained_20261030';O=B+'/results/revtrace/dsn_native_sustained_20261030'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):pathlib.Path(p).write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
selection_path=F/'METADATA_SELECTION_v1_FROZEN.json';selection=read(selection_path);manifest=F/'packages/DATA_SOURCE_v1.json';source=read(manifest)
assert sha(selection_path)=='b0cfc858da370da871bdffffa97f7364d1ec232169333cb5a09036c67d4af65a'
assert source['source_commit']=='6ad60f8aa69cf0324041e6a1672acffdde9631b4' and read(F/'CPU_RESULTS_v1/GATE.json')['tests']==18
current=read(R/'experiments/repository_identity_20261027/CURRENT.json');assert current['source_commit']==source['source_commit']
assert read(F/'ROOT_DATA_SELECTION_PREFLIGHT_v1.json')['code_commit']==source['source_commit']
operator=dict(operator_id='SC_SUSTAINED_EXACT_RANGE_TRANSPORT_OPERATOR_V1',operator_file_sha256=sha(__file__),pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_sha256=sha(selection_path),scientific_extraction_source_commit=source['source_commit'],scope='Byte transport only; extraction/recipe/PCM semantics execute in the separately frozen7-file source. No new model, data replacement, local audio file or PCM transformation.',data_root=B+'/datasets/revtrace/native_sustained_20261030',raw_ranges=P+'/transport_v1_ranges')
op=F/'TRANSPORT_OPERATOR_START_v1.json';assert not op.exists();put(op,operator);print(json.dumps(operator),flush=True)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
client=ssh_client();s=client.open_sftp()
def mkdir(path):
 assert path.startswith(B+'/')
 parts=pathlib.PurePosixPath(path).parts;now=''
 for part in parts:
  now=now+'/'+part if now else part
  if len(now)<=len(B):continue
  try:s.stat(now)
  except FileNotFoundError:s.mkdir(now)
def upload(local,target):
 data=pathlib.Path(local).read_bytes()
 try:
  with s.open(target,'rb') as f:assert f.read()==data
 except FileNotFoundError:
  with s.open(target,'wx') as f:f.write(data);f.flush()
def remote(code):
 stdin,stdout,stderr=client.exec_command(shlex.quote(PY)+' -B -',timeout=120);stdin.write(code);stdin.flush();stdin.channel.shutdown_write();a=stdout.read();b=stderr.read();rc=stdout.channel.recv_exit_status()
 if rc:raise RuntimeError('remote setup/acquisition launch failed: '+b.decode('utf8',errors='replace')[-2000:])
 return a
try:
 mkdir(P);mkdir(O);mkdir(P+'/transport_v1_ranges')
 for local,name in [(manifest,'DATA_SOURCE_v1.json'),(F/'packages/DATA_SOURCE_v1.bundle','DATA_SOURCE_v1.bundle'),(selection_path,'METADATA_SELECTION_v1_FROZEN.json')]:upload(local,P+'/'+name)
 code="""import pathlib,json,hashlib,subprocess,sys,os,datetime,io,unittest
P=pathlib.Path(PVALUE);O=pathlib.Path(OVALUE);source=P/'source_v1';manifest=P/'DATA_SOURCE_v1.json'
m=json.loads(manifest.read_bytes());assert m['source_commit']==COMMIT
if not source.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'DATA_SOURCE_v1.bundle'),str(source)],check=True);subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(source),'checkout','-q',COMMIT],check=True)
sys.path.insert(0,str(source));from data_common import verify_source,put,sha
identity=verify_source(source,manifest,COMMIT)
out=O/'data_cpu_v1';out.mkdir(exist_ok=False);tmp=O/'cpu_tmp';tmp.mkdir();os.environ['TMPDIR']=str(tmp)
cfg=dict(experiment_id='SC_SUSTAINED_REMOTE_DATA_CPU_V1',source_commit=COMMIT,manifest_sha256=sha(manifest),tests_expected=18,model_calls=0)
put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,model_calls=0))
put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=COMMIT,frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'CPU_CONTROLS.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(source),pattern='test_*.py'));(out/'CPU_CONTROLS.log').write_text(log.getvalue())
assert result.wasSuccessful() and result.testsRun==18 and not result.skipped and 'torch' not in sys.modules
gate=dict(status='PASS_REMOTE_COMPLETE_SOURCE_AND18_CPU_CONTROLS_NO_NEURAL',source_commit=COMMIT,source_identity=identity,tests=18,skipped=0,model_calls=0)
put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate);print(json.dumps(gate))
""".replace('PVALUE',repr(P)).replace('OVALUE',repr(O)).replace('COMMIT',repr(source['source_commit']))
 result=remote(code);(F/'REMOTE_CPU_STAGE_STDOUT_v1.json').write_bytes(result);print(result.decode(),flush=True)
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','CPU_CONTROLS.log','SUMMARY.json','GATE.json']:
  d=F/'REMOTE_CPU_RESULTS_v1';d.mkdir(exist_ok=True);s.get(O+'/data_cpu_v1/'+name,str(d/name))
 entries=[entry for recipe in selection['recipes'] for entry in recipe['members']]
 def fetch(entry):
  begin=entry['local_offset'];length=entry['compressed']+4096;end=begin+length-1
  for attempt in range(3):
   for suffix in ('','?download=true'):
    try:
     req=urllib.request.Request(selection['archive_public_url']+suffix,headers={'Range':f'bytes={begin}-{end}'})
     with urllib.request.urlopen(req,timeout=45) as response:
      raw=response.read(length+1);status=response.status;content_range=response.headers.get('Content-Range','')
     if status==206 and len(raw)==length and content_range.startswith(f'bytes {begin}-{end}/'):
      return entry,raw,content_range,suffix
    except OSError:pass
  raise RuntimeError('exact frozen public Range unavailable: '+entry['source_id'])
 staged=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(fetch,e) for e in entries]
  for future in concurrent.futures.as_completed(futures):
   entry,raw,content_range,suffix=future.result();name=entry['source_id'];path=P+'/transport_v1_ranges/'+name+'.range';digest=hashlib.sha256(raw).hexdigest()
   try:
    with s.open(path,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==digest
   except FileNotFoundError:
    with s.open(path+'.part','wx') as f:f.write(raw);f.flush()
    s.rename(path+'.part',path);s.chmod(path,0o444)
   staged.append(dict(source_id=name,path=path,bytes=len(raw),sha256=digest,content_range=content_range,public_source=selection['archive_public_url'],route_suffix=suffix,local_audio_file_written=False))
   print(json.dumps(dict(staged=len(staged),target=48,source_id=name,bytes=len(raw))),flush=True)
 staged.sort(key=lambda x:next(i for i,e in enumerate(entries) if e['source_id']==x['source_id']))
 transport=dict(operator=operator,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_sha256=sha(selection_path),members=48,staged_ranges=staged,new_model_calls=0,local_audio_files_written=False)
 put(F/'STAGED_RANGE_TRANSPORT_v1.json',transport)
 old=read(R/'experiments/dsn_streamcorrect_independent_20261029/ACQUISITION_v2_FROZEN.json')
 cfg=dict(experiment_id='SC_SUSTAINED_TWO_NEW_SPEAKER_48PART_ACQUISITION_V1',source_commit=source['source_commit'],selection=P+'/METADATA_SELECTION_v1_FROZEN.json',selection_sha256=sha(selection_path),designated_disk=B,out=O+'/acquisition_v1',dataset_root=B+'/datasets/revtrace/native_sustained_20261030',reference_metadata=old['reference_metadata'],reference_metadata_sha256=old['reference_metadata_sha256'],staged_ranges={x['source_id']:x for x in staged},transport_operator_sha256=sha(__file__),environment_python=PY,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 cp=F/'ACQUISITION_v1_FROZEN.json';assert not cp.exists();put(cp,cfg)
 put(F/'ACQUISITION_PRELAUNCH_v1.json',dict(experiment_id=cfg['experiment_id'],code_commit=source['source_commit'],frozen_config=str(cp),config_sha256=sha(cp),environment_record=str(F/'REMOTE_CPU_RESULTS_v1/ENVIRONMENT.json'),environment_sha256=sha(F/'REMOTE_CPU_RESULTS_v1/ENVIRONMENT.json'),raw_result_location=cfg['out'],aggregate_summary_location=cfg['out']+'/SUMMARY.json',gate_decision_location=cfg['out']+'/GATE.json',model_calls=0))
 upload(cp,P+'/ACQUISITION_v1_FROZEN.json');upload(F/'STAGED_RANGE_TRANSPORT_v1.json',P+'/STAGED_RANGE_TRANSPORT_v1.json')
 code="""import pathlib,json,hashlib,subprocess,sys,os,datetime
P=pathlib.Path(PVALUE);O=pathlib.Path(OVALUE);cfg=P/'ACQUISITION_v1_FROZEN.json';assert hashlib.sha256(cfg.read_bytes()).hexdigest()==CFGSHA
gate=json.loads((O/'data_cpu_v1/GATE.json').read_bytes());assert gate['tests']==18 and gate['source_commit']==COMMIT
command=[sys.executable,'-B',str(P/'source_v1/acquire_recipe.py'),'--config',str(cfg),'--manifest',str(P/'DATA_SOURCE_v1.json')];log=O/'acquisition_v1.log'
assert not (O/'acquisition_v1').exists() and not (O/'ACQUISITION_HANDLE_v1.json').exists()
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit=COMMIT,config_sha256=CFGSHA,raw_result_location=str(O/'acquisition_v1'),log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),expected_parts=48,expected_streams=2,model_calls=0)
(O/'ACQUISITION_HANDLE_v1.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
""".replace('PVALUE',repr(P)).replace('OVALUE',repr(O)).replace('COMMIT',repr(source['source_commit'])).replace('CFGSHA',repr(sha(cp)))
 result=remote(code);record=json.loads(result);put(F/'ACQUISITION_HANDLE_v1.json',record);print(json.dumps(record),flush=True)
except BaseException as exc:
 put(F/'TRANSPORT_OR_SETUP_FAILURE_v1.json',dict(operator_id=operator['operator_id'],error_type=type(exc).__name__,selected_members_unchanged=True,new_model_calls=0))
 raise
finally:s.close();client.close()

