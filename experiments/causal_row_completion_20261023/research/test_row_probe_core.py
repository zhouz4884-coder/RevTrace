import pytest
from row_probe_core import RowFinalStream,result_equal,observer_lead

class V:
    def __init__(self,x):self.x=x
    def tolist(self):return self.x

def make(n=2,budget=3):
    events=[];tick=iter(range(100))
    s=RowFinalStream([str(i) for i in range(n)],eos=[9],budget=budget,events=events,
      render=lambda j,z:(z,str(z)),phase='CPU_FIXTURE',clock=lambda:next(tick))
    return s,events

def test_row_final_does_not_free_worker():
    s,e=make();s.put(V([[1],[2]]));s.put(V([9,3]));assert len(e)==1 and not e[0]['worker_reusable']
    s.put(V([0,9]));s.end();assert len(e)==2 and e[0]['Z']==[9]

def test_budget_is_complete_but_not_eos():
    s,e=make(1,2);s.put(V([[1]]));s.put(V([2]));s.put(V([3]));s.end()
    assert e[0]['stop_kind']=='budget' and e[0]['Z']==[2,3]

def test_prompt_eos_is_not_generation():
    s,e=make(1);s.put(V([[9,9]]));assert not e
    s.put(V([9]));s.end();assert len(e)==1

def test_incomplete_is_not_row_final():
    s,e=make(1);s.put(V([[1]]));s.put(V([2]));assert not e
    with pytest.raises(ValueError):s.end()

def test_wrong_batch_binding():
    s,e=make()
    with pytest.raises(ValueError):s.put(V([[1]]))

def test_wrong_decode_width():
    s,e=make();s.put(V([[1],[2]]))
    with pytest.raises(ValueError):s.put(V([9]))

def test_duplicate_row_identity():
    with pytest.raises(ValueError):RowFinalStream(['x','x'],eos=[9],budget=2,events=[],render=None,phase='CPU')

def test_exact_content_and_terminal_comparison():
    a={'token_ids':[9],'state_tokens':[1],'text':'a','terminated_by_eos':True,'hit_token_limit':False}
    assert result_equal(a,dict(a));assert not result_equal(a,dict(a,text='b'))

def test_lead_is_not_new_saved_serving_time():
    assert observer_lead({'complete_render_perf':2},5)==3
