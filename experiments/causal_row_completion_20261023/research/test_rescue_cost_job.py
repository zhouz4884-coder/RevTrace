import pytest
from rescue_cost_job import make_job

def recipe():return {'parent_frontier':96000,'target_frontier':128000,'parent_window':3,'target_window':4,'session_id':1,
 'source_id':'one','language':'English','parent_epoch':1,'parent_version':1,'parent_P':[2,3],'parent_contract_digest':'base'}

def test_FP32_placement_never_grants_state_write_permission():
    j=make_job(recipe(),bytes(128000*4),runtime_digest='FP32',contract_digest='cost-only',label='one',now=1.)
    assert j['role']=='proposal' and not j['Canonical_admission_or_publication_permitted']
    assert j['prompt_tokens']==[2,3] and j['audio_start_sample']==96000

def test_unreleased_audio_fails_before_generation():
    with pytest.raises(ValueError):make_job(recipe(),bytes(100000*4),runtime_digest='FP32',contract_digest='x',label='x',now=1)

def test_partial_final_window_uses_ceiling_not_rounding():
    r=recipe();r.update(target_frontier=97000,target_window=4)
    assert make_job(r,bytes(97000*4),runtime_digest='FP32',contract_digest='x',label='x',now=1)['end_window']==4

def test_future_or_rewound_parent_not_permitted():
    r=recipe();r['target_frontier']=95000
    with pytest.raises(ValueError):make_job(r,bytes(128000*4),runtime_digest='FP32',contract_digest='x',label='x',now=1)
