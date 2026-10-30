"""Streaming diagnostic of the unchanged imported native original program.

This driver adds durable observations and allocator controls only. It does not
replace inference, C/U, precision, cadence, source audio, or internal model code.
"""
from __future__ import annotations
import argparse,datetime,gc,hashlib,json,os,pathlib,platform,random,subprocess,sys,traceback

def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):pathlib.Path(p).write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def own_identity(manifest):
 root=pathlib.Path(__file__).resolve().parent;m=read(manifest)
 git=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
 if git('rev-parse','HEAD')!=m['source_commit'] or git('status','--porcelain','--untracked-files=all'):raise ValueError('diagnostic source not frozen and clean')
 if set(git('ls-files').splitlines())!={r['path'] for r in m['files']}:raise ValueError('incomplete diagnostic source manifest')
 for r in m['files']:
  if sha(root/r['path'])!=r['sha256'] or (root/r['path']).stat().st_size!=r['bytes']:raise ValueError('diagnostic source bytes differ')
 return m['source_commit']
def failure_start(tb):
 while tb is not None:
  f=tb.tb_frame
  if f.f_code.co_name=='continuous_transitions' and 'start' in f.f_locals:
   return dict(start=f.f_locals['start'].state,end=f.f_locals['end'],previous=f.f_locals['previous'])
  tb=tb.tb_next
 return None
class DurableRows:
 def __init__(self,path):self.f=pathlib.Path(path).open('xb');self.count=0
 def write(self,row):
  self.f.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8'));self.f.flush();os.fsync(self.f.fileno());self.count+=1
 def close(self):self.f.close()
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();cfg=read(a.config);commit=own_identity(a.manifest)
 if cfg['diagnostic_source_commit']!=commit:raise ValueError('diagnostic config source differs')
 plan=read(cfg['imported_reference_plan']);B=pathlib.Path(plan['designated_disk']);out=a.out.resolve()
 if not out.is_relative_to(B):raise ValueError('raw output outside designated8TB')
 if sha(cfg['imported_reference_plan'])!=cfg['imported_reference_plan_sha256']:raise ValueError('imported actual reference plan differs')
 out.mkdir();put(out/'CONFIG.json',cfg)
 for key,leaf in [('HF_HOME','hf'),('HUGGINGFACE_HUB_CACHE','hub'),('HF_MODULES_CACHE','modules'),('TORCH_HOME','torch'),('TRITON_CACHE_DIR','triton'),('XDG_CACHE_HOME','xdg'),('TMPDIR','tmp')]:
  d=pathlib.Path(plan['cache_root'])/leaf;d.mkdir(parents=True,exist_ok=True);os.environ[key]=str(d)
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=str(plan['gpu']),TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8')
 allocator=cfg['allocator_conf']
 if allocator is None:os.environ.pop('PYTORCH_CUDA_ALLOC_CONF',None);os.environ.pop('PYTORCH_ALLOC_CONF',None)
 else:
  if allocator!='expandable_segments:True':raise ValueError('unfrozen allocator control')
  os.environ['PYTORCH_CUDA_ALLOC_CONF']=allocator;os.environ.pop('PYTORCH_ALLOC_CONF',None)
 put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),TF32=False,corrector_dtype='float32',reference_only=True))
 put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,imported_neural_source_commit=plan['source_commit'],frozen_config=str(a.config),config_sha256=sha(a.config),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0))
 sys.path.insert(0,plan['source_root']);from native_service import verify_source
 verify_source(pathlib.Path(plan['source_manifest']))
 if sha(plan['source_manifest'])!=plan['source_manifest_sha256']:raise ValueError('neural source manifest differs')
 for key in ('environment_record','source_receipt'):
  if sha(plan[key])!=plan[key+'_sha256']:raise ValueError('imported frozen dependency differs')
 import importlib.metadata
 packages=read(plan['environment_record'])['packages']
 if {k:importlib.metadata.version(k) for k in packages}!=packages:raise ValueError('packages differ')
 import numpy as np,soundfile as sf,torch
 torch.cuda.set_device(0);torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
 from candidate_bridge import CandidateBridge
 from feedback_contract import FeedbackCut
 from native_bridge import restore_cut,export_cut
 from long_reference import continuous_transitions
 source=next(s for s in plan['settings']['sources'] if s['source_id']=='SC_SYNTH_S0770_24UTT_V1');settings=plan['settings'];warm=settings['warmup'];warm_source=next(s for s in settings['model_sources'] if s['source_id']==warm['source_id'])
 audio={}
 for s in (warm_source,source):
  if sha(s['path'])!=s['audio_sha256']:raise ValueError('original fixed WAV differs')
  data,hz=sf.read(s['path'],dtype='float32')
  if hz!=16000 or data.ndim!=1 or len(data)!=s['frames']:raise ValueError('PCM contract differs')
  audio[s['source_id']]=data
 model=CandidateBridge(stage_role='authority',source_commit=plan['source_commit'],corrector_dtype='float32',**settings['backend'])
 warm_start=model.rebind_warm_cut(warm['original_reference_start_state'],warm_source['audio_sha256']);warm_record=model.warm_neural_ready(audio=audio[warm['source_id']],start=warm_start,end=32000)
 if not warm_record['neural_C_confirmed'] or not warm_record['reset_to_genesis']:raise ValueError('original fixed warmup failed')
 dtypes={n:sorted({str(p.dtype) for p in mod.parameters() if p.is_floating_point()}) for n,mod in [('asr',model.engine.model),('corrector',model.corrector_model)]}
 if any(x!=['torch.float32'] for x in dtypes.values()):raise ValueError('precision changed')
 put(out/'MODEL_READY.json',dict(actual_parameter_dtypes=dtypes,actual_runtime_identity=model.runtime_identity,warmup=warm_record,allocator_conf=allocator,reference_only=True))
 def reset():
  g=model.initial_for(source['audio_sha256']);restore_cut(model.engine,g,audio=audio[source['source_id']],contract=g.state['contract']);model.engine.first_token_generated=False;model.engine.first_token_latency=None
 def memory():return dict(allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),max_allocated=torch.cuda.max_memory_allocated(),max_reserved=torch.cuda.max_memory_reserved())
 reset();rows=DurableRows(out/'COMPLETE_ROWS.jsonl');results=[];failed=None
 try:
  if cfg['mode']=='continuous_prefix':
   if cfg['prefix_end'] not in (760000,768000):raise ValueError('only fixed95/96 original prefixes allowed')
   try:
    transition_loop=continuous_transitions
    if cfg.get('release_generation',False):
     from memory_release import continuous_transitions_release_g
     transition_loop=continuous_transitions_release_g
    for row in transition_loop(model,source,audio[source['source_id']],cut_export=export_cut,to_tensor=lambda x:torch.from_numpy(np.asarray(x,dtype=np.float32).copy()),sync=torch.cuda.synchronize,stop_at=cfg['prefix_end']):
     rows.write(row);put(out/'LAST_GOOD_COMPLETE_ROW.json',row);put(out/'PROGRESS.json',dict(completed=rows.count,last_end=row['end'],target_end=cfg['prefix_end'],memory=memory(),reference_only=True))
   except torch.OutOfMemoryError as exc:
    failed=failure_start(exc.__traceback__);put(out/'OOM_FAILURE_INPUT.json',failed);(out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');results.append(dict(kind='original_continuous_OOM',failure_end=failed['end'] if failed else None,memory=memory(),message=str(exc)))
  elif cfg['mode']=='same_input_restore_twice':
   if sha(cfg['failure_input'])!=cfg['failure_input_sha256']:raise ValueError('fixed actual failed input differs')
   failed=read(cfg['failure_input']);start=FeedbackCut(failed['start'])
   if failed['end']!=760000 or start.frontier!=752000:raise ValueError('same-input control boundary differs')
   for repeat in range(2):
    gc.collect();torch.cuda.empty_cache()
    try:
     cut,record=model.full_step(audio=audio[source['source_id']],start=start,end=failed['end'],is_last=False);row=dict(repeat=repeat,source_id=source['source_id'],end=failed['end'],original_full_start_cut=start.state,original_full_cut=cut.state,original_full_result=record,same_input=True,reference_only=True);rows.write(row);results.append(dict(repeat=repeat,success=True,start_sha256=start.sha256,end_sha256=cut.sha256,memory=memory()))
    except torch.OutOfMemoryError as exc:
     (out/('failure_repeat'+str(repeat)+'.txt')).write_text(traceback.format_exc(),encoding='utf8');results.append(dict(repeat=repeat,success=False,error='CUDA_OOM',message=str(exc),memory=memory()))
  else:raise ValueError('unknown frozen diagnostic mode')
 finally:rows.close()
 summary=dict(status=('RECORDED_ORIGINAL_NATIVE_PREFIX_OOM' if cfg['mode']=='continuous_prefix' and results else 'PASS_ORIGINAL_NATIVE_PREFIX') if cfg['mode']=='continuous_prefix' else 'RECORDED_TWO_SAME_INPUT_NATIVE_CONTROLS',diagnostic_source_commit=commit,imported_neural_source_commit=plan['source_commit'],mode=cfg['mode'],allocator_conf=allocator,release_generation=cfg.get('release_generation',False),complete_rows=rows.count,complete_rows_sha256=sha(out/'COMPLETE_ROWS.jsonl'),results=results,source_id=source['source_id'],source_frames=source['frames'],original_C_U_precision_and_cadence_unchanged=True,reference_only=True,actual_serving_cells=0,scope='Fixed original95/96 prefix or two original failed-input calls for allocation/mechanism triage. Full long equivalence and serving remain separate.')
 if cfg.get('comparison_inputs'):
  from memory_release import compare_rows
  actual=[json.loads(b) for b in (out/'COMPLETE_ROWS.jsonl').read_bytes().splitlines() if b.strip()];checks=[]
  for fixed in cfg['comparison_inputs']:
   if sha(fixed['path'])!=fixed['sha256']:raise ValueError('actual baseline diagnostic bytes changed')
   old=[json.loads(b) for b in pathlib.Path(fixed['path']).read_bytes().splitlines() if b.strip()];compared=compare_rows(old,actual);passed=compared['all_old_rows_matched'] and compared['all_common_semantics_equal'] and (compared['old_keys_are_contiguous_new_prefix'] or fixed['kind']=='same_input_twice');put(out/('COMPARE_'+fixed['label']+'.json'),compared);checks.append(dict(label=fixed['label'],kind=fixed['kind'],old_rows=len(old),compared_pairs=compared['compared_pairs'],all_full_start_end_C_IDs_equal=passed,details_sha256=sha(out/('COMPARE_'+fixed['label']+'.json'))))
  releases=[r['diagnostic_generation_release'] for r in actual if 'diagnostic_generation_release' in r];drops=[r['allocated_drop_bytes'] for r in releases];summary.update(fixed_actual_controls=checks,all_fixed_actual_complete_state_C_IDs_equal=bool(checks) and all(c['all_full_start_end_C_IDs_equal'] for c in checks),generation_lifetime=dict(measured_edges=len(releases),minimum_allocated_drop_bytes=min(drops) if drops else None,maximum_allocated_drop_bytes=max(drops) if drops else None,maximum_exclusive_g_storage_bytes=max((r['storage']['g_exclusive_storage_bytes'] for r in releases),default=None),no_empty_cache_in_release=all(r['empty_cache_called'] is False for r in releases)))
  if rows.count==96 and not results and summary['all_fixed_actual_complete_state_C_IDs_equal']:summary['status']='PASS_RELEASE_G96_AND_ALL_FIXED_ACTUAL_PREFIX_AND_INPUT_CONTROLS'
  else:summary['status']='FAIL_RELEASE_G96_OR_STRICT_ACTUAL_CONTROLS_PRESERVED'
 put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
