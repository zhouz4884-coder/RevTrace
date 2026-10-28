"""Fresh-process CPU conformance, not a model or serving measurement."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,platform,random,shutil,struct,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from revtrace.light_render import file_sha,canonical_sha,FORBIDDEN_IMPORTS


def put(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def lines(p,partial=False):
    raw=p.read_bytes();out=[];parts=raw.splitlines(keepends=True)
    for i,b in enumerate(parts):
        try:out.append(json.loads(b))
        except (ValueError,UnicodeDecodeError):
            assert partial and i==len(parts)-1 and not b.endswith(b'\n')
    return out


def frames(p):
    data=p.read_bytes();pos=0;prev='';out=[]
    while pos<len(data):
        assert len(data)-pos>=4;n=struct.unpack_from('>I',data,pos)[0];end=pos+4+n+32
        assert 0<n<=32*1024*1024 and end<=len(data)
        raw=data[pos+4:pos+4+n];digest=hashlib.sha256(raw).digest();assert digest==data[pos+4+n:end]
        r=json.loads(raw);assert r['sequence']==len(out) and r['previous_sha256']==prev
        out.append(r);prev=digest.hex();pos=end
    return out


def build_bank(recovery,operators):
    bank=[];inputs=[]
    def observe(path):inputs.append(dict(path=str(path),sha256=file_sha(path)))
    summary=json.loads((recovery/'SUMMARY.json').read_text());assert len(summary['completed'])==4
    observe(recovery/'SUMMARY.json')
    for cell in summary['completed']:
        D=recovery/cell
        for attempt in [0,1]:
            C=D/f'attempt{attempt}';jobs={}
            for p in sorted(C.glob('*.submissions')):
                observe(p)
                for batch in lines(p,partial=attempt==0):
                    for j in batch['jobs']:jobs[j['job_id']]=j
            for p in sorted(C.glob('worker-*-receipts.jsonl')):
                observe(p)
                for r in lines(p,partial=attempt==0):
                    if r['kind']!='row-complete':continue
                    m=r['message'];assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
                    v=json.loads(m['payload_json']);j=jobs[v['job_id']]
                    bank.append(dict(id=f'{cell}/attempt{attempt}/{v["job_id"]}',tier='observed-GPU-row',job=j,Z=v['token_ids'],P=v['state_tokens'],text=v['text']))
        observe(D/'canonical.wal')
        for r in frames(D/'canonical.wal'):
            if r['kind']!='commit':continue
            e=r['event'];x=e['text_binding']['render_inputs']
            bank.append(dict(id=f'{cell}/wal/{r["sequence"]}',tier='durable-bound-text',job=x,Z=x['token_ids'],P=x['state_tokens'],text=e['committed_text']))
    for p in sorted(operators.glob('[01][01]-*-r[01].json')):
        observe(p);r=json.loads(p.read_text());jobs={j['job_id']:j for j in r['jobs']}
        for jid,v in r['rows'].items():bank.append(dict(id=p.name+'/'+jid,tier='paid-own-input-operator',job=jobs[jid],Z=v['token_ids'],P=v['state_tokens'],text=v['text']))
    assert len([r for r in bank if r['tier']=='observed-GPU-row'])==184
    assert len([r for r in bank if r['tier']=='durable-bound-text'])==56
    assert len([r for r in bank if r['tier']=='paid-own-input-operator'])==28
    return dict(schema='qwen-render-own-input-bank-v1',cases=bank,source_files=inputs,scope='same-job replay only; no new generation or service credit')


def worker(a):
    source=json.loads(a.source_manifest.read_text())
    assert subprocess.check_output(['git','-C',str(a.source_root),'rev-parse','HEAD'],text=True).strip()==source['code_commit']
    assert not subprocess.check_output(['git','-C',str(a.source_root),'status','--porcelain'],text=True).strip()
    for r in source['files']:assert file_sha(a.source_root/r['path'])==r['sha256']
    assert not a.out.exists();a.out.mkdir(parents=True)
    d=json.loads((a.bundle/'descriptor.json').read_text());assert file_sha(a.bundle/'descriptor.json')==a.descriptor_sha256
    bank=json.loads(a.bank.read_text());assert file_sha(a.bank)==a.bank_sha256
    environment=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']})
    put(a.out/'ENVIRONMENT.json',environment)
    put(a.out/'FREEZE.json',dict(experiment_id='REVTRACE-RENDER-CONFORMANCE-'+a.worker.upper()+'-20261028',source_commit=source['code_commit'],source_manifest_sha256=file_sha(a.source_manifest),config=a.config_metadata,descriptor_sha256=a.descriptor_sha256,bank_sha256=a.bank_sha256,environment_sha256=file_sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),GPU_inference_calls=0))
    before={n:any(x==n or x.startswith(n+'.') for x in sys.modules) for n in FORBIDDEN_IMPORTS};start=time.perf_counter()
    try:
        if a.worker=='negative':
            from revtrace.light_render import load_light_context
            observed=[]
            for name in ['descriptor-bytes','program-bytes','wrong-version','wrong-loader','wrong-helper','missing-assets','unsupported-special-mode']:
                fixture=a.out/name;fixture.mkdir();copy=dict(d);package=a.package_root;model=a.model
                shutil.copyfile(a.bundle/d['program_file'],fixture/d['program_file'])
                if name=='program-bytes':
                    with (fixture/d['program_file']).open('ab') as f:f.write(b' ')
                elif name=='wrong-version':copy['packages']={**d['packages'],'tokenizers':'invalid-fixture'}
                elif name=='wrong-loader':copy['light_module_sha256']='0'*64
                elif name=='unsupported-special-mode':copy['encode_special_tokens']='false'
                elif name=='missing-assets':model=fixture/'empty-model';model.mkdir()
                elif name=='wrong-helper':
                    package=fixture/'package'
                    for rel in d['qwen_package_python']:
                        target=package/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.package_root/rel,target)
                    with (package/'inference/utils.py').open('a') as f:f.write('\n# changed helper fixture\n')
                put(fixture/'descriptor.json',copy);expected=file_sha(fixture/'descriptor.json')
                if name=='descriptor-bytes':
                    with (fixture/'descriptor.json').open('ab') as f:f.write(b' ')
                try:load_light_context(fixture,expected_descriptor_sha256=expected,model=model,package_root=package)
                except ValueError as e:observed.append(dict(case=name,rejected_before_replay=True,error=str(e)))
                else:raise AssertionError('negative loader did not fail closed:'+name)
            after={n:any(x==n or x.startswith(n+'.') for x in sys.modules) for n in FORBIDDEN_IMPORTS};assert not any(after.values())
            put(a.out/'RESULT.json',dict(status='PASS_NEGATIVE_LOADER_CONTROLS',rows=observed,modules_after=after,GPU_inference_calls=0));put(a.out/'GATE.json',dict(gate='PASS_NEGATIVE_COMPONENT_CONTROLS',cases=len(observed),GPU_inference_calls=0));return
        if a.worker=='native':
            from revtrace.startup_overlap import load_native_qwen_context
            c=load_native_qwen_context(a.model);assert c.contract==d['native_reference_contract'];tok,parse=c.processor.tokenizer,c.parse
            tok.encode('');backend=tok.backend_tokenizer
        else:
            from revtrace.light_render import load_light_context
            c=load_light_context(a.bundle,expected_descriptor_sha256=a.descriptor_sha256,model=a.model,package_root=a.package_root);tok,parse=c.tokenizer,c.parse;backend=tok._backend
        assert canonical_sha(json.loads(backend.to_str()))==d['native_default_backend_sha256']
        assert backend.encode_special_tokens==d['encode_special_tokens']
        from revtrace.certified_display import TrustedQwenRender
        gen=json.loads((a.model/'generation_config.json').read_text());eos=gen['eos_token_id'];eos=[eos] if type(eos) is int else eos;render=TrustedQwenRender(tok,parse,eos,256)
        load_seconds=time.perf_counter()-start
        records=[];start=time.perf_counter()
        for r in bank['cases']:
            P,text=render(r['job'],r['Z']);assert P==r['P'] and text.encode()==r['text'].encode(),r['id']
            records.append(dict(id=r['id'],P_sha256=canonical_sha(P),text_sha256=hashlib.sha256(text.encode()).hexdigest()))
        replay_seconds=time.perf_counter()-start
        # Exhaustive single-token decoding under both actual skip modes. The
        # backend identity supplies more than the bounded random encode controls.
        ids=sorted(set(backend.get_vocab(with_added_tokens=True).values()));vocab_blocks=[]
        for lo in range(0,len(ids),512):
            data=[[i,tok.decode([i],skip_special_tokens=False,clean_up_tokenization_spaces=False),tok.decode([i],skip_special_tokens=True,clean_up_tokenization_spaces=False)] for i in ids[lo:lo+512]]
            vocab_blocks.append(dict(first_id=ids[lo],count=len(data),sha256=canonical_sha(data)))
        rng=random.Random(20261028);valid=[i for i in ids if i not in eos];synthetic=[]
        for i in range(4096):
            prompt=[rng.choice(ids) for _ in range(rng.randrange(129))]
            z=[rng.choice(valid) for _ in range(rng.randrange(65))]+[eos[i%len(eos)]]
            j=dict(prompt_tokens=prompt,chunk_id=i%6,language=['English','Chinese',None,''][i%4])
            P,text=render(j,z);raw=tok.decode(prompt,skip_special_tokens=False,clean_up_tokenization_spaces=False)
            synthetic.append(canonical_sha(dict(P=P,text=text,reencoded=tok.encode(raw))))
        parser_results=[parse(x,user_language=lang) for x in [None,'','language Chinese<asr_text>你好','language None<asr_text>','x'*30,('abcde '*25),'language English\n<asr_text> hi','a\ufffdb😀'] for lang in [None,'English','Chinese','']]
        capP,capText=render(dict(prompt_tokens=[],chunk_id=0,language='English'),[valid[0]]*256)
        rejected=[]
        for z in [[],[1],[eos[0],1],[1]*257]:
            try:render(dict(prompt_tokens=[],chunk_id=0,language='English'),z)
            except ValueError:rejected.append(True)
            else:rejected.append(False)
        assert all(rejected)
        after={n:any(x==n or x.startswith(n+'.') for x in sys.modules) for n in FORBIDDEN_IMPORTS}
        if a.worker=='light':assert not any(before.values()) and not any(after.values()),after
        result=dict(status='PASS_CPU_CONFORMANCE_OPERATIONS',worker=a.worker,load_seconds=load_seconds,replay_seconds=replay_seconds,case_count=len(records),records=records,record_digest=canonical_sha(records),vocab_ids=len(ids),vocab_blocks=vocab_blocks,vocab_digest=canonical_sha(vocab_blocks),random_cases=len(synthetic),synthetic_digest=canonical_sha(synthetic),parser_digest=canonical_sha(parser_results),valid_budget_termination_digest=canonical_sha([capP,capText]),invalid_stop_rejected=rejected,modules_before=before,modules_after=after,model_weights_loaded=0,GPU_inference_calls=0,scope='CPU conformance and component load clocks only; not serving RTO')
        put(a.out/'RESULT.json',result);put(a.out/'GATE.json',dict(gate='PASS_CPU_COMPONENT_NOT_SERVING',source_commit=source['code_commit'],records=len(records),GPU_inference_calls=0));print(json.dumps({k:v for k,v in result.items() if k not in ['records','vocab_blocks']}),flush=True)
    except BaseException:
        put(a.out/'STOP.json',dict(error=traceback.format_exc(),GPU_inference_calls=0));raise


def compare(a):
    source=json.loads(a.source_manifest.read_text())
    for r in source['files']:assert file_sha(a.source_root/r['path'])==r['sha256']
    assert not a.out.exists();a.out.mkdir(parents=True)
    inputs={'native':a.compare_native,'light':a.compare_light,'negative':a.compare_negative}
    results={k:json.loads(p.read_text()) for k,p in inputs.items()}
    put(a.out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform()))
    put(a.out/'FREEZE.json',dict(experiment_id='REVTRACE-RENDER-PROGRAM-INDEPENDENT-COMPARISON-20261028',source_commit=source['code_commit'],source_manifest_sha256=file_sha(a.source_manifest),input_sha256={k:file_sha(v) for k,v in inputs.items()},environment_sha256=file_sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),GPU_inference_calls=0))
    fields=['case_count','record_digest','vocab_ids','vocab_digest','random_cases','synthetic_digest','parser_digest','valid_budget_termination_digest','invalid_stop_rejected']
    mismatches=[k for k in fields if results['native'].get(k)!=results['light'].get(k)]
    ok=(not mismatches and results['native']['status']==results['light']['status']=='PASS_CPU_CONFORMANCE_OPERATIONS'
        and results['negative']['status']=='PASS_NEGATIVE_LOADER_CONTROLS'
        and not any(results['light']['modules_before'].values()) and not any(results['light']['modules_after'].values()))
    result=dict(gate='GO_CPU_COMPONENT_CONFORMANCE_NOT_SERVING_RTO' if ok else 'NO_GO_CONFORMANCE_MISMATCH_PRESERVED',source_commit=source['code_commit'],mismatched_fields=mismatches,matched_fields=fields if ok else [],case_count=results['light'].get('case_count'),vocab_ids=results['light'].get('vocab_ids'),random_cases=results['light'].get('random_cases'),negative_cases=len(results['negative']['rows']),native_load_seconds=results['native'].get('load_seconds'),light_load_seconds=results['light'].get('load_seconds'),GPU_inference_calls=0,scope='conditional component equivalence and bounded conformance; does not change old WAL contract or establish deployed RTO/whole-program refinement')
    put(a.out/'RESULT.json',result);put(a.out/'GATE.json',result);print(json.dumps(result),flush=True)
    if not ok:raise RuntimeError('renderer conformance did not pass')


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',choices=['native','light','negative']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',type=Path);p.add_argument('--bundle',type=Path);p.add_argument('--descriptor-sha256');p.add_argument('--package-root',type=Path)
    p.add_argument('--bank',type=Path);p.add_argument('--bank-sha256');p.add_argument('--source-root',type=Path);p.add_argument('--source-manifest',type=Path)
    p.add_argument('--compare-native',type=Path);p.add_argument('--compare-light',type=Path);p.add_argument('--compare-negative',type=Path)
    p.add_argument('--build-bank-recovery',type=Path);p.add_argument('--build-bank-operators',type=Path);a=p.parse_args()
    if a.worker:
        # argparse paths are metadata, not a JSON encoder extension.
        a.config_metadata={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()}
        worker(a)
    elif a.compare_native:compare(a)
    else:put(a.out,build_bank(a.build_bank_recovery,a.build_bank_operators))


if __name__=='__main__':main()
