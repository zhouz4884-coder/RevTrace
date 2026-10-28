"""Paid batch1 current-input operator gate. NOT online service or Goodput."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from pathlib import Path
import sys,json,time,hashlib,traceback,argparse,subprocess,importlib.metadata
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.prefix_continuation import CurrentInputExecutor,stop_shape,head_rows
from revtrace.dgft import digest_tokens
from memory_gpu_pilot import Power
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')

def put(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Engine:
    def __init__(self,device,dtype):
        import torch
        from qwen_asr import Qwen3ASRModel,parse_asr_output
        self.t=torch;self.device=device;self.dtype=dtype;self.parser=parse_asr_output
        self.e=Qwen3ASRModel.from_pretrained(str(B/'models/Qwen3-ASR-1.7B'),torch_dtype=dtype,
            device_map={'':'cuda:'+str(device)},attn_implementation='eager',low_cpu_mem_usage=True,
            local_files_only=True,max_inference_batch_size=1,max_new_tokens=256)
        self.model=self.e.model;self.proc=self.e.processor;self.tok=self.proc.tokenizer
        eos=self.model.generation_config.eos_token_id;self.eos={eos} if isinstance(eos,int) else set(eos)
    def prepare(self,j,wav):
        raw=self.tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
        if j['chunk_id']>=2 and raw:
            ids=self.tok.encode(raw);k=5
            while True:
                prefix=self.tok.decode(ids[:max(0,len(ids)-k)])
                if '\ufffd' not in prefix or k>=len(ids):break
                k+=1
        prompt=self.e._build_text_prompt(context='',force_language=j['language'])+prefix
        x=self.proc(text=[prompt],audio=[wav[:j['audio_end_sample']]],return_tensors='pt',padding=True)
        x={k:v.to('cuda:'+str(self.device),dtype=self.dtype if v.is_floating_point() else v.dtype) for k,v in x.items()}
        return x,prefix
    def render(self,j,prefix,z):
        raw=prefix+self.tok.decode(z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        lang,text=self.parser(raw,user_language=j['language']);P=self.tok.encode(raw)
        return dict(Z=z,P=P,text=text,language=lang,Zsha=digest_tokens(z),Psha=digest_tokens(P),
            textsha=hashlib.sha256(text.encode()).hexdigest(),EOS=bool(z and z[-1] in self.eos),
            complete_Stop=stop_shape(z,self.eos,256))
    def native(self,x):
        t=self.t;t.cuda.synchronize(self.device);a=time.perf_counter()
        with t.inference_mode():out=self.model.generate(**x,do_sample=False,max_new_tokens=256,output_scores=False)
        t.cuda.synchronize(self.device);b=time.perf_counter()
        return out.sequences[0,x['input_ids'].shape[1]:].detach().cpu().tolist(),a,b

def main():
    import torch,soundfile as sf,numpy as np
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(exist_ok=False,parents=True);rows=[];calls=[];power=None
    try:
        apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True)
        assert not apps.strip(),'another GPU task is active'
        source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
        for r in source['files']:assert sha(W/r['path'])==r['sha256']
        spec=json.loads(a.profiles.read_text());profiles=spec['profiles']
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True);torch.set_num_threads(4)
        put(a.out/'FREEZE.json',dict(source=source,profile_sha256=sha(a.profiles),spec=spec,
            environment={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']},
            scope='actual paid FP16 producer and FP32 target conditional-state operators; no deployed availability, latency SLO or protocol performance claim',
            gate='pilot full Z/P/text/Stop equality native/repeated/shared fresh/self verifier/prefix and controlled mismatch; any failure closes formal32 and online integration'))
        P=Engine(0,torch.float16);A=Engine(1,torch.float32);power=Power(a.out/'power.jsonl')
        # Two source IDs, both rhos; metadata-selected, not token-selected.
        ids=list(dict.fromkeys(q['source_id'] for q in profiles))[:2]
        pilot=[q for q in profiles if q['source_id'] in ids and q['repeat']==0]
        cache={}
        def audio(q):
            sid=q['source_id']
            if sid not in cache:
                v,rate=sf.read(q['source']['path'],dtype='float32');assert rate==16000 and v.ndim==1
                assert hashlib.sha256(np.asarray(v,dtype='<f4').tobytes()).hexdigest()==q['source']['audio_sha256'];cache[sid]=v
            return cache[sid]
        def generated(engine,x,label):
            z,st,en=engine.native(x);r=dict(label=label,Z=z,started_perf=st,completed_perf=en,seconds=en-st,device=engine.device)
            calls.append(r);return z,r
        for q in pilot:
            wav=audio(q);j=q['target_job'];x,pre=A.prepare(j,wav)
            oracle,o=generated(A,x,q['id']+':native-reference')
            repeat,rr=generated(A,x,q['id']+':native-repeat');assert oracle==repeat,'same-input native repeat differs'
            expected=A.render(j,pre,oracle);checks=[]
            seedjob=q['selected_seed_job'];px,pp=P.prepare(seedjob,wav);seed,pc=generated(P,px,q['id']+':paid-producer')
            seedraw=pp+P.tok.decode(seed,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            draft=A.tok.encode(seedraw[len(pre):]) if seedraw.startswith(pre) else []
            if seed and seed[-1] in P.eos and draft:draft.append(min(A.eos))
            corrupt=list(oracle);pos=max(0,len(corrupt)//2);corrupt[pos]=1 if corrupt[pos]!=1 else 2
            controls=[('fresh',[],'shared-optimized-fresh'),('strict-full',oracle,'self-Strict'),
                ('prefix',oracle,'self-prefix-full-EOS'),('prefix',corrupt,'controlled-first-mismatch'),
                ('strict-full',draft,'ready-seed-Strict'),('prefix',draft,'ready-seed-prefix')]
            for mode,d,control in controls:
                ex=CurrentInputExecutor(A.model.thinker,x,eos=A.eos,budget=256,pad=A.tok.pad_token_id or 0)
                st=time.perf_counter();z,proof=ex.select(mode,d);en=time.perf_counter();r=A.render(j,pre,z)
                ok=all(r[k]==expected[k] for k in ['Z','P','text','EOS','complete_Stop'])
                rec=dict(profile=q['id'],control=control,mode=mode,full_equal=ok,actual=r,reference=expected,
                    producer=pc,draft=d,proof=proof,phases=ex.phases,started_perf=st,completed_perf=en,
                    target_wall_seconds=en-st,both_GPU_joules=power.joules(st,en),input=ex.input_identity)
                checks.append(rec);calls.append(dict(label=q['id']+':'+control,phases=ex.phases,Z=z))
                put(a.out/(q['id']+'-'+control+'.json'),rec)
            rows.extend(checks);put(a.out/'PILOT_PROGRESS.json',dict(profiles_done=len(rows)//6,checks=len(rows),all_equal=all(r['full_equal'] for r in rows)))
            if not all(r['full_equal'] for r in checks):
                put(a.out/'SUMMARY.json',dict(status='NO_GO_FROZEN_FRESH_EQUIVALENCE',pilot_profiles=len(rows)//6,checks=len(rows),
                    mismatches=[dict(profile=r['profile'],control=r['control']) for r in rows if not r['full_equal']],
                    formal32_started=False,online_integration_started=False,rows=rows));return
        # Actual operator comparisons; fourth mode is explicitly SAME executor,
        # not a fabricated protocol run. A subsequent service integration gate is separate.
        formal=[]
        for q in profiles:
            wav=audio(q);j=q['target_job'];x,pre=A.prepare(j,wav);group=[]
            for mode in ['fresh','strict-full','prefix','revtrace-prefix']:
                px,pp=P.prepare(q['selected_seed_job'],wav);seed,pc=generated(P,px,q['id']+':'+mode+':producer')
                seedraw=pp+P.tok.decode(seed,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                draft=A.tok.encode(seedraw[len(pre):]) if seedraw.startswith(pre) else []
                if draft and seed[-1] in P.eos:draft.append(min(A.eos))
                ex=CurrentInputExecutor(A.model.thinker,x,eos=A.eos,budget=256,pad=A.tok.pad_token_id or 0)
                st=time.perf_counter();z,proof=ex.select(mode,draft);en=time.perf_counter();r=A.render(j,pre,z)
                rec=dict(profile=q['id'],source_id=q['source_id'],rho=q['rho'],repeat=q['repeat'],mode=mode,
                    producer=pc,actual=r,draft=draft,proof=proof,phases=ex.phases,
                    target_wall_seconds=en-st,paid_compute_seconds=pc['seconds']+sum(v['seconds'] for v in ex.phases),
                    both_GPU_target_joules=power.joules(st,en),scope='conditional-state operator; revtrace-prefix is shared-executor control, NOT full protocol claim')
                group.append(rec);put(a.out/(q['id']+'-'+mode+'.json'),rec)
            ref=group[0]['actual'];equal=all(all(r['actual'][k]==ref[k] for k in ['Z','P','text','EOS','complete_Stop']) for r in group)
            formal.extend(group);put(a.out/'FORMAL_PROGRESS.json',dict(tuples=len(formal)//4,all_current_tuple_equal=equal))
            if not equal:
                put(a.out/'SUMMARY.json',dict(status='NO_GO_FORMAL_FRESH_EQUIVALENCE',formal_tuples=len(formal)//4,expected_tuples=32,rows=formal));return
        put(a.out/'SUMMARY.json',dict(status='COMPLETE_32_CONDITIONAL_STATE_TUPLES',pilot_checks=len(rows),formal_tuples=32,rows=formal,
            next_gate='independent cost audit before genuine protocol/service integration; do not rename operator as serving'))
    except BaseException:put(a.out/'STOP.json',dict(error=traceback.format_exc(),completed_rows=rows));raise
    finally:
        put(a.out/'CALLS.json',calls)
        if power:power.close()
if __name__=='__main__':main()
