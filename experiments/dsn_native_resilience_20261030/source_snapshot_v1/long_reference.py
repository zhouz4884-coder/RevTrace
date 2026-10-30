"""Offline continuous-author oracle versus every serialized/restored input edge.

The continuous path calls the original engine insert_audio/infer directly and
never restores a cut between steps. Reference timing is not serving evidence.
Both passes use the same loaded protected FP32 pipeline on the same GPU;
on a mismatch deterministic diagnostic controls preserve the failing run.
"""
from __future__ import annotations
import argparse,datetime,hashlib,importlib.metadata,json,os,pathlib,platform,random,sys,time,traceback
from feedback_contract import FeedbackCut,canonical_bytes

def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def frontiers(frames):
 if not isinstance(frames,int) or frames<=0:raise ValueError('positive integer source frames required')
 return list(range(8000,frames,8000))+[frames]

def continuous_transitions(model,source,audio,*,cut_export,to_tensor,sync,observer=None,stop_at=None):
 """Caller initializes genesis once; this loop contains no restore/full_step."""
 engine=model.engine;contract=model.initial_for(source['audio_sha256']).state['contract'];previous=0;text=''
 for index,end in enumerate(frontiers(source['frames'])):
  if stop_at is not None and end>stop_at:break
  start=cut_export(engine,frontier=previous,transcript=text,contract=contract)
  if observer:observer.bind(source_id=source['source_id'],job_id=f'continuous_{index:06d}',start_frontier=previous,end_frontier=end)
  engine.insert_audio(to_tensor(audio[previous:end]));sync();begun=time.perf_counter();wall=time.time()
  ids,g=engine.infer(is_last=end==source['frames'],start_time=wall,corrector_model=model.corrector_model,corrector_processor=model.corrector_processor,corrector_type='speechlm')
  sync();finished=time.perf_counter();appended=engine.tokenizer.decode(ids);text+=appended
  closed=cut_export(engine,frontier=end,transcript=text,contract=contract)
  result=dict(token_ids=list(ids),selected_correction=g.get('error_corrector'),appended_text=appended,native_model_evaluated='starting_tokens' in g)
  yield dict(source_id=source['source_id'],end=end,original_full_start_cut=start.state,original_full_cut=closed.state,original_full_result=result,continuous_original_no_between_step_restore=True,reference_only=True,original_model_start=begun,original_model_end=finished)
  previous=end

def compare_edge(reference,cut,record):
 start=FeedbackCut(reference['original_full_start_cut']);expected=FeedbackCut(reference['original_full_cut']);result=reference['original_full_result']
 checks=dict(complete_start_hash=record['start_state']==start.sha256,complete_end_state=cut.same(expected),complete_end_hash=record['end_state']==cut.sha256,selected_original_C=canonical_bytes(record['selected_correction'])==canonical_bytes(result['selected_correction']),returned_IDs=record['token_ids']==result['token_ids'])
 fields=sorted(k for k in expected.state if canonical_bytes(expected.state[k])!=canonical_bytes(cut.state[k]))
 return dict(source_id=reference['source_id'],end=reference['end'],all_equal=all(checks.values()),checks=checks,different_complete_cut_fields=fields,reference_start_sha256=start.sha256,reference_end_sha256=expected.sha256,actual_end_sha256=cut.sha256)

class JsonLines:
 def __init__(self,path):self.file=pathlib.Path(path).open('xb');self.count=0
 def write(self,row):self.file.write(canonical_bytes(row)+b'\n');self.file.flush();self.count+=1
 def close(self):self.file.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();plan=read(a.plan)
 from native_service import verify_source
 identity=verify_source(a.manifest)
 if identity['source_commit']!=plan['source_commit']:raise ValueError('oracle actual source differs')
 B=pathlib.Path(plan['designated_disk']);out=a.out.resolve();cache=pathlib.Path(plan['cache_root']).resolve()
 if not out.is_relative_to(B) or not cache.is_relative_to(B):raise ValueError('model/cache/raw outside designated8TB')
 out.mkdir();(out/'sources').mkdir();(out/'controls').mkdir()
 for key,leaf in [('HF_HOME','hf'),('HUGGINGFACE_HUB_CACHE','hub'),('HF_MODULES_CACHE','modules'),('TORCH_HOME','torch'),('TRITON_CACHE_DIR','triton'),('XDG_CACHE_HOME','xdg'),('TMPDIR','tmp')]:
  directory=cache/leaf;directory.mkdir(parents=True,exist_ok=True);os.environ[key]=str(directory)
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=str(plan['gpu']),TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8');sys.dont_write_bytecode=True
 put(out/'CONFIG.json',plan);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),scope='Offline neural continuous-author/restore equivalence only, not serving'))
 put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],frozen_config=str(a.plan),config_sha256=sha(a.plan),source_manifest=str(a.manifest),source_manifest_sha256=sha(a.manifest),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0))
 allrows=[];comparisons=[];source_summaries=[];controls=[];inputs={};model=None
 try:
  if plan.get('continuous_no_between_step_restore') is not True or plan.get('per_edge_restore_comparison') is not True:raise ValueError('must compare independent continuous engine with each restored input edge')
  if plan.get('failure_controls')!={'same_input_adapter_repeats':2,'original_continuous_prefix_repeats':1,'first_failed_boundary_per_source':True}:raise ValueError('frozen first-failure controls required')
  for key in ('environment_record','source_receipt'):
   if sha(plan[key])!=plan[key+'_sha256']:raise ValueError('frozen dependency changed: '+key)
   inputs[key]=dict(path=plan[key],sha256=sha(plan[key]))
  frozen=read(plan['environment_record']);actual_packages={k:importlib.metadata.version(k) for k in frozen['packages']}
  if actual_packages!=frozen['packages']:raise ValueError('frozen packages changed')
  receipt=read(plan['source_receipt'])
  if receipt['sources']!=plan['settings']['sources'] or receipt['status']!='PASS_FROZEN_TWO_SPEAKER_48_PART_SYNTHETIC_LONG_INPUTS':raise ValueError('sources differ from fixed complete recipe receipt')
  import numpy as np,soundfile as sf,torch
  torch.cuda.set_device(0);torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
  from candidate_bridge import CandidateBridge
  from native_bridge import restore_cut,export_cut
  from state_telemetry import NativeStateObserver
  settings=plan['settings'];warm=settings['warmup'];model_sources={s['source_id']:s for s in settings['model_sources']};sources=settings['sources']
  audio={}
  for source in [model_sources[warm['source_id']],*sources]:
   if sha(source['path'])!=source['audio_sha256']:raise ValueError('immutable WAV changed')
   data,hz=sf.read(source['path'],dtype='float32')
   if hz!=16000 or data.ndim!=1 or len(data)!=source['frames']:raise ValueError('WAV PCM contract changed')
   audio[source['source_id']]=data;inputs['audio:'+source['source_id']]=dict(path=source['path'],sha256=source['audio_sha256'],frames=source['frames'])
  model=CandidateBridge(stage_role='authority',source_commit=plan['source_commit'],corrector_dtype='float32',**settings['backend'])
  warm_source=model_sources[warm['source_id']];warm_start=model.rebind_warm_cut(warm['original_reference_start_state'],warm_source['audio_sha256']);warm_record=model.warm_neural_ready(audio=audio[warm['source_id']],start=warm_start,end=32000)
  if not warm_record['neural_C_confirmed'] or not warm_record['reset_to_genesis']:raise ValueError('original fixed neural warmup not satisfied')
  dtypes={name:sorted({str(p.dtype) for p in module.parameters() if p.is_floating_point()}) for name,module in [('asr',model.engine.model),('corrector',model.corrector_model)]}
  if any(v!=['torch.float32'] for v in dtypes.values()):raise ValueError('original FP32 parameter contract changed')
  put(out/'MODEL_READY.json',dict(actual_runtime_identity=model.runtime_identity,packages=actual_packages,actual_parameter_dtypes=dtypes,warmup=warm_record,continuous_and_restore_same_model_and_GPU=True,gpu=plan['gpu'],TF32=False,autocast=torch.is_autocast_enabled(),reference_only=True))
  def reset_genesis(source):
   genesis=model.initial_for(source['audio_sha256']);restore_cut(model.engine,genesis,audio=audio[source['source_id']],contract=genesis.state['contract']);model.engine.first_token_generated=False;model.engine.first_token_latency=None
  for source in sources:
   sid=source['source_id'];folder=out/'sources'/sid;folder.mkdir();telemetry=JsonLines(folder/'STATE_BOUNDARIES.jsonl');reset_genesis(source);rows=[]
   with NativeStateObserver(model.engine,emit=telemetry.write) as observer:
    for row in continuous_transitions(model,source,audio[sid],cut_export=export_cut,to_tensor=lambda x:torch.from_numpy(np.asarray(x,dtype=np.float32).copy()),sync=torch.cuda.synchronize,observer=observer):
     rows.append(row);put(out/'PROGRESS.json',dict(stage='continuous_original_no_restore',source_id=sid,completed=len(rows),expected=len(frontiers(source['frames']))))
    continuous_summary=observer.summary()
   # Commit the independent original trajectory before any restored comparison.
   put(folder/'CONTINUOUS_DETAILS.json',rows);allrows.extend(rows);reset_genesis(source);stream_comparisons=[]
   with NativeStateObserver(model.engine,emit=telemetry.write) as observer:
    for i,reference in enumerate(rows):
     start=FeedbackCut(reference['original_full_start_cut']);observer.bind(source_id=sid,job_id=f'restore_{i:06d}',start_frontier=start.frontier,end_frontier=reference['end'])
     cut,record=model.full_step(audio=audio[sid],start=start,end=reference['end'],is_last=reference['end']==source['frames'])
     compared=compare_edge(reference,cut,record);stream_comparisons.append(compared)
     if not compared['all_equal']:put(folder/f'RESTORE_MISMATCH_{i:06d}.json',dict(comparison=compared,reference=reference,actual_cut=cut.state,actual_record=record))
     put(out/'PROGRESS.json',dict(stage='per_edge_serialized_restore',source_id=sid,completed=i+1,expected=len(rows),mismatches=sum(not r['all_equal'] for r in stream_comparisons)))
    restored_summary=observer.summary()
   comparisons.extend(stream_comparisons);put(folder/'RESTORE_COMPARISONS.json',stream_comparisons)
   first_bad=next((i for i,r in enumerate(stream_comparisons) if not r['all_equal']),None)
   if first_bad is not None:
    reference=rows[first_bad];start=FeedbackCut(reference['original_full_start_cut']);control=dict(source_id=sid,end=reference['end'],same_input_adapter_repeats=[],original_continuous_prefix_repeat=[])
    for repeat in range(2):
     cut,record=model.full_step(audio=audio[sid],start=start,end=reference['end'],is_last=reference['end']==source['frames']);control['same_input_adapter_repeats'].append(dict(repeat=repeat,comparison=compare_edge(reference,cut,record),actual_cut=cut.state,actual_record=record))
    reset_genesis(source)
    repeated=list(continuous_transitions(model,source,audio[sid],cut_export=export_cut,to_tensor=lambda x:torch.from_numpy(np.asarray(x,dtype=np.float32).copy()),sync=torch.cuda.synchronize,stop_at=reference['end']))
    for old,new in zip(rows,repeated):control['original_continuous_prefix_repeat'].append(dict(end=old['end'],complete_start_equal=old['original_full_start_cut']==new['original_full_start_cut'],complete_end_equal=old['original_full_cut']==new['original_full_cut'],C_equal=old['original_full_result']['selected_correction']==new['original_full_result']['selected_correction'],IDs_equal=old['original_full_result']['token_ids']==new['original_full_result']['token_ids']))
    put(out/'controls'/(sid+'_FIRST_FAILURE_CONTROLS.json'),control);controls.append(dict(source_id=sid,first_mismatch_end=reference['end'],same_input_adapter_repeats=2,original_continuous_prefix_repeats=1,control_path=str(out/'controls'/(sid+'_FIRST_FAILURE_CONTROLS.json'))))
   telemetry.close();source_summaries.append(dict(source_id=sid,frames=source['frames'],original_continuous_steps=len(rows),restored_edge_calls=len(stream_comparisons),all_equal=all(r['all_equal'] for r in stream_comparisons),mismatches=sum(not r['all_equal'] for r in stream_comparisons),continuous_state_boundaries=continuous_summary,restored_state_boundaries=restored_summary,continuous_details=dict(path=str(folder/'CONTINUOUS_DETAILS.json'),sha256=sha(folder/'CONTINUOUS_DETAILS.json'),bytes=(folder/'CONTINUOUS_DETAILS.json').stat().st_size)))
  # Existing campaign audit can consume this raw array on8TB. It need not be
  # copied into Git when larger than the bounded-evidence limit.
  put(out/'DETAILS.json',allrows);put(out/'RESTORE_COMPARISONS.json',comparisons);put(out/'INPUT_MANIFEST.json',inputs)
  for record in inputs.values():
   if sha(record['path'])!=record['sha256']:raise ValueError('reference input mutated')
  ok=all(r['all_equal'] for r in comparisons) and len(comparisons)==sum(len(frontiers(s['frames'])) for s in sources)
  summary=dict(status='PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES' if ok else 'FAIL_RESTORE_EQUIVALENCE_WITH_DIAGNOSTIC_CONTROLS_PRESERVED',source_commit=identity['source_commit'],sources=len(sources),acoustic_speakers=len({s['speaker_id'] for s in sources}),reference_full_calls=len(allrows),restored_full_calls=len(comparisons),all_original_full_state_C_IDs_equal=ok,reference_details_sha256=sha(out/'DETAILS.json'),reference_details_bytes=(out/'DETAILS.json').stat().st_size,source_details=source_summaries,failure_controls=controls,original_continuous_no_between_step_restore=True,reference_only=True,actual_serving_cells=0,scope='Continuous raw-author task versus every restored input edge on the same GPU and loaded original FP32 models. Full raw/details remain on8TB; no serving latency/goodput or natural-long-recording claim.')
  put(out/'SUMMARY.json',summary);put(out/'DETAILS_INDEX.json',dict(reference_details=dict(path=str(out/'DETAILS.json'),sha256=summary['reference_details_sha256'],bytes=summary['reference_details_bytes']),sources=source_summaries));put(out/'GATE.json',summary);print(json.dumps(summary,indent=2))
  if not ok:raise RuntimeError('original continuous/restore task gate failed; controls and all inputs preserved')
 except BaseException:
  (out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
  if not (out/'GATE.json').exists():put(out/'GATE.json',dict(status='FAIL_CONTINUOUS_ORACLE_SETUP_OR_EXECUTION_PRESERVED',source_commit=identity['source_commit'],reference_only=True,actual_serving_cells=0))
  raise
if __name__=='__main__':main()
