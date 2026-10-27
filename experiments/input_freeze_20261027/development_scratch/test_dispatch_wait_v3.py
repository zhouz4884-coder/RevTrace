"""CPU timing/observation obligations; no GPU performance evidence."""
from types import SimpleNamespace as NS
import pytest
from revtrace.dispatch_wait import DispatchWaitController, POLICIES


def fixture(policy, **config):
    c = DispatchWaitController(dict(policy=policy, **config))
    s = NS(sid=0, done=False, fine_window=3, segment_start=1,
           branch_chunk=2, branch_tokens=(20,), audio=b'\0'*80,
           branch_parent=1,branch_root_frontier=4,state_available_perf=4.,
           state=NS(checkpoint_id=1, audio_frontier_window=4,
                    prompt_tokens=(10,), contract_epoch=1))
    a = NS(name='a', execution_phase='model-executing')
    j = dict(job_id='a0', session_id=0, role='authority', parent=1,
             contract_epoch=1, contract_digest='contract',
             enqueue_perf=4.8, audio_end_sample=8, end_window=2)
    scheduler = NS(now=6., fine=2., sample_rate=2, sessions={0:s},
                   t0=0.,executors={'proposal':[NS(name='p')]},
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


def test_raw_slack_preserves_deadline_but_does_not_promise_output_deadline():
    c,q,s=fixture('fixed', deadline_reserve='raw_slack');q.now=7.7
    assert c.filter_candidates(q,[s])==[]
    w=c.waits[0,3];assert w.until<=8 and w.deadline==8
    e=next(e for e in q.events if e['kind']=='dispatch-wait-decision')
    assert e['reserved_generation_seconds']==0 and not e['output_deadline_guaranteed']
    q.now=8
    assert c.filter_candidates(q,[s])==[s]


@pytest.mark.parametrize('policy', ['fixed','pending_eta','backpressure','recent_gain','state_aware'])
def test_reserve_mode_is_shared_by_all_wait_baselines(policy):
    conservative,q,s=fixture(policy, private_cost_default_seconds=1.9,
                              initial_recent_wait_seconds=.7)
    raw=DispatchWaitController(dict(policy=policy, private_cost_default_seconds=1.9,
                              initial_recent_wait_seconds=.7,deadline_reserve='raw_slack'))
    conservative.filter_candidates(q,[s]);raw.filter_candidates(q,[s])
    assert conservative.waits[0,3].until<=6.1+1e-8
    assert raw.waits[0,3].until>conservative.waits[0,3].until
    assert raw.waits[0,3].deadline==conservative.waits[0,3].deadline==8


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
    assert next(e for e in q.events if e['kind']=='dispatch-wait-release')['target_now_covered']


def test_completed_history_uses_actual_past_receipt_and_batch_support():
    c,q,s=fixture('pending_eta')
    c.observe_event(dict(kind='enqueue',job_id='old',role='authority',time=1.))
    c.observe_event(dict(kind='batch-dispatched',job_ids=['old','another']))
    e=dict(kind='executor-complete',job_id='old',role='authority',enqueue=1.,received=1.4)
    c.observe_event(e);c.observe_event(e)
    value,n,exact=c._cost('authority',2)
    assert value==pytest.approx(.4) and n==1 and exact
    assert c._cost('authority',16)[2] is False


def test_recent_adaptation_requires_actual_consumer_and_service_not_refresh():
    c,q,s=fixture('recent_gain', initial_recent_wait_seconds=.6)
    initial=c.recent_wait;c.filter_candidates(q,[s])
    q.now=6.1;s.state.checkpoint_id=2;s.state.prompt_tokens=(30,)
    c.filter_candidates(q,[s])
    assert c.recent_wait == initial
    c.observe_event(dict(kind='enqueue',role='proposal',session_id=0,end_window=3,
        job_id='p0',enqueue_perf=6.1,declared_prompt_tokens=[30],chunk_id=2,
        audio_start_sample=8,audio_end_sample=12,parent=2))
    c.observe_event(dict(kind='executor-complete',job_id='p0',role='proposal',enqueue=6.1,received=6.6))
    q.now=6.7
    c.observe_consumer_ack(q,NS(session_id=0,owner_incarnation=0.,contract_digest='contract',
        canonical_epoch=1,observed_perf=6.65,valid_visible_frontier=12))
    c.tick(q)
    assert c.recent_wait > initial
    assert next(e for e in q.events if e['kind']=='dispatch-wait-feedback')['actual_D2_pass']


def test_late_actual_consumer_multiplicatively_reduces_wait_once():
    c,q,s=fixture('recent_gain',initial_recent_wait_seconds=.6)
    c.filter_candidates(q,[s]);q.now=6.8;c.tick(q)
    c.observe_event(dict(kind='enqueue',role='proposal',session_id=0,end_window=3,
        job_id='p0',enqueue_perf=6.8,declared_prompt_tokens=[20],chunk_id=2,
        audio_start_sample=4,audio_end_sample=12,parent=1))
    c.observe_event(dict(kind='executor-complete',job_id='p0',role='proposal',enqueue=6.8,received=8.2))
    q.now=8.4
    c.observe_consumer_ack(q,NS(session_id=0,owner_incarnation=0.,contract_digest='contract',
        canonical_epoch=1,observed_perf=8.3,valid_visible_frontier=12))
    c.tick(q);assert c.recent_wait==pytest.approx(.3)
    c.tick(q);assert c.recent_wait==pytest.approx(.3)


def test_no_consumer_output_is_unknown_not_success():
    c,q,s=fixture('recent_gain',initial_recent_wait_seconds=.6)
    initial=c.recent_wait;c.filter_candidates(q,[s]);q.now=10.;c.tick(q)
    assert c.recent_wait==initial and not c.waits[0,3].feedback_done
    assert not any(e['kind']=='dispatch-wait-feedback' for e in q.events)


def test_tick_closes_parent_advance_while_physical_worker_remains_busy():
    c,q,s=fixture('fixed');c.filter_candidates(q,[s])
    p=NS(name='p');q.inflight['p']=(p,['other-session-job'])
    q.now=6.1;s.state.checkpoint_id=2;s.state_available_perf=6.09
    c.tick(q)
    e=next(e for e in q.events if e['kind']=='dispatch-wait-release')
    assert e['policy_suppression_seconds']==pytest.approx(.09)
    assert e['owner_observation_lag_seconds']==pytest.approx(.01)
    assert not e['proposal_worker_available'] and 'p' in q.inflight


def test_pre_wait_input_description_matches_rebase_without_mutation():
    c,q,s=fixture('state_aware');s.branch_parent=0
    before=vars(s).copy()
    desc=c.describe_private_input(q,s,3)
    assert desc['would_rebase'] and desc['prompt_tokens']==[10] and desc['chunk_id']==1
    assert vars(s)==before
    c.filter_candidates(q,[s])
    e=next(e for e in q.events if e['kind']=='dispatch-wait-decision')
    assert not e['private_projection_differs'] and e['private_depth']==0


def test_recent_budget_smaller_than_eta_dispatches_without_pointless_hold():
    c,q,s=fixture('recent_gain', initial_recent_wait_seconds=.1)
    assert c.filter_candidates(q,[s])==[s]
    assert not c.waits[0,3].active


def test_fixed_pending_strong_baseline_does_not_delay_without_pending_job():
    c,q,s=fixture('fixed');q.inflight={}
    assert c.filter_candidates(q,[s])==[s]
    allready=DispatchWaitController(dict(policy='fixed', fixed_condition='all_ready'))
    assert allready.filter_candidates(q,[s])==[]


def test_pending_disappearance_releases_early_without_rearming():
    c,q,s=fixture('pending_eta');assert c.filter_candidates(q,[s])==[]
    q.now=6.05;q.inflight={}
    assert c.filter_candidates(q,[s])==[s]
    e=next(e for e in q.events if e['kind']=='dispatch-wait-release')
    assert e['reason']=='pending-job-no-longer-leased' and e['waited_seconds']<.1


def test_row_received_pending_install_survives_physical_drain():
    c,q,s=fixture('pending_eta');q.inflight={};s.auth_result={'job_id':'a0'}
    assert c.filter_candidates(q,[s])==[]
    pending=next(e for e in q.events if e['kind']=='dispatch-wait-decision')['pending_authority']
    assert pending['observed_phase']=='owner-result-pending-install'
    q.now=6.1
    assert c.filter_candidates(q,[s])==[]


def test_cohort_logs_all_candidates_and_holdouts_without_poll_flood():
    c,q,s=fixture('pending_eta');other=NS(**vars(s));other.sid=1;q.sessions[1]=other
    assert c.filter_candidates(q,[s,other])==[other]
    e=next(e for e in q.events if e['kind']=='dispatch-wait-cohort')
    assert e['eligible']==[dict(session_id=0,window=3),dict(session_id=1,window=3)]
    assert e['held']==[dict(session_id=0,window=3)]
    n=len(q.events)
    q.now=6.01;assert c.filter_candidates(q,[s,other])==[other]
    assert len(q.events)==n


@pytest.mark.parametrize('cfg',[{'policy':'other'},{'max_wait_seconds':-1},
    {'fixed_wait_seconds':float('nan')},{'display_slo_seconds':0},
    {'service_quantile':1.1},{'history_size':0},{'unexpected_future_feature':1}])
def test_invalid_or_unfrozen_config_rejected(cfg):
    with pytest.raises(ValueError):DispatchWaitController(cfg)
