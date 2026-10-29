"""Bounded original native re-execution and read-only A/C/H boundary profiling."""
import argparse,pathlib,json,hashlib,subprocess,sys,os,datetime,time,statistics,traceback
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def verified_source(manifest):
 m=read(manifest);commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();assert commit==m['source_commit'] and not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True)
 assert set(subprocess.check_output(['git','-C',str(R),'ls-files'],text=True).splitlines())=={x['path'] for x in m['files']}
 for row in m['files']:
  b=(R/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 return commit
def set_environment(plan,gpu):
 cache=pathlib.Path(plan['cache_root'])
 for key,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
  p=cache/rel;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
 (cache/'xdg/torch/kernels').mkdir(parents=True,exist_ok=True)
 os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',TOKENIZERS_PARALLELISM='false')
def run_worker(plan,run,out,manifest):
 out.mkdir(parents=True,exist_ok=False);commit=verified_source(manifest);set_environment(plan,run['gpu'])
 import torch,numpy as np,soundfile as sf,random,importlib.metadata,collections
 torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
 native_plan=read(plan['native_plan']);assert sha(plan['native_plan'])==plan['native_plan_sha256'];source=native_plan['sources'][run['source_index']];cohort='A' if run['source_index']<2 else 'B'
 reference_cell=next(c for c in native_plan['cells'] if c['stage']=='formal' and c['cohort']==cohort and c['arm']=='sequential' and c['repeat']==0);cfg=read(reference_cell['config']);backend=cfg['settings']['backend'];reference=read(pathlib.Path(reference_cell['out'])/'CANONICAL_HISTORIES.json')[source['source_id']];byF={x['F']:x for x in reference}
 env=dict(python=sys.version,executable=sys.executable,packages={k:importlib.metadata.version(k) for k in ['torch','transformers','peft','triton','numpy','soundfile']},gpu=run['gpu'],no_autocast=True,tf32=False,native_model_contract=backend['contract']);put(out/'CONFIG.json',run);put(out/'ENVIRONMENT.json',env)
 put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id']+'_'+run['run_id'],code_commit=commit,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'trace'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),native_semantic_dependency=plan['native_model_source_commit']))
 from native_bridge import NativeBridge
 from feedback_contract import FeedbackCut
 from stage_probe import StageProbe,packet_input_signature
 model=NativeBridge(**backend,role='authority')
 def dtypes(module):
  c=collections.Counter()
  for p in module.parameters():c[str(p.dtype)]+=p.numel()
  return dict(c)
 put(out/'ACTUAL_PARAMETER_DTYPES.json',dict(asr=dtypes(model.engine.model),corrector=dtypes(model.corrector_model),cuda_autocast_enabled=torch.is_autocast_enabled(),tf32=False))
 probe=StageProbe(model.engine,out/'trace',pathlib.Path(backend['author_root'])/'simul_whisper/simul_whisper.py',capture_mode=run['capture']) if run['capture']!='off' else None
 warm_source=native_plan['sources'][0 if cohort=='A' else 2];a,sr=sf.read(warm_source['path'],dtype='float32');assert sr==16000
 warm_start=model.initial_for(warm_source['audio_sha256'])
 if probe:probe.begin(dict(step_id='warmup',source_id=warm_source['source_id'],complete_input_cut=warm_start.state,complete_input_cut_sha=warm_start.sha256,end_frontier=16000,role='declared_frontend_warmup_first_actual_C_retained'))
 warm_cut,warm=model.step(audio=a,start=warm_start,end=16000,is_last=False)
 warm_trace=probe.end(warm,warm_cut) if probe else None
 put(out/'WARMUP.json',dict(native_record=warm,stage_trace=warm_trace,first_actual_C_not_dropped=True))
 audio,sr=sf.read(source['path'],dtype='float32');assert sr==16000 and sha(source['path'])==source['audio_sha256']
 if run['kind']=='full':start=model.initial_for(source['audio_sha256']);targets=list(range(8000,source['frames'],8000))+[source['frames']]
 else:start=FeedbackCut(byF[24000]['state']);targets=[32000]
 results=[]
 try:
  for i,end in enumerate(targets):
   step=dict(step_id=f'step_{i:04d}',source_id=source['source_id'],start_frontier=start.frontier,end_frontier=end,complete_input_cut=start.state,complete_input_cut_sha=start.sha256,native_model_contract=backend['contract'])
   if probe:probe.begin(step)
   cut,record=model.step(audio=audio,start=start,end=end,is_last=end==source['frames'])
   trace=probe.end(record,cut) if probe else None
   equality=cut.sha256==byF[end]['state_sha256'] and record['token_ids']==byF[end]['token_ids'];assert equality,'instrumented original selected output/full cut differs from frozen v8 reference'
   results.append(dict(end=end,reference_equal=True,closed_cut_sha=cut.sha256,native_model_evaluated=record['native_model_evaluated'],selected=record['selected_correction'],model_seconds=record['model_seconds'],stage_seconds=trace['stage_seconds'] if trace else None,C_called=trace['C_called'] if trace else None,packet_signature=packet_input_signature(trace['calls'][0]['packet']) if trace and trace['calls'] else None,capture_mode=run['capture']))
   start=cut
 finally:
  if probe:probe.close()
 summary=dict(status='PASS_ORIGINAL_NATIVE_PROFILE_RUN_REFERENCE_EQUIVALENCE',run=run,native_steps=len(results),warmup_steps=1,warmup_stage_seconds=warm_trace['stage_seconds'] if warm_trace else None,results=results,blob_file_bytes=sum(p.stat().st_size for p in (out/'trace/blobs').glob('*.pt')),trace_json_bytes=sum(p.stat().st_size for p in (out/'trace').glob('*.json')),scope='component replay only, not serving; no stage handoff or resume implemented')
 put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],all_reference_states_equal=True,native_steps=len(results)));print(json.dumps(dict(run=run['run_id'],status=summary['status'],steps=len(results))))
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--worker-run');a=p.parse_args();plan=read(a.plan)
 if a.worker_run:return run_worker(plan,next(r for r in plan['runs'] if r['run_id']==a.worker_run),a.out,a.manifest)
 commit=verified_source(a.manifest);a.out.mkdir(parents=True,exist_ok=False);put(a.out/'FROZEN_PLAN.json',plan);put(a.out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=sys.platform,worker_environment='each worker records actual isolated native environment before model initialization'));put(a.out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=commit,frozen_config=str(a.out/'FROZEN_PLAN.json'),frozen_config_sha256=sha(a.out/'FROZEN_PLAN.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')));results=[]
 try:
  for run in plan['runs']:
   assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
   out=a.out/run['run_id'];command=[sys.executable,'-B',str(R/'run_stage_profile.py'),'--plan',str(a.plan),'--manifest',str(a.manifest),'--out',str(out),'--worker-run',run['run_id']]
   with (a.out/(run['run_id']+'.log')).open('x') as log:child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);put(a.out/'ACTIVE_CHILD.json',dict(run_id=run['run_id'],pid=child.pid));rc=child.wait()
   assert rc==0,'profile run failed and preserved';results.append(read(out/'SUMMARY.json'));put(a.out/'PROGRESS.json',dict(completed=len(results),total=len(plan['runs'])))
   for _ in range(30):
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    if not apps:break
    time.sleep(.2)
   assert not apps
  controls=[x for x in results if x['run']['kind']=='control' and x['run']['capture']!='off'];signatures=[x['results'][0]['packet_signature'] for x in controls if x['run']['source_index']==0];assert signatures and all(x==signatures[0] for x in signatures),'same-input full ordered packet differs across capture/fresh/GPU controls'
  stages=[x['stage_seconds'] for r in results if r['run']['kind']=='full' for x in r['results'] if x['C_called']];timing={k:dict(mean=statistics.mean(x[k] for x in stages),median=statistics.median(x[k] for x in stages),count=len(stages)) for k in ['A','C','H','capture']}
  summary=dict(status='PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS',source_commit=commit,runs=len(results),full_original_sources=4,controls=6,whole_reference_equivalence=True,same_input_packet_equivalence=True,stage_timing_seconds=timing,first_actual_C_warmup_stage_seconds=[r['warmup_stage_seconds'] for r in results if r['warmup_stage_seconds']],runs_summary=results,limitation='No serving claim. H is original tail/synchronization/unclassified residual, not handoff/IPC; capture and post-model materialization are measured instrumentation costs. Open KV/attention payload omitted, original cleanup still executes; no handoff/tail implementation or global numerical guarantee. First actual C per process is separately retained, not removed from scope.')
  put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',dict(status=summary['status'],full_sources=4,controls=6));print(json.dumps({k:v for k,v in summary.items() if k!='runs_summary'},indent=2))
 except BaseException:
  (a.out/'failure.txt').write_text(traceback.format_exc());put(a.out/'GATE.json',dict(status='FAIL_STAGE_PROFILE_PRESERVED',completed_runs=len(results)));raise
if __name__=='__main__':main()
