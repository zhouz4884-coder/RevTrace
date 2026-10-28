"""Bounded real-model LangGraph/SQLite memory pilot. Not serving capacity.

Each method actually executes its model calls; no replayed neural results.
Frozen source/readset interventions are controlled, not natural prevalence.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
from pathlib import Path
import sys,json,time,hashlib,threading,concurrent.futures,importlib.metadata,platform,re,subprocess,traceback
W=Path(__file__).resolve().parent
from memory_app import *

class Power:
    def __init__(self,path):
        self.path=path;self.rows=[];self.stop=threading.Event();self.lock=threading.Lock()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
        limit=time.perf_counter()+8
        while len(self.rows)<2 and time.perf_counter()<limit:time.sleep(.05)
        assert len(self.rows)>=2,'no real GPU power samples'
    def run(self):
        with self.path.open('x') as f:
            while not self.stop.is_set():
                begin=time.perf_counter()
                raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,power.draw,memory.used','--format=csv,noheader,nounits'],text=True)
                end=time.perf_counter();values={}
                for line in raw.splitlines():
                    i,p,m=line.split(',');values[int(i)]=dict(watts=float(p),memory_MiB=float(m))
                r=dict(observed_perf=(begin+end)/2,query_seconds=end-begin,GPUs=values)
                with self.lock:self.rows.append(r)
                f.write(json.dumps(r)+'\n');f.flush();self.stop.wait(.18)
    def joules(self,start,end):
        limit=time.perf_counter()+8
        while self.rows[-1]['observed_perf']<end and time.perf_counter()<limit:time.sleep(.04)
        with self.lock:rows=list(self.rows)
        assert rows[0]['observed_perf']<=start and rows[-1]['observed_perf']>=end
        total=0.
        for a,b in zip(rows,rows[1:]):
            lo=max(start,a['observed_perf']);hi=min(end,b['observed_perf'])
            if hi<=lo:continue
            dt=b['observed_perf']-a['observed_perf'];pa=sum(x['watts'] for x in a['GPUs'].values());pb=sum(x['watts'] for x in b['GPUs'].values())
            plo=pa+(pb-pa)*(lo-a['observed_perf'])/dt;phi=pa+(pb-pa)*(hi-a['observed_perf'])/dt
            total+=(plo+phi)/2*(hi-lo)
        return total
    def close(self):self.stop.set();self.thread.join(timeout=8)

class Neural:
    def __init__(self,modeldir,device,dtype,budget):
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        self.torch=torch;self.device=device;self.budget=budget;self.calls=[];self.lock=threading.RLock()
        self.tokenizer=AutoTokenizer.from_pretrained(modeldir,local_files_only=True,trust_remote_code=False)
        self.model=AutoModelForCausalLM.from_pretrained(modeldir,dtype=dtype,attn_implementation='eager',local_files_only=True,trust_remote_code=False).to('cuda:'+str(device)).eval()
        self.contract=dict(model=str(modeldir),dtype=str(dtype),budget=budget,do_sample=False,attention='eager',device=device,
            transformers=importlib.metadata.version('transformers'),torch=torch.__version__,batch_size=1)
        self.observed=None
        def pre_hook(module,args,kwargs):
            ids=kwargs.get('input_ids',args[0] if args else None)
            if self.observed is None and ids is not None:self.observed=ids.detach().cpu().tolist()
        self.hook=self.model.register_forward_pre_hook(pre_hook,with_kwargs=True)
    def prepare(self,messages):
        ids=self.tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True)
        return dict(messages=messages,input_ids=ids,contract=self.contract,identity=sha(dict(input_ids=ids,contract=self.contract)))
    def generate(self,request,started=None):
        with self.lock:
            t=self.torch;self.observed=None
            x=t.tensor([request['input_ids']],device='cuda:'+str(self.device),dtype=t.long)
            t.cuda.synchronize(self.device);begin=time.perf_counter()
            if started is not None:started.set()
            with t.inference_mode():
                generated=self.model.generate(input_ids=x,attention_mask=t.ones_like(x),do_sample=False,max_new_tokens=self.budget,
                    pad_token_id=self.tokenizer.eos_token_id,return_dict_in_generate=True)
            t.cuda.synchronize(self.device);end=time.perf_counter();seq=generated.sequences[0].detach().cpu().tolist();z=seq[len(request['input_ids']):]
            assert self.observed==[request['input_ids']] and seq[:len(request['input_ids'])]==request['input_ids']
            eos=self.model.generation_config.eos_token_id;eos={eos} if isinstance(eos,int) else set(eos or [])
            text=self.tokenizer.decode(z,skip_special_tokens=True);clean=text.strip()
            if clean.startswith('```'):
                lines=clean.splitlines();clean='\n'.join(lines[1:-1]) if lines[-1].strip()=='```' else clean
            record=dict(request=request,actual_first_input_ids=self.observed[0],request_identity=request['identity'],new_tokens=z,
                decoded=text,terminated_by_eos=bool(z and z[-1] in eos),started_perf=begin,completed_perf=end,
                actual_gpu_seconds=end-begin,device=self.device)
            self.calls.append(record)
            if not record['terminated_by_eos']:raise ValueError('declared EOS/budget gate failed')
            value=json.loads(clean);assert set(value)=={'destination','owner'} and all(isinstance(v,str) for v in value.values())
            record['value']=value;return record

def framework_generate(neural,request,checkpoint,thread_id,started):
    from langgraph.graph import StateGraph,START,END
    from langgraph.checkpoint.sqlite import SqliteSaver
    from typing_extensions import TypedDict
    class S(TypedDict):request:dict;selected:dict
    def select(state):return dict(selected=neural.generate(state['request'],started))
    with SqliteSaver.from_conn_string(str(checkpoint)) as saver:
        graph=StateGraph(S);graph.add_node('select_complete_memory_delta',select);graph.add_edge(START,'select_complete_memory_delta');graph.add_edge('select_complete_memory_delta',END)
        app=graph.compile(checkpointer=saver)
        return app.invoke(dict(request=request),dict(configurable=dict(thread_id=thread_id)),durability='sync')['selected']

def run_episode(root,index,task,condition,method,repeat,A,R,contract,power):
    E=root/f'{index:03}-{task["id"]}-{condition}-{method}-r{repeat}';E.mkdir()
    start=time.perf_counter();store=ProjectStore(E/'project.sqlite',task,start)
    adapter=MemoryKernelAdapter(store,contract) if method=='revtrace_kernel_latest_read' else None
    initial=store.snapshot();request=A.prepare(update_messages(task,initial));job=adapter.dispatch(initial,request) if adapter else None
    event=threading.Event();before_calls=len(A.calls)+len(R.calls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(framework_generate,A,request,E/'graph.sqlite',str(index),event)
        assert event.wait(45),'real model did not start'
        if condition=='controlled_source_revision_before_background_install':
            if adapter:adapter.revise(task['revision'])
            else:store.revise(task['revision'])
        revision_applied=time.perf_counter();selected=future.result(timeout=120)
    if adapter:
        adapter.complete(job,selected);accepted=adapter.install(job,selected)
    else:accepted=store.install(selected['value'],initial['readset'],dict(request_identity=selected['request_identity']),check_versions=method!='metadata_application')
    old_accepted=accepted;fallbacks=0;followup_selection=None
    if not accepted:
        fallbacks=1;now=store.snapshot();fresh=A.prepare(update_messages(task,now));newjob=adapter.dispatch(now,fresh) if adapter else None
        followup_selection=A.generate(fresh)
        if adapter:
            adapter.complete(newjob,followup_selection);assert adapter.install(newjob,followup_selection)
        else:assert store.install(followup_selection['value'],now['readset'],dict(request_identity=followup_selection['request_identity']),check_versions=True)
    memory=store.memory();read_at=time.perf_counter();answer=R.generate(R.prepare(answer_messages(task,memory['value'])))
    consumed_at=time.perf_counter();expected=task['expected_new'] if condition=='controlled_source_revision_before_background_install' else task['expected_old']
    # Independent task scoring is not used by the decision policy.
    scores={k:answer['value'][k].casefold()==expected[k].casefold() for k in expected}
    result=dict(episode=E.name,task_id=task['id'],split=task['split'],condition=condition,method=method,repeat=repeat,
        actual_old_input_snapshot=initial,source_after=store.snapshot(),old_selection=selected,old_result_installed=old_accepted,
        latest_read_violation=old_accepted and initial['readset']!=store.snapshot()['readset'],actual_fallback_generations=fallbacks,
        fallback_selection=followup_selection,stored_memory=memory,actual_memory_read_perf=read_at,answer=answer,
        actual_consumer_applied_perf=consumed_at,task_exact_correct=all(scores.values()),field_correct=scores,
        memory_exact_correct=all(memory['value'][k].casefold()==expected[k].casefold() for k in expected),
        old_generation_before_revision=selected['started_perf']<=revision_applied if condition!='clean_same_versions' else None,
        revision_boundary=('during_neural_call' if revision_applied<selected['completed_perf'] else 'complete_but_not_installed') if condition!='clean_same_versions' else 'no_revision',
        source_revision_applied_perf=revision_applied if condition!='clean_same_versions' else None,wall_seconds=consumed_at-start,
        GPU_joules_measured_both_devices=power.joules(start,consumed_at),
        live_protocol_state_bytes=len(canonical(dict(C=adapter.k.state.C,I=adapter.k.state.I,V=adapter.k.state.V)).encode()) if adapter else None,
        project_database_bytes=(E/'project.sqlite').stat().st_size,graph_checkpoint_bytes=(E/'graph.sqlite').stat().st_size,
        actual_new_model_calls=len(A.calls)+len(R.calls)-before_calls,
        kernel_events=adapter.k.trace if adapter else None,
        evidence_tier='actual model-resident LangGraph/SQLite application pilot, not network serving/ASR capacity/natural fault rate')
    (E/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    import argparse,torch
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--split',choices=['development','validation'],required=True);a=p.parse_args()
    a.root.mkdir(parents=True,exist_ok=False);task_file=W/'MEMORY_TASKS_v4.json';spec=json.loads(task_file.read_text())
    source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
    for f in source['files']:assert hashlib.sha256((W/f['path']).read_bytes()).hexdigest()==f['sha256']
    tasks=[t for t in spec['tasks'] if t['split']==a.split];reps=spec[a.split+'_repeats']
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True)
    assert not apps.strip(),'GPU busy: no competing work started'
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True);torch.set_num_threads(4)
    B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
    os.environ['HF_HOME']=str(B/'cache/huggingface');os.environ['HF_HUB_OFFLINE']='1'
    model_files=[]
    for name in [spec['authority']['model'],spec['responder']['model']]:
        for f in sorted((B/'models'/name).glob('*')):
            if not f.is_file() or f.suffix not in ['.json','.txt','.model','.safetensors']:continue
            assert f.resolve().is_relative_to(B)
            h=hashlib.sha256()
            with f.open('rb') as stream:
                for block in iter(lambda:stream.read(2**22),b''):h.update(block)
            model_files.append(dict(path=str(f),bytes=f.stat().st_size,sha256=h.hexdigest()))
    (a.root/'MODELS.json').write_text(json.dumps(model_files,indent=2)+'\n')
    loaded=time.perf_counter();A=Neural(B/'models'/spec['authority']['model'],1,torch.float32,spec['authority']['max_new_tokens']);R=Neural(B/'models'/spec['responder']['model'],0,torch.float16,spec['responder']['max_new_tokens'])
    contract=sha(dict(authority=A.contract,responder=R.contract,adapter='structured-memory-latest-read-v1',task_spec_sha256=hashlib.sha256(task_file.read_bytes()).hexdigest()))
    freeze=dict(status='FROZEN_BEFORE_FIRST_MODEL_CALL',spec=spec,split=a.split,contract=contract,model_load_seconds=time.perf_counter()-loaded,
        source=source,
        runtime={n:importlib.metadata.version(n) for n in ['torch','transformers','langgraph','langgraph-checkpoint-sqlite']},python=sys.version,platform=platform.platform())
    (a.root/'FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[];index=0;power=Power(a.root/'power.jsonl')
    try:
        for rep in range(reps):
            for ti,task in enumerate(tasks):
                for condition in spec['conditions']:
                    methods=spec['methods'];rot=(ti+rep)%len(methods)
                    for method in methods[rot:]+methods[:rot]:
                        r=run_episode(a.root,index,task,condition,method,rep,A,R,contract,power);rows.append(r);index+=1
                        (a.root/'PROGRESS.json').write_text(json.dumps(dict(status='RUNNING',completed=index,expected=len(tasks)*2*3*reps))+'\n')
        assert index==len(tasks)*2*3*reps
        summary=dict(status='COMPLETE',expected=index,completed=index,unique_tasks=len(tasks),split=a.split,
            calls=len(A.calls)+len(R.calls),rows=[{k:v for k,v in r.items() if k not in ['old_selection','fallback_selection','answer','kernel_events']} for r in rows])
        (a.root/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(dict(status='COMPLETE',episodes=index,calls=summary['calls'])))
    except BaseException:
        (a.root/'STOP.json').write_text(json.dumps(dict(status='FAILED_RETAINED',completed=index,error=traceback.format_exc(),authority_calls=A.calls,responder_calls=R.calls),indent=2)+'\n');raise
    finally:
        power.close()
        (a.root/'ALL_ACTUAL_CALLS.json').write_text(json.dumps(dict(authority=A.calls,responder=R.calls),indent=2)+'\n')
if __name__=='__main__':main()
