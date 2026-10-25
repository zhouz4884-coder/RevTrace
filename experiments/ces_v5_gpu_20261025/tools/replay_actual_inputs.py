"""All physical peer batches, CPU tensor restaging/repeat only; no generation."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,sys
import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor
from qwen_asr import Qwen3ASRModel

def main():
    torch.set_num_threads(2)
    B=Path(sys.argv[1]);stage=sys.argv[2];O=B/'results/revtrace/ces_v5_20261025'
    terminal=json.loads((O/'SUMMARY.json').read_text())
    assert terminal['status']=='COMPLETE_BOUNDED_V5_GPU_PILOT_AND_AUDIT'
    D=O/(stage+'_processor_replay_v1');D.mkdir(exist_ok=False)
    proc=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True);tok=proc.tokenizer
    obj=object.__new__(Qwen3ASRModel);obj.processor=proc;bases={l:obj._build_text_prompt('',l) for l in ['English','Chinese']}
    waves={}
    manifests=[B/'datasets/revtrace/phaseD_20261021/manifest.json',B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json']
    for mp in manifests:
     for s in json.loads(mp.read_text())['sessions']:
        wave,sr=sf.read(s['path'],dtype='float32');assert sr==16000 and wave.ndim==1
        waves[s['source_id']]=np.asarray(wave,dtype='<f4')
    def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
    def identity(x):
        x=x.detach().cpu().contiguous()
        return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
    def prefix(j):
        prompt=j.get('fault_actual_prompt_tokens',j['prompt_tokens'])
        raw=tok.decode(prompt,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if j['chunk_id']<2 or not raw:return ''
        ids=tok.encode(raw);k=5
        while True:
            text=tok.decode(ids[:max(0,len(ids)-k)])
            if '\ufffd' not in text or k>=len(ids):return text
            k+=1
    cells=batches=rows=changed=0;hashes={}
    try:
        with (D/'PHYSICAL_INPUT_REPLAYS.jsonl').open('w') as stream:
            for C in sorted((O/stage).iterdir()):
                if not C.is_dir() or not (C/'result.json').exists():continue
                cfg=json.loads((C/'config.json').read_text());recs=lines(C/'worker_records.jsonl');accounts={}
                grouped=defaultdict(list)
                if cfg['result_delivery']=='row':
                    accounts={a['batch_id']:a for a in lines(C/'worker_batch_accounting.jsonl')}
                    byid={r['job']['job_id']:r for r in recs}
                    for bid,a in accounts.items():grouped[bid]=[byid[j] for j in a['job_ids']]
                else:
                    for r in recs:grouped[r['job']['role'],r['result']['started_perf'],r['result']['completed_perf']].append(r)
                assert sum(map(len,grouped.values()))==len(recs)
                hashes[C.name]={'worker_records_sha256':hashlib.sha256((C/'worker_records.jsonl').read_bytes()).hexdigest(),
                    'config_sha256':hashlib.sha256((C/'config.json').read_bytes()).hexdigest()}
                for key,rs in grouped.items():
                    ps=[prefix(r['job']) for r in rs]
                    ws=[waves[r['job']['source_id']][:r['job']['audio_end_sample']] for r in rs]
                    prompts=[bases[r['job']['language']]+p for r,p in zip(rs,ps)]
                    actual=proc(text=prompts,audio=ws,return_tensors='pt',padding=True)
                    repeat=proc(text=prompts,audio=ws,return_tensors='pt',padding=True)
                    ids={k:identity(v) for k,v in actual.items()}
                    assert ids=={k:identity(v) for k,v in repeat.items()}
                    for i,r in enumerate(rs):
                        j,z=r['job'],r['result'];a=z['model_input_audit']
                        assert a['rollback_prefix']==ps[i] and a['batch_rows']==len(rs)
                        assert a['batch_tensors']==ids and a['input_ids']==actual['input_ids'][i].tolist() and a['attention_mask']==actual['attention_mask'][i].tolist()
                        assert a['waveform_sha256']==hashlib.sha256(ws[i].tobytes()).hexdigest()
                    proof=accounts[key].get('verification_batch') if accounts else rs[0]['result'].get('online_verification')
                    if proof and proof.get('fallback_input_ids') is not None:
                        expected=[actual['input_ids'][i].tolist() for i in proof['fallback_row_indices']]
                        assert proof['fallback_input_ids']==expected
                        assert proof['fallback_executed_job_ids']==[rs[i]['job']['job_id'] for i in proof['fallback_row_indices']]
                    record={'cell':C.name,'physical_batch_id':str(key),'role':rs[0]['job']['role'],
                      'ordered_job_ids':[r['job']['job_id'] for r in rs],'physical_rows':len(rs),'input_tensor_identities':ids,
                      'CPU_same_input_repeat_exact':True,'all_observed_processed_inputs_exact':True,
                      'pre_dtype_cast_not_all_GPU_forward_attestation':True,'new_generation_calls':0}
                    stream.write(json.dumps(record,allow_nan=False)+'\n');batches+=1;rows+=len(rs)
                cells+=1;print('RESTAGED',C.name,len(grouped),flush=True)
        expected=48
        assert cells==expected
        (D/'INPUT_HASHES.json').write_text(json.dumps(hashes,indent=2)+'\n')
        out={'status':'PASS_ALL_ACTUAL_PHYSICAL_BATCH_INPUTS_CPU_RESTAGED','stage':stage,'cells':cells,'physical_batches':batches,
          'row_inputs':rows,'model_generation_calls':0,'CPU_repeat_exact':True,
          'scope':'CPU preprocessing repeats with original peer order/padding and actual F2 context; not GPU arithmetic equivalence or an extra neural oracle',
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
    except BaseException as e:
        (D/'STOP.json').write_text(json.dumps({'error':repr(e),'completed_cells':cells,'completed_physical_batches':batches,'raw_retained':True})+'\n');raise

if __name__=='__main__':main()
