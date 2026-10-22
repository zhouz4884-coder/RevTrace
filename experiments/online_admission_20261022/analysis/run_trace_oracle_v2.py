"""Bounded trace-derived GPU oracle/future control, NOT serving performance."""
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,math,sys,time
import numpy as np
import soundfile as sf

def main():
    B=Path(sys.argv[1]);P=B/'projects/revtrace_online_admission_20261022';S=P/'pilot_sdk_v2';O=B/'results/revtrace/online_admission_20261022';D=O/'trace_oracle_v2';D.mkdir(exist_ok=False)
    sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
    from tc_live_worker import GPUExecutor
    from revtrace.live_qwen import fingerprint
    from revtrace.dgft import digest_tokens
    from run_v100_matrix import PowerSampler
    def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    assert json.loads((O/'PILOT_v2_AUDIT_GATE.json').read_text())['status']=='PASS_BOUND_ONLINE_KERNEL_AND_INPUT_AUDIT'
    root=O/'pilot_v2/unprotected-F2';raw=[json.loads(l) for l in (root/'worker_records.jsonl').read_text().splitlines()];records={r['job']['job_id']:r for r in raw};groups=defaultdict(list)
    for rr in raw:
     if rr['job']['role']=='authority':groups[rr['result']['started_perf'],rr['result']['completed_perf']].append(rr)
    targets={};eligible=[]
    for rr in raw:
     j=rr['job']
     if j['role']=='authority' and 'fault_actual_prompt_tokens' in records[j['candidate_origin_job_id']]['job']:eligible.append(rr)
    assert len(eligible)==4 and len({r['job']['source_id'] for r in eligible})==4
    cfg=json.loads((root/'config.json').read_text());rt=copy.deepcopy(cfg['authority_runtime']);rt.update(online_selection_mode=None,online_oracle_diagnostic=False)
    protocol={'experiment':'TRACE-DERIVED-FP32-ORACLE-v2','source_commit':json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit'],'runtime':rt,'scope':'controlled trace-derived GPU target/future operator, NOT live performance or new state migration','all_effective_source_targets_retained':True,'max_unique_sources':4,'repeats':2}
    save(D/'RUN.json',protocol);digest=fingerprint(protocol)
    config={**rt,'gpu':1,'model':str(B/'models/Qwen3-ASR-1.7B'),'manifest':str(O/'PILOT_MANIFEST.json'),'runtime_digest':digest,'capture_model_inputs':True,'lifecycle_instrumentation':True,'allow_execution_context_override':False}
    worker=GPUExecutor('trace-oracle-authority',config);sampler=PowerSampler([1],interval=.2);phases=[]
    def run(name,original):
     js=copy.deepcopy(original)
     for i,j in enumerate(js):
      j['origin_job_id']=j['job_id'];j['job_id']=name+'-'+str(i);j['runtime_digest']=digest;j['contract_digest']=fingerprint(protocol);j['audio_ready_perf']=0.;j['enqueue_perf']=time.perf_counter()
      for k in list(j):
       if k.startswith('candidate_') or k.startswith('online_'):j.pop(k)
     worker.submit(js);start=time.perf_counter();telemetry=[]
     while True:
      rs=worker.poll();telemetry+=worker.drain_telemetry()
      if rs is not None:break
      if time.perf_counter()-start>600:raise TimeoutError('bounded trace control exceeded limit')
      time.sleep(.001)
     save(D/(name+'.json'),{'phase':name,'jobs':js,'results':rs,'worker_telemetry':telemetry,'wall_seconds':time.perf_counter()-start});phases.append(name);print(name,flush=True);return rs
    try:
     worker.wait_ready();save(D/'WORKER.json',{'config':config,'ready':worker.ready});sampler.start();summary=[]
     for gi,(key,group) in enumerate(groups.items()):
      if not any(rr in eligible for rr in group):continue
      jobs=[rr['job'] for rr in group];a=run('target-'+str(gi),jobs);b=run('target-repeat-'+str(gi),jobs)
      for old,x,y in zip(group,a,b):
       assert x['token_ids']==y['token_ids'] and x['state_tokens']==y['state_tokens'],'Oracle repeat changed'
       assert x['model_input_audit']['batch_tensors']==old['result']['model_input_audit']['batch_tensors'],'Actual input realization mismatch; no target equivalence claim'
       if old in eligible:targets[old['job']['session_id']]=(old,x)
     manifest=json.loads((O/'PILOT_MANIFEST.json').read_text());sources={r['source_id']:r for r in manifest['sessions']}
     for sid,(old,oracle) in sorted(targets.items()):
      j=old['job'];later=sorted([r['job'] for r in raw if r['job']['role']=='authority' and r['job']['session_id']==sid and r['job']['audio_start_sample']==j['audio_end_sample']],key=lambda r:r['audio_end_sample']);assert later
      base=copy.deepcopy(later[0]);source=sources[j['source_id']];wav,rate=sf.read(source['path'],dtype='float32');assert rate==16000;wav=np.asarray(wav,dtype='<f4');total=len(wav)
      base.update(audio_end_sample=total,end_window=math.ceil(total/32000),chunk_advance=math.ceil(total/32000)-base['chunk_id'],prefix_audio_sha256=hashlib.sha256(wav.tobytes()).hexdigest(),interval_audio_sha256=hashlib.sha256(wav[base['audio_start_sample']:].tobytes()).hexdigest())
      bad=copy.deepcopy(base);good=copy.deepcopy(base);bad['job_id']='future-bad-'+str(sid);good['job_id']='future-good-'+str(sid);bad['prompt_tokens']=old['result']['state_tokens'];good['prompt_tokens']=oracle['state_tokens']
      for x in [bad,good]:x['parent_prompt_digest']=digest_tokens(x['prompt_tokens'])
      a=run('future-pair-'+str(sid),[bad,good]);b=run('future-pair-repeat-'+str(sid),[bad,good]);assert all(x['token_ids']==y['token_ids'] and x['state_tokens']==y['state_tokens'] for x,y in zip(a,b))
      summary.append({'session_id':sid,'source_id':j['source_id'],'candidate_Z_differs_correct_context_FP32':old['result']['token_ids']!=oracle['token_ids'],'admitted_P_differs_correct_context_FP32':old['result']['state_tokens']!=oracle['state_tokens'],'future_new_Z_differs':a[0]['token_ids']!=a[1]['token_ids'],'future_P_differs':a[0]['state_tokens']!=a[1]['state_tokens'],'future_text_differs':a[0]['text']!=a[1]['text'],'candidate_same_input_Oracle_repeat':True,'future_pair_same_input_repeat':True,'future_outputs':[r['text'] for r in a],'reference':source['reference'],'scope':'fixed-future trace-derived final-prefix operator, not live trajectory WER or latency'})
     power=sampler.stop();save(D/'POWER.json',{'GPU_indices':[1],'samples':sampler.rows,'operator_campaign':power,'not_serving_energy':True});save(D/'SUMMARY.json',{'status':'COMPLETE_TRACE_DERIVED_ORACLE_FUTURE_CONTROL','sources':summary,'phases':phases,'all_four_sources_not_outcome_filtered':True,'performance_claim':False})
    except BaseException as e:save(D/'STOP.json',{'error':repr(e),'completed_phases':phases});raise
    finally:sampler.stop();worker.close()

if __name__=='__main__':main()
