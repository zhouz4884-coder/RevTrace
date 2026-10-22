"""Actual production row-worker controls, original peers, no state installation."""
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,subprocess,sys,time

def main():
 B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
 S=P/'source_row_sdk_v1';OLD=B/'results/revtrace/online_admission_20261022';D=O/'row_operator_v1'
 assert not D.exists() and json.loads((O/'ROW_CPU_GATE_v1.json').read_text())['status'].startswith('PASS')
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 D.mkdir();sys.path[:0]=[str(S/'src'),str(S/'scripts')]
 from tc_live_worker import GPUExecutor
 from row_delivery_executor import RowGPUExecutor
 from revtrace.dgft import digest_tokens
 from revtrace.sequence_verifier import token_stop_certificate
 def read(p):return json.loads(p.read_text())
 def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
 meta=read(S/'SOURCE_MANIFEST.json')
 for r in meta['files']:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['sha256']
 control=read(P/'OPERATOR_SOURCE_IDENTITY_v1.json')
 assert control['controller_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 model_identity=[]
 for r in read(OLD/'FORMAL_FREEZE.json')['weights']:
  with (B/'models/Qwen3-ASR-1.7B'/r['file']).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  assert actual==r['sha256'];model_identity.append({'file':r['file'],'sha256':actual})
 operations=[r for r in read(O/'p0_v1/GPU_PROBE_PLAN.json')['operations'] if r['status']=='FROZEN_BEFORE_NEW_GPU']
 run={'experiment_id':'REVTRACE-ROW-PRODUCTION-OPERATOR-v1','runtime_code_commit':meta['code_commit'],
   'controller_code_commit':control['controller_code_commit'],'model_weights':model_identity,'python':sys.version,
   'observed_hardware':subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version','--format=csv,noheader'],text=True),
   'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'operations':operations,
   'batch_reference_repeats':1,'row_delivery_repeats':2,'scope':'original-input GPU operators, no online install/Goodput claim'}
 save(D/'RUN.json',run);contract=hashlib.sha256(json.dumps(run,sort_keys=True).encode()).hexdigest()
 groups=defaultdict(list)
 for i,o in enumerate(operations):groups[o['role'],o['method'] if o['has_verification'] else None].append((i,o))
 original={};all_results={};completed=[];checks=[];worker=None
 try:
  for (role,mode),items in groups.items():
   cfg=read(OLD/'formal_v1'/items[0][1]['cell']/'config.json')
   for delivery in ['batch','row']:
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    rt=copy.deepcopy(cfg['proposal_runtime' if role=='proposal' else 'authority_runtime'])
    rt.update(row_delivery=delivery,code_commit=meta['code_commit'])
    digest=hashlib.sha256(json.dumps(rt,sort_keys=True).encode()).hexdigest()
    wc={**rt,'gpu':0 if role=='proposal' else 1,'model':str(B/'models/Qwen3-ASR-1.7B'),
      'manifest':str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'runtime_digest':digest,
      'capture_model_inputs':True,'lifecycle_instrumentation':True,'allow_execution_context_override':role=='proposal',
      'online_selection_mode':mode,'online_oracle_diagnostic':False}
    cls=GPUExecutor if delivery=='batch' else RowGPUExecutor
    worker=cls(f'production-operator-{role}-{mode}-{delivery}',wc);worker.wait_ready()
    save(D/f'WORKER-{role}-{mode}-{delivery}.json',{'config':wc,'ready':worker.ready,'pid':worker.process.pid})
    for i,o in items:
     if i not in original:
      rs=[json.loads(x) for x in (OLD/'formal_v1'/o['cell']/'worker_records.jsonl').read_text().splitlines()]
      byid={r['job']['job_id']:r for r in rs};original[i]=[byid[j] for j in o['job_ids']]
     old=original[i]
     for repeat in range(1 if delivery=='batch' else 2):
      label=f'op{i}-{delivery}-r{repeat}';jobs=copy.deepcopy([r['job'] for r in old]);found={};receipts=[];tele=[]
      for k,j in enumerate(jobs):j.update(job_id=label+'-'+str(k),origin_job_id=old[k]['job']['job_id'],
        audio_ready_perf=0.,enqueue_perf=time.perf_counter(),contract_epoch=1,runtime_digest=digest,contract_digest=contract)
      worker.submit(jobs);began=time.perf_counter()
      while True:
       result=worker.poll();tele+=worker.drain_telemetry()
       if result is not None:
        observed=time.perf_counter()
        for r in result:
         assert r['job_id'] not in found,'duplicate selected row delivered to owner'
         found[r['job_id']]=r;receipts.append({'job_id':r['job_id'],'owner_available_perf':observed})
        if delivery=='batch' or worker.batch_drained:break
       if time.perf_counter()-began>240:raise TimeoutError('bounded row operator timed out')
       time.sleep(.001)
      end=time.perf_counter();ordered=[found[j['job_id']] for j in jobs]
      save(D/(label+'.json'),{'operation':o,'jobs':jobs,'results':ordered,'row_availability':receipts,
        'telemetry':tele,'physical_drained_observed_perf':end,'not_serving_latency':True})
      completed.append(label);save(D/'PROGRESS.json',{'completed':completed,'expected':36});print(label,flush=True)
      for a,b in zip(old,ordered):
       for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']:assert a['result'][k]==b[k],(label,k)
       assert a['result']['model_input_audit']['batch_tensors']==b['model_input_audit']['batch_tensors']
       assert a['result']['model_input_audit']['input_ids']==b['model_input_audit']['input_ids']
       eos=b['model_input_audit']['eos_token_ids'];assert token_stop_certificate(b['token_ids'],b['token_ids'],eos_token_ids=eos,max_new_tokens=256)[0]
       if mode:assert a['result']['online_verification']['candidate_accepted']==b['online_verification']['candidate_accepted']
      if delivery=='row':
       account=[t for t in tele if t['kind']=='batch-accounting'];assert len(account)==1
       assert set(account[0]['job_ids'])==set(found)
       for r in account[0]['selected_output_digests']:
        b=found[r['job_id']];assert r['Z_sha256']==digest_tokens(b['token_ids']) and r['P_sha256']==digest_tokens(b['state_tokens'])
        assert r['text_sha256']==hashlib.sha256(b['text'].encode()).hexdigest()
       assert worker.inbox.worker_reusable
      checks.append({'operation':i,'delivery':delivery,'repeat':repeat,'all_original_selected_outputs_and_inputs_equal':True,
        'duplicates_delivered':0,'all_submitted_work_drained':True,
        'maximum_measured_row_availability_lead_s':max(end-r['owner_available_perf'] for r in receipts)})
      all_results[i,delivery,repeat]=ordered
    worker.close();worker=None
  assert len(completed)==36
  save(D/'SUMMARY.json',{'status':'PASS_PRODUCTION_ROW_OPERATOR_CONTROLS','invocations':36,'checks':checks,
   'all_actual_original_operations_and_repeat_controls_equal':True,'not_an_online_performance_or_recovery_result':True,
   'GO_bounded_live_pilot':True,'no_automatic_formal_launch':True})
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'completed':completed,'raw_results_retained':True,'no_silent_retry':True});raise
 finally:
  if worker is not None:worker.close()

if __name__=='__main__':main()
