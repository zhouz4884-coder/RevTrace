from copy import deepcopy
from dataclasses import asdict
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent/'runtime/src'))
from revtrace.composed_kernel import State,step,Denied
from revtrace.retirement_runtime import reason_for


def state():
    k=State('c',1,0.)
    f=dict(v=1,F=2,P='selected',Z='z',textsha='x'*64,txn='a')
    k.C={0:f};k.D={0:{1:f}};k.V={0:dict(v=1,F=2,visible=2)}
    k.I={0:dict(accepted=4,offered=4,reserved=4)};k.restored_input=True
    k.J={'p':dict(id='p',sid=0,role='proposal',worker='p0',identity='i',end=2,result=None)}
    k.leases={'p0':['p']}
    return k


@pytest.mark.parametrize('incremental',[False,True])
def test_requested_cancel_does_not_release_lease_or_create_selection(incremental):
    original=state();k,_=step(original,'cancel-request',dict(id='p',worker='p0',identity='i',reason='trusted-coverage',requested_perf=3.),incremental=incremental)
    assert k.leases==original.leases and k.J['p']['result'] is None
    assert k.C==original.C and k.D==original.D and k.I==original.I
    assert 'cancel_intent' not in original.J['p']
    with pytest.raises(Denied):step(k,'batch-drained',dict(worker='p0'),incremental=incremental)
    k,_=step(k,'row-cancelled',dict(id='p',worker='p0',identity='i',reason='trusted-coverage',request_id='r',terminal_digest='d',requested_perf=3.,acknowledged_perf=4.,emitted_perf=4.1,decoded_tokens=3),incremental=incremental)
    assert k.J['p']['result'] is None and k.C==original.C and k.I==original.I
    k,_=step(k,'batch-drained',dict(worker='p0'),incremental=incremental)
    assert not k.leases
    with pytest.raises(Denied):step(k,'publish',dict(sid=0,key='bad',publication=dict(canonical=False,job='p',end=2,textsha='x'*64)))


def test_authority_and_partial_cancelled_output_never_authorize():
    k=state();k.J['p']['role']='authority'
    with pytest.raises(Denied):step(k,'cancel-request',dict(id='p',worker='p0',identity='i',reason='trusted-coverage',requested_perf=3.))
    k=state();k,_=step(k,'cancel-request',dict(id='p',worker='p0',identity='i',reason='trusted-coverage',requested_perf=3.))
    payload=dict(id='p',worker='p0',identity='i',reason='trusted-coverage',request_id='r',terminal_digest='d',requested_perf=3.,acknowledged_perf=4.,emitted_perf=4.1,decoded_tokens=3,Z='partial')
    with pytest.raises(Denied):step(k,'row-cancelled',payload)


def test_coverage_not_old_parent_is_sufficient_invalidation():
    j=dict(role='proposal',parent=1,branch_generation=2,audio_end_sample=10)
    options=dict(frontier=6,parent=3,generation=2,now=5.,started=4.,watchdog_seconds=2.)
    assert reason_for('causal',j,**options) is None
    assert reason_for('covered',j,**options) is None
    assert reason_for('parent',j,**options)=='parent-version-superseded'
    assert reason_for('causal',j,**{**options,'frontier':10})=='trusted-coverage'
    assert reason_for('causal',j,**{**options,'generation':3})=='retired-generation'
    assert reason_for('watchdog',j,**{**options,'now':6.})=='watchdog-timeout'
    assert reason_for('watchdog',j,**{**options,'started':None,'now':100.}) is None
