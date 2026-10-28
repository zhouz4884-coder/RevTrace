"""CPU contract checks. No model, tokenizer, torch or GPU imports."""
import copy,json,sys,types
from contextlib import nullcontext
import pytest
from diagnostic import validate_plan,terminal,conditioning,integrate,digest,REQUIRED_ORDER,words,errors

def plan():
    case=dict(original_job=dict(role='authority',audio_start_sample=8,audio_end_sample=16),
      original_result=dict(hit_token_limit=True,generated_tokens=256,model_input_audit=dict(dtype='float32',batch_rows=1,
        shape=[1,80,3000],actual_first_decoder_ids=[50360,42,50257,50362],actual_interval=[8,16])),
      expected_initial_decoder_ids_sha256=digest([50360,42,50257,50362]))
    return dict(schema='whisper-bad-data-nine-call-diagnostic-v1',
      calls=[dict(call_id=str(i),kind=k,case_id=c,repeat=r) for i,(k,c,r) in enumerate(REQUIRED_ORDER)],
      cases={name:copy.deepcopy(case) for name in ['word_short','word_full2s','blank_short']},
      gpu=1,dtype='float32',max_new_tokens=256,do_sample=False,
      warmup={'calls':1,'audio_samples':16000,'max_new_tokens':4,'history':[],
        'scope':'synthetic zero audio; separately counted, not a formal diagnostic call'},
      forbidden_features=['VAD','deduplication','repetition stopping','fallback','parameter sweep','holdout selection'])

def test_exact_nine_calls_and_explicit_warmup_cannot_expand():
    p=plan();validate_plan(p)
    p['calls'].append(dict(call_id='extra',kind='whole',case_id='blank_short',repeat=None))
    with pytest.raises(ValueError,match='exact six repeats'):validate_plan(p)
    p=plan();p['warmup']['calls']=2
    with pytest.raises(ValueError,match='exact separate warmup'):validate_plan(p)

def test_order_and_fixed_gpu_precision_budget_are_preserved():
    p=plan();p['calls'][0],p['calls'][1]=p['calls'][1],p['calls'][0]
    with pytest.raises(ValueError,match='exact six repeats'):validate_plan(p)
    p=plan();p['gpu']=0
    with pytest.raises(ValueError,match='GPU1'):validate_plan(p)
    p=plan();p['max_new_tokens']=32
    with pytest.raises(ValueError,match='greedy256'):validate_plan(p)

def test_original_decoder_list_is_bound_by_its_full_sha():
    p=plan();p['cases']['word_short']['original_result']['model_input_audit']['actual_first_decoder_ids'][1]=41
    with pytest.raises(ValueError,match='decoder ID'):validate_plan(p)

def test_no_text_stopping_and_blank_token_budget_is_a_full_terminal():
    full=[50257,50362,383]+[220]*255
    r=terminal(full,[50257,50362],50256,256)
    assert r['Z']==[383]+[220]*255 and r['hit_token_limit'] and not r['terminated_by_eos']
    assert r['generated_tokens']==256

def test_actual_prefix_must_match_and_short_incomplete_cannot_be_certified():
    with pytest.raises(ValueError,match='actual observed decoder'):terminal([50257,9,5,50256],[50257,50362],50256,256)
    with pytest.raises(ValueError,match='short/incomplete'):terminal([50257,50362,5],[50257,50362],50256,256)

def test_eos_is_included_and_any_raw_tail_is_retained():
    r=terminal([50257,50362,5,50256,50256],[50257,50362],50256,256)
    assert r['Z']==[5,50256] and r['raw_tail_after_first_EOS']==[50256]
    assert r['terminated_by_eos'] and not r['hit_token_limit']

def test_original_conditioning_keeps_internal_spaces_and_marker():
    class Processor:
        def get_prompt_ids(self,history,return_tensors):
            assert history=='one  two' and return_tensors=='np'
            return [50360,1,220,220,2]
    cfg=dict(max_target_positions=448,initial_decoder_ids=[50257,50362],previous_start_token_id=50360)
    prompt,initial,control=conditioning(Processor(),'one  two',256,cfg)
    assert prompt==[50360,1,220,220,2] and initial==prompt+[50257,50362] and control['trimmed']==0

def test_capacity_control_matches_original_suffix_rule_without_changing_budget():
    class Processor:
        def get_prompt_ids(self,*args,**kwargs):return [50360]+list(range(1,250))
    cfg=dict(max_target_positions=448,initial_decoder_ids=[50257,50362],previous_start_token_id=50360)
    prompt,initial,control=conditioning(Processor(),'nonempty',256,cfg)
    assert len(prompt)==190 and len(initial)==192 and prompt[0]==50360 and prompt[1:]==list(range(61,250))
    assert control['trimmed']==60

def test_gpu_energy_is_measured_only_over_bracketed_actual_interval():
    rows=[dict(t=0.,watts=100.),dict(t=1.,watts=120.),dict(t=2.,watts=140.)]
    assert integrate(rows,.5,1.5)==pytest.approx(120.)
    with pytest.raises(ValueError,match='bracket'):integrate(rows,-1,1)

def test_whole_source_quality_does_not_hide_inserted_repetition():
    assert errors(words('one two'),words('one two two two'))==2
    assert 100*errors(words('one'),words('one two three'))/len(words('one'))==200.

def test_returned_raw_sequence_is_saved_even_if_terminal_contract_fails(tmp_path,monkeypatch):
    from diagnostic import generate_one
    class Tensor:
        def __init__(self,value):self.value=value
        def to(self,*args,**kwargs):return self
        def float(self):return self
        def cpu(self):return self
        def detach(self):return self
        def numpy(self):return types.SimpleNamespace(tobytes=lambda:b'exact-CPU-mock')
        def tolist(self):return self.value
    callbacks=[]
    decoder=types.SimpleNamespace(register_forward_pre_hook=lambda callback,**kwargs:(callbacks.append(callback) or types.SimpleNamespace(remove=lambda:None)))
    def generate(**kwargs):
        callbacks[0](None,(),{'input_ids':Tensor([[1,2]])})
        return types.SimpleNamespace(sequences=[Tensor([1,2,7])])
    model=types.SimpleNamespace(model=types.SimpleNamespace(decoder=decoder),generate=generate)
    torch=types.SimpleNamespace(float32='float32',inference_mode=nullcontext,cuda=types.SimpleNamespace(synchronize=lambda:None))
    monkeypatch.setitem(sys.modules,'torch',torch)
    raw=tmp_path/'returned.json';processor=types.SimpleNamespace(tokenizer=types.SimpleNamespace(eos_token_id=9))
    packet=dict(x=types.SimpleNamespace(input_features=Tensor(None),attention_mask=Tensor(None)),prompt=[],initial=[1,2],history='')
    with pytest.raises(ValueError,match='short/incomplete'):
        generate_one(model,processor,packet,budget=256,raw_path=raw)
    saved=json.loads(raw.read_text());assert saved['raw_sequence']==[1,2,7]
    assert saved['status']=='RAW_NEURAL_RETURN_BEFORE_TERMINAL_OR_TEXT_CHECKS'
