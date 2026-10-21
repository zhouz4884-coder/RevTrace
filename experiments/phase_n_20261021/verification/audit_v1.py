"""Independent FP32 token/termination/Phi and paid-cost audit of fixed-state probes."""
import argparse,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def independent_token_check(candidate,predicted,stops,budget):
    if not 0<len(candidate)<=budget:return False
    positions=[i for i,t in enumerate(candidate) if t in stops]
    if positions and positions!=[len(candidate)-1]:return False
    if not positions and len(candidate)!=budget:return False
    return list(candidate)==list(predicted[:len(candidate)]) and len(predicted)>=len(candidate)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);a=p.parse_args();root=a.root
    assert json.loads((root/'SUMMARY.json').read_text())['status']=='COMPLETE' and not (root/'STOP.json').exists()
    rawfiles=[f for f in root.glob('*.json') if f.name not in ['INDEPENDENT_AUDIT.json']]
    before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in rawfiles}
    cases=json.loads(a.cases.read_text())['cases'];cm={c['case_id']:c for c in cases}
    from qwen_asr import Qwen3ASRModel
    from transformers import AutoProcessor
    tokenizer=AutoProcessor.from_pretrained(a.model,local_files_only=True).tokenizer
    def reconstruct(job,tokens):
        actual=job.get('fault_actual_prompt_tokens',job['prompt_tokens'])
        text=tokenizer.decode(actual,skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
        if job['chunk_id']>=2 and text:
            ids=tokenizer.encode(text);k=5
            while True:
                prefix=tokenizer.decode(ids[:max(0,len(ids)-k)])
                if '\ufffd' not in prefix or k>=len(ids):break
                k+=1
        raw=tokenizer.decode(tokens,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        return tokenizer.encode(prefix+raw),prefix
    phases={f.stem:json.loads(f.read_text()) for f in rawfiles if 'jobs' in json.loads(f.read_text())}
    for name,phase in phases.items():
        assert len(phase['jobs'])==len(phase['results'])
        for job,row in zip(phase['jobs'],phase['results']):
            assert job['job_id']==row['job_id'] and row['runtime_digest']==job['runtime_digest']
            assert row['completed_perf']>=row['started_perf']
            if row['token_ids']:
                projection,prefix=reconstruct(job,row['token_ids'])
                assert row['state_tokens']==projection
                assert row['model_input_audit']['rollback_prefix']==prefix
    def mapped(phase):return {j['probe_case_id']:(j,r) for j,r in zip(phase['jobs'],phase['results'])}
    drafts=mapped(phases['C3-extra-root-draft-b16']);faults=mapped(phases['F2-actual-wrong-context-draft-b16'])
    candidate={k:r for k,(_,r) in drafts.items()}|{k:r for k,(_,r) in faults.items()}
    for c in cases:
        if c['group'] in ['C1','C2'] and c['candidate']:candidate[c['case_id']]=c['candidate']['result']
    decisions=[];oracle_unstable=[];false_accept=[];fallback_disagreement=[];generation_processors=[];selfcheck=[]
    for batch in [16,4,1]:
        for group in ['C1','C2','C3','F2']:
            prefix=f'{group}-';oracle=mapped(phases[f'{group}-oracle-b{batch}']);repeat=mapped(phases[f'{group}-oracle-repeat-b{batch}'])
            checked=mapped(phases[f'{group}-verify-b{batch}']);fallback=phases.get(f'{group}-full-fallback-b{batch}')
            positive=mapped(phases[f'{group}-oracle-selfcheck-b{batch}']);positive_repeat=mapped(phases[f'{group}-oracle-selfcheck-repeat-b{batch}'])
            if fallback:
                for case,(j,r) in mapped(fallback).items():
                    o=oracle[case][1]
                    if r['token_ids']!=o['token_ids'] or r['state_tokens']!=o['state_tokens']:fallback_disagreement.append([batch,group,case])
            for case,(j,o) in oracle.items():
                pj,pv=positive[case];pr=positive_repeat[case][1];pa=o['model_input_audit']
                legitimate_pass=independent_token_check(o['token_ids'],pv['full_predicted_token_ids'],set(pa['eos_token_ids']),pa['max_new_tokens'])
                pp,_=reconstruct(pj,o['token_ids']);assert pp==o['state_tokens']
                assert legitimate_pass==pv['certificate_accept']
                selfcheck.append({'batch':batch,'group':group,'case_id':case,'accepted':legitimate_pass,
                    'same_input_repeat_equal':pv['full_predicted_token_ids']==pr['full_predicted_token_ids']})
                rr=repeat[case][1];stable=o['token_ids']==rr['token_ids'] and o['state_tokens']==rr['state_tokens']
                if not stable:oracle_unstable.append([batch,group,case])
                if case not in candidate:
                    assert fallback is not None
                    decisions.append({'batch':batch,'group':group,'case_id':case,'present':False,'accepted':False,'exact':None});continue
                proposal=candidate[case];vj,v=checked[case];audit=o['model_input_audit']
                assert v['model_input_audit']['dtype']=='float32'
                assert v['model_input_audit']['unpadded_input_ids']==audit['unpadded_input_ids']
                assert v['model_input_audit']['waveform_sha256']==audit['waveform_sha256']
                assert sum(v['candidate_attention_mask'])==len(proposal['token_ids'])
                budget=audit['max_new_tokens'];stops=set(audit['eos_token_ids'])
                good_token=independent_token_check(proposal['token_ids'],v['full_predicted_token_ids'],stops,budget)
                projected,prefix=reconstruct(vj,proposal['token_ids'])
                assert projected==v['reconstructed_state_tokens'] and prefix==v['model_input_audit']['rollback_prefix']
                good_projection=projected==proposal['state_tokens']
                accept=good_token
                assert accept==v['certificate_accept']
                assert v['offered_pair_accept']==(good_token and good_projection)
                exact=proposal['token_ids']==o['token_ids'] and projected==o['state_tokens']
                if accept and not exact:false_accept.append([batch,group,case])
                first=next((i for i,(x,y) in enumerate(zip(proposal['token_ids'],o['token_ids'])) if x!=y),
                    min(len(proposal['token_ids']),len(o['token_ids'])))
                if exact:first=None
                decisions.append({'batch':batch,'group':group,'case_id':case,'present':True,'accepted':accept,'exact':exact,
                    'source_id':j['source_id'],'oracle_stable':stable,'token_gate':good_token,'projection_gate':good_projection,
                    'offered_projection_matches_oracle':proposal['state_tokens']==o['state_tokens'],
                    'offered_pair_accept':v['offered_pair_accept'],
                    'candidate_tokens':len(proposal['token_ids']),'oracle_tokens':len(o['token_ids']),'first_divergence':first,
                    'actual_fault_changed_prefix':proposal.get('model_input_audit',{}).get('rollback_prefix')!=audit['rollback_prefix'] if group=='F2' else None})
                cfg=audit['generation_config']
                active={k:cfg.get(k) for k in ['forced_bos_token_id','forced_eos_token_id','suppress_tokens','begin_suppress_tokens','bad_words_ids'] if cfg.get(k) not in [None,[]]}
                for k in ['forced_decoder_ids','sequence_bias','watermarking_config','exponential_decay_length_penalty']:
                    if cfg.get(k) not in [None,[],{}]:active[k]=cfg[k]
                if cfg.get('repetition_penalty',1)!=1:active['repetition_penalty']=cfg['repetition_penalty']
                for k in ['min_length','min_new_tokens','no_repeat_ngram_size']:
                    if cfg.get(k) not in [None,0]:active[k]=cfg[k]
                if active:generation_processors.append(active)
    negatives=[]
    for j,r in zip(phases['C3-stop-negative-b16']['jobs'],phases['C3-stop-negative-b16']['results']):
        assert not independent_token_check(j['audit_rescore_tokens'],r['full_predicted_token_ids'],set(r['model_input_audit']['eos_token_ids']),256)
        assert not r['certificate_accept'];negatives.append(j['probe_case_id'])
    cap=[]
    co=mapped(phases['cap4-oracle-b4']);cr=mapped(phases['cap4-oracle-repeat-b4']);cv=mapped(phases['cap4-verify-b4']);cd=mapped(phases['cap4-draft-b4'])
    for case,(j,o) in co.items():
        v=cv[case][1];draft=cd[case][1];rr=cr[case][1];stops=set(o['model_input_audit']['eos_token_ids'])
        gate=independent_token_check(draft['token_ids'],v['full_predicted_token_ids'],stops,4)
        projected,_=reconstruct(cv[case][0],draft['token_ids'])
        assert gate==v['certificate_accept']
        exact=draft['token_ids']==o['token_ids'] and projected==o['state_tokens']
        cap.append({'case_id':case,'accepted':gate,'exact':exact,'eos':o['token_ids'][-1] in stops,'length':len(o['token_ids']),
            'repeat_equal':o['token_ids']==rr['token_ids'] and o['state_tokens']==rr['state_tokens']})
        if gate and not exact:false_accept.append(['cap4',case])
    costs=[]
    for group in ['C1','C2','C3']:
        oracle=phases[f'{group}-oracle-b16']['wall_seconds'];verify=phases[f'{group}-verify-b16']['wall_seconds']
        fallback=phases.get(f'{group}-full-fallback-b16',{}).get('wall_seconds',0.)
        extra=phases['C3-extra-root-draft-b16']['wall_seconds'] if group=='C3' else 0.
        costs.append({'group':group,'oracle_wall':oracle,'verification_wall':verify,'actual_full_fallback_wall':fallback,
            'extra_root_draft_wall':extra,'inclusive_fixed_state_work':verify+fallback+extra,
            'conditional_saving_fraction':1-(verify+fallback+extra)/oracle,
            'scope':'fixed-state model workload, native draft common cost cancels; not deployed throughput or commit P99'})
    assert before=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in rawfiles}
    controls_stable=all(r['same_input_repeat_equal'] for r in selfcheck)
    nonvacuous=any(r['accepted'] for r in selfcheck)
    result={'decision':'PASS_BOUNDED_FP32_CERTIFICATION' if not false_accept and not oracle_unstable and not fallback_disagreement and not generation_processors and controls_stable and nonvacuous else 'NO_GO_STRICT_EQUIVALENCE',
        'comparisons':decisions,'false_accepts':false_accept,'oracle_repeat_disagreements':oracle_unstable,
        'fallback_oracle_disagreements':fallback_disagreement,'active_generation_processors':generation_processors,
        'stop_negative_controls':len(negatives),'cap4_controls':cap,'oracle_as_candidate_controls':selfcheck,
        'oracle_selfcheck_repeats_stable':controls_stable,'oracle_selfcheck_nonvacuous':nonvacuous,
        'costs':costs,'raw_sha256':before,
        'scope':'repeated contexts and batch forms are not independent acoustic samples; no online selector performance claim'}
    save(root/'INDEPENDENT_AUDIT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['comparisons','raw_sha256']},indent=2))
if __name__=='__main__':main()
