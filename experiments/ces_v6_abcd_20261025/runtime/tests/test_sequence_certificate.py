import pytest
from revtrace.sequence_verifier import token_stop_certificate as cert
@pytest.mark.parametrize('candidate,pred,expected,reason',[
    ([1,2,9],[1,2,9],True,'eos'),([1,2],[1,2],False,'early-nonterminal-prefix'),
    ([1,9,2],[1,9,2],False,'tokens-after-stop'),([1,2,3,4],[1,2,3,4],True,'budget-cap'),
    ([1,2,3,4],[1,2,0,4],False,'argmax-mismatch'),([1,9],[1],False,'incomplete-prediction'),
    ([],[],False,'invalid-length'),([1,2,3,4,5],[1,2,3,4,5],False,'invalid-length')])
def test_all_tokens_and_stop(candidate,pred,expected,reason):
    assert cert(candidate,pred,eos_token_ids=[9],max_new_tokens=4)==(expected,reason)

def test_long_candidate_not_truncated_at_64():
    candidate=list(range(130))+[1000]
    assert cert(candidate,candidate,eos_token_ids=[1000],max_new_tokens=256)[0]
    changed=candidate.copy();changed[120]=-1
    assert not cert(candidate,changed,eos_token_ids=[1000],max_new_tokens=256)[0]
