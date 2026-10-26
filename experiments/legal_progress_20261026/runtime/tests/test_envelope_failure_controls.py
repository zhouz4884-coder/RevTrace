"""Before/after CPU counterexamples and live snapshot failure controls."""
import importlib.util
from dataclasses import replace
from pathlib import Path
import pytest
from revtrace.certified_display import ConsumerAck
s=importlib.util.spec_from_file_location('failed_env_fixture',Path(__file__).with_name('test_certified_envelope.py'))
f=importlib.util.module_from_spec(s);s.loader.exec_module(f)

def test_old_completed_cursor_counterexample_and_repaired_same_input(tmp_path):
    original,_,_=f.build(tmp_path/'old');original.run();original.close()
    before,_,_=f.build(tmp_path/'old',clock=original.clock)
    for session in before.sessions.values():
        if session.auth_done:session.fine_window=1  # Exact pre-fix cursor condition.
    with pytest.raises(AssertionError,match='offered fine windows'):before.run()
    before.close()
    correct,_,_=f.build(tmp_path/'fixed');correct.run();correct.close()
    after,_,_=f.build(tmp_path/'fixed',clock=correct.clock)
    result=after.run();after.close()
    assert result['fine_window_accounting_complete'] and result['certified_commits']==0

def test_snapshot_fsync_failure_does_not_change_active_book_or_start_models(tmp_path):
    a,_,events=f.build(tmp_path)
    def fail():raise OSError('CPU snapshot sync failure')
    a.input_journal._sync=fail
    with pytest.raises(OSError):a.run()
    assert all(b.accepted==0 for b in a.book.sessions.values())
    assert not any(e['kind'] in ['input-ack','enqueue','commit'] for e in events)
    a.close()

def test_stale_observation_is_fenced_without_killing_canonical_service(tmp_path):
    a,c,events=f.build(tmp_path)
    c.acks.append(ConsumerAck(99,a.t0-1,a.contract_digest,0,a.owner_epoch-1,0,0,0,a.clock()))
    result=a.run();a.close()
    assert result['fine_window_accounting_complete']
    assert any(e['kind']=='consumer-ack-fenced' for e in events)
    assert all(b.accepted==b.certified for b in a.book.sessions.values() if not b.rejected)
