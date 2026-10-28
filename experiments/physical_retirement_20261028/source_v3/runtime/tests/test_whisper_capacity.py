"""Pure protocol fixtures: not model or GPU evidence."""
import pytest
from revtrace.whisper_adapter import conditioning_prompt_ids,TrustedWhisperRender


class Processor:
    class Tokenizer:
        eos_token_id=99
        def decode(self,z,**kw):return ' '.join(map(str,z))
        def encode(self,text,**kw):return [int(t) for t in text.split()]
    tokenizer=Tokenizer()
    def get_prompt_ids(self,history,**kw):return [900]+[int(t) for t in history.split()]


CFG=dict(policy='reserve-generation-tail-v1',max_target_positions=448,
         initial_decoder_ids=[901,902],previous_start_token_id=900)


def test_reserves_budget_and_preserves_prev_marker_without_modifying_history():
    history=' '.join(map(str,range(300)))
    p,plan=conditioning_prompt_ids(Processor(),history,256,CFG)
    assert len(p)==190 and p==[900]+list(range(111,300))
    assert len(plan['expected_initial_decoder_ids'])+256==448
    assert plan['raw_prompt_ids']==[900]+list(range(300))
    assert plan['trimmed']==111


def test_short_and_empty_context_keep_exact_native_prefix():
    assert conditioning_prompt_ids(Processor(),'1 2',256,CFG)[0]==[900,1,2]
    assert conditioning_prompt_ids(Processor(),'',256,CFG)[1]['expected_initial_decoder_ids']==[901,902]
    p,_=conditioning_prompt_ids(Processor(),'1 2',256,dict(policy='unbounded-native-v1'))
    assert p==[900,1,2]


def test_budget_and_prefix_fail_closed():
    with pytest.raises(ValueError):conditioning_prompt_ids(Processor(),'1',447,CFG)
    with pytest.raises(ValueError):conditioning_prompt_ids(Processor(),'1',0,CFG)
    with pytest.raises(ValueError):conditioning_prompt_ids(Processor(),'1',256,{**CFG,'previous_start_token_id':7})


def test_conditioning_truncation_does_not_truncate_canonical_parent_or_accept_short_stop():
    parent=list(range(110,410));job=dict(prompt_tokens=parent)
    r=TrustedWhisperRender(Processor(),256,CFG)
    p,text=r(job,[7,99])
    assert p==parent+[7,99] and job['prompt_tokens']==parent
    assert text.endswith('7 99')
    with pytest.raises(ValueError):r(job,[7])
