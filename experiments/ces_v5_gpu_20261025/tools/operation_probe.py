"""Paid same-state whole/split FP32 generation diagnostic, never serving."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time

B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime'
O=B/'results/revtrace/ces_v5_20261025';D=O/'operation_probe_v1'
sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
from row_delivery_executor import RowGPUExecutor
from run_v100_matrix import PowerSampler
from revtrace.live_qwen import fingerprint
from revtrace.certified_display import TrustedQwenRender

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def signature(r):return {k:r[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit','model_input_audit']}

def main():
 assert not D.exists();D.mkdir()
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 old=B/'results/revtrace/ces_20261023/formal_v1/validation-staggered-mixed-fine-r0'
 cfg=read(old/'config.json');records=lines(old/'worker_records.jsonl');byid={r['job']['job_id']:r for r in records}
 batches=lines(old/'worker_batch_accounting.jsonl')
 chosen=next(a for a in batches if a['worker'].startswith('authority') and len(a['job_ids'])>=4)
 jobs=[copy.deepcopy(byid[j]['job']) for j in chosen['job_ids'][:4]]
 assert len({j['session_id'] for j in jobs})==4 and all(j['ces_operation']=='generate' for j in jobs)
 manifest=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
 rt=cfg['authority_runtime'];rd=fingerprint(rt)
 assert all(j['runtime_digest']==rd for j in jobs)
 plan=[('whole',0,[jobs]),('split',0,[jobs[:2],jobs[2:]]),('split',1,[jobs[:2],jobs[2:]]),('whole',1,[jobs])]
 save(D/'FREEZE.json',{'experiment_id':'REVTRACE-CES-V5-OPERATOR-20261025','source_commit':read(S/'SOURCE_MANIFEST.json')['code_commit'],
  'selection_rule':'first archived Fine authority batch with at least4rows, first4 archive-order rows',
  'source_cell':str(old),'source_batch_id':chosen['batch_id'],'jobs':jobs,
  'layouts':[{'layout':a,'repeat':r,'batch_rows':list(map(len,bs))} for a,r,bs in plan],
  'source_files':{n:sha(old/n) for n in ['config.json','worker_records.jsonl','worker_batch_accounting.jsonl']},
  'controller_sha256':sha(Path(__file__)),'scope':'fixed-state paid operator only; no online admission or serving speedup'})
 from transformers import AutoProcessor,GenerationConfig
 from qwen_asr import parse_asr_output
 processor=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True)
 eos=GenerationConfig.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).eos_token_id
 renderer=TrustedQwenRender(processor.tokenizer,parse_asr_output,[eos] if isinstance(eos,int) else eos,256)
 worker=None;sampler=PowerSampler([1],interval=.05);results=[]
 try:
  worker=RowGPUExecutor('authority-1',{**rt,'runtime_digest':rd,'gpu':1,'model':str(B/'models/Qwen3-ASR-1.7B'),
   'manifest':str(manifest),'capture_model_inputs':True,'lifecycle_instrumentation':True})
  save(D/'OWNED_WORKER.json',{'pid':worker.process.pid,'worker_incarnation':worker.incarnation})
  worker.wait_ready();save(D/'WORKER_READY.json',worker.ready)
  sampler.start();time.sleep(.25)
  for layout,repeat,parts in plan:
   action_rows=[];accounts=[];action_start=time.perf_counter()
   for part_index,part in enumerate(parts):
    batch=copy.deepcopy(part)
    for j in batch:
     j['probe_original_job_id']=j['job_id'];j['job_id']=f'probe-{layout}-r{repeat}-{j["job_id"]}'
    submitted=time.perf_counter();worker.submit(batch);rows=[];telemetry=[]
    while not worker.batch_drained:
     if time.perf_counter()-submitted>300:raise TimeoutError('operator batch did not drain')
     value=worker.poll()
     if value:
      received=time.perf_counter()
      for r in value:r['probe_owner_received_perf']=received
      rows.extend(value)
     telemetry.extend(worker.drain_telemetry());time.sleep(.001)
    telemetry.extend(worker.drain_telemetry())
    assert len(rows)==len(batch)
    physical=[t for t in telemetry if t['kind']=='batch-accounting'];assert len(physical)==1
    accounts.extend(physical)
    for j,r in zip(batch,sorted(rows,key=lambda r:next(i for i,x in enumerate(batch) if x['job_id']==r['job_id']))):
     assert r['job_id']==j['job_id']
     assert r['execution_context_audit']['executed_prompt_tokens']==j['prompt_tokens']
     assert r['execution_context_audit']['actual_audio_sha256']==j['prefix_audio_sha256']
     Pout,text=renderer(j,r['token_ids']);assert Pout==r['state_tokens'] and text==r['text']
     action_rows.append({'job':j,'result':r})
    save(D/f'{layout}-r{repeat}-batch{part_index}.json',{'submitted_perf':submitted,'jobs':batch,'rows':rows,'telemetry':telemetry})
   results.append({'layout':layout,'repeat':repeat,'wall_s':time.perf_counter()-action_start,
    'worker_lease_s':sum(a['batch_drained_perf']-a['worker_started_perf'] for a in accounts),
    'model_call_s':sum(p['completed_perf']-p['started_perf'] for a in accounts for p in a['phases']),
    'physical_batches':len(accounts),'rows':action_rows})
  time.sleep(.25);sampler.stop();save(D/'POWER_SAMPLES.json',sampler.rows)
  stable={}
  for layout in ['whole','split']:
   a,b=[r for r in results if r['layout']==layout]
   aa={r['job']['probe_original_job_id']:signature(r['result']) for r in a['rows']}
   bb={r['job']['probe_original_job_id']:signature(r['result']) for r in b['rows']}
   stable[layout]=aa==bb
  whole={r['job']['probe_original_job_id']:signature(r['result']) for r in results[0]['rows']}
  split={r['job']['probe_original_job_id']:signature(r['result']) for r in results[1]['rows']}
  changed={k:sum(whole[j][k]!=split[j][k] for j in whole) for k in ['token_ids','state_tokens','text','terminated_by_eos','model_input_audit']}
  summary={'status':'PASS_PAID_OPERATOR_REPEAT_AND_D1' if all(stable.values()) else 'REPEAT_INSTABILITY_STOP_BEFORE_ONLINE',
   'same_layout_repeat_equal_full_Z_P_text_stop_inputs':stable,'cross_layout_changed_rows':changed,
   'cross_layout_equality_not_required_or_assumed':True,'scope':'GPU1 fixed-state operator; not serving',
   'physical_batches':sum(r['physical_batches'] for r in results),
   'results':[{k:v for k,v in r.items() if k!='rows'} for r in results]}
  save(D/'SUMMARY.json',summary);print(json.dumps(summary),flush=True)
  assert all(stable.values()),'Repeated same-layout actual model execution differed'
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'completed_actions':len(results),'raw_retained':True});raise
 finally:
  sampler.stop()
  if worker:worker.close()

if __name__=='__main__':main()
