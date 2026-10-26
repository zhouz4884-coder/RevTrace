"""Additional CPU interleavings against frozen runtime, never GPU evidence.

These tests live outside the frozen GPU source; they do not alter its bytes.
"""
from pathlib import Path
import sys,importlib.util
import pytest
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.kernel_runtime import KernelEnvelopeScheduler
from revtrace.composed_kernel import Denied,State,step
spec=importlib.util.spec_from_file_location('cpu_native_fixture',W/'runtime/tests/test_certified_envelope.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

def ready(s):
    for group in s.executors.values():
        for w in group:w.ready={};s.execution_ready(w)

@pytest.mark.parametrize('point',['input-ack','commit'])
def test_actual_journals_survive_cpu_abort_at_composed_boundary(tmp_path,monkeypatch,point):
    monkeypatch.setattr(f,'CertifiedEnvelopeScheduler',KernelEnvelopeScheduler)
    class Stop(RuntimeError):pass
    def abort(e):
        if e['kind']==point:raise Stop('CPU abort, not SIGKILL/GPU')
    s,c,events=f.build(tmp_path,emit_hook=abort);ready(s)
    with pytest.raises(Stop):s.run()
    before={sid:b.accepted for sid,b in s.book.sessions.items()};assert max(before.values())>0
    orig=s.origin;clock=s.clock;s.close();clock.sleep(.08)
    r,c,es=f.build(tmp_path,clock=clock)
    assert r.owner_epoch==2 and r.origin==orig
    assert all(r.book.session(sid).accepted>=A for sid,A in before.items())
    assert not r.kernel.state.ready
    # Restored facts apply independently of execution readiness.
    assert all(r.kernel.state.V[sid]['F']==x.state.audio_frontier_window for sid,x in r.sessions.items())
    ready(r);out=r.run();assert out['fine_window_accounting_complete']
    for sid in r.sessions:
        b=r.book.session(sid)
        # Original-clock expiration may explicitly reject a never-accepted
        # session. It may not erase an accepted obligation.
        assert r.kernel.state.C[sid]['F']==b.accepted
        assert b.accepted==1920 or (b.accepted==0 and b.rejected and before[sid]==0)
    r.close()
    # Legal baseline oracle, same CPU inputs/delays/original clock and abort.
    native=W/'runtime/src/revtrace/certified_envelope.py'
    from revtrace.certified_envelope import CertifiedEnvelopeScheduler
    monkeypatch.setattr(f,'CertifiedEnvelopeScheduler',CertifiedEnvelopeScheduler)
    oracle_path=tmp_path/'native_oracle';oracle_path.mkdir()
    n,_,_=f.build(oracle_path,emit_hook=abort)
    with pytest.raises(Stop):n.run()
    n.close();n.clock.sleep(.08)
    nr,_,_=f.build(oracle_path,clock=n.clock);nr.run()
    assert {sid:(b.accepted,b.rejected) for sid,b in nr.book.sessions.items()}=={
        sid:(b.accepted,b.rejected) for sid,b in r.book.sessions.items()}
    nr.close()

@pytest.mark.parametrize('field,value',[('contract','other'),('epoch',0),('owner',0.)])
def test_old_boundary_receipt_cannot_cross_recovery(field,value):
    k=State('pinned',1,1.)
    with pytest.raises(Denied):step(k,'worker-ready',dict(worker='a',**{field:value}))

def test_exact_chain_private_receipt_after_canonical_advance():
    import hashlib
    textsha=lambda t:hashlib.sha256(t.encode()).hexdigest()
    g=dict(v=0,F=0,P='p0',Z='',textsha=textsha(''),txn='')
    k,_=step(State('c',1,1.),'recover-fact',dict(sid=0,fact=g))
    k,_=step(k,'input-synced',dict(items={0:dict(accepted=2,offered=2,reserved=2,prefix='a'*64)},recovery=True))
    for w in ['a','p']:k,_=step(k,'worker-ready',dict(worker=w))
    def dispatch(k,w,jid,role,start,end,root,P):
        j=dict(id=jid,sid=0,role=role,parent=0,start=start,end=end,rootF=root,inputP=P,identity=jid)
        return step(k,'dispatch',dict(worker=w,jobs=[j]))[0]
    def row(k,w,jid,P):return step(k,'row-complete',dict(id=jid,worker=w,identity=jid,P=P,Z='z',textsha=textsha(P)))[0]
    k=dispatch(k,'p','p1','proposal',0,1,0,'p0');k=row(k,'p','p1','p1')
    k,_=step(k,'batch-drained',dict(worker='p'))
    k=dispatch(k,'p','p2','proposal',0,2,1,'p1');k=row(k,'p','p2','p2')
    k=dispatch(k,'a','a1','authority',0,1,0,'p0');k=row(k,'a','a1','p1')
    fact=dict(v=1,F=1,P='p1',Z='z',textsha=textsha('p1'),txn='t1')
    k,_=step(k,'admission-request',dict(sid=0,job='a1',operation='t1',fact=fact))
    k,_=step(k,'canonical-synced',dict(operation='t1'));k,_=step(k,'install',dict(sid=0,fact=fact))
    k,_=step(k,'publish',dict(sid=0,key='c1',publication=dict(canonical=True,fact=fact)))
    v=dict(v=1,F=1,P='p1',visible=1,text='p1',revision=1,private=None)
    k,_=step(k,'apply-request',dict(sid=0,key='c1',view=v,operation='v1'));k,_=step(k,'view-applied',dict(operation='v1'))
    k,_=step(k,'publish',dict(sid=0,key='late',publication=dict(canonical=False,job='p2',end=2,textsha=textsha('p2'))))
    v=dict(v=1,F=1,P='p1',visible=2,text='p2',revision=2,private='p2')
    k,_=step(k,'apply-request',dict(sid=0,key='late',view=v,operation='v2'));k,_=step(k,'view-applied',dict(operation='v2'))
    assert k.V[0]['visible']==2 and k.C[0]['F']==1
    # Private visibility does not make this result eligible for state write.
    with pytest.raises(Denied):step(k,'admission-request',dict(sid=0,job='p2',operation='bad',fact=dict(fact,v=2,F=2,txn='bad')))

@pytest.mark.parametrize('boundary',['dispatch','admission-request','install','apply-request','input-synced'])
def test_kernel_is_a_real_effect_gate_not_a_trace_observer(tmp_path,monkeypatch,boundary):
    monkeypatch.setattr(f,'CertifiedEnvelopeScheduler',KernelEnvelopeScheduler)
    s,c,events=f.build(tmp_path);ready(s);actual=s.kernel.event;blocked=[]
    def deny(source,kind,operation,payload):
        if kind==boundary:
            blocked.append((source,operation));raise Denied('external CPU gate injection')
        return actual(source,kind,operation,payload)
    s.kernel.event=deny
    try:
        with pytest.raises(Denied):s.run()
        assert blocked
        if boundary=='dispatch':assert not any(e['kind']=='batch-dispatched' for e in events)
        if boundary=='admission-request':assert all(x.checkpoint_id==0 for x in s._journal.states())
        if boundary=='install':
            assert any(x.checkpoint_id>0 for x in s._journal.states())
            assert all(x.state.checkpoint_id==0 for x in s.sessions.values())
        if boundary=='apply-request':assert all(x['certified_frontier']==0 for x in c.rows)
        if boundary=='input-synced':
            assert all(b.accepted==0 for b in s.book.sessions.values())
            assert not any(e['kind']=='input-ack' for e in events)
    finally:s.close()

def test_post_selection_content_substitution_cannot_be_laundered_by_new_consistent_certificate(tmp_path,monkeypatch):
    """CPU integration-fault control, NOT a compromised-Authority defense.

    After a legitimate selection receipt, substitute Z/P/Y consistently before
    WAL preparation. Local render and a newly built hash certificate alone
    would not establish that these were the originally selected contents.
    """
    from revtrace.certified_display import validate_bound_text
    monkeypatch.setattr(f,'CertifiedEnvelopeScheduler',KernelEnvelopeScheduler)
    s,c,events=f.build(tmp_path);ready(s);boundary=s.protocol_row;changed=[]
    def replace_after_binding(name,job,result):
        boundary(name,job,result)
        if job['role']=='authority':
            result.update(token_ids=[999],state_tokens=[999],text='999',generated_tokens=1)
            result['text_binding']=validate_bound_text(s.trusted_render,job,result)
            changed.append(job['job_id'])
    s.protocol_row=replace_after_binding
    try:
        with pytest.raises(Denied,match='selected content changed'):s.run()
        assert changed and all(st.checkpoint_id==0 for st in s._journal.states())
    finally:s.close()
