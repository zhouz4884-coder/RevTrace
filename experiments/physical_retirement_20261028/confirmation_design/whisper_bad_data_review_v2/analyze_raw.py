"""Independent text/input/clock diagnosis of retained failed-quality cells."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,re,unicodedata,zlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RAW=HERE/'RAW_EXTRACT.json'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def words(text):return re.findall(r"[a-z0-9']+",unicodedata.normalize('NFKC',text).lower())
def align(ref,hyp):
    table=[[None]*(len(hyp)+1) for _ in range(len(ref)+1)];table[0][0]=(0,0,0,0)
    for i in range(1,len(ref)+1):table[i][0]=(i,0,i,0)
    for j in range(1,len(hyp)+1):table[0][j]=(j,0,0,j)
    for i,a in enumerate(ref,1):
        for j,b in enumerate(hyp,1):
            v=table[i-1][j-1];same=(v[0]+(a!=b),v[1]+(a!=b),v[2],v[3])
            v=table[i-1][j];delete=(v[0]+1,v[1],v[2]+1,v[3])
            v=table[i][j-1];insert=(v[0]+1,v[1],v[2],v[3]+1)
            table[i][j]=min([same,delete,insert],key=lambda x:x[0])
    e,s,d,i=table[-1][-1];return dict(errors=e,substitutions=s,deletions=d,insertions=i,N=len(ref),H=len(hyp),WER=100*e/len(ref))
def put(name,value):(HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    raw=read(RAW);old=read(ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json')
    references={s['source_id']:s['reference'] for s in old['sessions']};all_sources=[];trajectories=[];invariants=Counter();paired=[]
    for name in [k for k in raw if k.startswith('dev-')]:
        run=raw[name];records=run['records'];bykey={(r['job']['session_id'],r['job']['role'],r['job']['end_window']):r for r in records}
        for final in run['result']['final_states']:
            sid=final['session_id'];spec=next(s for s in run['sessions'] if s['session_id']==sid)
            grade=align(words(references[spec['source_id']]),words(final['text']))
            rows=sorted([r for r in records if r['job']['session_id']==sid and r['job']['role']=='authority'],key=lambda r:r['job']['end_window'])
            all_sources.append(dict(run=name,session_id=sid,source_id=spec['source_id'],duration=spec['duration'],
              reference=references[spec['source_id']],final_text=final['text'],**grade,
              authority_cap_rows=sum(r['result']['hit_token_limit'] for r in rows),
              authority_model_seconds=sum(r['result']['row_terminal_perf']-r['result']['model_started_perf'] for r in rows)))
            if 'whisper' not in name:continue
            previous=[];last_end=0
            for rec in rows:
                j,r=rec['job'],rec['result'];a=r['model_input_audit'];h=a['history'];full=r['text']
                segment=full[len(h)+1:] if h and full.startswith(h+' ') else full
                normalized_render=((h+' '+segment).strip() if h else segment.strip())
                checks=dict(parent_equals_previous=(j['prompt_tokens']==previous),
                  interval_matches_job=(a['actual_interval']==[j['audio_start_sample'],j['audio_end_sample']]),
                  interval_contiguous=(a['actual_interval'][0]==last_end),
                  decoder_prefix_exact=(a['full_decoder_sequence'][:len(a['actual_first_decoder_ids'])]==a['actual_first_decoder_ids']),
                  raw_Z_exact=(a['full_decoder_sequence'][len(a['actual_first_decoder_ids']):]==r['token_ids']),
                  renderer_append_exact=(normalized_render==full),
                  effective_capacity=(len(a['actual_first_decoder_ids'])+a['max_new_tokens']<=a['conditioning_contract']['max_target_positions']))
                for k,v in checks.items():invariants[k+'_pass' if v else k+'_FAIL']+=1
                previous=r['state_tokens'];last_end=j['audio_end_sample']
                textbytes=segment.encode();ratio=len(textbytes)/len(zlib.compress(textbytes)) if textbytes else 0.
                trajectories.append(dict(session_id=sid,source_id=j['source_id'],job_id=j['job_id'],parent=j['parent'],window=j['end_window'],
                  actual_interval=a['actual_interval'],interval_seconds=(a['actual_interval'][1]-a['actual_interval'][0])/16000,
                  generated_tokens=r['generated_tokens'],cap=r['hit_token_limit'],EOS=r['terminated_by_eos'],
                  history_characters=len(h),raw_prompt_tokens=len(a['conditioning_plan']['raw_prompt_ids']),
                  actual_initial_decoder_tokens=len(a['actual_first_decoder_ids']),trimmed=a['conditioning_plan']['trimmed'],
                  segment_text=segment,segment_words=len(words(segment)),segment_compression_ratio=ratio,
                  model_seconds=r['row_terminal_perf']-r['model_started_perf'],
                  accepted_input_wait_seconds=r['model_started_perf']-j['audio_ready_perf'],
                  history=h,complete_text=full,checks=checks))
                proposer=bykey[(sid,'proposal',j['end_window'])];pa=proposer['result']['model_input_audit'];pr=proposer['result']
                same_input=(pa['actual_interval']==a['actual_interval'] and pa['input_features_sha256']==a['input_features_sha256'] and pa['actual_first_decoder_ids']==a['actual_first_decoder_ids'] and pa['max_new_tokens']==a['max_new_tokens'])
                paired.append(dict(session_id=sid,window=j['end_window'],same_CPU_features_and_decoder_ids=same_input,
                  proposer_tokens=pr['generated_tokens'],authority_tokens=r['generated_tokens'],proposer_cap=pr['hit_token_limit'],authority_cap=r['hit_token_limit'],
                  exact_Z=(pr['token_ids']==r['token_ids']),
                  input_precision_scope='same CPU features and decoder IDs when flagged; actual GPU FP16 vs FP32 features/arithmetic intentionally differ'))
    w=[r for r in all_sources if 'whisper' in r['run']];q=[r for r in all_sources if 'qwen' in r['run']]
    caps=[r for r in trajectories if r['cap']];bad=[r for r in w if r['session_id'] in [6,7]]
    summary=dict(scope='independent retained raw recount; no neural/tokenizer execution or source edits',
      raw_extract_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest(),
      Whisper=dict(errors=sum(r['errors'] for r in w),N=sum(r['N'] for r in w),
        substitutions=sum(r['substitutions'] for r in w),deletions=sum(r['deletions'] for r in w),insertions=sum(r['insertions'] for r in w),
        WER=100*sum(r['errors'] for r in w)/sum(r['N'] for r in w),
        bad_two_errors=sum(r['errors'] for r in bad),bad_two_N=sum(r['N'] for r in bad),
        first_six_errors=sum(r['errors'] for r in w if r['session_id']<6),first_six_N=sum(r['N'] for r in w if r['session_id']<6),
        authority_rows=len(trajectories),authority_cap_rows=len(caps),
        capped_row_model_seconds=sum(r['model_seconds'] for r in caps),all_authority_model_seconds=sum(r['model_seconds'] for r in trajectories),
        capped_row_generated_tokens=sum(r['generated_tokens'] for r in caps),all_authority_generated_tokens=sum(r['generated_tokens'] for r in trajectories),
        first_caps=[next(r for r in trajectories if r['session_id']==sid and r['cap']) for sid in [6,7]]),
      Qwen=dict(errors=sum(r['errors'] for r in q),N=sum(r['N'] for r in q),WER=100*sum(r['errors'] for r in q)/sum(r['N'] for r in q)),
      invariants=dict(invariants),existing_precision_pairs=dict(rows=len(paired),
        same_input_pairs=sum(r['same_CPU_features_and_decoder_ids'] for r in paired),
        same_input_exact_Z=sum(r['same_CPU_features_and_decoder_ids'] and r['exact_Z'] for r in paired),
        same_input_cap_disagreement=[r for r in paired if r['same_CPU_features_and_decoder_ids'] and r['proposer_cap']!=r['authority_cap']],
        first_cap_pairs=[r for r in paired if (r['session_id'],r['window']) in [(6,7),(7,8)]]),
      alignment_scope='deterministic minimum-Levenshtein path preferring diagonal on equal cost; total errors match original metric, S/D/I decomposition can have tie alternatives')
    if summary['Whisper']['errors']!=808 or summary['Whisper']['N']!=340 or summary['Qwen']['errors']!=10:raise ValueError('raw metric recount mismatch')
    put('SUMMARY.json',summary);put('SOURCE_QUALITY.json',all_sources);put('AUTHORITY_TRAJECTORIES.json',trajectories);put('PAID_PRECISION_PAIRS.json',paired)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['Whisper']}|{'Whisper':{k:v for k,v in summary['Whisper'].items() if k!='first_caps'}},indent=2))

if __name__=='__main__':main()
