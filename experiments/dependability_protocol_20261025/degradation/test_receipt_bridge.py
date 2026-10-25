import importlib.util,sys
from pathlib import Path
import pytest
HERE=Path(__file__).parent
def load(name):
    s=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
core=load('envelope_core');logs=load('input_journal')

def test_intent_alone_neither_mints_accepted_debt_nor_dispatch_permission():
    b=core.CreditBook(6);b.offer(0,2);b.reserve(0,6)
    assert b.acceptance_intent(0,2)==dict(session_id=0,from_sample=0,to_sample=2)
    assert b.session(0).accepted==0
    with pytest.raises(TypeError):b.accept_released(0,2)
    with pytest.raises(ValueError):b.accept_released(0,2,durable_receipt={})
    assert b.debt==0

def test_real_input_sync_precedes_accepted_frontier(tmp_path):
    b=core.CreditBook(6);b.offer(0,2);b.reserve(0,6)
    with logs.InputJournal(tmp_path/'i.wal',manifest_sha256='a'*64,policy_sha256='b'*64) as j:
        r=core.accept_durably(b,j,0,2,'c'*64)
        assert r['decision_id']==j.receipts[0,2]['decision_id']
        assert b.session(0).accepted==j.accepted[0]==2 and j.fsync_calls==2

def test_sync_failure_cannot_make_input_dispatch_eligible(tmp_path):
    b=core.CreditBook(6);b.offer(0,2);b.reserve(0,6)
    with logs.InputJournal(tmp_path/'i.wal',manifest_sha256='a'*64,policy_sha256='b'*64) as j:
        def fail():raise OSError('CPU fsync failure before acceptance ACK')
        j._sync=fail
        with pytest.raises(OSError):core.accept_durably(b,j,0,2,'c'*64)
        assert b.session(0).accepted==0 and b.debt==0

def test_future_or_unreserved_prefix_rejected_before_journal_write(tmp_path):
    b=core.CreditBook(6);b.offer(0,2);b.reserve(0,6)
    with logs.InputJournal(tmp_path/'i.wal',manifest_sha256='a'*64,policy_sha256='b'*64) as j:
        before=(tmp_path/'i.wal').read_bytes()
        with pytest.raises(ValueError):core.accept_durably(b,j,0,4,'c'*64)
        assert (tmp_path/'i.wal').read_bytes()==before and b.debt==0
