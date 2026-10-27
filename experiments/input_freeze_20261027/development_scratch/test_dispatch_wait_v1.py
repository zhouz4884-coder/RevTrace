"""CPU timing/observation obligations; no GPU performance evidence."""
from types import SimpleNamespace as NS
import pytest
from revtrace.dispatch_wait import DispatchWaitController, POLICIES


def fixture(policy, **config):
    c = DispatchWaitController(dict(policy=policy, **config))
    s = NS(sid=0, done=False, fine_window=3, segment_start=1,
           branch_chunk=2, branch_tokens=(20,), audio=b'\0'*80,
           state=NS(checkpoint_id=1, audio_frontier_window=4,
                    prompt_tokens=(10,), contract_epoch=1))
    a = NS(name='a', execution_phase='model-executing')
    j = dict(job_id='a0', session_id=0, role='authority', parent=1,
             contract_epoch=1, contract_digest='contract',
             enqueue_perf=4.8, audio_end_sample=8, end_window=2)
    scheduler = NS(now=6., fine=2., sample_rate=2, sessions={0:s},
                   contract={'microbatch':16}, contract_digest='contract',
                   jobs={'a0':j}, inflight={'a':(a,['a0'])}, events=[])
    scheduler.clock = lambda: scheduler.now
    scheduler._end_seconds = lambda s,w: w*2.
    scheduler._ready_time = lambda s,w: w*2.
    scheduler._event = lambda kind, **fields: scheduler.events.append(dict(kind=kind, **fields))
    return c, scheduler, s


@pytest.mark.parametrize('policy', POLICIES)
def test_original_deadline_and_bounded_release(policy):
    c, q, s = fixture(policy)
    c.filter_candidates(q,[s])
    w = c.waits[0,3]
    assert w.audio_ready == 6 and w.deadline == 8
    assert w.until <= 6.75
    q.now=8.
    assert c.filter_candidates(q,[s]) == [s]
    assert w.deadline == 8
    assert q.jobs['a0']['parent'] == 1


def test_no_job_created_until_caller_releases_and_builds():
    c,q,s=fixture('state_aware')
    before=dict(q.jobs)
    assert c.filter_candidates(q,[s]) == []
    assert q.jobs == before and s.state.checkpoint_id == 1


def test_parent_update_releases_without_renewing_or_mutating_old_job():
    c,q,s=fixture('pending_eta')
    assert c.filter_candidates(q,[s]) == []
    opened=c.waits[0,3].opened
    q.now=6.1;s.state.checkpoint_id=2;s.state.audio_frontier_window=8;s.state.prompt_tokens=(30,)
    assert c.filter_candidates(q,[s]) == [s]
    q.now=6.2
    assert c.filter_candidates(q,[s]) == [s]
    assert c.waits[0,3].opened==opened and q.jobs['a0']['parent']==1


def test_other_session_keeps_progress_and_input_order():
    c,q,s=fixture('pending_eta')
    other=NS(**vars(s));other.sid=1
    q.sessions[1]=other
    assert c.filter_candidates(q,[s,other]) == [other]


def test_future_audio_is_not_marked_ready_by_filter():
    c,q,s=fixture('immediate')
    # Real _ready supplies an empty set before release; the controller never
    # enumerates new candidate sessions or replaces its caller's gates.
    q.now=5.9
    assert c.filter_candidates(q,[]) == []
    assert not c.waits


@pytest.mark.parametrize('key,value', [('parent',0),('contract_epoch',0),
    ('contract_digest','other'),('session_id',9),('role','proposal')])
def test_wrong_pending_identity_is_not_a_wait_reason(key,value):
    c,q,s=fixture('pending_eta');q.jobs['a0'][key]=value
    assert c.filter_candidates(q,[s]) == [s]


def test_observed_future_and_fault_fields_are_not_consulted():
    class Forbidden(dict):
        def __getitem__(self,k):
            assert k not in ('source_id','fault_plan','result','predicted_future_output')
            return super().__getitem__(k)
        def get(self,k,*a):
            assert k not in ('source_id','fault_plan','result','predicted_future_output')
            return super().get(k,*a)
    c,q,s=fixture('state_aware');q.jobs['a0']=Forbidden(q.jobs['a0'])
    assert c.filter_candidates(q,[s]) == []


def test_state_signal_changes_only_timing_not_a_permission_predicate():
    plain,q,s=fixture('pending_eta')
    s.branch_tokens=s.state.prompt_tokens
    assert plain.filter_candidates(q,[s]) == []
    state=DispatchWaitController({'policy':'state_aware'})
    assert state.filter_candidates(q,[s]) == [s]
    assert q.jobs['a0']['parent']==s.state.checkpoint_id


def test_no_slack_releases_without_deadline_extension():
    c,q,s=fixture('pending_eta');q.now=7.7
    assert c.filter_candidates(q,[s]) == [s]
    assert c.waits[0,3].deadline==8.


def test_eta_error_does_not_extend_one_shot_hold():
    c,q,s=fixture('pending_eta')
    assert c.filter_candidates(q,[s])==[]
    until=c.waits[0,3].until
    for t in [6.1,6.2,6.5]:
        q.now=t;assert c.filter_candidates(q,[s])==[]
        assert c.waits[0,3].until==until
    q.now=until
    assert c.filter_candidates(q,[s])==[s]
    assert 'a' in q.inflight  # timing control never releases physical leases


def test_covered_or_retired_cursor_closes_without_creating_a_job():
    c,q,s=fixture('pending_eta');c.filter_candidates(q,[s])
    q.now=6.2;s.fine_window=4;s.state.audio_frontier_window=12
    assert c.filter_candidates(q,[])==[]
    assert c.waits[0,3].closed and len(q.jobs)==1
    assert q.events[-1]['target_now_covered']


def test_completed_history_uses_actual_past_receipt_and_batch_support():
    c,q,s=fixture('pending_eta')
    c.observe_event(dict(kind='enqueue',job_id='old',role='authority',time=1.))
    c.observe_event(dict(kind='batch-dispatched',job_ids=['old','another']))
    e=dict(kind='executor-complete',job_id='old',role='authority',enqueue=1.,received=1.4)
    c.observe_event(e);c.observe_event(e)
    value,n,exact=c._cost('authority',2)
    assert value==pytest.approx(.4) and n==1 and exact
    assert c._cost('authority',16)[2] is False


def test_recent_adaptation_explicitly_uses_refresh_proxy():
    c,q,s=fixture('recent_gain')
    initial=c.recent_wait;c.filter_candidates(q,[s])
    q.now=6.1;s.state.checkpoint_id=2;s.state.prompt_tokens=(30,)
    c.filter_candidates(q,[s])
    assert c.recent_wait > initial
    assert q.events[-1]['recent_feedback_proxy']=='canonical-refresh-or-covered-target'


@pytest.mark.parametrize('cfg',[{'policy':'other'},{'max_wait_seconds':-1},
    {'fixed_wait_seconds':float('nan')},{'display_slo_seconds':0},
    {'service_quantile':1.1},{'history_size':0},{'unexpected_future_feature':1}])
def test_invalid_or_unfrozen_config_rejected(cfg):
    with pytest.raises(ValueError):DispatchWaitController(cfg)
