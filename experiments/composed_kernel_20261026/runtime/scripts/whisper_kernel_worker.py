"""Real Whisper GPU adapter. Variable prompt rows run serially in one lease.

This intentionally exposes every neural call; it is not called a free
heterogeneous batch. Both methods get exactly this executor.
"""
import os,time,hashlib,json,traceback
from pathlib import Path

def worker_main(commands,results,config):
    os.environ['CUDA_VISIBLE_DEVICES']=str(config['gpu'])
    os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['OMP_NUM_THREADS']='2'
    try:
        import torch,numpy as np,soundfile as sf
        from transformers import WhisperProcessor,WhisperForConditionalGeneration
        from row_delivery_worker import RowDeliveryTap
        from revtrace.whisper_adapter import TrustedWhisperRender
        from revtrace.dgft import digest_tokens
        torch.set_num_threads(2)
        proc=WhisperProcessor.from_pretrained(config['model'],local_files_only=True)
        dtype=torch.float32 if config['dtype']=='float32' else torch.float16
        model=WhisperForConditionalGeneration.from_pretrained(config['model'],torch_dtype=dtype,
            attn_implementation='eager',local_files_only=True).to('cuda:0').eval()
        sources={}
        for row in json.loads(Path(config['manifest']).read_text())['sessions']:
            x,sr=sf.read(row['path'],dtype='float32');assert sr==16000 and x.ndim==1
            assert hashlib.sha256(x.tobytes()).hexdigest()==row['audio_sha256'];sources[row['source_id']]=x
        render=TrustedWhisperRender(proc,config['max_new_tokens'])
        tap=RowDeliveryTap(results,proc,None,config,[proc.tokenizer.eos_token_id]);tap.render=render
        features=proc(np.zeros(16000,dtype='float32'),sampling_rate=16000,return_tensors='pt').input_features.to('cuda:0',dtype=dtype)
        with torch.inference_mode():model.generate(features,do_sample=False,max_new_tokens=4,return_timestamps=False)
        torch.cuda.synchronize()
        results.put(dict(kind='ready',gpu=config['gpu'],runtime_digest=config['runtime_digest'],
            dtype=config['dtype'],adapter='whisper-get_prompt_ids-v1',physical_rows='serial variable prompts',
            pid=os.getpid(),peak_memory_allocated=torch.cuda.max_memory_allocated()))
        while True:
            jobs=commands.get()
            if jobs is None:break
            started=time.perf_counter();results.put(dict(kind='batch-started',started_perf=started,job_ids=[j['job_id'] for j in jobs]))
            audits=[];contexts=[];inputs=[]
            for j in jobs:
                assert time.perf_counter()>=j['audio_ready_perf']
                # This declared adapter consumes each new contiguous audio
                # interval and actual accumulated feedback through get_prompt_ids.
                a=sources[j['source_id']][j['chunk_id']*32000:j['audio_end_sample']]
                assert len(a)>0
                history=proc.tokenizer.decode(j['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
                prompt=proc.get_prompt_ids(history,return_tensors='pt') if history else None
                x=proc(a,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
                features=x.input_features
                prefixsha=hashlib.sha256(sources[j['source_id']][:j['audio_end_sample']].tobytes()).hexdigest()
                contexts.append(dict(actual_audio_sha256=prefixsha,executed_prompt_tokens=list(j['prompt_tokens']),
                    declared_prompt_digest=digest_tokens(j['prompt_tokens']),executed_prompt_digest=digest_tokens(j['prompt_tokens']),
                    actual_interval_sha256=hashlib.sha256(a.tobytes()).hexdigest(),fault_override=False))
                audits.append(dict(adapter='whisper-get_prompt_ids-v1',source_id=j['source_id'],
                    declared_prompt_tokens=j['prompt_tokens'],waveform_sha256=prefixsha,
                    eos_token_ids=[proc.tokenizer.eos_token_id],
                    actual_interval=[j['chunk_id']*32000,j['audio_end_sample']],history=history,
                    prompt_ids=prompt.tolist() if prompt is not None else [],
                    input_features_sha256=hashlib.sha256(features.numpy().tobytes()).hexdigest(),
                    shape=list(features.shape),dtype=config['dtype'],batch_rows=1,do_sample=False,
                    max_new_tokens=config['max_new_tokens']))
                inputs.append((x,prompt))
            tap.prepare(jobs,prefixes=['']*len(jobs),contexts=contexts,audits=audits,started=started)
            final=[];phases=[]
            for i,(j,(x,prompt)) in enumerate(zip(jobs,inputs)):
                kwargs=dict(input_features=x.input_features.to('cuda:0',dtype=dtype),
                    attention_mask=x.attention_mask.to('cuda:0'),do_sample=False,
                    max_new_tokens=config['max_new_tokens'],return_timestamps=False,return_dict_in_generate=True)
                if prompt is not None:kwargs['prompt_ids']=prompt.to('cuda:0')
                actual=[]
                def record(_module,args,kwargs):
                    if not actual:
                        ids=kwargs.get('input_ids',args[0] if args else None)
                        if ids is not None:actual.extend(ids.detach().cpu().tolist())
                hook=model.model.decoder.register_forward_pre_hook(record,with_kwargs=True)
                ms=time.perf_counter();tap.set_phase('whisper-independent-generate',ms,[i])
                with torch.inference_mode():out=model.generate(**kwargs)
                torch.cuda.synchronize();mc=time.perf_counter();hook.remove()
                full=out.sequences[0].cpu().tolist()
                # Default Whisper convenience output removes EOS. Preserve
                # the underlying generation result and exclude only the actual
                # observed initial decoder input, never infer stop from text.
                assert actual and full[:len(actual[0])]==actual[0]
                z=full[len(actual[0]):];eos=proc.tokenizer.eos_token_id
                stop=next((n+1 for n,t in enumerate(z) if t==eos),len(z));z=z[:stop]
                audits[i]['actual_first_decoder_ids']=actual[0] if actual else []
                audits[i]['full_decoder_sequence']=full
                audits[i]['actual_gpu_features_sha256']=hashlib.sha256(kwargs['input_features'].float().cpu().numpy().tobytes()).hexdigest()
                if prompt is not None:
                    # Actual neural decoder consumption, not just constructed input.
                    p=prompt.tolist();assert audits[i]['actual_first_decoder_ids'][:len(p)]==p
                tap.emit(i,z,terminal=mc)
                row=dict(tap.rows[i],model_completed_perf=mc,model_started_perf=ms)
                final.append(row);phases.append(dict(phase='whisper-independent-generate',started_perf=ms,
                    completed_perf=mc,physical_batch_rows=1,executed_job_ids=[j['job_id']]))
            tap.explicit_phases=phases;tap.finish(final)
    except BaseException:
        results.put(dict(kind='error',traceback=traceback.format_exc()))
