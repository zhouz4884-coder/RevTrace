"""Independent HF/eager implementation of current-input prefix verification.

Standard speculative-prefix algorithm; NOT a reproduction of VoiceAgent's
FlashAttention engine and NOT a new RevTrace decoding primitive. No API accepts
old-context KV. All retained state is created in THIS target operation.
"""
from contextlib import contextmanager
import time,hashlib

@contextmanager
def head_rows(model,start=None,count=None):
    """Ordinary projection optimization, shared by fresh and fallback too."""
    def select(_module,args):
        h=args[0]
        return (h[:,-1:,:] if start is None else h[:,start:start+count,:],)
    hook=model.lm_head.register_forward_pre_hook(select)
    try:yield
    finally:hook.remove()

def tensor_id(t):
    raw=t.detach().contiguous().cpu().numpy().tobytes()
    return dict(shape=list(t.shape),dtype=str(t.dtype),sha256=hashlib.sha256(raw).hexdigest())

def stop_shape(z,eos,budget):
    if not z or len(z)>budget:return False
    positions=[i for i,x in enumerate(z) if x in eos]
    return positions==[len(z)-1] if positions else len(z)==budget

def continuation_plan(draft,predicted,*,prompt_width,eos,budget):
    """Pure off-by-one/Stop plan also exercised by CPU legal-oracle tests."""
    if prompt_width<1 or len(predicted)!=len(draft)+1:raise ValueError('prediction alignment')
    accepted=next((i for i,(a,b) in enumerate(zip(draft,predicted)) if a!=b),len(draft))
    selected=list(draft[:accepted]);terminal=bool(selected) and (selected[-1] in eos or len(selected)==budget)
    bonus=None if terminal else predicted[accepted]
    if bonus is not None:selected.append(bonus)
    return dict(accepted=accepted,cache_length=prompt_width+accepted,selected_prefix=selected,bonus=bonus,
        terminal=bool(selected) and (selected[-1] in eos or len(selected)==budget))

class CurrentInputExecutor:
    """Batch1 bounded prototype; one physical worker lease until all phases end.

    Audio encoding and last-row LM projection are offered equally to strong
    fresh, Strict/full-fallback, native-algorithm adaptation and RevTrace paths.
    Old literal worker double-encoding costs are separate diagnostics.
    """
    def __init__(self,model,data,*,eos,budget,pad,observer=None):
        import torch
        if data['input_ids'].shape[0]!=1:raise ValueError('prototype freezes batch1')
        self.torch=torch;self.model=model;self.data=data;self.eos=set(eos);self.budget=int(budget);self.pad=int(pad)
        self.device=data['input_ids'].device;self.L=data['input_ids'].shape[1];self.phases=[];self.base=None
        if self.L<1 or next(model.parameters()).dtype!=torch.float32:raise ValueError('frozen nonempty FP32 target required')
        self.observer=observer
        self.input_identity={k:tensor_id(v) for k,v in data.items()}
    def measured(self,name,fn):
        t=self.torch;t.cuda.synchronize(self.device);a=time.perf_counter()
        if self.observer:self.observer(name,'started',a)
        with t.inference_mode():value=fn()
        t.cuda.synchronize(self.device);b=time.perf_counter()
        self.phases.append(dict(phase=name,started_perf=a,completed_perf=b,seconds=b-a))
        if self.observer:self.observer(name,'completed',b)
        return value
    def encode_current(self):
        if self.base is not None:raise ValueError('one target encode per executor instance')
        def encode():
            m=self.model;d=self.data;emb=m.get_input_embeddings()(d['input_ids'])
            features=m.get_audio_features(d['input_features'],feature_attention_mask=d.get('feature_attention_mask'))
            features=features.to(emb.device,emb.dtype)
            mask=m.get_placeholder_mask(d['input_ids'],inputs_embeds=emb)
            return emb.masked_scatter(mask,features)
        self.base=self.measured('current-audio-encode-and-embedding',encode)
        self.base_identity=tensor_id(self.base)
    def fresh(self):
        if self.base is None:raise ValueError('current input must be encoded first')
        m=self.model;d=self.data
        def generate():
            with head_rows(m):
                out=m.generate(input_ids=d['input_ids'],inputs_embeds=self.base,attention_mask=d['attention_mask'],
                    feature_attention_mask=d.get('feature_attention_mask'),input_features=None,use_cache=True,
                    do_sample=False,max_new_tokens=self.budget,eos_token_id=list(self.eos),pad_token_id=self.pad,
                    return_dict_in_generate=True,output_scores=False)
            row=out.sequences[0,self.L:].detach().cpu().tolist()
            return row
        z=self.measured('fresh-current-target-generation',generate)
        if not stop_shape(z,self.eos,self.budget):raise ValueError('fresh complete Stop/budget invalid')
        return z
    def verify(self,draft,cache):
        t=self.torch;m=self.model;d=self.data;N=len(draft)
        ids=t.tensor([draft],dtype=t.long,device=self.device)
        joined=t.cat([d['input_ids'],ids],1);mask=t.cat([d['attention_mask'],t.ones_like(ids)],1)
        embeds=t.cat([self.base,m.get_input_embeddings()(ids)],1)
        def forward():
            with head_rows(m,self.L-1,N+1):
                out=m(input_ids=joined,inputs_embeds=embeds,attention_mask=mask,
                    feature_attention_mask=d.get('feature_attention_mask'),input_features=None,use_cache=cache,
                    cache_position=t.arange(joined.shape[1],device=self.device),return_dict=True)
            if not bool(t.isfinite(out.logits).all()):raise ValueError('nonfinite trusted target logits')
            predicted=out.logits.argmax(-1)[0].detach().cpu().tolist()
            if len(predicted)!=N+1:raise ValueError('verification/bonus projection alignment')
            return out,predicted
        return self.measured('correct-current-verify-cache' if cache else 'correct-current-verify-no-cache',forward)
    def select(self,mode,draft):
        if mode not in ['fresh','strict-full','prefix','revtrace-prefix']:raise ValueError('unknown executor mode')
        if self.base is None:self.encode_current()
        draft=list(draft)[:self.budget];N=len(draft)
        vocab=self.model.get_input_embeddings().weight.shape[0]
        audio_id=getattr(self.model.config,'audio_token_id',None)
        malformed=any(not isinstance(x,int) or not 0<=x<vocab or x==audio_id for x in draft)
        malformed=malformed or any(x in self.eos for x in draft[:-1])
        if mode=='fresh' or N==0 or malformed:
            return self.fresh(),dict(mode=mode,draft_tokens=N,accepted_prefix=0,cache_created=False,reason='fresh/empty/malformed')
        out,pred=self.verify(draft,cache=mode!='strict-full')
        accepted=next((i for i,(a,b) in enumerate(zip(draft,pred)) if a!=b),N)
        proof=dict(mode=mode,draft_tokens=N,accepted_prefix=accepted,predicted_tokens=pred,
            current_input=self.input_identity,current_embedding=self.base_identity,
            cache_created=mode!='strict-full',no_old_context_KV=True)
        if mode=='strict-full':
            if accepted==N and stop_shape(draft,self.eos,self.budget):return draft,dict(proof,reason='full-candidate-selected')
            return self.fresh(),dict(proof,reason='paid-full-fallback')
        cache=out.past_key_values
        if cache is None or cache.get_seq_length()!=self.L+N:raise ValueError('new current-input KV length mismatch')
        plan=continuation_plan(draft,pred,prompt_width=self.L,eos=self.eos,budget=self.budget)
        proof['cache_before_crop']=cache.get_seq_length();target=plan['cache_length']
        cache.crop(target)
        if cache.get_seq_length()!=target:raise ValueError('cache crop failed')
        for layer in cache.layers:
            if layer.get_seq_length()!=target:raise ValueError('per-layer crop mismatch')
        proof['cache_after_crop']=target
        selected=plan['selected_prefix'];proof['bonus']=plan['bonus']
        if plan['terminal']:return selected,dict(proof,reason='accepted-terminal-prefix' if plan['bonus'] is None else 'trusted-bonus-terminal')
        t=self.torch;d=self.data;continuation=t.tensor([selected],dtype=t.long,device=self.device)
        full=t.cat([d['input_ids'],continuation],1);mask=t.cat([d['attention_mask'],t.ones_like(continuation)],1)
        def residual():
            with head_rows(self.model):
                answer=self.model.generate(input_ids=full,attention_mask=mask,past_key_values=cache,
                    input_features=None,feature_attention_mask=d.get('feature_attention_mask'),
                    cache_position=t.arange(target,full.shape[1],device=self.device),
                    use_cache=True,do_sample=False,max_new_tokens=self.budget-len(selected),
                    eos_token_id=list(self.eos),pad_token_id=self.pad,return_dict_in_generate=True,output_scores=False)
            return answer.sequences[0,self.L:].detach().cpu().tolist()
        z=self.measured('trusted-residual-generation',residual)
        if z[:len(selected)]!=selected or not stop_shape(z,self.eos,self.budget):raise ValueError('residual complete token/Stop/budget mismatch')
        return z,dict(proof,reason='new-current-KV-prefix-plus-residual')
