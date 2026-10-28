"""Canonical replay + independent actual offered/consumed/view/physical cost."""
from pathlib import Path
import json,sys,hashlib,csv,traceback
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/scripts'));sys.path.insert(0,str(W/'runtime/src'))
from x_service_metrics import audit_episode,read,lines,tokens
from x_certificate_audit import audit as replay
from audit_dsn_journal import audit as replay_wal
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def main():
    from transformers import AutoProcessor
    from qwen_asr import parse_asr_output
    D=O/'x_service_v2';complete=read(D/'SUMMARY.json');assert complete['status']=='COMPLETE' and len(complete['completed'])==16
    manifest=read(D/'manifest.json');processor=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True);tok=processor.tokenizer
    out=[];frontiers=[];proofs=[]
    for name in complete['completed']:
        E=D/name;C=E/'attempt0';config=read(C/'config.json');record=lines(C/'worker_records.jsonl');alljobs={r['job']['job_id']:r for r in record}
        tc=replay(C);wal=replay_wal(E/'canonical.wal',C);s,fs=audit_episode(E,manifest)
        controls=[]
        for row in record:
            j=row['job'];r=row['result'];raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);pre=''
            if j['chunk_id']>=2 and raw:
                ids=tok.encode(raw);k=5
                while True:
                    pre=tok.decode(ids[:max(0,len(ids)-k)])
                    if '\ufffd' not in pre or k>=len(ids):break
                    k+=1
            raw=pre+tok.decode(r['token_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
            lang,text=parse_asr_output(raw,user_language=j['language']);P=tok.encode(raw)
            assert P==r['state_tokens'] and text==r['text']
            if j['role']!='authority':continue
            proof=r['prefix_selection'];seed=j.get('prefix_seed');draft=[]
            if seed:
                ancestor=alljobs[seed['job_id']];assert ancestor['job']['role']=='proposal'
                assert seed['state_tokens']==ancestor['result']['state_tokens'];assert seed['host_verified_perf']<=j['enqueue_perf']
                assert ancestor['result']['received_perf']<=seed['host_verified_perf']
                assert seed['audio_end_sample']==ancestor['job']['audio_end_sample']<=j['audio_end_sample']
                offered=tok.decode(seed['state_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                if offered.startswith(pre):
                    draft=tok.encode(offered[len(pre):])
                    if draft and seed['complete_EOS']:draft.append(r['model_input_audit']['eos_token_ids'][0])
            if 'predicted_tokens' in proof:
                assert proof['no_old_context_KV'];pred=proof['predicted_tokens'];draft=draft[:config['authority_runtime']['max_new_tokens']]
                accepted=next((i for i,(a,b) in enumerate(zip(draft,pred)) if a!=b),len(draft))
                assert accepted==proof['accepted_prefix']
                assert r['token_ids'][:accepted]==draft[:accepted]
                if proof['mode']=='strict-full' and proof['reason']=='paid-full-fallback':
                    # A fallback's generated prefix need not equal the rejected
                    # draft after first mismatch; matching accepted prefix does.
                    assert accepted<len(draft) or (draft[-1] not in r['model_input_audit']['eos_token_ids'] and len(draft)<256)
                if 'cache_after_crop' in proof:assert proof['cache_before_crop']-len(draft)+accepted==proof['cache_after_crop']
            controls.append(dict(job=j['job_id'],mode=proof['mode'],seed=proof.get('seed_job_id'),accepted=proof['accepted_prefix'],
                target_tokens=len(r['token_ids']),reason=proof['reason'],phases=proof.get('phases',[])))
        s.update(mode=config['prefix_executor_mode'],rho=config['rho'],repeat=int(name.rsplit('-r',1)[1]),
            full_native_Render_rows=len(record),prefix_checks=len(controls),certificate_audit=tc['decision'],WAL_audit=wal['decision'],
            audio_rollback_samples=sum(r['audio_rollback_samples'] for r in lines(C/'consumer.jsonl')),
            erased_characters=sum(r['erased_characters'] for r in lines(C/'consumer.jsonl')),
            scope='2-source DEVELOPMENT service,2 timing repeats; no held-out statistical superiority or exclusive decoding claim')
        out.append(s);frontiers.extend(dict(episode=name,**f) for f in fs);proofs.append(dict(episode=name,checks=controls))
    result=dict(status='PASS_FULL_SERVICE_INDEPENDENT_RECOUNT',runs=16,rows=out,prefix_proofs=proofs,
        limitations='2 development audio sources only. All offered frontiers counted; actual legal Consumer times not executor finish. Both GPUs and retired work paid. Shared Standard prefix baseline may match RevTrace.')
    (O/'X_SERVICE_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (O/'X_SERVICE_RUNS.csv').open('w',newline='') as f:
        rows=[{k:v for k,v in r.items() if k not in ['mode_entries','power_coverage']} for r in out];w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (O/'X_SERVICE_FRONTIERS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(frontiers[0]));w.writeheader();w.writerows(frontiers)
    print(json.dumps(dict(status=result['status'],runs=16)))
if __name__=='__main__':main()
