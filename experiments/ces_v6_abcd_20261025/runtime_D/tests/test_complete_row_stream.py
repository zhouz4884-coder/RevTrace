"""CPU token-event fixtures only, not generated model outputs."""
import pytest
from revtrace.row_stream import CompleteRowStream
class V:
    def __init__(self,v):self.v=v
    def tolist(self):return self.v
def stream(indices=(0,1),budget=3):
    calls=[];s=CompleteRowStream(indices,eos=[9],budget=budget,on_complete=lambda i,Z,t:calls.append((i,Z,t)))
    return s,calls
def test_complete_row_precedes_other_rows_without_consuming_their_prefix():
    s,c=stream();s.put(V([[1],[2]]));s.put(V([9,3]));assert len(c)==1 and c[0][:2]==(0,(9,))
    s.put(V([0,9]));s.end();assert len(c)==2
def test_fallback_subset_keeps_original_row_indices():
    s,c=stream((1,3));s.put(V([[1],[2]]));s.put(V([9,9]));s.end();assert [x[0] for x in c]==[1,3]
def test_budget_termination_retains_complete_capped_sequence():
    s,c=stream((0,),2);s.put(V([[1]]));s.put(V([2]));s.put(V([3]));s.end();assert c[0][1]==(2,3)
def test_early_nonteminal_prefix_never_completes():
    s,c=stream((0,));s.put(V([[1]]));s.put(V([2]));assert not c
    with pytest.raises(ValueError):s.end()
def test_prompt_stop_token_is_not_generated_eos():
    s,c=stream((0,));s.put(V([[9]]));assert not c
    s.put(V([9]));s.end();assert len(c)==1
def test_wrong_physical_width_rejected_before_emission():
    s,c=stream()
    with pytest.raises(ValueError):s.put(V([[1]]))
    assert not c
