"""Bounded original-peer diagnostic ABA probe; not online serving performance."""
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,os,statistics,subprocess,sys,time

def main():
 B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
 OLD=B/'results/revtrace/online_admission_20261022';S=P/'runtime';D=O/'probe_v1'
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU is owned elsewhere; do not start'
 D.mkdir(exist_ok=False)
 sys.path[:0]=[str(P),str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
 import tc_live_worker
 import probe_worker
 from row_probe_core import result_equal
 from run_v100_matrix import PowerSampler
 def read(p):return json.loads(p.read_text())
 def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 manifest=read(P/'SOURCE_MANIFEST.json')
 for r in manifest['files']:assert sha(P/r['path'])==r['sha256']
 weights=[]
 for r in read(OLD/'FORMAL_FREEZE.json')['weights']:
  p=B/'models/Qwen3-ASR-1.7B'/r['file']
  with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  assert actual==r['sha256'];weights.append({'file':r['file'],'sha256':actual})
 save(D/'MODEL_IDENTITY.json',{'weights':weights,'rehashed_before_GPU':True})
 plan=read(O/'p0_v1/GPU_PROBE_PLAN.json');ops=[p for p in plan['operations'] if p['status']=='FROZEN_BEFORE_NEW_GPU']
 assert len(ops)<=12
 save(D/'RUN.json',{'experiment_id':'REVTRACE-ROW-PROBE-20261023-v1','source_commit':manifest['code_commit'],
  'source_manifest_sha256':sha(P/'SOURCE_MANIFEST.json'),'probe_plan_sha256':sha(O/'p0_v1/GPU_PROBE_PLAN.json'),
  'protocol_sha256':sha(P/'PROTOCOL.md'),'measurement_amendment_sha256':sha(P/'PROBE_AMENDMENT_PRE_GPU.md'),
  'operations':ops,'cycles':2,'postcast_identity_pairs':True,'no_online_installations':True})
 tc_live_worker.worker_main=probe_worker.worker_main
 groups=defaultdict(list)
 for i,o in enumerate(ops):
  mode=o['method'] if o['has_verification'] else None
  groups[('proposal' if o['role']=='proposal' else 'authority',mode)].append((i,o))
 completed=[];summaries=[];w=None;sampler=None
 try:
  sampler=PowerSampler([0,1],interval=.2);sampler.start()
  for (role,mode),items in groups.items():
   cfg=read(OLD/'formal_v1'/items[0][1]['cell']/'config.json')
   rt=copy.deepcopy(cfg['proposal_runtime' if role=='proposal' else 'authority_runtime'])
   digest=hashlib.sha256(json.dumps(rt,sort_keys=True).encode()).hexdigest()
   worker_cfg={**rt,'gpu':0 if role=='proposal' else 1,'model':str(B/'models/Qwen3-ASR-1.7B'),
    'manifest':str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'runtime_digest':digest,
    'capture_model_inputs':True,'lifecycle_instrumentation':True,
    'online_selection_mode':mode,'online_oracle_diagnostic':False,'allow_execution_context_override':role=='proposal'}
   w=tc_live_worker.GPUExecutor('row-probe-'+role+'-'+str(mode),worker_cfg)
   w.wait_ready();save(D/('WORKER-'+role+'-'+str(mode)+'.json'),{'config':worker_cfg,'ready':w.ready,'pid':w.process.pid})
   for i,o in items:
    C=OLD/'formal_v1'/o['cell'];raw=[json.loads(x) for x in (C/'worker_records.jsonl').read_text().splitlines()]
    byid={r['job']['job_id']:r for r in raw};old=[byid[j] for j in o['job_ids']]
    original=[r['job'] for r in old]
    expected=[r['result'] for r in old]
    def run(label,enabled,capture=False):
     jobs=copy.deepcopy(original)
     for k,j in enumerate(jobs):
      j.update(job_id=f'op{i}-{label}-{k}',origin_job_id=original[k]['job_id'],
        audio_ready_perf=0.,enqueue_perf=time.perf_counter(),runtime_digest=digest,
        _probe_enabled=enabled,_probe_capture_inputs=capture)
     w.submit(jobs);began=time.perf_counter();tele=[]
     while True:
      result=w.poll();tele+=w.drain_telemetry()
      if result is not None:break
      if time.perf_counter()-began>180:raise TimeoutError('bounded probe invocation timed out')
      time.sleep(.001)
     save(D/f'op{i}-{label}.json',{'operation':o,'jobs':jobs,'results':result,'telemetry':tele,
       'probe':enabled,'postcast_identity_capture':capture,'source_commit':manifest['code_commit'],
       'operator_wall_s':time.perf_counter()-began,'not_serving_latency':True})
     completed.append(f'op{i}-{label}');save(D/'PROGRESS.json',{'completed':completed,'maximum_invocations':96})
     print(f'op{i}-{label}',flush=True)
     # Model outputs and original processor layout are checked, not guessed.
     for a,b in zip(expected,result):
      assert result_equal(a,b),'same physical operation output differs from original'
      assert a['model_input_audit']['batch_tensors']==b['model_input_audit']['batch_tensors']
      assert a['model_input_audit']['input_ids']==b['model_input_audit']['input_ids']
     if enabled:
      events=result[0]['diagnostic_row_probe'];actual={r['job_id']:r for r in result}
      finals=[e for e in events if e['kind'] in ['probe-row-final','probe-verified-row-final']]
      assert len(finals)==len(jobs),'one complete result per original row required'
      for e in finals:
       r=actual[e['job_id']]
       assert e['Z']==r['token_ids'] and e['P']==r['state_tokens'] and e['text']==r['text']
       assert e['complete_render_perf']<=r['completed_perf']
     return result
    effects=[];leads=[]
    for cycle in range(2):
     a=run(f'c{cycle}-before',False);p=run(f'c{cycle}-probe',True);z=run(f'c{cycle}-after',False)
     def elapsed(rr):return rr[0]['completed_perf']-rr[0]['started_perf']
     effects.append(elapsed(p)/statistics.mean([elapsed(a),elapsed(z)])-1)
     for e in p[0]['diagnostic_row_probe']:
      if e['kind'] in ['probe-row-final','probe-verified-row-final']:
       leads.append({'kind':e['kind'],'job_id':e['job_id'],'lead_s':p[0]['completed_perf']-e['complete_render_perf'],
          'EOS_ready_perf':e['terminal_observed_perf'],'complete_render_perf':e['complete_render_perf']})
    a=run('identity-before',False,True);p=run('identity-probe',True,True)
    def hashes(rr):return [{k:v for k,v in e.items() if k!='job_ids'} for e in rr[0]['diagnostic_row_probe'] if e['kind']=='actual-postcast-inputs']
    assert hashes(a)==hashes(p),'actual postcast layout/bytes changed'
    summaries.append({'operation_index':i,'operation':o,'probe_overhead_effects':effects,
      'median_probe_overhead':statistics.median(effects),'row_leads':leads,
      'complete_outputs_and_actual_input_controls_pass':True})
   w.close();w=None
  save(D/'POWER.json',{'integrated':sampler.stop(),'samples':sampler.rows,'diagnostic_not_serving_energy':True})
  lead_ops=sum(any(l['lead_s']>=(.05 if l['kind']=='probe-verified-row-final' else .1) for l in s['row_leads']) for s in summaries)
  overhead=statistics.median(s['median_probe_overhead'] for s in summaries)
  save(D/'SUMMARY.json',{'status':'COMPLETE_BOUNDED_ROW_GPU_PROBE','operations':summaries,
   'completed_invocations':len(completed),'lead_qualified_operations':lead_ops,
   'median_operation_probe_overhead':overhead,'GO_minimal_interface':lead_ops>=2 and overhead<=.05,
   'not_a_measured_online_Goodput_improvement':True,'no_automatic_formal_launch':True})
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'completed_invocations':completed,'no_silent_retry':True,'raw_outputs_retained':True});raise
 finally:
  if sampler is not None:sampler.stop()
  if w is not None:w.close()

if __name__=='__main__':main()
