"""Bounded prepared-input real-GPU probe. Not a serving throughput study.

This script only runs one preregistered case. A separate frozen controller must
gate resources, source/weights/manifest, same-input repeats and oracle results.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,copy,hashlib,importlib.metadata,inspect,json,os,platform,subprocess,sys,time
RUNTIME_COMMIT='408d75624104e7e11af3f0f2832263c632b10ed8'
PAYLOAD=' Violet Saturn Alder crossed the quiet bridge before the afternoon bell.'
TARGET='violet saturn alder'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 q=p.with_name(p.name+'.partial');q.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');q.replace(p)
def start_padded_power(sampler,*,clock=time.perf_counter,sleep=time.sleep):
 capture_start=clock();sampler.start();sleep(.35)
 return capture_start,clock()
def finish_padded_power(sampler,*,clock=time.perf_counter,sleep=time.sleep):
 operator_end=clock();sleep(.35);summary=sampler.stop()
 return operator_end,clock(),summary
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--model',type=Path,required=True)
 ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--source-id',required=True);ap.add_argument('--base-config',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True);ap.add_argument('--method',choices=['renderer_only','strict','revtrace','standard'],required=True)
 ap.add_argument('--traffic',choices=['clean','coherent-proposer'],required=True);ap.add_argument('--harness-commit',required=True);a=ap.parse_args()
 if not a.output.resolve().is_relative_to(Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025')):raise ValueError('8TB scoped output required')
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'another task owns GPU'
 assert not a.output.exists();a.output.mkdir(parents=True)
 sys.path[:0]=[str(a.runtime/'src'),str(a.runtime/'scripts'),str(a.runtime/'scripts/v100')]
 from revtrace.live_qwen import fingerprint
 from revtrace.certified_display import TrustedQwenRender,RealtimeConsumer
 from row_delivery_executor import RowGPUExecutor
 from run_v100_matrix import PowerSampler
 from role_channel import OwnProposerChannel
 from operator_controller import PreparedOwner,FeedbackOperator
 manifest=json.loads(a.manifest.read_text());selected=next(s for s in manifest['sessions'] if s['source_id']==a.source_id)
 assert TARGET not in selected['reference'].casefold(),'payload must not be reference text'
 import numpy as np,soundfile as sf
 from transformers import AutoProcessor,GenerationConfig
 from qwen_asr import parse_asr_output
 data,rate=sf.read(selected['path'],dtype='float32');wave=np.asarray(data,dtype='<f4')
 assert rate==16000 and wave.ndim==1 and len(wave)>=10*16000
 assert hashlib.sha256(wave.tobytes()).hexdigest()==selected['audio_sha256']
 base=json.loads(a.base_config.read_text());rt=copy.deepcopy(base['authority_runtime']);proposal=copy.deepcopy(base['proposal_runtime'])
 for t in [rt,proposal]:
  t.update(microbatch=1,max_new_tokens=256,code_commit=RUNTIME_COMMIT)
  for key in ['allow_execution_context_override','F2_field_normalization']:t.pop(key,None)
 rt.update(online_selection_mode='unprotected' if a.method=='renderer_only' else 'strict',score_threshold=.05,
  online_oracle_diagnostic=False,fallback_layout='full')
 for key in ['online_selection_mode','score_threshold','online_oracle_diagnostic','fallback_layout']:proposal.pop(key,None)
 processor=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=processor.tokenizer
 generation=GenerationConfig.from_pretrained(a.model,local_files_only=True);eos=generation.eos_token_id
 eos=[eos] if isinstance(eos,int) else list(eos or []);assert eos
 render=TrustedQwenRender(tok,parse_asr_output,eos,256);payload_Z=tok.encode(PAYLOAD,add_special_tokens=False)+[eos[0]]
 assert len(payload_Z)<=256 and [i for i,x in enumerate(payload_Z) if x in eos]==[len(payload_Z)-1]
 assets=rt['render_contract']
 for name,value in assets['assets'].items():assert sha(a.model/name)==value
 assert hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()==assets['parse_source_sha256']
 def contains(x):
  text=tok.decode(x,skip_special_tokens=True,clean_up_tokenization_spaces=False) if isinstance(x,(list,tuple)) else x
  return TARGET in text.casefold()
 cfg=dict(study='REVTRACE-ROLE-FEEDBACK-OPERATOR-20261026',policy='fine_certified',rho=1,fine_seconds=2,sample_rate=16000,
  authority_runtime=rt,proposal_runtime=proposal,microbatch=1,authority_microbatch=1,seed=20261026,
  proposal_barrier='decoupled',proposal_reconciliation='lazy',publish_canonical_display=True,
  trusted_text_binding=True,async_implementation='standard' if a.method=='standard' else 'revtrace',
  consumer_policy='two_lane',display_protocol='canonical-snapshot-v1',blocking_instrumentation=True,
  capture_worker_records=True,diagnostic_lifecycle=True,verification_policy='operator_strict_or_paid_generation',
  retain_verified_private_prefix=True,durability_mode='wal',journal_mode='durable',journal_sync_mode='single',
  manifest_sha256=sha(a.manifest),timeout_seconds=600,result_delivery='row',
  evidence_type='real_gpu_prepared_input_fault_operator_NOT_arrival_serving',
  operator_harness_commit=a.harness_commit,runtime_commit=RUNTIME_COMMIT,
  operator_policy=a.method,arrival_contract='all immutable prepared audio released before owner creation',
  diagnostic_reference='two full FP32 same-target repeats before install, never admitted',
  unchecked_candidate_policy=(a.method=='renderer_only'))
 save(a.output/'config.json',cfg)
 save(a.output/'CASE_PLAN.json',dict(source_id=a.source_id,method=a.method,traffic=a.traffic,harness_commit=a.harness_commit,
  literal_payload=PAYLOAD,target=TARGET,payload_token_ids=payload_Z,controlled_own_role_only=True,
  metadata_only='shadow decision on coherent Renderer-only trace; no extra GPU/cost claim'))
 save(a.output/'provenance.json',dict(runtime_commit=RUNTIME_COMMIT,harness_commit=a.harness_commit,
  script_sha256={p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('operator_controller.py'),Path(__file__).with_name('role_channel.py')]},
  runtime_manifest_sha256=sha(a.runtime/'SOURCE_MANIFEST.json'),manifest_sha256=sha(a.manifest),source=selected,
  python=sys.version,platform=platform.platform(),hostname=platform.node(),software={k:importlib.metadata.version(k) for k in ['torch','transformers','qwen-asr']},
  GPUs=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,driver_version','--format=csv,noheader'],text=True),
  trust='own-Proposer in-transit corruption only; no Authority/job/audio/epoch/binding changes; no OS isolation proof'))
 workers={};channel=None;owner=None;consumer=None;sampler=None;out=None;physical_calls=[];events=[];records=[];registered={}
 initialized=time.perf_counter()
 try:
  for role,gpu,t in [('proposal',0,proposal),('authority',1,rt)]:
   workers[role]=RowGPUExecutor(f'{role}-{gpu}',dict(t,runtime_digest=fingerprint(t),gpu=gpu,
    model=str(a.model),manifest=str(a.manifest),capture_model_inputs=True,lifecycle_instrumentation=True,
    receipt_trace_path=str(a.output/f'worker-{role}-receipts.jsonl')))
  for w in workers.values():w.wait_ready()
  handles=[]
  for role,w in workers.items():
   p=Path('/proc')/str(w.process.pid);handles.append(dict(role=role,pid=w.process.pid,linux_start_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]))
  save(a.output/'OWNED_WORKERS.json',handles);save(a.output/'workers.json',[w.ready for w in workers.values()])
  if a.traffic=='coherent-proposer':
   p=workers['proposal'];channel=OwnProposerChannel(p.results,worker_name=p.name,job_lookup=lambda jid:registered[jid],
    target_window=3,build_tokens=lambda j:payload_Z,render=render,eos=eos,budget=256);p.results=channel
  consumer=RealtimeConsumer(a.output/'consumer.jsonl','two_lane',strict_bound=True)
  with (a.output/'events.jsonl').open('x',encoding='utf8') as trace:
   def emit(e):
    if e['kind']=='worker-record':records.append(copy.deepcopy(e));return
    events.append(copy.deepcopy(e));trace.write(json.dumps(e,allow_nan=False)+'\n');trace.flush();consumer.put(e)
   sampler=PowerSampler([0,1],interval=.2);capture_start,power_start=start_padded_power(sampler)
   owner=PreparedOwner(sessions=[dict(session_id=0,audio=wave.tobytes(),source_id=a.source_id,language=selected['language'],offset=0.)],
    contract=cfg,executors={k:[v] for k,v in workers.items()},emit=emit,durable_journal_path=a.output/'canonical.wal',trusted_render=render)
   def execute(j,purpose):
    w=workers[j['role']];registered[j['job_id']]=j;w.submit([j]);seen=[];telemetry=[];deadline=time.perf_counter()+180
    while True:
     part=w.poll()
     if part:seen.extend(part)
     telemetry.extend(w.drain_telemetry())
     if w.batch_drained:break
     if time.perf_counter()>deadline:raise TimeoutError('bounded actual GPU operation did not drain')
     time.sleep(.002)
    assert len(seen)==1 and seen[0]['job_id']==j['job_id']
    accounting=[e for e in telemetry if e['kind']=='batch-accounting'];assert len(accounting)==1
    physical=accounting[0];physical_calls.append(dict(job=copy.deepcopy(j),result=copy.deepcopy(seen[0]),purpose=purpose,telemetry=telemetry))
    return seen[0],physical
   result=FeedbackOperator(owner,execute=execute,method=a.method,contains_payload=contains).run()
  result['consumer']=consumer.close();consumer=None;power_end,capture_end,power_summary=finish_padded_power(sampler);samples=sampler.rows;sampler=None
  save(a.output/'POWER.json',dict(samples=samples,summary=power_summary,start_perf=power_start,end_perf=power_end,
   capture_start_perf=capture_start,capture_end_perf=capture_end,pre_post_padding_seconds=.35,
   scope='GPU only; operator window excludes equal sampler padding, raw capture includes it; all prelude/diagnostic calls retained; not serving/SLO/CPU energy'))
  result['worker_initialization_seconds']=owner.t0-initialized
  result['contract_digest']=owner.contract_digest;result['final_state']=asdict(next(iter(owner.sessions.values())).state)
  result['literal_payload_injected']=(channel.applied if channel else False)
  if channel:assert channel.applied,'fixed target not reached; do not silently choose another target'
  result['new_neural_vs_carry_note']='only original workerZ/new descendantZ are neural outputs; injectedZ and adapter-carried marker are separate'
  result['reference']=selected['reference'];result['decision']='COMPLETE_OPERATOR_PENDING_INDEPENDENT_AUDIT'
  out=result
 except BaseException as e:
  save(a.output/'FAILURE.json',dict(error=repr(e),raw_retained=True,no_automatic_retry=True));raise
 finally:
  if sampler:
   summary=sampler.stop();save(a.output/'FAILED_POWER.json',dict(samples=sampler.rows,summary=summary))
  save(a.output/'PHYSICAL_CALLS.json',dict(calls=physical_calls,scope='actual calls including diagnostic work, no free/hidden fallback'))
  if channel:save(a.output/'CONTROLLED_TRANSFORMS.json',dict(transforms=channel.transforms,original_physical_accounting=channel.original_physical_accounting))
  with (a.output/'worker_records.jsonl').open('x',encoding='utf8') as f:
   for r in records:f.write(json.dumps(r,allow_nan=False)+'\n')
  if consumer:
   try:consumer.close()
   except Exception:pass
  if owner:owner.close()
  for w in workers.values():w.close()
 if out:save(a.output/'result.json',out);print(json.dumps({k:v for k,v in out.items() if k not in ['all_raw_calls','final_state','final_canonical_P','candidate_tokens']}))
if __name__=='__main__':main()
