"""Read-only instance boundary wrappers around the original native corrector.

Open post-ASR snapshots are NOT closed FeedbackCuts or handoff admissions.
The original method receives and returns the original objects unchanged.
"""
import dataclasses,hashlib,inspect,json,pathlib,time

class BlobStore:
    def __init__(self,path):self.path=pathlib.Path(path);self.path.mkdir(parents=True,exist_ok=True)
    def encode(self,x):
        import torch,numpy as np
        if torch.is_tensor(x) or isinstance(x,np.ndarray):
            t=x.detach().cpu().contiguous() if torch.is_tensor(x) else torch.from_numpy(np.ascontiguousarray(x))
            raw=t.numpy().tobytes();meta=dict(shape=list(t.shape),dtype=str(t.dtype));h=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()+raw).hexdigest();p=self.path/(h+'.pt')
            if not p.exists():torch.save(t,p)
            return dict(tensor_blob=str(p),sha256_content=h,bytes=len(raw),**meta)
        if x is None or isinstance(x,(str,int,float,bool)):return x
        if dataclasses.is_dataclass(x):return self.encode(dataclasses.asdict(x))
        if isinstance(x,(list,tuple)):return [self.encode(v) for v in x]
        if isinstance(x,dict):return {str(k):self.encode(v) for k,v in x.items()}
        return dict(static_or_opaque_type=type(x).__module__+'.'+type(x).__qualname__)

class DeferredStore(BlobStore):
    def __init__(self,path):super().__init__(path);self.pending=[]
    def encode(self,x):
        import torch,numpy as np
        if torch.is_tensor(x) or isinstance(x,np.ndarray):
            value=x.detach().clone() if torch.is_tensor(x) else np.array(x,copy=True);i=len(self.pending);self.pending.append(value);return dict(deferred_tensor=i)
        return super().encode(x)
    def materialize(self,x):
        if isinstance(x,dict) and set(x)=={'deferred_tensor'}:return BlobStore.encode(self,self.pending[x['deferred_tensor']])
        if isinstance(x,dict):return {k:self.materialize(v) for k,v in x.items()}
        if isinstance(x,list):return [self.materialize(v) for v in x]
        return x

def cache_meta(x):
    if hasattr(x,'shape') and hasattr(x,'dtype'):return dict(shape=list(x.shape),dtype=str(x.dtype),payload_omitted=True)
    if isinstance(x,dict):return {str(i):cache_meta(v) for i,v in enumerate(x.values())}
    if isinstance(x,(list,tuple)):return [cache_meta(v) for v in x]
    return dict(type=type(x).__module__+'.'+type(x).__qualname__)

PERSISTENT=('segments','tokens','last_attend_frame','detected_language','initial_tokens','initial_token_length','sot_index','decoder_type','cfg','is_warmup')
FALLBACK=('current_tokens','token_len_before_decoding','fire_detected','is_last','new_segment','completed','use_error_corrector','content_mel_len','tokens_to_split','new_hypothesis','corrector_type','infer_start_time','start_time','t_before_decoding')

class StageProbe:
    def __init__(self,engine,path,author_file,*,sync=None,clock=None,capture_mode='full'):
        if sync is None:
            import torch
            sync=torch.cuda.synchronize
        self.engine=engine;self.path=pathlib.Path(path);self.path.mkdir(parents=True,exist_ok=True);self.store=(BlobStore if capture_mode=='full' else DeferredStore)(self.path/'blobs');self.author_file=str(pathlib.Path(author_file).resolve());self.sync=sync;self.clock=clock or time.perf_counter;self.active=None;self.capture_mode=capture_mode
        self.original_c=engine._run_SpeechLM_error_corrector;self.original_clean=engine._clean_cache
        self.fixed_objects={k:getattr(engine,k) for k in ('_speechlm_model','_speechlm_processor','_speechlm_model_type') if hasattr(engine,k)};self.corrector_call_count=0
        engine._run_SpeechLM_error_corrector=self._corrector
        engine._clean_cache=self._clean
    def _caller(self,frame):
        return frame.f_code.co_name=='infer' and str(pathlib.Path(frame.f_code.co_filename).resolve())==self.author_file
    def _state(self):
        e=self.engine;state={name:self.store.encode(vars(getattr(e,name)) if name=='cfg' and hasattr(getattr(e,name),'__dict__') and not dataclasses.is_dataclass(getattr(e,name)) else getattr(e,name)) for name in PERSISTENT if hasattr(e,name)}
        context=getattr(e,'context',None)
        state['context']=dict(text=getattr(context,'text',None),prefix_token_ids=self.store.encode(getattr(context,'prefix_token_ids',None)),token_ids=self.store.encode(context.as_token_ids()) if context is not None and hasattr(context,'as_token_ids') else None,all_object_field_names=sorted(vars(context)) if context is not None and hasattr(context,'__dict__') else [])
        state['open_state']=True;state['closed_cut']=False
        state['ephemeral_cache_metadata']=dict(kv_cache=cache_meta(getattr(e,'kv_cache',None)),dec_attns=cache_meta(getattr(e,'dec_attns',None)),inference_kv_cache=cache_meta(getattr(getattr(e,'inference',None),'kv_cache',None)),beam_finished_sequences=self.store.encode(getattr(getattr(e,'token_decoder',None),'finished_sequences',None)))
        state['all_engine_field_names']=sorted(vars(e));return state
    def _frame(self,frame):
        if not self._caller(frame):raise ValueError('capture boundary is not the pinned author infer frame')
        local=frame.f_locals
        result=dict(present_local_names=sorted(local),fallback_locals={k:self.store.encode(local[k]) for k in FALLBACK if k in local})
        g=local.get('generation',{});result['native_generation_flags']={k:self.store.encode(g.get(k)) for k in ('no_speech','no_speech_prob','frame_delay','first_token_latency') if k in g};return result
    def begin(self,step):
        if self.active is not None:raise ValueError('previous profile step not ended')
        self.active=dict(step=step,calls=[],preclean=[],capture_seconds=0.)
    def _corrector(self,*args,**kwargs):
        if self.active is None:return self.original_c(*args,**kwargs)
        for key,value in self.fixed_objects.items():
            assert getattr(self.engine,key) is value,'original corrector runtime binding changed'
        self.sync();entry=self.clock();frame=inspect.currentframe().f_back
        packet=dict(corrector_input={k:self.store.encode(v) for k,v in kwargs.items() if k not in ('corrector_model','corrector_processor')},post_asr_open_state=self._state(),caller=self._frame(frame),fixed_runtime_binding=dict(model_device=str(getattr(getattr(self.engine,'model',None),'device',None)),model_type=type(kwargs.get('corrector_model')).__qualname__,processor_type=type(kwargs.get('corrector_processor')).__qualname__,speechlm_model_cache_present=hasattr(self.engine,'_speechlm_model'),speechlm_processor_cache_present=hasattr(self.engine,'_speechlm_processor'),speechlm_model_type_cache=self.store.encode(getattr(self.engine,'_speechlm_model_type',None))));del frame
        self.sync();captured=self.clock();c_start=self.clock();result=self.original_c(*args,**kwargs);self.sync();c_end=self.clock()
        packet['original_corrector_result']=self.store.encode(result)
        for key in ('_speechlm_model','_speechlm_processor','_speechlm_model_type'):
            if hasattr(self.engine,key):
                value=getattr(self.engine,key)
                if key in self.fixed_objects:assert value is self.fixed_objects[key],'original corrector replaced a bound runtime object'
                else:self.fixed_objects[key]=value
        packet['post_call_fixed_runtime_types']={key:type(value).__module__+'.'+type(value).__qualname__ for key,value in self.fixed_objects.items()}
        self.sync();saved=self.clock();self.active['capture_seconds']+=(captured-entry)+(saved-c_end)
        self.corrector_call_count+=1
        self.active['calls'].append(dict(corrector_call_index_in_process=self.corrector_call_count,first_actual_corrector_call_in_process=self.corrector_call_count==1,corrector_entry_perf=entry,c_start_perf=c_start,c_end_perf=c_end,packet=packet))
        return result
    def _clean(self,*args,**kwargs):
        frame=inspect.currentframe().f_back
        if self.active is not None and self._caller(frame):
            t=self.clock();self.active['preclean'].append(dict(state=self._state(),caller=self._frame(frame)));self.sync();self.active['capture_seconds']+=self.clock()-t
        del frame
        return self.original_clean(*args,**kwargs)
    def end(self,record,cut):
        active=self.active
        if active is None:raise ValueError('no profile step')
        self.active=None;calls=active['calls'];assert len(calls)<=1
        active['native_record']=record;active['closed_end_state_sha']=cut.sha256;active['closed_end_state']=cut.state
        active['C_called']=bool(calls);active['candidate_packet_admitted']=False
        if calls:
            c=calls[0];A=c['corrector_entry_perf']-record['model_start'];C=c['c_end_perf']-c['c_start_perf'];H=record['model_seconds']-A-C-active['capture_seconds']
            active['stage_seconds']=dict(A=A,C=C,H=H,capture=active['capture_seconds'],instrumented_model_total=record['model_seconds']);assert H>=-.002,'stage closure inconsistent'
        else:active['stage_seconds']=dict(A=record['model_seconds']-active['capture_seconds'],C=0.,H=0.,capture=active['capture_seconds'],instrumented_model_total=record['model_seconds'])
        active['scope']='instrumented native component replay only; H is native tail/synchronization/unclassified residual, not measured handoff or IPC cost; capture and later materialization are real instrumentation costs, not free deployment transport; no serving performance, resume or handoff implementation'
        t=self.clock()
        if isinstance(self.store,DeferredStore):active=self.store.materialize(active);self.store.pending.clear()
        active['post_model_materialize_seconds']=self.clock()-t;active['capture_mode']=self.capture_mode
        name=active['step']['step_id'];p=self.path/(name+'.json');assert not p.exists();p.write_text(json.dumps(active,ensure_ascii=False,indent=2));return active
    def close(self):
        self.engine._run_SpeechLM_error_corrector=self.original_c;self.engine._clean_cache=self.original_clean

def packet_input_signature(packet):
    """Input validity ignores the identity prediction's ultimately selected end."""
    def canonical(x):
        if isinstance(x,dict):return {k:canonical(v) for k,v in x.items() if k not in ('tensor_blob','first_token_latency','infer_start_time','start_time','t_before_decoding')}
        if isinstance(x,list):return [canonical(v) for v in x]
        return x
    value=dict(corrector_input=packet['corrector_input'],post_asr_state={k:v for k,v in packet['post_asr_open_state'].items() if k not in ('all_engine_field_names','ephemeral_cache_metadata')},beam_finished_sequences=packet['post_asr_open_state']['ephemeral_cache_metadata']['beam_finished_sequences'],native_generation_flags=packet['caller']['native_generation_flags'],fallback={k:v for k,v in packet['caller']['fallback_locals'].items() if k not in ('infer_start_time','start_time','t_before_decoding')})
    return hashlib.sha256(json.dumps(canonical(value),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
