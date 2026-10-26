"""Deterministic causal toy oracle. Not Transformer/GPU correctness evidence."""
from pathlib import Path
import sys,hashlib,random
import pytest
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.prefix_continuation import continuation_plan,stop_shape
EOS=101
def next_token(prefix,context,end):
    if len(prefix)>=end:return EOS
    return 1+hashlib.sha256(bytes(prefix)+bytes([context])).digest()[0]%90
def fresh(context,end,budget):
    z=[]
    while len(z)<budget:
        z.append(next_token(z,context,end))
        if z[-1]==EOS:break
    return z
@pytest.mark.parametrize('L',[1,17,128])
@pytest.mark.parametrize('budget',[1,7,16])
def test_prefix_crop_bonus_and_residual_match_exact_causal_oracle(L,budget):
    for end in [0,1,4,12]:
        ref=fresh(3,end,budget)
        for corrupt in [None,0,len(ref)//2,len(ref)-1]:
            draft=list(ref)
            if corrupt is not None:draft[corrupt]=100 if draft[corrupt]!=100 else 99
            predicted=[next_token(draft[:i],3,end) for i in range(len(draft)+1)]
            p=continuation_plan(draft,predicted,prompt_width=L,eos={EOS},budget=budget)
            z=p['selected_prefix'];assert p['cache_length']==L+p['accepted']
            while not p['terminal'] and len(z)<budget:
                z.append(next_token(z,3,end))
                if z[-1]==EOS:break
            assert z==ref and stop_shape(z,{EOS},budget)
def test_empty_alignment_and_partial_draft():
    p=continuation_plan([], [9],prompt_width=5,eos={EOS},budget=4)
    assert p['cache_length']==5 and p['selected_prefix']==[9]
    with pytest.raises(ValueError):continuation_plan([1],[1],prompt_width=1,eos={EOS},budget=4)
def test_full_eos_never_appends_bonus():
    p=continuation_plan([5,EOS],[5,EOS,77],prompt_width=9,eos={EOS},budget=4)
    assert p['bonus'] is None and p['terminal'] and p['selected_prefix']==[5,EOS]
