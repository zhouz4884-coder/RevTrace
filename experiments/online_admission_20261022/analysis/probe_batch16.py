"""Real GPU stop-negative protocol control, not ASR prevalence/serving speedup."""
from pathlib import Path
import copy,hashlib,json,os,sys,time

def main():
    os.environ['CUDA_VISIBLE_DEVICES']='1';os.environ['OMP_NUM_THREADS']='2'
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_asr import Qwen3ASRModel,parse_asr_output
    B=Path(sys.argv[1]);P=B/'projects/revtrace_online_admission_20261022';S=P/'pilot_sdk_v3';O=B/'results/revtrace/online_admission_20261022';D=O/'batch16_protocol_v1';D.mkdir(exist_ok=False)
    sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
    from online_selection_worker import select_online
    from revtrace.dgft import digest_tokens
    from revtrace.live_qwen import fingerprint
    from run_v100_matrix import PowerSampler
    def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    source=json.loads((S/'SOURCE_MANIFEST.json').read_text());code=source['code_commit'];torch.set_num_threads(2)
    target=next(p for p in sorted((O/'trace_oracle_v2').glob('target-*.json')) if 'repeat' not in p.name);record=json.loads(target.read_text());jobs=copy.deepcopy(record['jobs']);assert len(jobs)==4;jobs=[copy.deepcopy(j) for _ in range(4) for j in jobs];n=len(jobs);assert n==16
    protocol={'source_commit':code,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'target_record_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'methods':['strict','score'],'layouts':['full','selective'],'negative':'remove final token of row1 reference; protocol construction not natural F2','scope':'direct frozen helper GPU protocol control, NOT deployed service comparison','GPU':1,'physical_rows':16,'unique_sources':4,'repeated_fixture_rows_not_independent_audio':True}
    save(D/'RUN.json',protocol);engine=Qwen3ASRModel.from_pretrained(B/'models/Qwen3-ASR-1.7B',torch_dtype=torch.float32,device_map={'':'cuda:0'},attn_implementation='eager',low_cpu_mem_usage=True,local_files_only=True,max_inference_batch_size=16,max_new_tokens=256)
    model,proc=engine.model,engine.processor;tok=proc.tokenizer;eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else list(eos or [])
    import importlib.metadata
    save(D/'ENVIRONMENT.json',{'python':sys.version,'torch':torch.__version__,'software':{k:importlib.metadata.version(k) for k in ['transformers','qwen-asr','tokenizers']},'device':torch.cuda.get_device_name(0),'physical_GPU':1,'dtype':'float32','model_config_sha256':hashlib.sha256((B/'models/Qwen3-ASR-1.7B/config.json').read_bytes()).hexdigest(),'source_commit':code})
    manifest=json.loads((O/'PILOT_MANIFEST.json').read_text());sources={s['source_id']:s for s in manifest['sessions']};prefixes=[];prompts=[];wavs=[];contexts=[]
    for j in jobs:
        raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
        if j['chunk_id']>=2 and raw:
            ids=tok.encode(raw);k=5
            while True:
                prefix=tok.decode(ids[:max(0,len(ids)-k)])
                if '\ufffd' not in prefix or k>=len(ids):break
                k+=1
        wav,rate=sf.read(sources[j['source_id']]['path'],dtype='float32');assert rate==16000;wav=np.asarray(wav,dtype='<f4')[:j['audio_end_sample']];prefixes.append(prefix);prompts.append(engine._build_text_prompt('',j['language'])+prefix);wavs.append(wav)
        contexts.append({'executed_prompt_tokens':j['prompt_tokens'],'actual_audio_sha256':hashlib.sha256(wav.tobytes()).hexdigest(),'fault_override':False})
    inputs=proc(text=prompts,audio=wavs,return_tensors='pt',padding=True)
    def identity(x):
        x=x.detach().cpu().contiguous();return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
    save(D/'ACTUAL_BATCH16_INPUTS.json',{'tensors':{k:identity(v) for k,v in inputs.items()},'physical_rows':16,'unique_sources':4,'not_claimed_equal_to_original_batch4_realization':True})
    moved={k:v.to('cuda:0',dtype=torch.float32) if v.is_floating_point() else v.to('cuda:0') for k,v in inputs.items()};width=moved['input_ids'].shape[1];audits=[]
    for i,j in enumerate(jobs):
        a=copy.deepcopy(record['results'][i%4]['model_input_audit']);mask=inputs['attention_mask'][i].bool();a.update(input_ids=inputs['input_ids'][i].tolist(),attention_mask=inputs['attention_mask'][i].tolist(),unpadded_input_ids=inputs['input_ids'][i][mask].tolist(),batch_rows=16,prompt_width=width,batch_tensors={k:identity(v) for k,v in inputs.items()},row_features={k:identity(v[i]) for k,v in inputs.items() if k not in ['input_ids','attention_mask'] and v.shape[0]==16});audits.append(a)
    def generate():
        with torch.inference_mode():out=model.generate(**moved,do_sample=False,max_new_tokens=256,output_scores=False)
        ans=[]
        for row in out.sequences[:,width:].cpu().tolist():
            stop=next((i+1 for i,t in enumerate(row) if t in eos),len(row));ans.append(row[:stop])
        return ans
    sampler=PowerSampler([1],interval=.2);sampler.start()
    try:
        reference=generate();repeat=generate();assert reference==repeat
        positive_P=[list(tok.encode(prefix+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False))) for prefix,z in zip(prefixes,reference)]
        save(D/'FRESH_BATCH16_ORACLE.json',{'token_ids':reference,'repeated_token_ids':repeat,'state_tokens':positive_P,'not_spliced_from_batch4':True})
        candidates=copy.deepcopy(reference);candidates[1]=candidates[1][:-1];summary=[]
        class Collector:
            def __init__(self):self.rows=[];self.phase=None;self.executed=[];self.fallback_input_checks=[]
            def put(self,x):
                self.rows.append(x)
                if x['kind']=='model-started':self.phase=x['online_phase'];self.executed=x['job_ids']
        original_generate=model.generate;active_collector=None
        def observed_generate(*args,**kwargs):
            c=active_collector
            if c is not None and c.phase=='fresh-FP32-fallback':
                selected=[int(j.split('-')[-1]) for j in c.executed];indices=torch.tensor(selected,dtype=torch.long,device='cuda:0')
                for k,v in moved.items():assert k in kwargs and torch.equal(kwargs[k],v.index_select(0,indices)),('actual fallback tensor mismatch',k)
                c.fallback_input_checks.append({'rows':selected,'all_actual_generate_input_tensor_bytes_equal_selected_target_rows':True})
            return original_generate(*args,**kwargs)
        model.generate=observed_generate
        for mode,layout in [('strict','full'),('strict','selective'),('score','selective'),('score','full')]:
            rt={'dtype':'float32','online_selection_mode':mode,'max_new_tokens':256,'score_threshold':.05,'fallback_layout':layout,'online_oracle_diagnostic':True,'runtime_digest':fingerprint(dict(protocol,mode=mode,layout=layout))}
            js=copy.deepcopy(jobs)
            for i,j in enumerate(js):j.update(job_id='protocol-'+str(i),candidate_origin_job_id='constructed-from-real-FP32-oracle',candidate_token_ids=candidates[i],candidate_state_tokens=positive_P[i],runtime_digest=rt['runtime_digest'],contract_digest=fingerprint(protocol),audio_ready_perf=0.)
            collector=Collector();active_collector=collector;a=time.perf_counter();rows=select_online(model=model,processor=proc,moved=moved,jobs=js,prefixes=prefixes,contexts=contexts,audits=audits,config=rt,start=a,results=collector);elapsed=time.perf_counter()-a
            expected_failed=[i for i,r in enumerate(rows) if r['online_verification']['fallback_used']];assert 1 in expected_failed
            if mode=='strict':assert expected_failed==[1]
            for r in rows:
                proof=r['online_verification'];assert proof['fallback_row_indices']==(expected_failed if layout=='selective' else list(range(n)))
                assert all(proof['pilot_oracle']['fallback_layout_selfchecks']) and proof['pilot_oracle']['fallback_layout_repeat_equal']
                for k,index in enumerate(proof['fallback_row_indices']):assert proof['fallback_input_ids'][k]==inputs['input_ids'][index].tolist()
            assert collector.fallback_input_checks
            name=mode+'-'+layout;save(D/(name+'.json'),{'jobs':js,'results':rows,'telemetry':collector.rows,'actual_fallback_input_checks':collector.fallback_input_checks,'elapsed_seconds':elapsed,'scope':'GPU protocol/paid operator cost only'})
            summary.append({'mode':mode,'layout':layout,'failed_rows':expected_failed,'actual_fallback_rows':rows[0]['online_verification']['fallback_batch_rows'],'selected_row_input_bytes_match':True,'all_oracles_and_repeats_pass':True});print(name,flush=True)
        save(D/'SUMMARY.json',{'status':'PASS_BATCH16_COMPLETE_VERIFICATION_AND_SELECTIVE_FALLBACK','cases':summary,'original_target_same_input_repeat':True,'performance_claim':False})
    except BaseException as e:save(D/'STOP.json',{'error':repr(e)});raise
    finally:
        power=sampler.stop();save(D/'POWER.json',{'samples':sampler.rows,'campaign':power,'GPU_indices':[1],'not_serving_energy':True})

if __name__=='__main__':main()
