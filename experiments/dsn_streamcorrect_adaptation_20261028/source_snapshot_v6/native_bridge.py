"""Unmodified-author inference bridge with closed native cache-boundary cuts.

Fixed 500ms/no-VAD front end is a declared controlled adaptation. The author's
candidate decoding, corrector prompt/generate call, selected IDs and feedback
update are called directly, not reimplemented or overridden here.
"""
from __future__ import annotations
import hashlib,importlib,json,pathlib,sys,time
from feedback_contract import FeedbackCut,digest

def sha_file(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def corrector_interface(*,corrector_base,text_backbone,corrector_audio_processor):
    """Construct original dynamic classes with explicit original local assets.

    AutoConfig keyword overrides occur after custom config __init__, too late
    for Ultravox's nested text loader. Its processor also independently reloads
    that config and the external 128-bin Whisper feature extractor. Resolve the
    same original assets before construction, retaining constructor behavior.
    """
    from transformers import AutoFeatureExtractor,AutoTokenizer
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    base=pathlib.Path(corrector_base);raw=json.loads((base/'config.json').read_text())
    cls=get_class_from_dynamic_module(raw['auto_map']['AutoConfig'],str(base),local_files_only=True)
    raw['text_model_id']=str(text_backbone);cfg=cls(**raw)
    pcls=get_class_from_dynamic_module(raw['auto_map']['AutoProcessor'],str(base),local_files_only=True)
    feature=AutoFeatureExtractor.from_pretrained(str(corrector_audio_processor),local_files_only=True)
    if feature.feature_size!=cfg.audio_config.num_mel_bins:raise ValueError('original native audio feature dimensions differ')
    tokenizer=AutoTokenizer.from_pretrained(str(base),local_files_only=True)
    tokenizer.padding_side='left';tokenizer.pad_token=tokenizer.eos_token
    return cfg,pcls(audio_processor=feature,tokenizer=tokenizer,stack_factor=cfg.stack_factor)

def native_mutable_state(engine):
    """Validate the actual reset that makes a finite native cut sufficient."""
    if engine.kv_cache or engine.dec_attns:raise ValueError('native cache not cleaned at cut')
    if engine.decoder_type!='beam':raise ValueError('this frozen adaptation requires beam=4')
    if engine.cfg.beam_size!=4 or engine.cfg.language!='zh':raise ValueError('changed native selection configuration')
    if engine.detected_language!='zh' or engine.is_warmup:raise ValueError('unsupported language or warmup cut')
    # BeamSearchDecoder.reset() is the native, mandatory post-infer reset.
    if getattr(engine.token_decoder,'finished_sequences',{}):raise ValueError('native beam survivors at cut')
    if engine.inference.kv_cache:raise ValueError('beam cache not reset')

def export_cut(engine,*,frontier,transcript,contract):
    native_mutable_state(engine)
    audio=[]
    for a in engine.segments:
        v=a.detach().cpu().contiguous().numpy()
        if str(v.dtype)!='float32' or v.ndim!=1:raise ValueError('frozen mono float32 source contract')
        audio.append(dict(samples=len(v),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
    context=dict(text=engine.context.text,prefix_token_ids=list(engine.context.prefix_token_ids),
                 token_ids=list(engine.context.as_token_ids()))
    s=dict(audio_segments=audio,tokens=[t.detach().cpu().tolist() for t in engine.tokens],context=context,
        last_attend_frame=engine.last_attend_frame,detected_language=engine.detected_language,
        initial_tokens=engine.initial_tokens.detach().cpu().tolist(),initial_token_length=engine.initial_token_length,
        sot_index=engine.sot_index,decoder_type=engine.decoder_type,contract=contract,
        frontier=int(frontier),transcript=transcript)
    return FeedbackCut(s)

def restore_cut(engine,cut:FeedbackCut,*,audio,contract):
    import numpy as np,torch
    s=cut.state
    if s['contract']!=contract:raise ValueError('native identity/config mismatch')
    engine._clean_cache()
    if s['detected_language']!='zh' or s['decoder_type']!='beam':raise ValueError('unsupported native cut')
    if not isinstance(s['last_attend_frame'],int):raise ValueError('invalid native alignment cursor')
    total=sum(a['samples'] for a in s['audio_segments']);pos=s['frontier']-total
    if pos<0 or s['frontier']>len(audio):raise ValueError('native buffer outside immutable source')
    segments=[]
    for a in s['audio_segments']:
        v=np.asarray(audio[pos:pos+a['samples']],dtype=np.float32);pos+=a['samples']
        if hashlib.sha256(v.tobytes()).hexdigest()!=a['sha256'] or a['dtype']!='float32':raise ValueError('native audio bytes changed')
        segments.append(torch.from_numpy(v.copy()))
    engine.segments=segments
    engine.tokens=[torch.tensor(t,dtype=torch.long,device=engine.model.device) for t in s['tokens']]
    engine.initial_tokens=torch.tensor(s['initial_tokens'],dtype=torch.long,device=engine.model.device)
    engine.initial_token_length=s['initial_token_length'];engine.sot_index=s['sot_index']
    engine.last_attend_frame=s['last_attend_frame'];engine.detected_language=s['detected_language']
    engine.context.text=s['context']['text'];engine.context.prefix_token_ids=list(s['context']['prefix_token_ids'])
    if engine.context.as_token_ids()!=s['context']['token_ids']:raise ValueError('context/tokenizer roundtrip changed')
    result=export_cut(engine,frontier=s['frontier'],transcript=s['transcript'],contract=contract)
    if not result.same(cut):raise ValueError('complete native state roundtrip changed')

def identity_prediction(engine,*,input_audio,current_tokens,token_len_before_decoding,**unused):
    """Private first-beam prediction through the same native selected-text append.

    No trusted future selection is available here. The real Authority function
    is untouched. Prefix decoding/cleanup follows the author interface, and the
    shared infer() tail retokenizes/appends the predicted continuation.
    """
    previous=engine.tokenizer.decode([int(t) for t in current_tokens[0,4:token_len_before_decoding].tolist() if t>=0]).strip()
    candidate=engine.tokenizer.decode([int(t) for t in current_tokens[0,4:].tolist() if t>=0]).strip()
    clean_previous=previous.rstrip('\ufffd');clean_candidate=candidate.rstrip('\ufffd')
    if not clean_candidate.startswith(clean_previous):
        raise ValueError('private first beam cannot represent the native confirmed prefix')
    prediction=clean_candidate[len(clean_previous):].strip()
    return dict(prompt=None,previous_transcription=previous,candidates=[candidate],
        corrected_appended_text=prediction,private_identity_prediction=True)

class NativeBridge:
    def __init__(self,*,author_root,asr_model,corrector_base,corrector_adapter,text_backbone,corrector_audio_processor,contract,role):
        import torch
        if role not in ('authority','private'):raise ValueError(role)
        self.role=role;self.contract=contract
        sys.path.insert(0,str(pathlib.Path(author_root).resolve()))
        from simul_whisper.simul_whisper import PaddedAlignAttWhisper
        import simul_whisper.whisper as native_whisper
        from simul_whisper.config import AlignAttConfig
        asr_model=pathlib.Path(asr_model).resolve(strict=True)
        if asr_model.name!='large-v2-zh.pt':raise ValueError('exact released native Chinese checkpoint required')
        cfg=AlignAttConfig(model_path=str(asr_model.parent/'large-v2.pt'),language='zh',audio_min_len=1.0,
            decoder_type='beam',beam_size=4,logdir=None,segment_length=.5,frame_threshold=20,
            rewind_threshold=1500,audio_max_len=30.0,cif_ckpt_path='',never_fire=False)
        # The pinned author loader first downloads generic large-v2 and then
        # replaces that path with cwd/large-v2-zh.pt plus its published key
        # conversion. Suppress only this redundant generic download and resolve
        # the exact original published checkpoint locally. Conversion and
        # alignment-head selection still execute in the unmodified loader.
        import os
        old_download=native_whisper._download;old_cwd=pathlib.Path.cwd()
        native_whisper._download=lambda *args,**kwargs:str(asr_model)
        try:
            os.chdir(asr_model.parent);self.engine=PaddedAlignAttWhisper(cfg)
        finally:
            native_whisper._download=old_download;os.chdir(old_cwd)
        self.engine.model.eval();self.corrector_model=None;self.corrector_processor=None
        if role=='authority':
            from transformers import AutoModel
            from peft import PeftModel
            # Only path resolution changes: the local original Meta backbone
            # is byte-matched to its public official Git-LFS pointer identity.
            cfg,self.corrector_processor=corrector_interface(corrector_base=corrector_base,
                text_backbone=text_backbone,corrector_audio_processor=corrector_audio_processor)
            m=AutoModel.from_pretrained(str(corrector_base),config=cfg,torch_dtype=torch.float32,
                trust_remote_code=True,local_files_only=True,device_map='cuda')
            self.corrector_model=PeftModel.from_pretrained(m,str(corrector_adapter),is_trainable=False,local_files_only=True)
            self.corrector_model.eval()
        else:
            import types
            self.engine._run_SpeechLM_error_corrector=types.MethodType(identity_prediction,self.engine)
            self.corrector_model=object()  # enables the unchanged native selected-feedback tail
        self.initial=export_cut(self.engine,frontier=0,transcript='',contract=contract)
    def initial_for(self,source_sha):
        s=self.initial.state;s['contract']=dict(self.contract,source_sha=source_sha);return FeedbackCut(s)
    def step(self,*,audio,start:FeedbackCut,end:int,is_last:bool):
        import numpy as np,torch
        if end<=start.frontier or end>len(audio):raise ValueError('invalid accepted audio interval')
        local_contract=start.state['contract']
        if {k:v for k,v in local_contract.items() if k!='source_sha'}!=self.contract:raise ValueError('changed frozen backend contract')
        restore_cut(self.engine,start,audio=audio,contract=local_contract)
        self.engine.insert_audio(torch.from_numpy(np.asarray(audio[start.frontier:end],dtype=np.float32).copy()))
        torch.cuda.synchronize();begin=time.perf_counter()
        # Exact native candidate/corrector choice and token feedback update.
        ids,g=self.engine.infer(is_last=is_last,start_time=begin,corrector_model=self.corrector_model,
            corrector_processor=self.corrector_processor,corrector_type='speechlm')
        torch.cuda.synchronize();finished=time.perf_counter()
        text=self.engine.tokenizer.decode(ids)
        cut=export_cut(self.engine,frontier=end,transcript=start.transcript+text,contract=local_contract)
        correction=g.get('error_corrector')
        changed=None;before=None;chosen=None
        if correction is not None:
            before=correction['candidates'][0]
            chosen=(correction['previous_transcription']+correction['corrected_appended_text']).strip()
            changed=before!=chosen
        record=dict(role=self.role,start=start.frontier,end=end,is_last=is_last,start_state=start.sha256,
            end_state=cut.sha256,token_ids=list(ids),text=text,selected_correction=correction,
            selection_changed=changed,top1_full_text=before,selected_full_text=chosen,
            model_start=begin,model_end=finished,model_seconds=finished-begin,
            inference='unmodified author PaddedAlignAttWhisper.infer',physical_early_exit=False,
            native_model_evaluated='starting_tokens' in g,
            private_prediction='first-beam identity through native selected-feedback append' if self.role=='private' else None)
        return cut,record
