from pathlib import Path
import json
import pytest
from common import Evidence,config_value,digest,file_sha
from paid_work import lease_pairs,union_overlap,stats
from task_truth import judge,prefix,prior_valid


def test_index_hash_and_containment(tmp_path):
    (tmp_path/'data').write_text('{}')
    i=tmp_path/'index.json';i.write_text(json.dumps({'files':[{'path':'data','bytes':2,'sha256':file_sha(tmp_path/'data')}]}))
    e=Evidence(tmp_path,[i]);assert e.json('data')=={} and len(e.used)==1
    (tmp_path/'data').write_text('[]')
    with pytest.raises(AssertionError):e.json('data')
    with pytest.raises(AssertionError):e.raw('../outside')


def test_config_paths_are_recursive():
    assert config_value({'a':[Path('one'),{'b':Path('two')}]})=={'a':['one',{'b':'two'}]}
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})


def test_lease_is_drained_not_first_row():
    t=[{'kind':'dispatch','operation':'w','observed_perf':1},
       {'kind':'row-complete','operation':'w','observed_perf':2},
       {'kind':'batch-drained','operation':'w','observed_perf':4}]
    assert lease_pairs(t)['w']==[(1,4)]
    with pytest.raises(AssertionError):lease_pairs(t[:2])
    with pytest.raises(AssertionError):lease_pairs([t[0],t[0],t[2]])


def test_overlap_is_union_not_sum():
    assert union_overlap(1,10,[(0,3),(2,4),(8,12)])==5
    assert union_overlap(5,7,[(0,3),(8,12)])==0
    assert stats([1,2,3])['p50']==2


def test_runbook_local_next_step_and_repair():
    s={'dependencies':{'inspect':[],'drain':['inspect'],'restart':['drain']}}
    p={'completed':[],'last_action':None};r={'action_budget':1}
    assert judge('runbook',s,p,r,{'completed':['inspect'],'last_action':'inspect'})['current_step_success']
    assert not judge('runbook',s,p,r,{'completed':['restart'],'last_action':'restart'})['current_output_valid']
    assert not judge('runbook',s,p,r,{'completed':['inspect','drain'],'last_action':'drain'})['current_step_success']
    assert prefix('runbook',s,{'completed':['inspect','restart']})==['inspect']
    assert not prior_valid('runbook',s,{'completed':[],'last_action':'restart'})
    assert prior_valid('runbook',s,p)


def test_resource_feasible_is_not_local_optimal():
    s={'capacity':5,'jobs':{'a':{'cost':3,'value':7},'b':{'cost':5,'value':8}}}
    p={'reserved':[],'remaining':5};r={'max_new_jobs':1}
    a=judge('resource_plan',s,p,r,{'reserved':['a'],'remaining':2})
    b=judge('resource_plan',s,p,r,{'reserved':['b'],'remaining':0})
    assert a['current_output_valid'] and a['transition_valid'] and not a['current_step_success']
    assert b['current_step_success']
    assert not judge('resource_plan',s,p,r,{'reserved':['a','b'],'remaining':-3})['current_output_valid']
    assert not judge('resource_plan',s,p,r,{'reserved':['unknown'],'remaining':5})['current_output_valid']
    assert not judge('resource_plan',s,p,r,{'reserved':[],'remaining':True})['schema_valid']
