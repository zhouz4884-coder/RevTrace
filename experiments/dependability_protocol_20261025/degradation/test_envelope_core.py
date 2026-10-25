from dataclasses import fields
import importlib.util
from pathlib import Path
import hashlib,random,sys
import pytest
spec=importlib.util.spec_from_file_location('envelope_core',Path(__file__).with_name('envelope_core.py'))
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def accept(b,sid,F):
    # Symbolic trusted-journal receipt for CPU accounting exploration only.
    j=b.acceptance_intent(sid,F)
    r=dict(j,kind='accepted-input',sequence=len(b.events)+1,prefix_sha256='c'*64,
        decision_id=hashlib.sha256(str((sid,j['from_sample'],F)).encode()).hexdigest())
    b.accept_released(sid,F,durable_receipt=r)

def test_whole_interval_credit_avoids_partial_reservation_deadlock():
    b=m.CreditBook(6)
    for sid in range(3):b.offer(sid,2)
    assert b.reserve(0,6)
    assert not b.reserve(1,6) and not b.reserve(2,6)
    accept(b,0,2)
    with pytest.raises(ValueError):accept(b,0,6)
    b.offer(0,6);accept(b,0,6)
    b.observe_admission(0,epoch=1,version=1,parent_frontier=0,frontier=6,receipt='real-owner-receipt-fixture')
    assert b.debt==b.committed_credit==0 and b.reserve(1,6)

def test_rejection_cannot_erase_existing_accepted_debt():
    b=m.CreditBook(6);b.offer(0,2);b.reserve(0,6);accept(b,0,2)
    with pytest.raises(ValueError,match='erased'):b.reject_unaccepted(0,'overload')
    assert b.debt==2
    b.offer(1,2);b.reject_unaccepted(1,'new-session quota')
    b.offer(1,10)
    assert b.session(1).offered==10 and b.session(1).accepted==0

def test_eof_shrinks_only_unused_reserved_credit():
    b=m.CreditBook(12);b.offer(0,2);b.reserve(0,6);accept(b,0,2)
    b.offer(0,3,eof=True);assert b.committed_credit==3
    accept(b,0,3)
    with pytest.raises(ValueError,match='EOF'):b.offer(0,4)
    assert b.debt==3

@pytest.mark.parametrize('attack',['epoch','version','frontier','receipt'])
def test_bad_progress_notice_does_not_mint_credit(attack):
    b=m.CreditBook(6);b.offer(0,6);b.reserve(0,6);accept(b,0,6)
    args=dict(epoch=1,version=1,parent_frontier=0,frontier=6,receipt='fixture')
    args[attack]={'epoch':0,'version':2,'frontier':7,'receipt':''}[attack]
    with pytest.raises(ValueError):b.observe_admission(0,**args)
    assert b.debt==6

def test_old_consumer_ack_never_becomes_fresh_coverage():
    b=m.CreditBook(12);b.offer(0,12);b.reserve(0,6);accept(b,0,6)
    b.observe_consumer(0,epoch=1,canonical_version=0,legal_frontier=6)
    assert b.valid_private_frontier(0)==6
    b.observe_admission(0,epoch=1,version=1,parent_frontier=0,frontier=6,receipt='fixture')
    assert b.valid_private_frontier(0)==0

def pressure(age=0,**kwargs):
    values=dict(pending_ingress=False,oldest_uncertified_age=age,actual_private_queue=0,
        actual_authority_queue=0,private_lease_active=False,authority_lease_active=False,
        consumer_caught_up=True,owner_and_input_recovered=True);values.update(kwargs)
    return m.ObservedPressure(**values)

def test_modes_never_create_write_permission_or_cancel_a_lease():
    b=m.CreditBook(6);p=m.EnvelopePolicy()
    assert p.decide(b,pressure()).mode==m.Mode.NORMAL
    assert p.decide(b,pressure(5)).mode==m.Mode.DEGRADED
    action=p.decide(b,pressure(9,private_lease_active=True))
    assert action.mode==m.Mode.CERTIFIED_ONLY and action.issue_authority
    assert not action.issue_private and not action.publish_provisional
    assert not action.cancel_running_GPU and not action.bypass_admission
    assert p.decide(b,pressure(3)).mode==m.Mode.CERTIFIED_ONLY
    assert p.decide(b,pressure(1)).mode==m.Mode.NORMAL

def test_recovery_waits_for_both_actual_input_and_consumer():
    b=m.CreditBook(6);p=m.EnvelopePolicy();p.begin_recovery()
    a=p.decide(b,pressure(owner_and_input_recovered=True,consumer_caught_up=False))
    assert a.mode==m.Mode.RECOVERY and not a.issue_authority
    a=p.decide(b,pressure());assert a.mode==m.Mode.NORMAL

def test_backpressure_keeps_authority_drain_and_does_not_relabel_debt():
    b=m.CreditBook(6);b.offer(0,2);b.reserve(0,6);accept(b,0,2)
    a=m.EnvelopePolicy().decide(b,pressure(pending_ingress=True))
    assert a.mode==m.Mode.BACKPRESSURE and a.issue_authority and not a.accept_new_credit
    assert b.session(0).certified==0

def test_policy_input_has_no_future_or_fault_label():
    assert not any('fault' in f.name or 'future' in f.name or 'output' in f.name for f in fields(m.ObservedPressure))

def test_seeded_cpu_conservation_many_interleavings_not_gpu():
    rng=random.Random(20261025);b=m.CreditBook(24)
    for _ in range(5000):
        sid=rng.randrange(8);s=b.session(sid)
        if rng.random()<.5:b.offer(sid,s.offered+rng.randrange(4))
        if b.reserve(sid,6):
            target=min(s.offered,s.reserved)
            accept(b,sid,target)
            if s.accepted==s.reserved and s.accepted>s.certified and rng.random()<.4:
                b.observe_admission(sid,epoch=1,version=s.version+1,parent_frontier=s.certified,
                    frontier=s.accepted,receipt=f'fixture-{sid}-{s.version+1}')
        b.check()
