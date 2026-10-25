"""FP32 correct-context selection + paid full-layout fallback, real worker only."""
import hashlib,time
from revtrace.online_admission import gate_candidate,target_identity,complete_candidate,fallback_row_plan

def select_online(*,model,processor,moved,jobs,prefixes,contexts,audits,config,start,results,delivery=None,raw_inputs=None):
    import torch
    from qwen_asr import parse_asr_output
    mode=config['online_selection_mode'];budget=int(config['max_new_tokens']);tok=processor.tokenizer
    eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else list(eos or [])
    candidates=[list(j['candidate_token_ids']) for j in jobs]
    malformed=[not c or len(c)>budget for c in candidates]
    n=len(jobs);length=moved['input_ids'].shape[1];device=moved['input_ids'].device
    predicted=[[] for _ in jobs];margins=[[] for _ in jobs];verify_seconds=fallback_seconds=0.;oracle={}
    phases=[];operator_probe={};fallback_realization={}
    # Extra diagnostic oracle calls do not authorize early installation.
    if config.get('online_oracle_diagnostic',False):delivery=None
    def measured(name,fn,indices=None):
        indices=list(range(n)) if indices is None else indices;job_ids=[jobs[i]['job_id'] for i in indices]
        torch.cuda.synchronize();a=time.perf_counter();results.put({'kind':'model-started','started_perf':a,'job_ids':job_ids,'online_phase':name})
        if delivery is not None:delivery.set_phase(name,a,indices)
        answer=fn();torch.cuda.synchronize();b=time.perf_counter();results.put({'kind':'model-completed','completed_perf':b,'job_ids':job_ids,'online_phase':name});phases.append({'phase':name,'started_perf':a,'completed_perf':b,'physical_batch_rows':len(indices),'executed_job_ids':job_ids})
        return answer,b-a
    def verify(rows,data=None):
        data=moved if data is None else data;size=len(rows);prompt_width=data['input_ids'].shape[1]
        w=max(map(len,rows));pad=tok.pad_token_id if tok.pad_token_id is not None else 0
        ids=torch.full((size,w),pad,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
        for i,c in enumerate(rows):ids[i,:len(c)]=torch.tensor(c,device=device);mask[i,:len(c)]=1
        checked=dict(data,input_ids=torch.cat((data['input_ids'],ids),1),attention_mask=torch.cat((data['attention_mask'],mask),1))
        def restrict(_module,values):return (values[0][:,prompt_width-1:prompt_width+w-1,:],)
        hook=model.thinker.lm_head.register_forward_pre_hook(restrict)
        try:
            with torch.inference_mode():
                logits=model.thinker(**checked,use_cache=False,return_dict=True).logits
                pred=logits.argmax(-1).cpu().tolist()
                if mode=='score':
                    top=logits.topk(2,-1);chosen=logits.gather(-1,ids.unsqueeze(-1)).squeeze(-1).float();other=torch.where(top.indices[:,:,0]==ids,top.values[:,:,1],top.values[:,:,0]).float();margin=(chosen-other).cpu().tolist()
                else:margin=[[0.]*len(c) for c in rows]
                return pred,margin
        finally:hook.remove()
    def generate(data=None,indices=None,proof_factory=None):
        data=moved if data is None else data
        extra={}
        if delivery is not None and indices is not None:extra['streamer']=delivery.stream(indices,proof_factory)
        with torch.inference_mode():out=model.generate(**data,do_sample=False,max_new_tokens=budget,output_scores=False,**extra)
        rows=out.sequences[:,data['input_ids'].shape[1]:].cpu().tolist();ans=[]
        for row in rows:
            end=next((i+1 for i,t in enumerate(row) if t in eos),len(row));ans.append(row[:end])
        return ans
    if mode!='unprotected' and not all(malformed):
        safe_rows=[c if not bad else [eos[0]] for c,bad in zip(candidates,malformed)]
        (predicted,margins),verify_seconds=measured('correct-context-'+mode,lambda:verify(safe_rows))
    checks=[gate_candidate(mode,c,p,m,eos=eos,budget=budget,threshold=config['score_threshold']) for c,p,m in zip(candidates,predicted,margins)]
    failed=[i for i,c in enumerate(checks) if not c[0]];repaired=None;fallback_data=None;fallback_indices=[];fallback_rows={}
    def early_proof(i,now):
        fallback=i in failed
        return {'row_completion_protocol':'complete-row-v1','mode':mode,'target_identity':target_identity(jobs[i]),
          'dtype':config['dtype'],'executed_prompt_tokens':contexts[i]['executed_prompt_tokens'],
          'actual_audio_sha256':contexts[i]['actual_audio_sha256'],'context_override_used':contexts[i]['fault_override'],
          'candidate_origin_job_id':jobs[i]['candidate_origin_job_id'],'candidate_accepted':checks[i][0],
          'reason':checks[i][1],'predicted_token_ids':predicted[i][:len(candidates[i])],
          'candidate_margins':margins[i][:len(candidates[i])],'eos_token_ids':eos,
          'verify_batch_seconds':verify_seconds,'fallback_used':fallback,'fallback_generated':fallback,
          'fallback_batch_seconds':None,'fallback_row_compute_seconds_so_far':now-delivery.phase_start if fallback else 0.,
          'fallback_executed_job_ids':[jobs[k]['job_id'] for k in fallback_indices] if fallback else [],
          'fallback_row_indices':list(fallback_indices) if fallback else [],
          'fallback_requested_layout':config.get('fallback_layout','full'),
          'physical_batch_rows':n,'row_index_in_original_batch':i,
          'full_physical_cost_in_separate_batch_accounting':True,
          'unsafe_no_FP32_selection':mode=='unprotected'}
    if delivery is not None:
        for i in range(n):
            if checks[i][0]:delivery.emit(i,candidates[i],terminal=time.perf_counter(),proof=early_proof(i,time.perf_counter()))
    if failed:
        requested_layout=config.get('fallback_layout','full')
        plan_layout='selective' if requested_layout=='selective_reprocess' else requested_layout
        fallback_indices=fallback_row_plan({k:list(v.shape) for k,v in moved.items()},n,failed,plan_layout)
        if fallback_indices==list(range(n)):fallback_data=moved
        else:
            indices=torch.tensor(fallback_indices,dtype=torch.long,device=device);fallback_data={k:v.index_select(0,indices) for k,v in moved.items()}
        original_fallback_data=fallback_data
        def reprocess(indices):
            if raw_inputs is None:raise ValueError('reprocessing requires actual original raw model inputs')
            rebuilt=processor(text=[raw_inputs['text'][i] for i in indices],audio=[raw_inputs['audio'][i] for i in indices],return_tensors='pt',padding=True)
            return {k:v.to(device=device,dtype=moved[k].dtype) for k,v in rebuilt.items()}
        if requested_layout=='selective_reprocess' and len(fallback_indices)<n:
            begin=time.perf_counter();fallback_data=reprocess(fallback_indices);torch.cuda.synchronize()
            fallback_realization={'layout':'selective_reprocess','preprocess_wall_s':time.perf_counter()-begin,
                'original_shapes':{k:list(v.shape) for k,v in original_fallback_data.items()},
                'actual_shapes':{k:list(v.shape) for k,v in fallback_data.items()},'indices':fallback_indices}
        repaired,fallback_seconds=measured('fresh-FP32-fallback',lambda:generate(fallback_data,fallback_indices,early_proof),fallback_indices)
        fallback_rows=dict(zip(fallback_indices,repaired))
        if config.get('fallback_operator_probe',False):
            # Standalone paid operator diagnostic, never an Owner-installed fast path.
            baseline_repeat,baseline_repeat_s=measured('operator-original-repeat',lambda:generate(original_fallback_data),fallback_indices)
            begin=time.perf_counter();compact=reprocess(fallback_indices);torch.cuda.synchronize();preprocess_s=time.perf_counter()-begin
            trimmed,trim_s=measured('operator-reprocessed-generate',lambda:generate(compact),fallback_indices)
            trim_repeat,trim_repeat_s=measured('operator-reprocessed-repeat',lambda:generate(compact),fallback_indices)
            identities=lambda data:{k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.detach().cpu().contiguous().numpy().tobytes()).hexdigest()} for k,v in data.items()}
            operator_probe={'scope':'paid standalone operator; no installed Canonical output from the experimental branch',
                'failed_indices':fallback_indices,'baseline_tokens':repaired,'baseline_repeat_tokens':baseline_repeat,
                'reprocessed_tokens':trimmed,'reprocessed_repeat_tokens':trim_repeat,
                'baseline_repeat_equal':repaired==baseline_repeat,'reprocessed_repeat_equal':trimmed==trim_repeat,
                'baseline_reprocessed_equal':repaired==trimmed,'baseline_seconds':fallback_seconds,'baseline_repeat_seconds':baseline_repeat_s,
                'reprocessed_model_seconds':trim_s,'reprocessed_repeat_seconds':trim_repeat_s,'reprocess_CPU_and_copy_seconds':preprocess_s,
                'baseline_input_tensors':identities(original_fallback_data),'reprocessed_input_tensors':identities(compact),
                'original_padding_side':tok.padding_side,'complete_tokens_stop_budget_checked_separately':True}
    if config.get('online_oracle_diagnostic',False) and mode!='unprotected':
        expected=repaired if repaired is not None and fallback_indices==list(range(n)) else None
        if expected is None:expected,_=measured('pilot-independent-greedy-oracle',generate)
        repeated,_=measured('pilot-greedy-oracle-repeat',generate)
        (op,_),_=measured('pilot-oracle-as-candidate',lambda:verify(expected))
        stable=expected==repeated;selfchecks=[complete_candidate(c,p,eos=eos,budget=budget)[0] for c,p in zip(expected,op)]
        accepted_exact=[not checks[i][0] or candidates[i]==expected[i] for i in range(n)]
        oracle={'same_input_repeat_equal':stable,'oracle_selfchecks':selfchecks,'accepted_equal_independent_greedy':accepted_exact,'oracle_token_ids':expected,'repeat_token_ids':repeated}
        if failed:
            fbrepeat,_=measured('pilot-fallback-layout-repeat',lambda:generate(fallback_data),fallback_indices)
            (fbpred,_),_=measured('pilot-fallback-layout-selfcheck',lambda:verify(repaired,fallback_data),fallback_indices)
            fbchecks=[complete_candidate(c,p,eos=eos,budget=budget)[0] for c,p in zip(repaired,fbpred)]
            oracle.update(fallback_layout_repeat_equal=repaired==fbrepeat,fallback_layout_selfchecks=fbchecks,fallback_equal_original_full_batch=[fallback_rows[i]==expected[i] for i in failed])
            if repaired!=fbrepeat or not all(fbchecks):raise AssertionError('fresh fallback-layout repeat/selfcheck disagreed')
        if not stable or not all(selfchecks) or not all(accepted_exact):raise AssertionError('pilot target-operation numerical/verification disagreement; no formal launch')
    fallback_input_ids=fallback_data['input_ids'].detach().cpu().tolist() if failed else None
    rows=[]
    for i,j in enumerate(jobs):
        selected=fallback_rows[i] if i in failed else candidates[i]
        shape,reason=complete_candidate(selected,selected,eos=eos,budget=budget)
        if not shape:raise ValueError('selected sequence violates complete shape: '+reason)
        raw=prefixes[i]+tok.decode(selected,skip_special_tokens=True,clean_up_tokenization_spaces=False);lang,text=parse_asr_output(raw,user_language=j['language']);P=list(tok.encode(raw))
        a=audits[i]
        proof={'mode':mode,'target_identity':target_identity(j),'dtype':config['dtype'],
            'executed_prompt_tokens':contexts[i]['executed_prompt_tokens'],
            'actual_audio_sha256':contexts[i]['actual_audio_sha256'],
            'context_override_used':contexts[i]['fault_override'],
            'candidate_origin_job_id':j['candidate_origin_job_id'],'candidate_accepted':checks[i][0],
            'reason':checks[i][1],'predicted_token_ids':predicted[i][:len(candidates[i])],
            'candidate_margins':margins[i][:len(candidates[i])],'eos_token_ids':eos,
            'verify_batch_seconds':verify_seconds,'fallback_used':i in failed,
            'fallback_generated':repaired is not None,'fallback_batch_seconds':fallback_seconds,
            'fallback_requested_layout':config.get('fallback_layout','full'),
            'fallback_row_indices':fallback_indices,'fallback_executed_job_ids':[jobs[z]['job_id'] for z in fallback_indices],
            'fallback_batch_rows':len(fallback_indices),'row_index_in_original_batch':i,
            'fallback_input_ids':fallback_input_ids,
            'fallback_input_row_origins':[audits[z] for z in fallback_indices],
            'offered_projection_equal_target_render':P==j['candidate_state_tokens'],
            'physical_batch_rows':n,'phases':phases,'pilot_oracle':oracle,
            'fallback_realization':fallback_realization,'fallback_operator_probe':operator_probe,
            'first_mismatch_position':next((k for k,(a,b) in enumerate(zip(candidates[i],predicted[i])) if a!=b),None),
            'unsafe_no_FP32_selection':mode=='unprotected','processor_input_audit':a}
        rows.append({'job_id':j['job_id'],'runtime_digest':config['runtime_digest'],'prefix_audio_sha256':j['prefix_audio_sha256'],'started_perf':start,'model_started_perf':phases[0]['started_perf'] if phases else None,'model_completed_perf':phases[-1]['completed_perf'] if phases else None,'token_ids':selected,'state_tokens':P,'text':text,'language':lang,'generated_tokens':len(selected),'hit_token_limit':len(selected)==budget and selected[-1] not in eos,'terminated_by_eos':selected[-1] in eos,'execution_context_audit':contexts[i],'model_input_audit':a,'online_verification':proof})
    completed=time.perf_counter()
    for r in rows:r['completed_perf']=completed
    return rows
