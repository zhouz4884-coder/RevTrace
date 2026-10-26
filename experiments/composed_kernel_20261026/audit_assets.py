"""CPU-only replay of actual audio/preprocessing/render and read-only WAL.
No model weights loaded, no new neural inference. Run only after GPU stage.
"""
import os,sys,json,hashlib,importlib.util,inspect
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='2';os.environ['TOKENIZERS_PARALLELISM']='false'
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
sys.path[:0]=[str(P/'runtime/scripts'),str(P/'runtime/src')]
from audit_dsn_journal import audit as wal_audit
def read(p):return json.loads(p.read_text())
def rows(p):
    if not p.exists():return []
    result=[];raw=p.read_bytes().splitlines(keepends=True)
    for i,line in enumerate(raw):
        try:result.append(json.loads(line))
        except (json.JSONDecodeError,UnicodeDecodeError):assert i==len(raw)-1 and not line.endswith(b'\n')
    return result
def sha(x):return hashlib.sha256(x).hexdigest()
def tensor(x):
    y=x.detach().cpu().contiguous();return dict(shape=list(y.shape),dtype=str(y.dtype),sha256=sha(y.numpy().tobytes()))
def main():
    import argparse,subprocess
    ap=argparse.ArgumentParser();ap.add_argument('--stage',required=True);a=ap.parse_args()
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    done=read(O/a.stage/'SUMMARY.json');dest=O/(a.stage+'_ASSETS.json');assert not dest.exists()
    import numpy as np,torch,soundfile as sf
    from transformers import AutoProcessor,WhisperProcessor
    from qwen_asr import Qwen3ASRModel,parse_asr_output
    torch.set_num_threads(2);manifest=read(P/'INDEPENDENT_MANIFEST_v1.json');waves={}
    for s in manifest['sessions']:
        x,sr=sf.read(s['path'],dtype='float32');assert sr==16000 and sha(x.tobytes())==s['audio_sha256'];waves[s['source_id']]=x
    processors={};allruns=[]
    for name in done['completed']:
        E=O/a.stage/name;final=1 if (E/'attempt1').exists() else 0;D=E/f'attempt{final}';cfg=read(D/'config.json')
        family=cfg['authority_runtime']['model_adapter'];model=B/'models'/cfg['authority_runtime']['model']
        if family not in processors:
            proc=AutoProcessor.from_pretrained(model,local_files_only=True) if family=='qwen' else WhisperProcessor.from_pretrained(model,local_files_only=True)
            processors[family]=proc
        proc=processors[family];tok=proc.tokenizer
        for file,value in cfg['authority_runtime']['render_contract']['assets'].items():assert sha((model/file).read_bytes())==value
        wal_before=sha((E/'canonical.wal').read_bytes());wa=wal_audit(E/'canonical.wal')
        wa=wal_audit(E/'canonical.wal',D,expected_prior_commits=wa['commits_before_latest_restart'] if final else 0)
        assert sha((E/'canonical.wal').read_bytes())==wal_before
        report=read(D/'BOUNDARY_PROBE.json') if (D/'BOUNDARY_PROBE.json').exists() else None
        corrupt={t['job']['job_id']:json.loads(t['corrupted_message']['payload_json']) for t in report['coherent_injection']} if report else {}
        checked=0;batches=0;consumed=0;unknown=0
        for attempt in range(final+1):
            C=E/f'attempt{attempt}';records=rows(C/'worker_records.jsonl')
            jobs={r['job']['job_id']:r['job'] for r in records};results={r['job']['job_id']:r['result'] for r in records}
            submissions=[]
            for f in C.glob('*.submissions'):submissions+=rows(f)
            if submissions:
                for s in submissions:
                    for j in s['jobs']:jobs[j['job_id']]=j
                for f in C.glob('worker-*-receipts.jsonl'):
                    for r in rows(f):
                        if r['kind']=='row-complete':
                            m=r['message'];assert sha(m['payload_json'].encode())==m['payload_digest']
                            body=json.loads(m['payload_json']);results[body['job_id']]=body
                groups=[s['jobs'] for s in submissions]
            else:
                groups=[]
                for b in rows(C/'worker_batch_accounting.jsonl'):groups.append([jobs[j] for j in b['job_ids']])
            for group in groups:
                available=[(i,j,results[j['job_id']]) for i,j in enumerate(group) if j['job_id'] in results]
                if not available:unknown+=len(group);continue
                if family=='qwen':
                    helper=object.__new__(Qwen3ASRModel);helper.processor=proc
                    prefixes=[]
                    for j in group:
                        raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
                        if j['chunk_id']>=2 and raw:
                            ids=tok.encode(raw);n=5
                            while True:
                                prefix=tok.decode(ids[:max(0,len(ids)-n)])
                                if '\ufffd' not in prefix or n>=len(ids):break
                                n+=1
                        prefixes.append(prefix)
                    x=proc(text=[helper._build_text_prompt(context='',force_language=j['language'])+p for j,p in zip(group,prefixes)],
                        audio=[waves[j['source_id']][:j['audio_end_sample']] for j in group],padding=True,return_tensors='pt')
                    ids={k:tensor(v) for k,v in x.items()}
                    for i,j,r in available:
                        m=r['model_input_audit'];assert m['batch_tensors']==ids and m['rollback_prefix']==prefixes[i]
                        assert m['input_ids']==x['input_ids'][i].tolist()
                        if j['prompt_tokens'] and prefixes[i]:consumed+=1
                        z=r['token_ids'];raw=prefixes[i]+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                        p=tok.encode(raw);_,y=parse_asr_output(raw,user_language=j['language'])
                        assert p==r['state_tokens'] and y==r['text'];checked+=1
                else:
                    for i,j,r in available:
                        m=r['model_input_audit'];history=tok.decode(j['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
                        prompt=proc.get_prompt_ids(history,return_tensors='pt').tolist() if history else []
                        assert m['history']==history and m['prompt_ids']==prompt
                        if prompt:assert m['actual_first_decoder_ids'][:len(prompt)]==prompt;consumed+=1
                        wave=waves[j['source_id']][j['chunk_id']*32000:j['audio_end_sample']]
                        x=proc(wave,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
                        assert sha(x.input_features.numpy().tobytes())==m['input_features_sha256']
                        dtype=torch.float32 if m['dtype']=='float32' else torch.float16
                        assert sha(x.input_features.to(dtype=dtype).float().numpy().tobytes())==m['actual_gpu_features_sha256']
                        assert m['full_decoder_sequence'][len(m['actual_first_decoder_ids']):]==r['token_ids']
                        segment=tok.decode(r['token_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
                        y=(history+' '+segment).strip() if history else segment.strip()
                        assert tok.encode(y,add_special_tokens=False)==r['state_tokens'] and y==r['text'];checked+=1
                batches+=1
            # Synthetic corruption remains explicitly separate from original
            # neural rows; only the following job can claim GPU consumption.
            for jid,body in corrupt.items():
                j=jobs[jid];z=body['token_ids']
                if family=='whisper':
                    history=tok.decode(j['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
                    y=(history+' '+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)).strip()
                    assert tok.encode(y,add_special_tokens=False)==body['state_tokens']
                following=[r for r in results.values() if jobs[r['job_id']]['session_id']==j['session_id']
                    and jobs[r['job_id']]['role']=='proposal' and jobs[r['job_id']]['end_window']==4]
                assert len(following)==1
                aud=following[0]['model_input_audit'];text=aud['history'] if family=='whisper' else aud['rollback_prefix']
                assert 'violet saturn alder' in text.casefold(),'injected feedback was not actually realized in following input'
        allruns.append(dict(episode=name,adapter=family,original_neural_completed_rows_CPU_replayed=checked,
            physical_input_groups_reprocessed=batches,actual_nonempty_feedback_consumptions=consumed,
            unfinished_jobs_without_neural_receipt=unknown,controlled_synthetic_injections=len(corrupt),WAL=wa))
    dest.write_text(json.dumps(dict(status='PASS_READ_ONLY_WAL_AND_CPU_ACTUAL_INPUT_RENDER_REPLAY',runs=allruns,
        new_neural_calls=0,scope='actual input/complete-result records; CPU preprocessing is not another GPU experiment'),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',episodes=len(allruns),rows=sum(r['original_neural_completed_rows_CPU_replayed'] for r in allruns))))
if __name__=='__main__':main()
