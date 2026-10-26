"""Shared current-input prefix executor inside the real Row GPU Worker."""
import time
from revtrace.prefix_continuation import CurrentInputExecutor
def select_prefix(*,model,processor,moved,jobs,prefixes,contexts,audits,config,start,results,delivery):
    from qwen_asr import parse_asr_output
    if len(jobs)!=1:raise ValueError('LP1 freezes all physical batches to one row')
    j=jobs[0];tok=processor.tokenizer;seed=j.get('prefix_seed');pre=prefixes[0];draft=[]
    if seed:
        if seed['host_verified_perf']>j['enqueue_perf'] or seed['audio_end_sample']>j['audio_end_sample']:raise ValueError('future seed')
        raw=tok.decode(seed['state_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if raw.startswith(pre):
            draft=tok.encode(raw[len(pre):])
            eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
            if draft and seed['complete_EOS']:draft.append(eos[0])
    eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
    def observed(phase,kind,stamp):
        results.put(dict(kind='model-'+kind,**{kind+'_perf':stamp},job_ids=[j['job_id']],online_phase=phase))
    ex=CurrentInputExecutor(model.thinker,moved,eos=eos,budget=config['max_new_tokens'],pad=tok.pad_token_id or 0,observer=observed)
    Z,proof=ex.select(config['current_prefix_mode'],draft);end=time.perf_counter()
    raw=pre+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    language,text=parse_asr_output(raw,user_language=j['language']);P=tok.encode(raw)
    row=dict(job_id=j['job_id'],runtime_digest=config['runtime_digest'],prefix_audio_sha256=j['prefix_audio_sha256'],
        started_perf=start,completed_perf=end,model_started_perf=ex.phases[0]['started_perf'],model_completed_perf=ex.phases[-1]['completed_perf'],
        token_ids=Z,state_tokens=P,text=text,language=language,generated_tokens=len(Z),hit_token_limit=len(Z)==config['max_new_tokens'] and Z[-1] not in eos,
        terminated_by_eos=Z[-1] in eos,execution_context_audit=contexts[0],model_input_audit=audits[0],
        prefix_selection=dict(proof,phases=ex.phases,seed_job_id=seed['job_id'] if seed else None,
            scope='new current-input FP32 cache; shared executor baseline; full actual protocol/Render/WAL/Consumer outside worker'))
    if delivery is not None:
        delivery.explicit_phases=[dict(p,physical_batch_rows=1,executed_job_ids=[j['job_id']]) for p in ex.phases]
        delivery.emit(0,Z,terminal=end,complete_result=row)
    return [row]
