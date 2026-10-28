"""Actual journal/consumer CPU fixtures; no neural/GPU claims."""
import importlib.util
from pathlib import Path
import pytest
from revtrace.composed_kernel import State,step,Denied,ReceiptBroker
from revtrace.kernel_runtime import KernelEnvelopeScheduler

spec=importlib.util.spec_from_file_location('envelope_fixture',Path(__file__).with_name('test_certified_envelope.py'))
env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)

def genesis():
    return dict(v=0,F=0,P='P0',Z='',textsha='0'*64,txn='')

def seeded():
    k,_=step(State('contract',1,1.),'recover-fact',dict(sid=0,fact=genesis()))
    items={0:dict(accepted=2,offered=2,reserved=2,prefix='a'*64)}
    k,_=step(k,'input-synced',dict(items=items,recovery=True))
    k,_=step(k,'worker-ready',dict(worker='a'))
    return k

def job(role='authority'):
    return dict(id='j',sid=0,role=role,parent=0,start=0,end=1,rootF=0,inputP='P0',identity='jobhash')

def dispatched(role='authority'):
    return step(seeded(),'dispatch',dict(worker='a',jobs=[job(role)]))[0]

@pytest.mark.parametrize('field,value',[('end',3),('start',1),('parent',1),('inputP','wrong'),('rootF',2)])
def test_illegal_dispatch_fails_closed(field,value):
    j=job();j[field]=value
    with pytest.raises(Denied):step(seeded(),'dispatch',dict(worker='a',jobs=[j]))

def test_no_worker_reuse_on_row_complete():
    k=dispatched();r=dict(id='j',worker='a',identity='jobhash',Z='Z',P='P1',textsha='1'*64)
    k,_=step(k,'row-complete',r)
    with pytest.raises(Denied):step(k,'dispatch',dict(worker='a',jobs=[dict(job(),id='j2')]))
    k,_=step(k,'batch-drained',dict(worker='a'));assert not k.leases
    with pytest.raises(Denied):step(k,'row-complete',r)

def test_private_cannot_install_even_complete_render():
    k=dispatched('proposal');k,_=step(k,'row-complete',dict(id='j',worker='a',identity='jobhash',Z='Z',P='P1',textsha='1'*64))
    with pytest.raises(Denied):step(k,'admission-request',dict(sid=0,job='j',operation='x',fact=dict(genesis(),v=1,F=1)))

def test_sync_install_apply_are_different_obligations():
    k=dispatched();k,_=step(k,'row-complete',dict(id='j',worker='a',identity='jobhash',Z='Z',P='P1',textsha='1'*64))
    f=dict(v=1,F=1,P='P1',Z='Z',textsha='1'*64,txn='t')
    with pytest.raises(Denied):step(k,'install',dict(sid=0,fact=f))
    k,_=step(k,'admission-request',dict(sid=0,job='j',operation='t',fact=f))
    k,_=step(k,'canonical-synced',dict(operation='t'))
    assert k.C[0]['v']==0 and k.V[0]['v']==0 and k.D[0][1]==f
    k,_=step(k,'install',dict(sid=0,fact=f));assert k.V[0]['v']==0

def test_receipt_fields_do_not_forge_boundary_identity():
    b=ReceiptBroker();r=b.issue('journal','op',{'v':1})
    with pytest.raises(Denied):b.take(object(),'journal','op')
    with pytest.raises(Denied):b.take(r,'worker','op')
    assert b.take(r,'journal','op')=={'v':1}
    with pytest.raises(Denied):b.take(r,'journal','op')

@pytest.mark.parametrize('method',['fine_fair','dgft_original','standard_fair','cde_full','standard_cde'])
def test_actual_full_scheduler_through_kernel(tmp_path,monkeypatch,method):
    monkeypatch.setattr(env,'CertifiedEnvelopeScheduler',KernelEnvelopeScheduler)
    s,c,events=env.build(tmp_path,method=method)
    for group in s.executors.values():
        for w in group:w.ready={};s.execution_ready(w)
    result=s.run()
    assert result['fine_window_accounting_complete']
    assert all(s.kernel.state.C[sid]['F']==v.state.audio_frontier_window for sid,v in s.sessions.items())
    assert all(s.kernel.state.V[sid]['F']==v.state.audio_frontier_window for sid,v in s.sessions.items())
    kinds={r['kind'] for r in s.kernel.trace}
    assert {'dispatch','row-complete','batch-drained','canonical-synced','view-applied'}<=kinds
    s.close()

def test_kernel_recovery_retains_accepted_input_before_ready(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'CertifiedEnvelopeScheduler',KernelEnvelopeScheduler)
    s,c,events=env.build(tmp_path)
    for group in s.executors.values():
        for w in group:w.ready={};s.execution_ready(w)
    s.run();states={sid:v.state.audio_frontier_window for sid,v in s.sessions.items()};s.close()
    r,c,_=env.build(tmp_path,clock=s.clock)
    assert not r.kernel.state.ready
    assert {sid:x['F'] for sid,x in r.kernel.state.C.items()}==states
    assert all(r.kernel.state.I[sid]['accepted']>=F for sid,F in states.items())
    assert all(r.kernel.state.V[sid]['F']==F for sid,F in states.items())
    r.close()

def test_initialization_failure_retains_debt_and_blocks_dispatch():
    k=seeded();k,_=step(k,'execution-failed',dict(worker='a'))
    with pytest.raises(Denied):step(k,'dispatch',dict(worker='a',jobs=[job()]))
    assert k.I[0]['accepted']==2 and k.C[0]['F']==0

def test_late_previous_epoch_event_cannot_mutate_new_owner():
    k=dispatched()
    with pytest.raises(Denied):step(k,'row-complete',dict(epoch=0,id='j',worker='a',identity='jobhash',Z='Z',P='P',textsha='1'*64))
    assert k.J['j']['result'] is None

def test_restore_must_retain_full_admission_identity_history():
    k=State('contract',2,2.);last=dict(v=2,F=2,P='P2',Z='Z',textsha='1'*64,txn='t2')
    with pytest.raises(Denied):step(k,'recover-fact',dict(sid=0,fact=last))

def test_batch_cannot_drain_before_row_or_be_relabelled():
    k=dispatched()
    with pytest.raises(Denied):step(k,'batch-drained',dict(worker='a'))
    with pytest.raises(Denied):step(k,'row-complete',dict(id='j',worker='b',identity='jobhash',Z='Z',P='P',textsha='1'*64))

def test_input_sync_receipt_must_match_requested_operation():
    k=seeded();items={0:dict(accepted=3,offered=3,reserved=3,prefix='a'*64)}
    with pytest.raises(Denied):step(k,'input-synced',dict(items=items))
    assert k.I[0]['accepted']==2
