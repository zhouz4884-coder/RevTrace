"""Diagnostic monkeypatches around the byte-frozen worker. No state installs."""
import hashlib,json,os,time
from row_probe_core import RowFinalStream
from tc_live_worker import worker_main as frozen_worker_main

def worker_main(commands,results,config):
    os.environ['CUDA_VISIBLE_DEVICES']=str(config['gpu'])
    os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['OMP_NUM_THREADS']='2'
    import torch
    from transformers.generation.utils import GenerationMixin
    from qwen_asr import Qwen3ASRModel,parse_asr_output
    from revtrace.certified_display import TrustedQwenRender
    import tc_live_worker
    import online_selection_worker
    state={'jobs':{},'enabled':False,'events':[],'engine':None,'ids':[],
           'phase':'independent-generate','selection_index':0,'capture_inputs':False}
    original_loader=Qwen3ASRModel.from_pretrained
    def loader(cls,*args,**kwargs):
        engine=original_loader(*args,**kwargs);state['engine']=engine
        eos=engine.model.generation_config.eos_token_id
        stops=[eos] if isinstance(eos,int) else list(eos or [])
        state['eos']=stops
        state['renderer']=TrustedQwenRender(engine.processor.tokenizer,parse_asr_output,stops,config['max_new_tokens'])
        def capture_verifier_inputs(_module,args,kwargs):
            if not state['capture_inputs'] or not state['phase'].startswith('correct-context'):return
            identities={}
            for k,v in kwargs.items():
                if isinstance(v,torch.Tensor):
                    x=v.detach().cpu().contiguous()
                    identities[k]={'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
            state['events'].append({'kind':'actual-postcast-verifier-inputs','phase':state['phase'],
                'job_ids':list(state['ids']),'tensors':identities,'not_a_timing_reference':True})
        state['verifier_input_hook']=engine.model.thinker.register_forward_pre_hook(capture_verifier_inputs,with_kwargs=True)
        return engine
    Qwen3ASRModel.from_pretrained=classmethod(loader)
    def render(jid,Z):return state['renderer'](state['jobs'][jid],Z)
    original_generate=GenerationMixin.generate
    def generate(self,*args,**kwargs):
        if not state['jobs']:return original_generate(self,*args,**kwargs)
        if state['capture_inputs']:
            identities={}
            for k,v in kwargs.items():
                if isinstance(v,torch.Tensor):
                    x=v.detach().cpu().contiguous()
                    identities[k]={'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
            state['events'].append({'kind':'actual-postcast-inputs','phase':state['phase'],
                'job_ids':list(state['ids']),'tensors':identities,'not_a_timing_reference':True})
        if state['enabled']:
            if kwargs.get('streamer') is not None:raise ValueError('do not replace an existing generation interface')
            kwargs['streamer']=RowFinalStream(state['ids'],eos=state['eos'],
                budget=config['max_new_tokens'],events=state['events'],render=render,phase=state['phase'])
        return original_generate(self,*args,**kwargs)
    GenerationMixin.generate=generate
    original_select=online_selection_worker.select_online
    original_gate=online_selection_worker.gate_candidate
    def gate(*args,**kwargs):
        answer=original_gate(*args,**kwargs)
        if state['enabled'] and state.get('selection_jobs'):
            i=state['selection_index'];state['selection_index']+=1
            jid=state['selection_jobs'][i]['job_id'];ready=time.perf_counter()
            if answer[0]:
                Z=tuple(args[1]);P,text=render(jid,Z);final=time.perf_counter()
                state['events'].append({'kind':'probe-verified-row-final','job_id':jid,
                 'phase':'correct-context-'+args[0],'terminal_observed_perf':ready,
                 'complete_render_perf':final,'observer_render_s':final-ready,
                 'Z':list(Z),'P':list(P),'text':text,'worker_reusable':False,
                 'diagnostic_not_online_installation':True})
        return answer
    def select(*args,**kwargs):
        state['selection_jobs']=kwargs['jobs'];state['selection_index']=0
        try:return original_select(*args,**kwargs)
        finally:state['selection_jobs']=None
    online_selection_worker.gate_candidate=gate;online_selection_worker.select_online=select
    class Commands:
        def get(self):
            jobs=commands.get()
            if jobs is not None:
                flags={j['_probe_enabled'] for j in jobs};capture={j.get('_probe_capture_inputs',False) for j in jobs}
                if len(flags)!=1 or len(capture)!=1:raise ValueError('mixed observer configurations')
                state.update(jobs={j['job_id']:j for j in jobs},enabled=flags.pop(),
                    capture_inputs=capture.pop(),events=[],ids=[j['job_id'] for j in jobs],phase='independent-generate')
            return jobs
    class Results:
        def put(self,value):
            if value.get('kind')=='model-started':
                state['ids']=list(value['job_ids']);state['phase']=value.get('online_phase','independent-generate')
            if value.get('kind')=='result':
                # Immutable diagnostic payload snapshot; never a published receipt.
                events=json.loads(json.dumps(state['events']))
                for r in value['rows']:
                    r['diagnostic_row_probe']=events;r['probe_enabled']=state['enabled']
            results.put(value)
    frozen_worker_main(Commands(),Results(),config)
