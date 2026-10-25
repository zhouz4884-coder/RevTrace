import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('cde_input_journal',Path(__file__).with_name('input_journal.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def open_log(path,**kw):return m.InputJournal(path,manifest_sha256=kw.get('manifest','a'*64),policy_sha256='b'*64)
def accept(log,**kw):return log.accept(0,from_sample=kw.get('start',0),to_sample=kw.get('end',2),prefix_sha256=kw.get('sha','c'*64))

def test_accepted_prefix_survives_and_retry_never_adds_a_record(tmp_path):
    p=tmp_path/'input.wal'
    with open_log(p) as j:
        r=accept(j);assert j.accepted=={0:2} and j.fsync_calls==2
    with open_log(p) as j:
        before=p.read_bytes();again=accept(j)
        assert again['decision_id']==r['decision_id'] and again['idempotent_input_retry']
        assert p.read_bytes()==before and j.accepted=={0:2}

def test_changed_retry_and_missing_prefix_fail_closed(tmp_path):
    with open_log(tmp_path/'i.wal') as j:
        accept(j)
        with pytest.raises(m.InputJournalError):accept(j,sha='d'*64)
        with pytest.raises(m.InputJournalError):accept(j,start=4,end=6)

@pytest.mark.parametrize('tail',[b'\0',b'\0\0\0',b'\0\0\x01\0torn'])
def test_only_partial_tail_is_removed(tmp_path,tail):
    p=tmp_path/'i.wal'
    with open_log(p) as j:accept(j)
    before=p.read_bytes()
    with p.open('ab') as f:f.write(tail);f.flush();__import__('os').fsync(f.fileno())
    with open_log(p) as j:
        assert j.accepted=={0:2} and j.truncated_tail_bytes==len(tail)
        assert p.read_bytes()==before

def test_complete_bad_frame_never_becomes_a_torn_tail(tmp_path):
    p=tmp_path/'i.wal'
    with open_log(p) as j:accept(j)
    raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
    with pytest.raises(m.InputJournalError,match='checksum'):open_log(p)

def test_sync_failure_returns_no_receipt_and_poisoned_writer_stops(tmp_path):
    with open_log(tmp_path/'i.wal') as j:
        def fail():raise OSError('CPU injected synchronization failure')
        j._sync=fail
        with pytest.raises(OSError):accept(j)
        assert j.accepted=={} and j.poisoned
        with pytest.raises(m.InputJournalError):accept(j)

def test_context_identity_and_second_owner_checked(tmp_path):
    p=tmp_path/'i.wal'
    with open_log(p):
        with pytest.raises((OSError,m.InputJournalError)):open_log(p)
    with pytest.raises(m.InputJournalError,match='context'):open_log(p,manifest='d'*64)
