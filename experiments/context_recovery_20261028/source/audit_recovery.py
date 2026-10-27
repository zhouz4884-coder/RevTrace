"""Native same-job asset/input/render audit and independent recovery clocks.

No model weights are loaded, no generation or admission function is invoked.
Re-rendering each recorded Z under its actual frozen parent is validation only.
"""
from pathlib import Path
import argparse,hashlib,importlib.metadata,inspect,json,os,platform,struct,sys,time,traceback


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4194304),b''):h.update(b)
    return h.hexdigest()


def frames(path):
    data=Path(path).read_bytes();offset=0;previous='';rows=[]
    while offset<len(data):
        assert offset+4<=len(data),'torn committed frame'
        n=struct.unpack_from('>I',data,offset)[0];end=offset+4+n+32
        assert 0<n<=32*1024*1024 and end<=len(data)
        body=data[offset+4:offset+4+n];s=hashlib.sha256(body).digest()
        assert s==data[offset+4+n:end]
        row=json.loads(body);assert row['sequence']==len(rows) and row['previous_sha256']==previous
        previous=s.hex();rows.append(row);offset=end
    return rows


def lines(path,partial=False):
    raw=Path(path).read_bytes();out=[]
    for i,b in enumerate(raw.splitlines(keepends=True)):
        try:out.append(json.loads(b))
        except (ValueError,UnicodeDecodeError):
            assert partial and i==len(raw.splitlines())-1 and not b.endswith(b'\n')
    return out


def rollback(tok,job):
    raw=tok.decode(job['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
    if job['chunk_id']<2 or not raw:return ''
    ids=tok.encode(raw);k=5
    while True:
        prefix=tok.decode(ids[:max(0,len(ids)-k)])
        if '\ufffd' not in prefix or k>=len(ids):return prefix
        k+=1


def render(tok,parser,job,z,eos,budget=256):
    assert 0<len(z)<=budget
    positions=[i for i,t in enumerate(z) if t in eos]
    assert positions==[len(z)-1] if positions else len(z)==budget
    raw=rollback(tok,job)+tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    _,text=parser(raw,user_language=job['language'])
    return list(tok.encode(raw)),text


def clocks(directory):
    D=Path(directory);kill=json.loads((D/'KILL.json').read_text());at=kill['kill_perf']
    history=frames(D/'canonical.wal.pre-recovery')
    F={int(k):v['audio_frontier_window'] for k,v in history[0]['states'].items()}
    for r in history[1:]:
        if r['kind']=='commit':F[r['session_id']]=r['state_delta']['audio_end_sample']
    A={int(k):v for k,v in json.loads((D/'FAULT_CUT.json').read_text())['accepted_frontiers'].items()}
    views=lines(D/'attempt1/consumer.jsonl')
    old=[min(v['observed_perf'] for v in views if v['session_id']==sid and v['certified_frontier']>=f) for sid,f in F.items() if f]
    fresh=[v['observed_perf'] for v in views if v['certified_frontier']>F[v['session_id']]]
    debt=[min(v['observed_perf'] for v in views if v['session_id']==sid and v['certified_frontier']>=A[sid]) for sid,f in F.items() if A[sid]>f]
    assert all(t>=at for t in old+fresh+debt)
    return dict(RTO_old_all_durable_facts=max(old)-at if old else None,RTO_new_first_certified_fact=min(fresh)-at if fresh else None,RTO_precrash_accepted_debt=max(debt)-at if debt else None)


def tensor_identity(x):
    a=x.detach().cpu().contiguous()
    return dict(shape=list(a.shape),dtype=str(a.dtype),sha256=hashlib.sha256(a.numpy().tobytes()).hexdigest())


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--runtime-source',type=Path,required=True)
    p.add_argument('--runtime-manifest',type=Path,required=True);p.add_argument('--descriptor',type=Path,required=True)
    p.add_argument('--analysis-manifest',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists();a.out.mkdir(parents=True)
    source=json.loads(a.analysis_manifest.read_text())
    for f in source['files']:assert digest(Path(__file__).parent/f['path'])==f['sha256']
    rt=json.loads(a.runtime_manifest.read_text())
    for f in rt['files']:assert digest(a.runtime_source/f['path'])==f['sha256']
    study=json.loads((a.study/'SUMMARY.json').read_text());assert len(study['completed'])==study['expected']==4
    env=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers','soundfile','numpy']})
    def put(name,x):(a.out/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    put('ENVIRONMENT.json',env)
    put('FREEZE.json',dict(experiment_id='REVTRACE-RECOVERY-NATIVE-ASSET-AUDIT-20261028',analysis_commit=source['code_commit'],analysis_manifest_sha256=digest(a.analysis_manifest),runtime_commit=rt['code_commit'],runtime_manifest_sha256=digest(a.runtime_manifest),descriptor_sha256=digest(a.descriptor),study_summary_sha256=digest(a.study/'SUMMARY.json'),environment_sha256=digest(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),evidence_tier='CPU_NATIVE_RECONSTRUCTION_OF_ACTUAL_GPU_RECORDS_ZERO_NEW_INFERENCE'))
    results=[]
    try:
        os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
        import torch,numpy as np,soundfile as sf
        from transformers import AutoProcessor,GenerationConfig
        from qwen_asr import Qwen3ASRModel,parse_asr_output
        torch.set_num_threads(2)
        proc=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=proc.tokenizer
        descriptor=json.loads(a.descriptor.read_text());contract=descriptor['render_contract']
        import qwen_asr
        package=Path(qwen_asr.__file__).resolve().parent
        actual_python={p.relative_to(package).as_posix():digest(p) for p in package.rglob('*.py')}
        assert actual_python==descriptor['package_files']
        for name,want in descriptor['packages'].items():assert importlib.metadata.version(name)==want
        for name,want in contract['assets'].items():assert digest(a.model/name)==want
        assert digest(inspect.getfile(type(proc)))==contract['processor_source_sha256']
        assert hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()==contract['parse_source_sha256']
        eos=GenerationConfig.from_pretrained(a.model,local_files_only=True).eos_token_id;eos={eos} if isinstance(eos,int) else set(eos)
        shell=Qwen3ASRModel.__new__(Qwen3ASRModel);shell.processor=proc
        bases={lang:shell._build_text_prompt(context='',force_language=lang) for lang in ('English','Chinese')}
        audio={}
        for r in json.loads((a.study/'manifest.json').read_text())['sessions']:
            x,rate=sf.read(r['path'],dtype='float32');assert rate==16000 and x.ndim==1
            x=np.asarray(x,dtype='<f4');assert hashlib.sha256(x.tobytes()).hexdigest()==r['audio_sha256'];audio[r['source_id']]=x
        for name in study['completed']:
            D=a.study/name;checked=0;observed_batches=0;durable=0
            weights=json.loads((a.study/'ENVIRONMENT.json').read_text())['model_weight_sha256']
            # Weights are checked once for this whole audit; they are not loaded.
            if not results:
                for filename,want in weights.items():assert digest(a.model/filename)==want
            for attempt in [0,1]:
                C=D/f'attempt{attempt}';submissions=[];outputs={}
                for path in sorted(C.glob('*.submissions')):submissions+=lines(path,attempt==0)
                for path in sorted(C.glob('worker-*-receipts.jsonl')):
                    for row in lines(path,attempt==0):
                        if row['kind']=='row-complete':
                            m=row['message'];assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
                            outputs[m['binding']['job_id']]=json.loads(m['payload_json'])
                for batch in submissions:
                    jobs=batch['jobs'];observed=[j for j in jobs if j['job_id'] in outputs]
                    if not observed:continue
                    prefixes=[rollback(tok,j) for j in jobs]
                    inp=proc(text=[bases[j['language']]+pre for j,pre in zip(jobs,prefixes)],audio=[audio[j['source_id']][:j['audio_end_sample']] for j in jobs],return_tensors='pt',padding=True)
                    hashes={k:tensor_identity(v) for k,v in inp.items()};observed_batches+=1
                    for i,j in enumerate(jobs):
                        if j['job_id'] not in outputs:continue
                        r=outputs[j['job_id']];audit=r['model_input_audit']
                        assert audit['batch_tensors']==hashes
                        assert audit['input_ids']==inp['input_ids'][i].tolist() and audit['attention_mask']==inp['attention_mask'][i].tolist()
                        P,text=render(tok,parse_asr_output,j,r['token_ids'],eos)
                        assert P==r['state_tokens'] and text==r['text'];checked+=1
            for record in frames(D/'canonical.wal'):
                if record['kind']!='commit':continue
                event=record['event'];binding=event['text_binding'];inputs=binding['render_inputs']
                P,text=render(tok,parse_asr_output,inputs,inputs['token_ids'],eos)
                assert P==inputs['state_tokens'] and text==event['committed_text']
                assert hashlib.sha256(text.encode()).hexdigest()==binding['text_sha256'];durable+=1
            times=clocks(D);original=json.loads((D/'AUDIT.json').read_text())['recovery']
            for k,v in times.items():assert v is not None and abs(v-original[k])<1e-7
            result=dict(cell=name,same_job_native_render_rows=checked,complete_batch_processed_input_reconstructions=observed_batches,durable_text_bindings=durable,recounted_clocks=times,actual_model_loads=0,new_GPU_inference=0)
            results.append(result);put('CELL_'+str(len(results))+'.json',result)
        put('RESULT.json',dict(status='PASS_NATIVE_ASSET_INPUT_RENDER_AND_CLOCK_RECOUNT',cells=results,scope='same-job CPU native reconstruction and direct Consumer clock recount; not new neural generation or proof of model truth'))
        put('GATE.json',dict(gate='PASS',analysis_commit=source['code_commit'],cells=len(results),new_GPU_inference=0))
    except BaseException:
        put('STOP.json',dict(completed=results,error=traceback.format_exc()));raise


if __name__=='__main__':main()
