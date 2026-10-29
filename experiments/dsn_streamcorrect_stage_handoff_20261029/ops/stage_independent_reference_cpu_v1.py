"""Stage frozen reference driver and verify data/environment/13 CPU controls.

No model construction or GPU execution. Invoke only after acquisition releases
its CPU/IO window. Actual NN launch remains a separate root allocation.
"""
import pathlib,hashlib,json,sys,shlex
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_reference_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
planpath=I/'ORIGINAL_FULL_REFERENCE_PLAN_v1_FROZEN.json';plan=json.loads(planpath.read_bytes());appraisal=I/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json'
assert json.loads(appraisal.read_bytes())['new_source_neural_calls_at_appraisal_freeze']==0
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 def mkdir(path):
  assert path.startswith(B+'/')
  try:s.stat(path)
  except FileNotFoundError:mkdir(str(pathlib.PurePosixPath(path).parent));s.mkdir(path)
 mkdir(P);mkdir(O)
 uploads=[(H/'packages/NEW_REFERENCE_GENERATOR_SOURCE_v1.bundle',P+'/GENERATOR_SOURCE_v1.bundle'),(H/'packages/NEW_REFERENCE_GENERATOR_SOURCE_v1.json',P+'/GENERATOR_SOURCE_v1.json'),(planpath,P+'/REFERENCE_PLAN_v1_FROZEN.json'),
  (I/'METADATA_SELECTION_v1_FROZEN.json',plan['metadata_selection_manifest']),(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json',plan['final_method_freeze_record']),
  (appraisal,B+'/projects/revtrace_dsn_streamcorrect_independent_20261029/FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json')]
 for local,target in uploads:
  mkdir(str(pathlib.PurePosixPath(target).parent));data=local.read_bytes()
  try:
   with s.open(target,'rb') as f:assert f.read()==data,'existing staged bytes differ; never overwrite'
  except FileNotFoundError:
   with s.open(target,'wb') as f:f.write(data)
 s.close()
 script="""import pathlib,json,hashlib,subprocess,sys,os,datetime,platform,importlib,importlib.metadata,io,unittest,wave
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);planpath=P/'REFERENCE_PLAN_v1_FROZEN.json';plan=json.loads(planpath.read_bytes());out=O/'reference_cpu_v1';out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def put(n,x):(out/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\\n')
assert sha(planpath)==PLAN_SHA
put('CONFIG.json',plan);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),scope='CPU dataset/source/config/environment and synthetic controls; no neural'))
put('RUN_RECORD.json',dict(experiment_id=plan['experiment_id']+'_CPU_PREFLIGHT',code_commit=plan['generator_source_commit'],imported_model_runtime_commit=plan['model_runtime_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'CPU_CONTROLS.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),model_calls=0,gpu_calls=0))
try:
 source=pathlib.Path(plan['generator_source_root'])
 if not source.exists():
  subprocess.run(['git','clone','--no-checkout',str(P/'GENERATOR_SOURCE_v1.bundle'),str(source)],check=True)
  subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
  subprocess.run(['git','-C',str(source),'checkout',plan['generator_source_commit']],check=True)
 sys.path.insert(0,str(source));from original_full_reference import verify_checkout,validate_selection,validate_original_bindings,METHOD_COMMIT,METHOD_MANIFEST_SHA256
 generator=verify_checkout(source,plan['generator_source_manifest'],plan['generator_source_commit'],plan['generator_source_manifest_sha256'])
 runtime=verify_checkout(plan['model_runtime_root'],plan['model_runtime_manifest'],METHOD_COMMIT,METHOD_MANIFEST_SHA256)
 for path,h in [(planpath,PLAN_SHA),(plan['metadata_selection_manifest'],plan['metadata_selection_manifest_sha256']),(plan['source_selection_manifest'],plan['source_selection_manifest_sha256']),(plan['final_method_freeze_record'],plan['final_method_freeze_sha256']),(plan['method_config'],plan['method_config_sha256']),(plan['old_task_fidelity_gate'],plan['old_task_fidelity_gate_sha256']),(plan['frozen_environment_record'],plan['frozen_environment_sha256'])]:assert sha(path)==h
 meta=read(plan['metadata_selection_manifest']);receipt=read(plan['source_selection_manifest']);final=read(plan['final_method_freeze_record'])
 stamp=lambda t:datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
 assert final['method_source_commit']==meta['method_source_commit']==receipt['method_source_commit']==METHOD_COMMIT
 assert stamp(final['created_utc'])<stamp(meta['selection_created_utc']) and meta['metadata_only_before_neural'] and not meta['reference_read'] and not meta['WAV_bytes_read'] and meta['model_calls']==0
 assert receipt['selection_sha256']==sha(plan['metadata_selection_manifest']) and receipt['frozen_method_sha256']==sha(plan['final_method_freeze_record'])
 assert receipt['status']=='PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE' and receipt['model_calls']==receipt['gpu_calls']==0 and receipt['all_selected_valid_sources_retained']
 assert len(receipt['sources'])==len(meta['selected'])==4
 for group,selected in zip(meta['selected'],receipt['sources']):assert selected['archive_member']==group['technical_fallback_order'][selected['technical_fallback_index']]
 selection=validate_selection(receipt,plan['sources']);validate_original_bindings(plan,read(plan['method_config']))
 actual_packages={k:importlib.metadata.version(k) for k in read(plan['frozen_environment_record'])['packages']};assert actual_packages==read(plan['frozen_environment_record'])['packages']
 wavs=[]
 for s in [plan['fixed_old_warmup']['audio_source'],*plan['sources']]:
  assert sha(s['path'])==s['audio_sha256']
  with wave.open(s['path'],'rb') as w:assert w.getnchannels()==1 and w.getframerate()==16000 and w.getsampwidth()==2 and w.getnframes()==s['frames'] and w.getcomptype()=='NONE'
  wavs.append(dict(source_id=s['source_id'],sha256=s['audio_sha256'],frames=s['frames']))
 author=pathlib.Path(plan['backend']['author_root']);assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==plan['backend']['contract']['native_author_commit']
 assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip();assert sha(author/'simul_whisper/simul_whisper.py')==plan['backend']['contract']['author_whisper_sha256']
 for path,asset in plan['backend']['contract']['model_assets'].items():assert pathlib.Path(path).stat().st_size==asset['bytes']
 sys.path.insert(0,str(pathlib.Path(plan['model_runtime_root'])))
 for name in ('candidate_bridge','native_bridge','native_tail','feedback_contract'):
  module=importlib.import_module(name);assert pathlib.Path(module.__file__).resolve().parent==pathlib.Path(plan['model_runtime_root']).resolve()
 assert 'torch' not in sys.modules
 log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(source),pattern='test_*.py');result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite);(out/'CPU_CONTROLS.log').write_text(log.getvalue())
 assert result.wasSuccessful() and not result.skipped and result.testsRun==13 and 'torch' not in sys.modules
 app=pathlib.Path(APP_PATH);assert sha(app)==APP_SHA;appraisal=read(app);assert appraisal['new_source_neural_calls_at_appraisal_freeze']==0 and appraisal['source_ids']==[s['source_id'] for s in plan['sources']]
 summary=dict(status='PASS_REFERENCE_DATA_COMPLETE_SOURCE_ENVIRONMENT_AND_13_CPU_CONTROLS',generator_source=generator,imported_runtime=runtime,selection=selection,source_ids=[s['source_id'] for s in plan['sources']],expected_original_full_calls=sum((s['frames']+7999)//8000 for s in plan['sources']),data_wavs=wavs,actual_packages=actual_packages,CPU_tests=13,CPU_skips=0,torch_imported=False,model_calls=0,gpu_calls=0,final_appraisal_sha256=sha(app),model_asset_sizes_checked=len(plan['backend']['contract']['model_assets']),model_asset_content_SHA_recomputed=False,scope='source/data/header/SHA/config/environment CPU prerequisite only; not neural or serving results')
 put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(dict(status=summary['status'],out=str(out),gate_sha256=sha(out/'GATE.json'),expected_original_full_calls=summary['expected_original_full_calls'],model_calls=0,gpu_calls=0)))
except BaseException:
 import traceback
 (out/'failure.txt').write_text(traceback.format_exc());put('GATE.json',dict(status='FAIL_REFERENCE_CPU_PREFLIGHT_PRESERVED',model_calls=0,gpu_calls=0));raise
""".replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('PLAN_SHA',repr(sha(planpath))).replace('APP_PATH',repr(B+'/projects/revtrace_dsn_streamcorrect_independent_20261029/FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json')).replace('APP_SHA',repr(sha(appraisal)))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=90);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(I/'REFERENCE_CPU_STAGE_STDOUT_v1.txt').write_bytes(stdout);(I/'REFERENCE_CPU_STAGE_STDERR_v1.txt').write_bytes(stderr);print(stdout.decode());print(stderr.decode(),file=sys.stderr)
 s=c.open_sftp();dest=I/'REFERENCE_CPU_RESULTS_v1';dest.mkdir(exist_ok=False)
 try:
  for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','CPU_CONTROLS.log','failure.txt']:
   try:s.get(O+'/reference_cpu_v1/'+name,str(dest/name))
   except FileNotFoundError:pass
 finally:s.close()
 assert rc==0,'reference CPU prerequisite failed; preserved without model launch'
finally:c.close()
