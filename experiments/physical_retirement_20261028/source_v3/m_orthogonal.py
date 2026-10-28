"""Real proposal/authority IPC, structured state install and neural consumption.

New application path, NOT an exploit in ER1 or LangGraph. Only proposal return
can be coherently substituted. Trust-role bindings are host pipe ownership,
not cryptographic GPU attestation. All abstentions remain denominator entries.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');os.environ['HF_HUB_OFFLINE']='1'
from pathlib import Path
import sys,json,time,hashlib,argparse,multiprocessing as mp,traceback,subprocess,copy
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from memory_app import ProjectStore,MemoryKernelAdapter,sha,canonical
from memory_gpu_pilot import Neural,Power
from content_fault import replace_value_tokens,parse_json_memory
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
METHODS=['occ-only','trusted-regenerate-occ','standard-strict-occ','revtrace-strict']
CONDITIONS=['current-clean','current-coherent','stale-clean','stale-coherent']
def put(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def messages(task,snapshot):
    return [dict(role='system',content='Copy the current project fields from the source documents. Return only JSON with exactly string keys destination and owner. Copy the IDs exactly, without explanation.'),
        dict(role='user',content='Project '+task['project']+'\n'+'\n'.join(d['text'] for d in snapshot['docs']))]
def answer_messages(memory):
    return [dict(role='system',content='Copy the stored memory fields exactly. Return only JSON with string keys destination and owner. Never change an ID.'),
        dict(role='user',content='Stored memory: '+canonical(memory)+'\nWhich destination and owner IDs should the next request use?')]

def worker(pipe,role,device):
    import torch
    torch.set_num_threads(3);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
    try:
        N=Neural(B/'models/Qwen2.5-1.5B-Instruct',device,torch.float32,96)
        # Preserve the provider's ORIGINAL generation contract. Raw argmax is
        # not the actual selector when repetition_penalty=1.1 is configured.
        gc=N.model.generation_config
        for key,wanted in [('no_repeat_ngram_size',0),('encoder_repetition_penalty',1.),('num_beams',1),('min_length',0)]:
            assert getattr(gc,key,wanted)==wanted,'unsupported nontrivial selector '+key
        for key in ['bad_words_ids','forced_bos_token_id','forced_eos_token_id','suppress_tokens','begin_suppress_tokens','sequence_bias']:
            assert not getattr(gc,key,None),'unsupported nontrivial selector '+key
        from transformers import RepetitionPenaltyLogitsProcessor
        repetition=RepetitionPenaltyLogitsProcessor(gc.repetition_penalty) if gc.repetition_penalty!=1 else None
        N.contract['effective_selection']=dict(do_sample=False,repetition_penalty=gc.repetition_penalty,
            eos_token_id=gc.eos_token_id,max_new_tokens=96)
        pipe.send(dict(stage='ready',role=role,contract=N.contract));seq=0
        while True:
            cmd=pipe.recv()
            if cmd['op']=='close':break
            jid=cmd['job_id'];purpose=cmd['purpose'];seq+=1
            if cmd['op']=='prepare':
                pipe.send(dict(stage='prepared',role=role,job_id=jid,request=N.prepare(cmd['messages'])));continue
            request=cmd['request'];pipe.send(dict(stage='started',role=role,job_id=jid,purpose=purpose,observed_perf=time.perf_counter()))
            if cmd['op']=='generate':r=N.generate(request)
            elif cmd['op']=='verify' and role=='authority':
                z=cmd['candidate'];eos=N.model.generation_config.eos_token_id;eos={eos} if isinstance(eos,int) else set(eos)
                assert z and len(z)<=96 and [i for i,t in enumerate(z) if t in eos]==[len(z)-1]
                t=torch;x=t.tensor([request['input_ids']+z],device='cuda:'+str(device));L=len(request['input_ids']);N.observed=None
                def slice_head(_m,args):return (args[0][:,L-1:L+len(z)-1,:],)
                hook=N.model.lm_head.register_forward_pre_hook(slice_head);t.cuda.synchronize(device);st=time.perf_counter()
                try:
                    with t.inference_mode():logits=N.model(input_ids=x,attention_mask=t.ones_like(x),use_cache=False,return_dict=True).logits
                    assert bool(t.isfinite(logits).all());rawpred=logits.argmax(-1)[0].cpu().tolist();pred=[]
                    for i in range(len(z)):
                        scores=logits[:,i,:].clone()
                        if repetition is not None:scores=repetition(x[:,:L+i],scores)
                        pred.append(int(scores.argmax(-1)[0]))
                    t.cuda.synchronize(device)
                finally:hook.remove()
                en=time.perf_counter();assert N.observed==[request['input_ids']+z]
                ok=pred==z;r=dict(request=request,request_identity=request['identity'],actual_first_input_ids=N.observed[0],
                    new_tokens=z,decoded=N.tokenizer.decode(z,skip_special_tokens=True),terminated_by_eos=True,
                    value=parse_json_memory(N.tokenizer.decode(z,skip_special_tokens=True)),accepted=ok,predicted=pred,raw_unprocessed_predicted=rawpred,
                    selection_processor=dict(kind='HF RepetitionPenaltyLogitsProcessor',penalty=gc.repetition_penalty,applied_to_actual_prefix_at_each_position=True),
                    started_perf=st,completed_perf=en,actual_gpu_seconds=en-st,device=device,operation='full_correct_context_verification')
            elif cmd['op']=='encode' and role=='proposal':
                e=N.model.generation_config.eos_token_id;es={e} if isinstance(e,int) else set(e)
                if 'content_only_original' in cmd:
                    z,control=replace_value_tokens(N.tokenizer,cmd['content_only_original'],cmd['old_value'],cmd['new_value'],es)
                    r=dict(new_tokens=z,value=cmd['value'],decoded=control['decoded'],content_only_control=control)
                else:
                    z=N.tokenizer.encode(canonical(cmd['value']),add_special_tokens=False);z.append(e if isinstance(e,int) else e[0])
                    r=dict(new_tokens=z,value=cmd['value'],decoded=canonical(cmd['value']))
            else:raise ValueError('operation not permitted for physical pipe role')
            r.update(physical_worker_role=role,physical_job_id=jid,purpose=purpose,worker_sequence=seq)
            pipe.send(dict(stage='result',role=role,job_id=jid,purpose=purpose,result=r))
    except BaseException:pipe.send(dict(stage='failure',role=role,error=traceback.format_exc()));raise

class Actor:
    def __init__(self,ctx,role,device,log):
        self.role=role;self.pipe,child=ctx.Pipe();self.proc=ctx.Process(target=worker,args=(child,role,device));self.proc.start();child.close();self.log=log;self.pending=None;self.counter=0
        ready=self.receive();assert ready['stage']=='ready' and ready['role']==role;self.contract=ready['contract']
    def receive(self):
        assert self.pipe.poll(180),'bounded worker timeout';r=self.pipe.recv()
        if r['stage']=='failure':raise RuntimeError(r['error'])
        return r
    def prepare(self,m):
        assert self.pending is None;self.counter+=1;j=f'{self.role}-{self.counter}'
        self.pipe.send(dict(op='prepare',purpose='immutable-input',job_id=j,messages=m));r=self.receive();assert r['job_id']==j and r['stage']=='prepared';return r['request']
    def start(self,op,request,purpose,**kw):
        assert self.pending is None;self.counter+=1;self.pending=f'{self.role}-{self.counter}'
        self.pipe.send(dict(op=op,job_id=self.pending,request=request,purpose=purpose,**kw));r=self.receive();assert r['stage']=='started' and r['role']==self.role and r['job_id']==self.pending
        return r
    def finish(self):
        r=self.receive();assert r['stage']=='result' and r['job_id']==self.pending and r['role']==self.role
        self.pending=None;self.log.append(r['result']);return r['result']
    def call(self,op,request,purpose,**kw):self.start(op,request,purpose,**kw);return self.finish()
    def close(self):
        if self.proc.is_alive():self.pipe.send(dict(op='close'));self.proc.join(20)
        assert not self.proc.is_alive(),'own worker failed to exit cleanly'

def stable_tasks():
    old=json.loads((W/'MEMORY_TASKS_v4.json').read_text());tasks=[]
    for i,t in enumerate(old['tasks']):
        t=copy.deepcopy(t);t['source_documents']=[dict(key='destination',version=0,text=f'Current destination ID is LOC_{i:02d}_OLD.'),
            dict(key='owner',version=0,text=f'Current owner ID is OWN_{i:02d}.')]
        t['revision']=dict(key='destination',version=1,text=f'Current destination ID is LOC_{i:02d}_NEW. The old value has been superseded.')
        t['expected_old']=dict(destination=f'LOC_{i:02d}_OLD',owner=f'OWN_{i:02d}');t['expected_new']=dict(destination=f'LOC_{i:02d}_NEW',owner=f'OWN_{i:02d}')
        t['fault']=dict(destination=f'LOC_{i:02d}_FAULT',owner=f'OWN_{i:02d}')
        t['renderer']={f'LOC_{i:02d}_OLD':old['tasks'][i]['expected_old']['destination'],f'LOC_{i:02d}_NEW':old['tasks'][i]['expected_new']['destination'],
            f'LOC_{i:02d}_FAULT':'Fixed wrong destination',f'OWN_{i:02d}':old['tasks'][i]['expected_old']['owner']}
        tasks.append(t)
    return tasks

def episode(D,task,condition,method,rep,P,A,power,contract,records,preserve_return_format=False):
    D.mkdir();st=time.perf_counter();before=len(records);store=ProjectStore(D/'project.sqlite',task,st)
    adapter=MemoryKernelAdapter(store,contract) if method=='revtrace-strict' else None
    s0=store.snapshot();preq=P.prepare(messages(task,s0));started=P.start('generate',preq,'low-trust-proposal')
    revision=None
    if condition.startswith('stale'):
        if adapter:adapter.revise(task['revision'])
        else:store.revise(task['revision'])
        revision=time.perf_counter()
    original=P.finish();candidate=copy.deepcopy(original)
    if condition.endswith('coherent'):
        extra=dict(content_only_original=original['new_tokens'],old_value=original['value']['destination'],new_value=task['fault']['destination']) if preserve_return_format else {}
        value=dict(original['value'],destination=task['fault']['destination']) if preserve_return_format else task['fault']
        candidate=P.call('encode',preq,'controlled-proposal-return-substitution',value=value,**extra)
        candidate.update(request_identity=original['request_identity'],substitution_only_on_low_trust_pipe=True)
    candidate['self_checksum']=sha(dict(tokens=candidate['new_tokens'],value=candidate['value']))
    current=store.snapshot();expected=task['expected_new'] if condition.startswith('stale') else task['expected_old']
    verify=None;selected=None;fallback=False;installed=False
    if method=='occ-only':
        installed=store.install(candidate['value'],s0['readset'],dict(kind='OCC-only-no-content-authorization',checksum=candidate['self_checksum']),True)
    else:
        req=A.prepare(messages(task,current));job=adapter.dispatch(current,req) if adapter else None
        if method=='trusted-regenerate-occ':selected=A.call('generate',req,'trusted-state-selection')
        else:
            verify=A.call('verify',req,'trusted-state-selection',candidate=candidate['new_tokens'])
            if verify['accepted']:selected=verify
            else:fallback=True;selected=A.call('generate',req,'trusted-state-selection-fallback')
        assert selected['physical_worker_role']=='authority' and selected['request_identity']==req['identity']
        if adapter:adapter.complete(job,selected);installed=adapter.install(job,selected)
        else:installed=store.install(selected['value'],current['readset'],dict(kind='actual-authority-selection',job=selected['physical_job_id'],request=req['identity']),True)
        assert installed
    memory=store.memory();answer=None;current_available=memory is not None and memory['readset']==store.snapshot()['readset']
    if memory is not None:
        answer=A.call('generate',A.prepare(answer_messages(memory['value'])),'read-only-neural-consumer-no-state-write')
        assert answer['purpose']=='read-only-neural-consumer-no-state-write'
    end=time.perf_counter();result=dict(task=task['id'],split=task['split'],condition=condition,method=method,repeat=rep,
        old_snapshot=s0,current_snapshot=store.snapshot(),proposal=original,returned_candidate=candidate,
        proposal_started=started,revision_perf=revision,verification=verify,selected=selected,actual_fallback=fallback,
        installed=installed,current_result_available=current_available,explicit_unfulfilled=memory is None,
        stored_memory=memory,actual_neural_consumer=answer,task_exact_correct=bool(answer) and answer['value']==expected,
        memory_correct=bool(memory) and memory['value']==expected,provenance_not_truth=True,
        authority_content_error=selected is not None and selected['value']!=expected,
        unauthorized_candidate_admitted=condition.endswith('coherent') and installed and method=='occ-only',
        original_candidate_versions_current=s0['readset']==store.snapshot()['readset'],expected=expected,
        rendered_memory={k:task['renderer'].get(v,'UNKNOWN-ID') for k,v in memory['value'].items()} if memory else None,
        wall_seconds=end-st,measured_both_GPU_joules=power.joules(st,end),actual_calls=len(records)-before,
        fsync_scope='SQLite synchronous FULL docs/input/memory/journal; actual wall and all model work charged',
        kernel_trace=adapter.k.trace if adapter else None,
        evidence='controlled real GPU actor/SQLite application; no network serving/natural prevalence/framework vulnerability claim')
    put(D/'RESULT.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    log=[];rows=[];actors=[];power=None
    try:
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
        for f in source['files']:assert hashlib.sha256((W/f['path']).read_bytes()).hexdigest()==f['sha256']
        tasks=stable_tasks();put(a.out/'FREEZE.json',dict(source=source,tasks=tasks,methods=METHODS,conditions=CONDITIONS,
            development_repeats=1,validation_repeats=2,expected_development=64,expected_validation=256,
            fault='fixed valid wrong destination token payload/self-checksum on proposal channel only',
            contract='FP32 Qwen2.5-1.5B eager, deterministic batch1,96token EOS; actual current-input full-token verification; source OCC; independent stable-ID renderer',
            gate='schema/Stop and full self verification must pass on all development sources before validation; semantic errors counted not silently corrected'))
        ctx=mp.get_context('spawn');P=Actor(ctx,'proposal',0,log);actors.append(P);A=Actor(ctx,'authority',1,log);actors.append(A)
        contract=sha(dict(A=A.contract,P=P.contract,adapter='orthogonal-stable-id-memory-v1',tasks=tasks))
        power=Power(a.out/'power.jsonl');selfchecks=[]
        for t in [t for t in tasks if t['split']=='development']:
            store=ProjectStore(a.out/(t['id']+'-self.sqlite'),t,time.perf_counter());req=A.prepare(messages(t,store.snapshot()))
            first=A.call('generate',req,'development-legal-oracle');repeat=A.call('generate',req,'same-input-repeat')
            v=A.call('verify',req,'full-self-verification',candidate=first['new_tokens'])
            selfchecks.append(dict(task=t['id'],repeat_equal=first['new_tokens']==repeat['new_tokens'],full_self_accept=v['accepted'],actual=first,repeat=repeat,verify=v))
        put(a.out/'SELF_CHECKS.json',selfchecks)
        if not all(c['repeat_equal'] and c['full_self_accept'] for c in selfchecks):
            put(a.out/'SUMMARY.json',dict(status='NO_GO_PROVIDER_OR_FULL_VERIFICATION_GATE',selfchecks=selfchecks,episodes=0));return
        for split,repeats in [('development',1),('validation',2)]:
            for rep in range(repeats):
                for t in [t for t in tasks if t['split']==split]:
                    for condition in CONDITIONS:
                        # Rotate execution order with frozen rep/task, not observed results.
                        order=METHODS[(rep+int(t['id'].split('-')[-1]))%4:]+METHODS[:(rep+int(t['id'].split('-')[-1]))%4]
                        for method in order:
                            eid=f'{len(rows):03}-{t["id"]}-{condition}-{method}-r{rep}'
                            rows.append(episode(a.out/eid,t,condition,method,rep,P,A,power,contract,log))
                            put(a.out/'PROGRESS.json',dict(status='RUNNING',episodes=len(rows),split=split,calls=len(log)))
            put(a.out/(split.upper()+'_SUMMARY.json'),dict(status='COMPLETE',episodes=sum(r['split']==split for r in rows),rows=[r for r in rows if r['split']==split]))
        put(a.out/'SUMMARY.json',dict(status='COMPLETE',episodes=len(rows),development=64,validation=256,actual_calls=len(log),rows=rows))
    except BaseException:put(a.out/'STOP.json',dict(error=traceback.format_exc(),completed=len(rows)));raise
    finally:
        put(a.out/'CALLS.json',log)
        if power:power.close()
        for actor in actors:actor.close()
if __name__=='__main__':main()
