"""Same-input/repeated GPU native API vs complete-result correctness oracle."""
import os,json,time,hashlib,sys
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='1';os.environ['OMP_NUM_THREADS']='2'
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/dependability_20261025'/P.name
import torch,soundfile as sf
from transformers import WhisperForConditionalGeneration,WhisperProcessor
torch.set_num_threads(2);assert not (O/'WHISPER_ORACLE.json').exists()
proc=WhisperProcessor.from_pretrained(B/'models/whisper-small.en',local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(B/'models/whisper-small.en',torch_dtype=torch.float32,
    attn_implementation='eager',local_files_only=True).to('cuda:0').eval()
rows=[]
for source in json.loads((P/'INDEPENDENT_MANIFEST_v1.json').read_text())['sessions'][:2]:
    x,sr=sf.read(source['path'],dtype='float32');assert sr==16000
    history=''
    for segment in range(2):
        a=x[segment*96000:(segment+1)*96000]
        inputs=proc(a,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        prompt=proc.get_prompt_ids(history,return_tensors='pt') if history else None
        kwargs=dict(input_features=inputs.input_features.to('cuda:0'),attention_mask=inputs.attention_mask.to('cuda:0'),
            max_new_tokens=256,return_timestamps=False,do_sample=False)
        if prompt is not None:kwargs['prompt_ids']=prompt.to('cuda:0')
        variants=[]
        for repeat in range(2):
            for complete in [False,True]:
                actual=[]
                def hook(_m,args,kw):
                    if not actual:actual.extend(kw['input_ids'].cpu().tolist())
                h=model.model.decoder.register_forward_pre_hook(hook,with_kwargs=True)
                began=time.perf_counter()
                with torch.inference_mode():out=model.generate(**kwargs,return_dict_in_generate=complete)
                torch.cuda.synchronize();end=time.perf_counter();h.remove()
                raw=out.sequences[0].cpu().tolist() if complete else out[0].cpu().tolist()
                z=raw[len(actual[0]):] if complete else raw
                variants.append(dict(complete=complete,repeat=repeat,Z=z,actual_first_decoder_ids=actual[0],
                    text=proc.tokenizer.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False),seconds=end-began))
        assert len({v['text'] for v in variants})==1,variants
        full=[v for v in variants if v['complete']]
        assert full[0]['Z']==full[1]['Z'] and full[0]['Z'][-1]==proc.tokenizer.eos_token_id
        if prompt is not None:assert all(v['actual_first_decoder_ids'][:len(prompt)]==prompt.tolist() for v in variants)
        rows.append(dict(source=source['source_id'],segment=segment,history=history,variants=variants))
        history=(history+' '+variants[0]['text']).strip()
(O/'WHISPER_ORACLE.json').write_text(json.dumps(dict(status='PASS_REAL_GPU_SAME_INPUT_REPEAT_COMPLETE_RESULT_NATIVE_TEXT',
    cases=rows,neural_calls=16,scope='two sources, two consecutive intervals, both API forms repeated; no serving performance claim'),indent=2)+'\n')
print(json.dumps(dict(status='PASS',neural_calls=16)))
