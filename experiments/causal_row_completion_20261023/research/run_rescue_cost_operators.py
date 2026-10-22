"""At most12 fresh private FP32 singleton operators, no admission/publication."""
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,os,subprocess,sys,time
import numpy as np,soundfile as sf

def main():
    B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023';S=P/'source_row_sdk_v2';D=O/'rescue_cost_gpu_v1'
    assert not D.exists();D.mkdir()
    sys.path[:0]=[str(P),str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
    from rescue_cost_job import make_job,digest
    from row_delivery_executor import RowGPUExecutor
    from revtrace.live_qwen import fingerprint
    from revtrace.certified_display import TrustedQwenRender,validate_bound_text
    from revtrace.sequence_verifier import token_stop_certificate
    from transformers import AutoProcessor,GenerationConfig
    from qwen_asr import parse_asr_output
    from run_v100_matrix import PowerSampler
    def read(p):return json.loads(p.read_text())
    def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    def gpu_pids():return {int(x) for x in subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).split()}
    control=read(P/'RESCUE_COST_SOURCE_v1.json')
    for n,sha in control['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==sha
    assert read(O/'rescue_feasibility_v1/SUMMARY.json')['status']=='GO_BOUNDED_COST_OPERATOR_ONLY'
    assert read(O/'matrix_consistency_v1/SUMMARY.json')['status'].startswith('PASS_COMPLETE150')
    recipe_path=O/'rescue_feasibility_v1/COST_RECIPES_FROZEN.json';recipe_data=read(recipe_path);recipes=recipe_data['recipes'];assert 0<len(recipes)<=6
    assert not gpu_pids(),'do not start alongside another GPU task'
    meta=read(S/'SOURCE_MANIFEST.json')
    for row in meta['files']:assert hashlib.sha256((S/row['path']).read_bytes()).hexdigest()==row['sha256']
    model=B/'models/Qwen3-ASR-1.7B';proc=AutoProcessor.from_pretrained(model,local_files_only=True)
    eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id;eos=[eos] if isinstance(eos,int) else eos
    renderer=TrustedQwenRender(proc.tokenizer,parse_asr_output,eos,256)
    save(D/'RUN.json',{'experiment_id':'REVTRACE-ROW-RESCUE-COST-OPERATOR-v1','runtime_code_commit':meta['code_commit'],
      'controller_code_commit':control['code_commit'],'recipe_sha256':hashlib.sha256(recipe_path.read_bytes()).hexdigest(),
      'recipes':recipes,'generation_calls_maximum':2*len(recipes),'execution_order':'source manifest lexical groups,recipe_id,two fresh same-input calls',
      'scope':'real_GPU_private_cost_operator;no_WAL_admission_Consumer_publication_or_integrated_online_Rescue',
      'cold_initialization_excluded_from_per_operation_cost_included_in_campaign_power':True,'python':sys.version})
    groups=defaultdict(list)
    for recipe in recipes:groups[recipe['source_manifest']].append(recipe)
    samples=[];worker=None;sampler=PowerSampler([0,1],interval=.2);sampler.start()
    try:
        for manifest,group in sorted(groups.items()):
            assert not gpu_pids()
            rt=copy.deepcopy(group[0]['authority_runtime']);assert rt['dtype']=='float32' and rt['max_new_tokens']==256 and rt['online_selection_mode'] is None
            runtime=fingerprint(rt)
            wc={**rt,'gpu':1,'model':str(model),'manifest':manifest,'runtime_digest':runtime,
              'capture_model_inputs':True,'lifecycle_instrumentation':True,'allow_execution_context_override':False,
              'online_oracle_diagnostic':False,'receipt_trace_path':None}
            worker=RowGPUExecutor('private-cost-1',wc);worker.wait_ready()
            save(D/('WORKER-'+str(group[0]['recipe_id'])+'.json'),{'config':wc,'ready':worker.ready,'pid':worker.process.pid})
            for recipe in sorted(group,key=lambda x:x['recipe_id']):
                assert recipe['authority_runtime']==group[0]['authority_runtime']
                wave,sr=sf.read(recipe['audio_path'],dtype='float32');assert sr==16000;audio=np.asarray(wave,dtype='<f4').tobytes()
                contract=digest({'base_Canonical_contract':recipe['parent_contract_digest'],'parent_version':recipe['parent_version'],
                  'parent_P':recipe['parent_P'],'parent_frontier':recipe['parent_frontier'],'target':recipe['target_frontier'],
                  'execution_profile':rt,'permission':'private-operator-only-no-admission-no-publication'})
                repeated=[]
                for repeat in range(2):
                    assert gpu_pids()<={worker.process.pid},'foreign GPU owner;stop our bounded probe without touching it'
                    started=time.perf_counter();label=f"recipe{recipe['recipe_id']}-r{repeat}"
                    job=make_job(recipe,audio,runtime_digest=runtime,contract_digest=contract,label=label,now=started)
                    worker.submit([job]);found=[];tele=[];row_available=None;owner_render_wall=None
                    while True:
                        result=worker.poll();tele+=worker.drain_telemetry()
                        if result is not None:
                            for row in result:
                                assert not found;row_available=time.perf_counter()
                                began=time.perf_counter();binding=validate_bound_text(renderer,job,row);owner_render_wall=time.perf_counter()-began
                                assert row['execution_context_audit']['executed_prompt_tokens']==recipe['parent_P'] and not row['execution_context_audit']['fault_override']
                                assert row['prefix_audio_sha256']==job['prefix_audio_sha256']
                                assert token_stop_certificate(row['token_ids'],row['token_ids'],eos_token_ids=eos,max_new_tokens=256)[0]
                                found.append(row)
                            if worker.batch_drained:break
                        if time.perf_counter()-started>120:raise TimeoutError('bounded singleton cost operator')
                        time.sleep(.001)
                    complete=time.perf_counter();assert len(found)==1 and worker.inbox.worker_reusable
                    assert gpu_pids()<={worker.process.pid},'foreign resource appearance;retain contaminated record and stop'
                    row=found[0];record={'recipe':recipe,'repeat':repeat,'job':job,'result':row,'telemetry':tele,
                      'row_owner_available_s':row_available-started,'complete_paid_operator_s':complete-started,'owner_Render_wall_s':owner_render_wall,
                      'owner_Render_binding':binding,'fits_observed_window_isolated':complete-started<=recipe['available_window_s'],
                      'not_an_online_deadline_or_goodput_measurement':True,'no_Canonical_install_or_publication':True}
                    save(D/(label+'.json'),record);samples.append(record);repeated.append(row)
                    save(D/'PROGRESS.json',{'completed_generation_calls':len(samples),'expected':2*len(recipes)});print(label,record['complete_paid_operator_s'],flush=True)
                for key in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']:
                    assert repeated[0][key]==repeated[1][key],'same-input repeated numerical/content disagreement: '+key
                assert repeated[0]['model_input_audit']['batch_tensors']==repeated[1]['model_input_audit']['batch_tensors']
            worker.close();worker=None
        power=sampler.stop();save(D/'CAMPAIGN_POWER.json',{'summary':power,'samples':sampler.rows,'scope':'whole isolated operator campaign including model loads and warmup;not serving J/audio-s'})
        per=[]
        for recipe in recipes:
            values=[s['complete_paid_operator_s'] for s in samples if s['recipe']['recipe_id']==recipe['recipe_id']]
            assert len(values)==2
            per.append({'recipe_id':recipe['recipe_id'],'cell':recipe['cell'],'source_id':recipe['source_id'],
              'available_window_s':recipe['available_window_s'],'complete_cost_s':values,'both_costs_fit_isolated':max(values)<=recipe['available_window_s'],
              'even_best_cost_cannot_fit':min(values)>recipe['available_window_s']})
        save(D/'SUMMARY.json',{'status':'COMPLETE12_REAL_PRIVATE_FP32_COST_OPERATORS' if len(samples)==12 else 'COMPLETE_BOUNDED_PRIVATE_FP32_COST_OPERATORS',
          'actual_generation_calls':len(samples),'same_input_repeats_and_Trusted_Render_pass':True,'recipes':per,
          'not_an_integrated_Rescue_or_new_algorithm_result':True,'no_state_WAL_or_publication_writes':True,
          'cold_load_not_part_of_online_warm_operator_cost':True,'no_automatic_implementation_or_more_GPU':True})
    except BaseException as e:
        save(D/'STOP.json',{'error':repr(e),'completed_generation_calls':len(samples),'raw_retained':True,'no_silent_retry':True});raise
    finally:
        if worker is not None:worker.close()
        sampler.stop()

if __name__=='__main__':main()
