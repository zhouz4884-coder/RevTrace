"""Actual scheduler CPU interleavings; these are not GPU measurements."""
import pytest
from test_live_qwen import build
from revtrace.live_qwen import LiveQwenScheduler


def run_policy(policy):
    old=build(rho=1,delay=.025,barrier='decoupled',count=2)
    config=dict(old.contract,proposal_reconciliation='lazy',dispatch_wait={
        'policy':policy,'max_wait_seconds':.012,'fixed_wait_seconds':.006,
        'private_cost_default_seconds':.001,'authority_cost_default_seconds':.025,
        'display_slo_seconds':.06,'poll_floor_seconds':.001,
        'initial_recent_wait_seconds':.006,'recent_step_seconds':.001})
    specs=[dict(session_id=s.sid,audio=s.audio,source_id=s.source_id,
                language=s.language,offset=s.offset) for s in old.sessions.values()]
    q=LiveQwenScheduler(sessions=specs,contract=config,executors=old.executors,
                        clock=old.clock,sleep=old.sleep,emit=lambda row:None)
    result=q.run()
    return q,result


@pytest.mark.parametrize('policy',['immediate','fixed','pending_eta','backpressure','recent_gain','state_aware'])
def test_closed_loop_never_reparents_frozen_jobs_or_skips_canonical_debt(policy):
    q,result=run_policy(policy)
    assert result['certified_commits']==12
    assert all(s.state.audio_frontier_window==960 for s in q.sessions.values())
    assert all(max(s.state.prompt_tokens)<999 for s in q.sessions.values())
    enqueues={e['job_id']:e for e in q.events if e['kind']=='enqueue'}
    for jid,j in q.jobs.items():
        assert j['parent']==enqueues[jid]['parent']
        assert j['audio_ready_perf']<=j['enqueue_perf']
    assert len(q.window_outcomes)==12
    for e in q.events:
        if e['kind']=='dispatch-wait-decision':
            assert e['wait_until_perf']<=e['original_deadline_perf']
            assert e['wait_budget_seconds']<=.012+1e-10


def test_actual_make_job_uses_current_parent_after_finite_wait():
    # This verifies input freezing after an active wait, not ETA accuracy.
    # The conditional predictor correctly refuses unsupported millisecond
    # tails under its production-scale cold-start installation fallback.
    q,_=run_policy('fixed')
    waits=[e for e in q.events if e['kind']=='dispatch-wait-decision' and e['decision']=='wait']
    assert waits,'fixture must activate the mechanism'
    releases=[e for e in q.events if e['kind']=='dispatch-wait-release']
    assert releases
    for e in releases:
        later=[j for j in q.jobs.values() if j['role']=='proposal' and j['session_id']==e['session_id']
               and j['end_window']==e['window'] and j['enqueue_perf']>=q.t0+e['time']-1e-8]
        if e['reason']=='canonical-advanced' and later:
            assert all(j['parent']>=e['current_parent'] for j in later)
    assert all(j['parent']==e['parent'] for j in q.jobs.values()
               for e in q.events if e['kind']=='enqueue' and e['job_id']==j['job_id'])
