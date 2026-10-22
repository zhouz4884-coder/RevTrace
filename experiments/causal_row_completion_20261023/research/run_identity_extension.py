"""Twelve verifier-input coverage calls; never used to infer serving speedups."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,time

def main():
 B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
 OLD=B/'results/revtrace/online_admission_20261022';D=O/'probe_identity_v2';D.mkdir(exist_ok=False)
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 sys.path[:0]=[str(P),str(P/'runtime/src'),str(P/'runtime/scripts')]
 import tc_live_worker,probe_worker
 from row_probe_core import result_equal
 tc_live_worker.worker_main=probe_worker.worker_main
 def read(p):return json.loads(p.read_text())
 def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
 meta=read(P/'SOURCE_MANIFEST.json')
 for r in meta['files']:assert hashlib.sha256((P/r['path']).read_bytes()).hexdigest()==r['sha256']
 plan=read(O/'p0_v1/GPU_PROBE_PLAN.json')
 selected=[(i,p) for i,p in enumerate(plan['operations']) if p.get('has_verification') and p['status']=='FROZEN_BEFORE_NEW_GPU']
 assert len(selected)==6
 save(D/'RUN.json',{'experiment_id':'REVTRACE-ROW-INPUT-COVERAGE-v2','source_commit':meta['code_commit'],
  'operations':selected,'identity_only_not_timing_or_serving':True,'repair_type':'missing verification-forward hash observation',
  'original96_preserved':True})
 completed=[];summaries=[];w=None
 try:
  for mode in ['strict','score']:
   todo=[(i,o) for i,o in selected if o['method']==mode]
   cfg=read(OLD/'formal_v1'/todo[0][1]['cell']/'config.json');rt=copy.deepcopy(cfg['authority_runtime'])
   digest=hashlib.sha256(json.dumps(rt,sort_keys=True).encode()).hexdigest()
   wc={**rt,'gpu':1,'model':str(B/'models/Qwen3-ASR-1.7B'),
    'manifest':str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'runtime_digest':digest,
    'capture_model_inputs':True,'lifecycle_instrumentation':True,'online_selection_mode':mode,
    'online_oracle_diagnostic':False,'allow_execution_context_override':False}
   w=tc_live_worker.GPUExecutor('identity-'+mode,wc);w.wait_ready()
   save(D/('WORKER-'+mode+'.json'),{'config':wc,'ready':w.ready,'pid':w.process.pid})
   for i,o in todo:
    allrows=[json.loads(x) for x in (OLD/'formal_v1'/o['cell']/'worker_records.jsonl').read_text().splitlines()]
    byid={r['job']['job_id']:r for r in allrows};old=[byid[j] for j in o['job_ids']];pair=[]
    for enabled in [False,True]:
     name=f'op{i}-'+('probe' if enabled else 'reference');jobs=copy.deepcopy([r['job'] for r in old])
     for k,j in enumerate(jobs):j.update(job_id=name+'-'+str(k),audio_ready_perf=0.,enqueue_perf=time.perf_counter(),runtime_digest=digest,_probe_enabled=enabled,_probe_capture_inputs=True)
     w.submit(jobs);start=time.perf_counter();tele=[]
     while True:
      result=w.poll();tele+=w.drain_telemetry()
      if result is not None:break
      if time.perf_counter()-start>180:raise TimeoutError('identity control timeout')
      time.sleep(.001)
     save(D/(name+'.json'),{'jobs':jobs,'results':result,'telemetry':tele,'operation':o,'not_timing_reference':True})
     for a,b in zip(old,result):
      assert result_equal(a['result'],b),'unchanged original operator output mismatch'
      assert a['result']['online_verification']['candidate_accepted']==b['online_verification']['candidate_accepted']
      assert a['result']['online_verification']['fallback_row_indices']==b['online_verification']['fallback_row_indices']
      assert a['result']['model_input_audit']['batch_tensors']==b['model_input_audit']['batch_tensors']
     pair.append(result);completed.append(name);save(D/'PROGRESS.json',{'completed':completed,'expected':12});print(name,flush=True)
    def hashes(rr):return [{k:v for k,v in e.items() if k!='job_ids'} for e in rr[0]['diagnostic_row_probe'] if e['kind'].startswith('actual-postcast')]
    assert hashes(pair[0])==hashes(pair[1])
    verifies=[e for e in hashes(pair[0]) if e['kind']=='actual-postcast-verifier-inputs']
    assert len(verifies)==1 and verifies[0]['tensors'],'verification input coverage still absent'
    summaries.append({'operation':i,'original_output_and_decision_equal':True,'verification_postcast_inputs_equal':True,
      'fallback_inputs_equal_where_present':True,'actual_tensor_observations':len(hashes(pair[0]))})
   w.close();w=None
  save(D/'SUMMARY.json',{'status':'PASS_ALL6_VERIFIER_POSTCAST_INPUT_CONTROLS','completed_invocations':len(completed),
   'operations':summaries,'not_a_timing_or_serving_result':True,'does_not_rewrite_original96':True})
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'completed':completed,'no_silent_retry':True});raise
 finally:
  if w is not None:w.close()

if __name__=='__main__':main()
