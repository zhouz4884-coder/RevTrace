"""Exactly nine paid Whisper diagnostic calls, never a serving experiment.

Six calls repeat three recorded single-row FP32 neural inputs; three use the
same complete source audio with empty history. One separate four-token warmup
is explicitly counted. No VAD, deduplication, fallback, early text stopping,
parameter search, current runtime import, or holdout selection is permitted.
"""
from __future__ import annotations
import argparse,hashlib,importlib.metadata,json,math,os,platform,re,subprocess,sys,threading,time,traceback,unicodedata
from pathlib import Path

B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
W=Path(__file__).resolve().parent
REQUIRED_ORDER=[('repeat','word_short',0),('repeat','word_full2s',0),('repeat','blank_short',0),
 ('repeat','blank_short',1),('repeat','word_full2s',1),('repeat','word_short',1),
 ('whole','word_short',None),('whole','word_full2s',None),('whole','blank_short',None)]

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4194304),b''):h.update(block)
    return h.hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def put(path,value):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],text=True).strip()

def verify_source(path):
    source=read(path);commit=source['code_commit']
    if not re.fullmatch('[0-9a-f]{40}',commit) or git('rev-parse','HEAD')!=commit or git('cat-file','-t',commit)!='commit':raise ValueError('full actual diagnostic source commit required')
    if Path(git('rev-parse','--show-toplevel')).resolve()!=W or git('status','--porcelain','--untracked-files=all'):raise ValueError('clean diagnostic Git root required')
    if git('config','--get','core.autocrlf')!='false':raise ValueError('byte-exact source checkout required')
    rows=source['files'];names={r['path'] for r in rows}
    if len(names)!=len(rows) or set(git('ls-files','-z').split('\0'))-{''}!=names or not {'diagnostic.py','test_diagnostic.py','PROTOCOL.md'}.issubset(names):raise ValueError('complete source manifest differs')
    for row in rows:
        p=W/row['path']
        if not p.resolve().is_relative_to(W) or p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('diagnostic source bytes differ')
    return dict(code_commit=commit,source_manifest_sha256=sha(path),files_verified=len(rows),clean=True)

def validate_plan(plan):
    if plan.get('schema')!='whisper-bad-data-nine-call-diagnostic-v1':raise ValueError('wrong fixed diagnostic schema')
    calls=plan['calls'];seen=[(c['kind'],c['case_id'],c['repeat']) for c in calls]
    if seen!=REQUIRED_ORDER or len({c['call_id'] for c in calls})!=9:raise ValueError('exact six repeats plus three whole-source calls required')
    if set(plan['cases'])!={'word_short','word_full2s','blank_short'}:raise ValueError('exact three diagnosed targets required')
    if plan['gpu']!=1 or plan['dtype']!='float32' or plan['max_new_tokens']!=256 or plan['do_sample'] is not False:raise ValueError('frozen FP32 GPU1 greedy256 required')
    if plan['warmup']!={'calls':1,'audio_samples':16000,'max_new_tokens':4,'history':[],'scope':'synthetic zero audio; separately counted, not a formal diagnostic call'}:raise ValueError('exact separate warmup required')
    if plan.get('forbidden_features')!=['VAD','deduplication','repetition stopping','fallback','parameter sweep','holdout selection']:raise ValueError('diagnostic scope changed')
    for case in plan['cases'].values():
        j=case['original_job'];a=case['original_result']['model_input_audit']
        if j['role']!='authority' or a['dtype']!='float32' or a['batch_rows']!=1 or a['shape']!=[1,80,3000]:raise ValueError('original single-row Authority input required')
        if case['expected_initial_decoder_ids_sha256']!=digest(a['actual_first_decoder_ids']):raise ValueError('original decoder ID identity changed')
        if a['actual_interval']!=[j['audio_start_sample'],j['audio_end_sample']]:raise ValueError('original audio interval changed')
        if not case['original_result']['hit_token_limit'] or case['original_result']['generated_tokens']!=256:raise ValueError('known original anomaly must be preserved')

def environment(plan):
    original=plan['original_environment'];model=Path(plan['model']).resolve(strict=True)
    if not model.is_relative_to(B/'models'):raise ValueError('model must stay on experiment disk')
    packages={key:importlib.metadata.version(key) for key in original['packages']}
    if packages!=original['packages']:raise ValueError('original numerical packages differ')
    for name,wanted in original['model_asset_sha256'].items():
        if sha(model/name)!=wanted:raise ValueError('original model/tokenizer asset differs: '+name)
    weights={name:sha(model/name) for name in original['model_weight_sha256']}
    if weights!=original['model_weight_sha256']:raise ValueError('original model weights differ')
    hardware=subprocess.check_output(['nvidia-smi','--id=1','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True).strip()
    expected_GPU=[line for line in original['hardware'].splitlines() if line.split(',',1)[0].strip()=='1']
    if len(expected_GPU)!=1 or hardware!=expected_GPU[0]:raise ValueError('original physical Authority GPU1 identity/driver differs')
    return dict(python=sys.version,platform=platform.platform(),hostname=platform.node(),packages=packages,hardware=hardware,
      model=str(model),model_asset_sha256=original['model_asset_sha256'],model_weight_sha256=weights,
      physical_GPU=1,dtype='float32',process_environment={key:os.environ.get(key) for key in ['CUDA_VISIBLE_DEVICES','CUBLAS_WORKSPACE_CONFIG','HF_HOME','HF_HUB_OFFLINE','TMPDIR']},
      cache_condition='new model process; existing filesystem caches; no disk eviction',
      scope='environment identity before any processor/model load; GPU1 board energy only, CPU unmeasured')

def conditioning(processor,history,budget,contract):
    raw=list(processor.get_prompt_ids(history,return_tensors='np')) if history else []
    raw=[int(x) for x in raw]
    cap=contract['max_target_positions']-len(contract['initial_decoder_ids'])-budget
    if cap!=190 or (raw and raw[0]!=contract['previous_start_token_id']):raise ValueError('original English conditioning contract differs')
    chosen=raw if len(raw)<=cap else [raw[0]]+raw[-(cap-1):]
    return chosen,chosen+contract['initial_decoder_ids'],dict(raw_prompt_ids=raw,trimmed=len(raw)-len(chosen),capacity=cap)

def prepare_cpu(plan,processor):
    import numpy as np,soundfile as sf
    manifest=read(plan['audio_manifest'])
    if sha(plan['audio_manifest'])!=plan['audio_manifest_sha256']:raise ValueError('original audio manifest differs')
    sources={r['source_id']:r for r in manifest['sessions']};prepared={};checks=[]
    for name,case in plan['cases'].items():
        j,r=case['original_job'],case['original_result'];a=r['model_input_audit'];spec=sources[j['source_id']]
        if spec!=case['original_audio_row']:raise ValueError('original complete source metadata differs')
        path=Path(spec['path']).resolve(strict=True)
        if not path.is_relative_to(B):raise ValueError('audio must stay on experiment disk')
        audio,rate=sf.read(path,dtype='float32');audio=np.asarray(audio,dtype='<f4')
        if rate!=16000 or audio.ndim!=1 or hashlib.sha256(audio.tobytes()).hexdigest()!=spec['audio_sha256']:raise ValueError('original source audio sample identity differs')
        begin,end=a['actual_interval'];interval=audio[begin:end]
        ctx=r['execution_context_audit']
        if hashlib.sha256(interval.tobytes()).hexdigest()!=ctx['actual_interval_sha256'] or hashlib.sha256(audio[:end].tobytes()).hexdigest()!=ctx['actual_audio_sha256']:raise ValueError('original prefix/interval sample identity differs')
        history=processor.tokenizer.decode(j['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
        if history!=a['history']:raise ValueError('original declared history decode differs')
        prompt,initial,cp=conditioning(processor,history,256,a['conditioning_contract'])
        if prompt!=a['prompt_ids'] or initial!=a['actual_first_decoder_ids'] or cp['raw_prompt_ids']!=a['conditioning_plan']['raw_prompt_ids'] or cp['trimmed']!=a['conditioning_plan']['trimmed']:raise ValueError('original actual decoder/prompt reconstruction differs')
        x=processor(interval,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        feature_sha=hashlib.sha256(x.input_features.numpy().tobytes()).hexdigest()
        if list(x.input_features.shape)!=a['shape'] or feature_sha!=a['input_features_sha256'] or feature_sha!=a['actual_gpu_features_sha256']:raise ValueError('original FP32 features differ')
        whole=processor(audio,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        prepared[name]=dict(repeat=dict(x=x,prompt=prompt,initial=initial,history=history),
          whole=dict(x=whole,prompt=[],initial=a['conditioning_contract']['initial_decoder_ids'],history=''))
        checks.append(dict(case_id=name,original_job_id=j['job_id'],source_id=j['source_id'],
          audio_interval=[begin,end],audio_sha256=spec['audio_sha256'],CPU_features_sha256=feature_sha,
          expected_GPU_FP32_features_sha256=a['actual_gpu_features_sha256'],actual_initial_decoder_ids=initial,
          initial_decoder_ids_sha256=digest(initial),expected_original_decoder_ids_sha256=case['expected_initial_decoder_ids_sha256'],
          attention_mask_sha256=hashlib.sha256(x.attention_mask.numpy().tobytes()).hexdigest(),
          attention_mask_scope='reconstructed by identical pinned processor; original worker passed it but did not separately hash it',
          history_exact=True,CPU_feature_exact=True,actual_decoder_ids_reconstruction_exact=True,
          whole_samples=len(audio),whole_reference=case['reference']))
    return prepared,checks

def terminal(full,initial,eos,budget):
    if full[:len(initial)]!=initial:raise ValueError('generated sequence does not begin with actual observed decoder IDs')
    raw=full[len(initial):];end=next((i+1 for i,t in enumerate(raw) if t==eos),len(raw));z=raw[:end]
    if not z or len(z)>budget or (eos not in z and len(z)!=budget):raise ValueError('short/incomplete or over-budget neural result')
    if eos in z and z[-1]!=eos:raise ValueError('nonterminal EOS')
    return dict(Z=z,terminated_by_eos=z[-1]==eos,hit_token_limit=len(z)==budget and z[-1]!=eos,
      raw_tail_after_first_EOS=raw[end:],generated_tokens=len(z))

def integrate(rows,start,end):
    if len(rows)<2 or rows[0]['t']>start or rows[-1]['t']<end or end<=start:raise ValueError('actual GPU1 samples must bracket interval')
    result=0.
    for a,b in zip(rows,rows[1:]):
        dt=b['t']-a['t']
        if dt<=0:raise ValueError('power clock order')
        lo,hi=max(start,a['t']),min(end,b['t'])
        if hi>lo:
            pa=a['watts']+(b['watts']-a['watts'])*(lo-a['t'])/dt
            pb=a['watts']+(b['watts']-a['watts'])*(hi-a['t'])/dt
            result+=(pa+pb)/2*(hi-lo)
    return result

class Power:
    def __init__(self,path):
        self.path=path;self.rows=[];self.stop=threading.Event();self.error=None;self.lock=threading.Lock()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start();self.wait(lambda:len(self.rows)>=2)
    def wait(self,predicate):
        until=time.perf_counter()+10
        while not predicate():
            if self.error:raise RuntimeError('GPU1 board-power sampler failed') from self.error
            if time.perf_counter()>=until:raise TimeoutError('GPU1 power observation timeout; no synthetic energy')
            time.sleep(.025)
    def run(self):
        try:
            with self.path.open('x') as stream:
                while not self.stop.is_set():
                    begin=time.perf_counter();raw=subprocess.check_output(['nvidia-smi','--id=1','--query-gpu=index,power.draw,memory.used','--format=csv,noheader,nounits'],text=True,timeout=8);end=time.perf_counter()
                    gpu,watts,memory=raw.strip().split(',')
                    if int(gpu)!=1:raise ValueError('power must observe physical Authority GPU1')
                    row=dict(t=(begin+end)/2,watts=float(watts),memory_MiB=float(memory),query_seconds=end-begin,physical_GPU=1)
                    if not math.isfinite(row['watts']) or row['watts']<0:raise ValueError('invalid measured watts')
                    with self.lock:self.rows.append(row)
                    stream.write(json.dumps(row)+'\n');stream.flush();self.stop.wait(.18)
        except BaseException as exc:self.error=exc
    def joules(self,start,end):
        self.wait(lambda:bool(self.rows) and self.rows[-1]['t']>=end)
        with self.lock:rows=list(self.rows)
        return integrate(rows,start,end)
    def close(self):self.stop.set();self.thread.join(timeout=10)

def words(text):return re.findall(r"[a-z0-9']+",unicodedata.normalize('NFKC',text).lower())
def errors(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def generate_one(model,processor,prepared,*,budget,expected_feature_sha=None,raw_path=None):
    import torch
    x=prepared['x'];features=x.input_features.to('cuda:0',dtype=torch.float32)
    actual_sha=hashlib.sha256(features.float().cpu().numpy().tobytes()).hexdigest()
    if expected_feature_sha is not None and actual_sha!=expected_feature_sha:raise ValueError('actual GPU1 FP32 features differ before generation')
    kwargs=dict(input_features=features,attention_mask=x.attention_mask.to('cuda:0'),do_sample=False,
      max_new_tokens=budget,return_timestamps=False,return_dict_in_generate=True)
    if prepared['prompt']:kwargs['prompt_ids']=torch.tensor(prepared['prompt'],dtype=torch.long,device='cuda:0')
    observed=[]
    def hook(module,args,kw):
        if not observed:
            ids=kw.get('input_ids',args[0] if args else None)
            if ids is None:raise ValueError('missing actual first decoder IDs')
            actual=ids.detach().cpu().tolist()
            if actual!=[prepared['initial']]:raise ValueError('actual initial decoder IDs differ before first decoder forward')
            observed.extend(actual)
    handle=model.model.decoder.register_forward_pre_hook(hook,with_kwargs=True)
    begin=time.perf_counter()
    try:
        with torch.inference_mode():out=model.generate(**kwargs)
        torch.cuda.synchronize();end=time.perf_counter()
    except BaseException:
        if raw_path is not None:
            put(raw_path,dict(status='NEURAL_CALL_FAILED_BEFORE_SEQUENCE_RETURN',actual_first_decoder_ids=observed,
              actual_GPU_FP32_features_sha256=actual_sha,model_started_perf=begin,failure_observed_perf=time.perf_counter(),
              traceback=traceback.format_exc(),no_sequence_returned=True))
        raise
    finally:handle.remove()
    full=out.sequences[0].detach().cpu().tolist()
    if raw_path is not None:
        put(raw_path,dict(status='RAW_NEURAL_RETURN_BEFORE_TERMINAL_OR_TEXT_CHECKS',raw_sequence=full,
          actual_first_decoder_ids=observed[0] if observed else [],actual_GPU_FP32_features_sha256=actual_sha,
          max_new_tokens=budget,model_started_perf=begin,model_completed_perf=end))
    if not observed:raise ValueError('no actual neural decoder input receipt')
    stop=terminal(full,observed[0],processor.tokenizer.eos_token_id,budget)
    segment=processor.tokenizer.decode(stop['Z'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
    history=prepared['history'];text=(history+' '+segment).strip() if history else segment.strip()
    state=processor.tokenizer.encode(text,add_special_tokens=False)
    return dict(raw_sequence=full,actual_first_decoder_ids=observed[0],actual_first_decoder_ids_sha256=digest(observed[0]),
      actual_GPU_FP32_features_sha256=actual_sha,raw_segment_text=segment,projected_text=text,projected_state_tokens=state,
      model_started_perf=begin,model_completed_perf=end,model_seconds=end-begin,**stop)

def run(plan,path,source,output,validate_only=False):
    validate_plan(plan)
    if plan['code_commit']!=source['code_commit'] or plan['source_manifest_sha256']!=source['source_manifest_sha256']:raise ValueError('plan/execution source differs')
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(B/'results/revtrace/physical_retirement_20261028'):raise ValueError('new external8TB output required')
    output.mkdir(parents=True);completed=[];warmups=0;formal_attempts=0;power=None
    try:
        env=environment(plan)
        put(output/'ENVIRONMENT.json',env)
        config=dict(experiment_id=plan['experiment_id'],plan=str(path),plan_sha256=sha(path),
          formal_calls=9,explicit_warmup_calls=1,validate_inputs_only=validate_only,physical_GPU=1,dtype='float32',
          scope=plan['scope'],selection='greedy256, original EOS/budget; no text-dependent stopping or retries',call_order=plan['calls'])
        put(output/'CONFIG.json',config)
        record=dict(experiment_id=plan['experiment_id']+('-CPU-INPUTS' if validate_only else ''),code_commit=source['code_commit'],
          source_manifest_sha256=source['source_manifest_sha256'],frozen_config=str(output/'CONFIG.json'),frozen_config_sha256=sha(output/'CONFIG.json'),
          environment_record=str(output/'ENVIRONMENT.json'),environment_record_sha256=sha(output/'ENVIRONMENT.json'),
          raw_result_location=str(output),aggregate_summary_location=str(output/'SUMMARY.json'),gate_decision_location=str(output/'GATE.json'))
        put(output/'RUN_RECORD.json',record);put(output/'PLAN.json',plan)
        if not validate_only:
            apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip()
            if apps:raise RuntimeError('GPU in use; no model load or generation launched; no foreign process signalled')
            os.environ['CUDA_VISIBLE_DEVICES']='1';os.environ['OMP_NUM_THREADS']='2';os.environ['TOKENIZERS_PARALLELISM']='false'
        preparation_started=time.perf_counter()
        import torch
        torch.set_num_threads(2)  # Original worker pins this before CPU features.
        from transformers import WhisperProcessor
        processor=WhisperProcessor.from_pretrained(plan['model'],local_files_only=True)
        prepared,checks=prepare_cpu(plan,processor);put(output/'INPUT_CHECKS.json',checks)
        put(output/'CPU_PREPARATION_TIMING.json',dict(started_perf=preparation_started,completed_perf=time.perf_counter(),
          scope='processor load, original audio/feature/decoder checks and whole-source feature preparation; no model generation'))
        if validate_only:
            summary=dict(status='PASS_CPU_INPUT_RECONSTRUCTION_NO_MODEL',source_commit=source['code_commit'],cases=3,formal_model_calls=0,warmup_model_calls=0,checks=checks)
            put(output/'SUMMARY.json',summary);put(output/'GATE.json',dict(gate='PASS_CPU_INPUT_RECONSTRUCTION_NO_MODEL',source_commit=source['code_commit'],ASR_model_calls=0));return summary
        # The second idle check is after CPU preparation and immediately before
        # model load; it never terminates another task.
        if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU became busy during CPU input preparation')
        power=Power(output/'power_samples.jsonl')
        import torch,numpy as np
        from transformers import WhisperForConditionalGeneration
        torch.set_num_threads(2);cold=time.perf_counter()
        model=WhisperForConditionalGeneration.from_pretrained(plan['model'],torch_dtype=torch.float32,attn_implementation='eager',local_files_only=True).to('cuda:0').eval()
        put(output/'ACTUAL_MODEL_RUNTIME.json',dict(torch=torch.__version__,dtype=str(next(model.parameters()).dtype),physical_GPU=1,
          matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
          generation_config=model.generation_config.to_dict(),architecture=type(model).__name__,logical_device='cuda:0 via CUDA_VISIBLE_DEVICES=1'))
        warm=processor(np.zeros(16000,dtype='float32'),sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        warmups+=1
        result=generate_one(model,processor,dict(x=warm,prompt=[],initial=[50257,50362],history=''),budget=4,raw_path=output/'WARMUP.RAW.json')
        result.update(scope=plan['warmup']['scope'],GPU1_joules=power.joules(result['model_started_perf'],result['model_completed_perf']))
        put(output/'WARMUP.json',result)
        (output/'calls').mkdir()
        for call in plan['calls']:
            if formal_attempts>=9:raise RuntimeError('formal call budget exhausted; no tenth generation')
            case=plan['cases'][call['case_id']];kind=call['kind'];packet=prepared[call['case_id']][kind]
            formal_attempts+=1
            put(output/'calls'/(call['call_id']+'.ATTEMPT.json'),dict(call=call,attempt_number=formal_attempts,
              original_job_id=case['original_job']['job_id'],input_decoder_ids_sha256=digest(packet['initial']),
              scope='same neural input single-row repeat, original peer scheduling omitted' if kind=='repeat' else 'different segmentation/full-source empty-history quality reference; not same-contract oracle or serving'))
            expected=case['original_result']['model_input_audit']['actual_gpu_features_sha256'] if kind=='repeat' else None
            result=generate_one(model,processor,packet,budget=256,expected_feature_sha=expected,
              raw_path=output/'calls'/(call['call_id']+'.RAW.json'))
            result.update(call=call,GPU1_joules=power.joules(result['model_started_perf'],result['model_completed_perf']),
              comparison_scope='exact original neural output comparison' if kind=='repeat' else 'full-source empty-history reference only')
            if kind=='repeat':
                old=case['original_result']
                result['expected_original_exact']=dict(Z=result['Z']==old['token_ids'],
                  raw_sequence=result['raw_sequence']==old['model_input_audit']['full_decoder_sequence'],
                  actual_first_decoder_ids=result['actual_first_decoder_ids']==old['model_input_audit']['actual_first_decoder_ids'],
                  projected_text=result['projected_text']==old['text'],projected_state_tokens=result['projected_state_tokens']==old['state_tokens'],
                  Stop=(result['terminated_by_eos']==old['terminated_by_eos'] and result['hit_token_limit']==old['hit_token_limit']))
            else:
                ref,hyp=words(case['reference']),words(result['projected_text']);result['whole_source_quality']=dict(N=len(ref),errors=errors(ref,hyp),WER_percent=100*errors(ref,hyp)/len(ref),
                  reference=case['reference'],original_streaming_text=case['original_streaming_final_text'],
                  scope='whole source vs its complete original reference, different input/segmentation contract; no online metric')
            put(output/'calls'/(call['call_id']+'.json'),result);completed.append(result)
        ended=time.perf_counter();cold_energy=power.joules(cold,ended)
        if len(completed)!=9 or formal_attempts!=9 or warmups!=1:raise ValueError('exact paid call/warmup accounting failed')
        verify_source(plan['source_manifest'])
        repeat_pairs=[]
        for name in plan['cases']:
            rr=[r for r in completed if r['call']['kind']=='repeat' and r['call']['case_id']==name]
            repeat_pairs.append(dict(case_id=name,two_repeats_equal_Z=rr[0]['Z']==rr[1]['Z'],
              each_matches_original=[all(r['expected_original_exact'].values()) for r in rr]))
        summary=dict(status='COMPLETE_NINE_PAID_DIAGNOSTIC_CALLS',code_commit=source['code_commit'],formal_model_calls=9,warmup_model_calls=1,
          repeat_pairs=repeat_pairs,whole_source_quality=[dict(case_id=r['call']['case_id'],**r['whole_source_quality']) for r in completed if r['call']['kind']=='whole'],
          formal_model_seconds=sum(r['model_seconds'] for r in completed),formal_GPU1_joules=sum(r['GPU1_joules'] for r in completed),
          cold_model_load_to_last_call_GPU1_joules=cold_energy,cold_model_load_started_perf=cold,cold_interval_ended_perf=ended,
          scientific_decision='results recorded; differing original output or bad whole-source quality remain evidence, not reasons for extra calls',
          not_serving=True,not_same_contract_oracle=True,no_VAD_dedup_fallback_or_parameter_search=True)
        put(output/'SUMMARY.json',summary);put(output/'GATE.json',dict(gate='PASS_NINE_PAID_CALLS_AND_INPUT_INVARIANTS',formal_model_calls=9,warmup_model_calls=1,code_commit=source['code_commit'],performance_or_quality_superiority='NOT_ASSUMED'))
        return summary
    except BaseException:
        put(output/'STOP.json',dict(status='FAILED_PRESERVED',traceback=traceback.format_exc(),
          completed_calls=[r['call']['call_id'] for r in completed],formal_attempts=formal_attempts,warmup_attempts=warmups,
          no_automatic_retry=True))
        if not (output/'GATE.json').exists():put(output/'GATE.json',dict(gate='FAIL_DIAGNOSTIC_PRESERVED',formal_attempts=formal_attempts,warmup_attempts=warmups))
        raise
    finally:
        if power is not None:power.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--source-manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--validate-inputs-only',action='store_true')
    a=parser.parse_args()
    if sys.flags.optimize:raise ValueError('normal Python required')
    for name,suffix in [('HF_HOME','cache/huggingface'),('XDG_CACHE_HOME','cache'),('TMPDIR','tmp/physical_retirement_20261028/whisper_diagnostic_v1')]:
        chosen=Path(os.environ.get(name,str(B/suffix))).resolve()
        if not chosen.is_relative_to(B):raise ValueError('diagnostic cache/temp must remain on8TB: '+name)
        chosen.mkdir(parents=True,exist_ok=True);os.environ[name]=str(chosen)
    os.environ['HF_HUB_OFFLINE']='1'
    if sha(a.plan)!=a.plan_sha256:raise ValueError('frozen input plan hash differs')
    source=verify_source(a.source_manifest);summary=run(read(a.plan),a.plan,source,a.out,a.validate_inputs_only)
    print(json.dumps(summary,allow_nan=False))

if __name__=='__main__':main()
