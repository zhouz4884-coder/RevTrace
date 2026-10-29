"""Generate original-full neural references, never timed serving results.

No source selection/download occurs here. Four metadata-selected new speakers
must be locked before this program starts. The unchanged complete bdfa runtime
is imported, and only original full_step with all speculative hooks disabled is
used. All source/EOS calls, including empty early returns, are preserved.
"""
from __future__ import annotations
import argparse,datetime,hashlib,importlib,importlib.metadata,json,os,pathlib,platform,re,subprocess,sys,traceback

METHOD_COMMIT='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
METHOD_MANIFEST_SHA256='258c33df4eba1d27bef88339aa20b2aae2ffe69f43489255d989ad337b717521'
METHOD_CONFIG_SHA256='30387d477ccd1ecbf35f8a37fcd72ee99360ba37383b68da254397d502ea759a'
OLD_TASK_GATE_SHA256='79f9355a41f42660fb16c3f002b3052551a547dbe6dafd89cdb0a0205c8d1411'
DISK='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
OLD_NATIVE_SPEAKERS={'S0764','S0765','S0767','S0768'}

def need(value,message):
 if not value:raise ValueError(message)
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_bytes())

def verify_checkout(root,manifest_path,expected_commit,expected_manifest_sha=None):
 root=pathlib.Path(root).resolve();manifest_path=pathlib.Path(manifest_path).resolve()
 if expected_manifest_sha is not None:need(sha(manifest_path)==expected_manifest_sha,'manifest SHA differs')
 manifest=read(manifest_path);need(manifest['source_commit']==expected_commit,'manifest source differs')
 def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
 need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root,'not an independent source root')
 need(git('rev-parse','HEAD')==expected_commit,'actual source commit differs')
 need(not git('status','--porcelain','--untracked-files=all'),'source must be clean')
 names=set(git('ls-files','-z').split('\0'))-{''};rows=manifest['files']
 need(names=={r['path'] for r in rows} and len(names)==len(rows),'manifest is not the complete source set')
 for row in rows:
  p=root/row['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root),'source path escaped root')
  data=p.read_bytes();need(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'source bytes differ: '+row['path'])
 return dict(source_commit=expected_commit,source_root=str(root),manifest_sha256=sha(manifest_path),files=len(rows))

def validate_selection(selection,sources):
 need(selection.get('metadata_only_before_neural') is True,'selection must be metadata-only and locked before neural outcomes')
 need(selection.get('method_source_commit')==METHOD_COMMIT,'method must be frozen before source selection')
 need(type(selection.get('selection_created_utc')) is str and bool(selection['selection_created_utc']),'selection timestamp missing')
 need(canonical(selection['sources'])==canonical(sources),'configured sources differ from locked source selection')
 need(len(sources)==4,'exactly four new source speakers required')
 excluded=set(selection['excluded_speakers']);need(OLD_NATIVE_SPEAKERS<=excluded,'old native speaker exclusions incomplete')
 ids=set();speakers=set()
 for s in sources:
  for key in ('source_id','speaker_id','path','audio_sha256','frames','reference'):need(key in s,'source field missing: '+key)
  need(s['source_id'] not in ids and s['speaker_id'] not in speakers,'duplicate source or speaker')
  need(s['speaker_id'] not in excluded,'speaker was used before this independent confirmation')
  matched=re.fullmatch(r'BAC009(S\d+)W\d+',s['source_id']);need(matched is not None and matched[1]==s['speaker_id'],'source/speaker identity differs')
  need(type(s['frames']) is int and 128000<=s['frames']<=240000,'metadata-frozen duration must be 8-15 seconds')
  need(re.fullmatch('[0-9a-f]{64}',s['audio_sha256']) is not None,'actual immutable audio SHA missing')
  need(type(s['reference']) is str and bool(s['reference'].strip()),'official text reference missing')
  need(str(s['path']).startswith(DISK+'/datasets/revtrace/'),'new audio must be on designated experiment disk')
  ids.add(s['source_id']);speakers.add(s['speaker_id'])
 return dict(sources=4,distinct_speakers=4,source_ids=[s['source_id'] for s in sources],excluded_speakers=sorted(excluded),selection_not_based_on_model_output=True)

def full_rows(model,audio,sources,progress=None):
 """Duck-typed for CPU controls; real model/cuts supplied only by main()."""
 rows=[]
 for source in sources:
  sid=source['source_id'];a=audio[sid];need(len(a)==source['frames'],'source sample count differs')
  start=model.initial_for(source['audio_sha256']);need(start.frontier==0,'reference must start at original genesis')
  for end in list(range(8000,source['frames'],8000))+[source['frames']]:
   before=start
   end_cut,record=model.full_step(audio=a,start=before,end=end,is_last=end==source['frames'],
      on_asr=None,capture_required=False,before_corrector=None)
   need(end_cut.frontier==end,'full result target differs')
   need(record['start']==before.frontier and record['end']==end,'original result interval differs')
   need(record['start_state']==before.sha256 and record['end_state']==end_cut.sha256,'original full record cut hashes differ')
   need(record['candidate_handoff'] is False and record['role']=='authority','reference used a non-original-full path')
   need(end_cut.state['contract']==before.state['contract'],'reference contract changed within a source')
   rows.append(dict(source_id=sid,speaker_id=source['speaker_id'],start=before.frontier,end=end,
    full_input_sha=before.sha256,original_full_start_cut=before.state,original_full_cut=end_cut.state,
    original_full_result=record,reference_only=True,not_serving=True))
   start=end_cut
   if progress is not None:progress(rows)
 return rows

def validate_original_bindings(plan,method_config):
 settings=method_config['settings'];warm=plan['fixed_old_warmup'];original=settings['warmup']
 need(settings['source_commit']==METHOD_COMMIT and settings['corrector_dtype']=='float32','original method config changed')
 need(canonical(plan['backend'])==canonical(settings['backend']),'original neural backend changed')
 need(warm['source_id']=='BAC009S0764W0209' and warm['fixed_start']==24000 and warm['fixed_end']==32000,'do not replace original fixed neural warmup')
 need(canonical(warm['original_reference_start_state'])==canonical(original['original_reference_start_state']),'original warmup state changed')
 sources=settings.get('model_sources',settings['sources']);source=next(s for s in sources if s['source_id']==warm['source_id'])
 need(canonical(warm['audio_source'])==canonical(source),'original warmup audio identity changed')
 return warm

def configure_environment(cache_root,gpu):
 need(str(cache_root).startswith(DISK+'/cache/'),'cache must be on the 8 TB experiment disk')
 for key,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
  p=pathlib.Path(cache_root)/rel;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
 os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--plan',type=pathlib.Path,required=True);parser.add_argument('--manifest',type=pathlib.Path,required=True);parser.add_argument('--out',type=pathlib.Path,required=True);args=parser.parse_args()
 root=pathlib.Path(__file__).resolve().parent;plan=read(args.plan)
 generator_identity=verify_checkout(root,args.manifest,plan['generator_source_commit'],plan['generator_source_manifest_sha256'])
 need(str(args.out).startswith(DISK+'/results/revtrace/'),'raw references must be on the designated 8 TB disk');args.out.mkdir(exist_ok=False)
 def put(name,value):(args.out/name).write_bytes(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode('utf8'))
 put('CONFIG.json',plan);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),scope='offline neural original-full oracle/reference; not online serving',actual_worker_environment='MODEL_READY.json after verified import and fixed original warmup'))
 put('RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=generator_identity['source_commit'],generator_source_identity=generator_identity,imported_model_runtime_commit=METHOD_COMMIT,
  frozen_config=str(args.out/'CONFIG.json'),frozen_config_sha256=sha(args.out/'CONFIG.json'),environment_record=str(args.out/'ENVIRONMENT.json'),environment_record_sha256=sha(args.out/'ENVIRONMENT.json'),
  raw_result_location=str(args.out/'RAW_STEPS.jsonl'),final_reference_details_location=str(args.out/'DETAILS.json'),aggregate_summary_location=str(args.out/'SUMMARY.json'),gate_decision_location=str(args.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0))
 receipts={}
 try:
  runtime_identity=verify_checkout(plan['model_runtime_root'],plan['model_runtime_manifest'],METHOD_COMMIT,METHOD_MANIFEST_SHA256)
  need(plan['method_config_sha256']==METHOD_CONFIG_SHA256 and plan['old_task_fidelity_gate_sha256']==OLD_TASK_GATE_SHA256,'original method/fidelity anchor differs')
  for name,path,expected in [('selection',plan['source_selection_manifest'],plan['source_selection_manifest_sha256']),('method_config',plan['method_config'],METHOD_CONFIG_SHA256),('old_task_fidelity',plan['old_task_fidelity_gate'],OLD_TASK_GATE_SHA256),('frozen_environment',plan['frozen_environment_record'],plan['frozen_environment_sha256'])]:
   need(sha(path)==expected,'frozen dependency bytes differ: '+name);receipts[name]=dict(path=path,sha256=expected,bytes=pathlib.Path(path).stat().st_size)
  selection=read(plan['source_selection_manifest']);selection_gate=validate_selection(selection,plan['sources'])
  need(read(plan['old_task_fidelity_gate'])['status']=='PASS_ALL_69_OLD_NATIVE_TASK_RESULTS_AFTER_EXACT_DECLARED_STAGE_TAG_PROJECTION','prior original task fidelity missing')
  need(plan['corrector_dtype']=='float32' and plan['gpu'] in (0,1),'original FP32/single reference GPU required')
  warm=validate_original_bindings(plan,read(plan['method_config']))
  need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU still owned by another run')
  controls=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root),'-p','test_*.py','-v'],cwd=root,capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),timeout=30)
  (args.out/'CPU_CONTROLS.log').write_text(controls.stdout+controls.stderr,encoding='utf8');need(controls.returncode==0 and 'skipped=' not in controls.stderr,'reference CPU controls failed/skipped')
  configure_environment(plan['cache_root'],plan['gpu'])
  import numpy as np,soundfile as sf,torch,random
  torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
  audio={}
  for s in [warm['audio_source'],*plan['sources']]:
   need(sha(s['path'])==s['audio_sha256'],'actual selected audio bytes differ');a,hz=sf.read(s['path'],dtype='float32');need(hz==16000 and a.ndim==1 and len(a)==s['frames'],'actual WAV header/data differs');audio[s['source_id']]=a;receipts['audio:'+s['source_id']]=dict(path=s['path'],sha256=s['audio_sha256'],bytes=pathlib.Path(s['path']).stat().st_size,actual_frames=len(a),actual_hz=hz)
  sys.path.insert(0,str(pathlib.Path(plan['model_runtime_root']).resolve()));module=importlib.import_module('candidate_bridge')
  need(pathlib.Path(module.__file__).resolve().parent==pathlib.Path(plan['model_runtime_root']).resolve(),'model runtime import shadowed')
  model=module.CandidateBridge(stage_role='authority',source_commit=METHOD_COMMIT,corrector_dtype='float32',**plan['backend'])
  start=model.rebind_warm_cut(warm['original_reference_start_state'],warm['audio_source']['audio_sha256']);warm_record=model.warm_neural_ready(audio=audio[warm['source_id']],start=start,end=32000)
  need(warm_record['neural_C_confirmed'] is True and warm_record['reset_to_genesis'] is True,'original neural warmup failed')
  from collections import Counter
  def dtypes(m):return dict(Counter({str(dtype):sum(p.numel() for p in m.parameters() if p.dtype==dtype) for dtype in {p.dtype for p in m.parameters()}}))
  actual_dtypes=dict(ASR=dtypes(model.engine.model),C=dtypes(model.corrector_model))
  need(not torch.is_autocast_enabled() and all(set(v)=={'torch.float32'} for v in actual_dtypes.values()),'actual original FP32 environment changed')
  put('MODEL_READY.json',dict(model_runtime=runtime_identity,actual_runtime_identity=model.runtime_identity,original_fixed_warmup=warm_record,source_selection_gate=selection_gate,actual_parameter_dtypes=actual_dtypes,packages={k:importlib.metadata.version(k) for k in ('torch','transformers','peft','triton','numpy','soundfile')},TF32=False,autocast_enabled=torch.is_autocast_enabled(),corrector_dtype='float32',gpu=plan['gpu'],reference_only=True,serving_cells=0))
  with (args.out/'RAW_STEPS.jsonl').open('x',encoding='utf8') as raw_steps:
   def progress(rows):
    raw_steps.write(json.dumps(rows[-1],ensure_ascii=False,separators=(',',':'))+'\n');raw_steps.flush()
    put('PROGRESS.json',dict(original_full_calls=len(rows),selected_sources=4,reference_only=True))
   rows=full_rows(model,audio,plan['sources'],progress)
  expected=sum((s['frames']+7999)//8000 for s in plan['sources']);need(len(rows)==expected,'reference input coverage incomplete')
  for name,r in receipts.items():need(sha(r['path'])==r['sha256'],'reference input changed during execution: '+name)
  put('DETAILS.json',rows);put('INPUT_MANIFEST.json',receipts)
  summary=dict(status='PASS_ALL_LOCKED_NEW_SPEAKER_ORIGINAL_FULL_REFERENCE_CALLS',experiment_id=plan['experiment_id'],generator_source_commit=generator_identity['source_commit'],imported_model_runtime_commit=METHOD_COMMIT,
   sources=4,speakers=4,full_calls=len(rows),all_EOS_preserved=True,source_ids=[s['source_id'] for s in plan['sources']],reference_details_sha256=sha(args.out/'DETAILS.json'),
   no_source_selection_or_downloading=True,no_early_projection_or_speculation=True,original_fixed_neural_warmup=True,reference_only=True,actual_serving_cells=0,serving_latency_or_goodput_claimed=False,
   scope='offline original full A+C+U reference for fixed metadata-selected new speakers; hash details before freezing final timed-service plan; no outcome-based selection')
  put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(summary,indent=2));return 0
 except BaseException:
  put('INPUT_MANIFEST.json',receipts);(args.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');put('GATE.json',dict(status='FAIL_NEW_SPEAKER_REFERENCE_PRESERVED',reference_only=True,actual_serving_cells=0));raise

if __name__=='__main__':raise SystemExit(main())
