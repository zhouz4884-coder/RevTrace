"""CPU asset-backed re-render and exact physical-batch input reprocessing.

No model weights are loaded, no neural generation or CUDA operation is called.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='2';os.environ['TOKENIZERS_PARALLELISM']='false'

def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tensor(x):
    y=x.detach().cpu().contiguous()
    return {'shape':list(y.shape),'dtype':str(y.dtype),'sha256':hashlib.sha256(y.numpy().tobytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    import numpy as np,soundfile as sf,torch
    from transformers import AutoProcessor
    from qwen_asr import Qwen3ASRModel,parse_asr_output
    torch.set_num_threads(2)
    processor=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=processor.tokenizer
    sources={}
    for s in read(a.manifest)['sessions']:
        wave,rate=sf.read(s['path'],dtype='float32');assert rate==16000 and wave.ndim==1
        sources[s['source_id']]=np.asarray(wave,dtype='<f4')
        assert hashlib.sha256(sources[s['source_id']].tobytes()).hexdigest()==s['audio_sha256']
    # The class helper also calls its own message builder. Allocate no model:
    # __new__ supplies methods while avoiding __init__/weights/device setup.
    prompt_helper=object.__new__(Qwen3ASRModel);prompt_helper.processor=processor
    bases={lang:prompt_helper._build_text_prompt(context='',force_language=lang) for lang in ['English','Chinese']}
    out=[]
    for name in read(a.stage/'SUMMARY.json')['completed']:
        C=a.stage/name/'attempt0';cfg=read(C/'config.json');assets=cfg['authority_runtime']['render_contract']
        for key,value in assets['assets'].items():assert sha(a.model/key)==value
        assert hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()==assets['parse_source_sha256']
        rec={r['job']['job_id']:r for r in rows(C/'worker_records.jsonl')};prefixes={}
        for jid,r in rec.items():
            j=r['job'];z=r['result']['token_ids'];result=r['result'];m=result['model_input_audit']
            assert z and len(z)<=m['max_new_tokens'];eos=set(m['eos_token_ids'])
            stops=[i for i,t in enumerate(z) if t in eos]
            assert stops==[len(z)-1] or (not stops and len(z)==m['max_new_tokens'])
            raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
            prefix=''
            if j['chunk_id']>=2 and raw:
                ids=tok.encode(raw);k=5
                while True:
                    prefix=tok.decode(ids[:max(0,len(ids)-k)])
                    if '\ufffd' not in prefix or k>=len(ids):break
                    k+=1
            assert prefix==m['rollback_prefix'];prefixes[jid]=prefix
            text_raw=prefix+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            P=tok.encode(text_raw);_,text=parse_asr_output(text_raw,user_language=j['language'])
            assert P==result['state_tokens'] and text.encode()==result['text'].encode()
        batches=[e for e in rows(C/'events.jsonl') if e['kind']=='worker-status' and e.get('status')=='batch-started']
        checked=set()
        for b in batches:
            ids=b['job_ids'];assert not checked.intersection(ids);checked.update(ids)
            jobs=[rec[j]['job'] for j in ids]
            wave=[sources[j['source_id']][:j['audio_end_sample']] for j in jobs]
            text=[bases[j['language']]+prefixes[j['job_id']] for j in jobs]
            tensors=processor(text=text,audio=wave,return_tensors='pt',padding=True)
            identities={k:tensor(v) for k,v in tensors.items()}
            for i,jid in enumerate(ids):
                m=rec[jid]['result']['model_input_audit']
                assert identities==m['batch_tensors'],(C.name,jid,'reprocessed full batch differs')
                assert tensors['input_ids'][i].tolist()==m['input_ids']
                assert tensors['attention_mask'][i].tolist()==m['attention_mask']
        assert checked==set(rec)
        out.append({'cell':name,'rendered_complete_rows':len(rec),'exact_reprocessed_physical_batches':len(batches)})
    a.output.write_text(json.dumps({'status':'PASS_CPU_ASSET_RENDER_AND_FULL_BATCH_REPROCESS',
        'runs':out,'new_neural_GPU_calls':0,'scope':'CPU deterministic processor/adapter replay of actual recorded input layouts; not a neural oracle'},indent=2)+'\n')
    print(a.output.read_text())
if __name__=='__main__':main()
