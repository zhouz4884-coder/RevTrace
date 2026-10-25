from pathlib import Path
from types import SimpleNamespace
import copy,time
import pytest
from revtrace.degradation_state import CreditBook
from revtrace.input_debt_journal import InputJournal,InputJournalError
from revtrace.envelope_display import EnvelopeView
from revtrace.certified_display import RealtimeConsumer

def snapshot():
    b=CreditBook(12);b.offer(0,3,eof=True);b.reserve(0,6)
    s=b.session(0);s.accepted=3;s.accepted_prefix_sha256='c'*64
    b.offer(1,2);b.reject_unaccepted(1,'explicit source refusal')
    return b.snapshot(100.)
def journal(p):return InputJournal(p,manifest_sha256='a'*64,policy_sha256='b'*64)

def test_whole_reservation_eof_and_rejection_survive_one_atomic_snapshot(tmp_path):
    p=tmp_path/'input.wal';snap=snapshot()
    with journal(p) as j:r=j.checkpoint(snap)
    with journal(p) as j:
        assert j.snapshot==snap and j.accepted=={0:3,1:0}
        states={0:SimpleNamespace(audio_frontier_window=0,checkpoint_id=0),1:SimpleNamespace(audio_frontier_window=0,checkpoint_id=0)}
        b=CreditBook.restore(j.snapshot,states,epoch=2,origin_perf=100.)
        assert b.session(1).rejected and b.committed_credit==3 and b.session(0).eof

@pytest.mark.parametrize('attack',['accepted','rejection','origin','budget','prefix','epoch'])
def test_semantic_bad_snapshot_rejected_before_append(tmp_path,attack):
    p=tmp_path/'i.wal'
    with journal(p) as j:
        snap=snapshot();j.checkpoint(snap);before=p.read_bytes();bad=copy.deepcopy(snap)
        if attack=='accepted':bad['sessions']['0']['accepted']=2
        if attack=='rejection':bad['sessions']['1']['rejected']=False
        if attack=='origin':bad['origin_perf']=101.
        if attack=='budget':bad['budget']=13
        if attack=='prefix':bad['sessions']['0']['accepted_prefix_sha256']='d'*64
        if attack=='epoch':bad['epoch']=0
        with pytest.raises(InputJournalError):j.checkpoint(bad)
        assert p.read_bytes()==before

def test_canonical_recovery_may_advance_but_never_exceed_accepted_audio():
    snap=snapshot();states={0:SimpleNamespace(audio_frontier_window=3,checkpoint_id=1),1:SimpleNamespace(audio_frontier_window=0,checkpoint_id=0)}
    b=CreditBook.restore(snap,states,epoch=2,origin_perf=100.)
    assert b.debt==0 and b.committed_credit==0
    states[0].audio_frontier_window=4
    with pytest.raises(ValueError):CreditBook.restore(snap,states,epoch=2,origin_perf=100.)

def test_full_interval_reservations_allow_fair_buffered_lead_not_one_interval_only():
    b=CreditBook(12);b.offer(0,12);assert b.reserve(0,6)
    b.session(0).accepted=6;b.session(0).accepted_prefix_sha256='c'*64
    assert b.reserve(0,6) and b.session(0).reserved==12
    assert b.committed_credit==12

def test_actual_thread_applies_stream_and_certified_only_control(tmp_path):
    c=RealtimeConsumer(tmp_path/'consumer.jsonl',strict_bound=True,
        view=EnvelopeView(policy='two_lane',strict_bound=True))
    t=time.perf_counter();c.put(dict(kind='run-start',t0_perf=t,contract_digest='C'))
    c.put(dict(kind='view-mode',mode='RECOVERY',session_id=0,displayed=0.,time=0.,
        display_revision=1,contract_epoch=1,contract_digest='C'))
    c.close();acks=c.drain_acks()
    assert isinstance(acks[0],dict) and acks[0]['kind']=='stream-start-applied'
    assert acks[1].envelope_mode=='RECOVERY'
    assert c.rows[0]['valid_visible_frontier']==c.rows[0]['certified_frontier']==0
    assert c.rows[0]['no_certified_snapshot_yet']
