"""CPU-only fixtures for immutable prior-cost bootstrap, not GPU evidence."""
import hashlib,json
import pytest
from revtrace.dispatch_wait import DispatchWaitController


def fixture(tmp_path):
    bank=dict(schema='dispatch-wait-prior-observations-v1',source_policy='immediate',
        source_status='COMPLETE_DEVELOPMENT_PILOT',source_commit='a'*40,
        source_cell='CPU-FIXTURE',inputs=[dict(path='fixture',sha256='b'*64)],samples=[
        dict(phase='receipt',role='authority',row_id='a0',batch_id='batch0',physical_batch_rows=1,
             started_perf=1.,completed_perf=2.,duration_seconds=1.),
        dict(phase='installation',role='authority',row_id='a0',batch_id='batch0',physical_batch_rows=1,
             started_perf=2.,completed_perf=2.2,duration_seconds=.2)])
    path=tmp_path/'bank.json';path.write_text(json.dumps(bank),encoding='utf8')
    return path,hashlib.sha256(path.read_bytes()).hexdigest(),bank


def test_load_frozen_completed_bank_without_marking_current_jobs_completed(tmp_path):
    p,sha,_=fixture(tmp_path);c=DispatchWaitController()
    report=c.load_prior_history(p,sha)
    assert list(c.history['authority',1])==[1.]
    assert list(c.install_history[1])==pytest.approx([.2])
    assert not c._completed_jobs and not c._authority_receipts
    assert report['row_observations_are_not_independent_batches']
    c.observe_event(dict(kind='executor-complete',role='authority',job_id='a0',enqueue=10.,received=12.))
    assert 'a0' in c._completed_jobs  # identical current job ID is not suppressed


def test_wrong_hash_fails_before_history_mutation(tmp_path):
    p,sha,_=fixture(tmp_path);c=DispatchWaitController()
    with pytest.raises(ValueError,match='hash'):c.load_prior_history(p,'0'*64)
    assert not c.history and not c.install_history


def test_later_bad_row_leaves_both_histories_empty(tmp_path):
    p,sha,b=fixture(tmp_path);b['samples'][1]['role']='proposal';p.write_text(json.dumps(b),encoding='utf8')
    c=DispatchWaitController()
    with pytest.raises(ValueError):c.load_prior_history(p,hashlib.sha256(p.read_bytes()).hexdigest())
    assert not c.history and not c.install_history


def test_duplicate_bootstrap_and_late_bootstrap_fail(tmp_path):
    p,sha,b=fixture(tmp_path);c=DispatchWaitController();c.load_prior_history(p,sha)
    with pytest.raises(ValueError):c.load_prior_history(p,sha)
    fresh=DispatchWaitController();fresh.observe_event(dict(kind='executor-complete',role='authority',job_id='new',enqueue=0.,received=1.))
    with pytest.raises(ValueError):fresh.load_prior_history(p,sha)


def test_duplicate_row_sample_not_counted_as_new_evidence(tmp_path):
    p,sha,b=fixture(tmp_path);b['samples'].append(dict(b['samples'][0]));p.write_text(json.dumps(b),encoding='utf8')
    c=DispatchWaitController()
    with pytest.raises(ValueError,match='duplicate'):c.load_prior_history(p,hashlib.sha256(p.read_bytes()).hexdigest())
